from __future__ import annotations

import inspect
import threading
from collections.abc import Awaitable, Callable
from enum import StrEnum
from time import monotonic
from typing import Any, TypeVar

from src.common.logger import logger
from src.common.tracing import extra


T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"依赖 {name} 熔断中，{retry_after:.1f}s 后可试探恢复")


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int | None = None,
        recovery_seconds: float | None = None,
        half_open_max_calls: int | None = None,
        clock: Callable[[], float] = monotonic,
    ):
        from src.core.config import settings

        self.name = name
        self.failure_threshold = failure_threshold if failure_threshold is not None else settings.circuit_failure_threshold
        self.recovery_seconds = recovery_seconds if recovery_seconds is not None else settings.circuit_recovery_seconds
        self.half_open_max_calls = half_open_max_calls if half_open_max_calls is not None else settings.circuit_half_open_max_calls
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0
        self._half_open_inflight = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._transition_locked()
            return self._state

    @property
    def retry_after(self) -> float:
        with self._lock:
            if self._state != CircuitState.OPEN:
                return 0.0
            return max(0.0, round(self.recovery_seconds - (self._clock() - self._opened_at), 2))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._transition_locked()
            retry_after = 0.0
            if self._state == CircuitState.OPEN:
                retry_after = max(0.0, round(self.recovery_seconds - (self._clock() - self._opened_at), 2))
            return {
                "name": self.name,
                "state": str(self._state),
                "failures": self._failures,
                "failure_threshold": self.failure_threshold,
                "retry_after_seconds": retry_after,
            }

    def reset(self) -> None:
        with self._lock:
            self._close_locked()

    def allow_request(self) -> bool:
        with self._lock:
            self._transition_locked()
            if self._state == CircuitState.OPEN:
                return False
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_inflight >= self.half_open_max_calls:
                    return False
                self._half_open_inflight += 1
            return True

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_inflight = max(0, self._half_open_inflight - 1)
                self._successes += 1
                if self._successes >= self.half_open_max_calls:
                    self._close_locked()
                    self._log("closed")
                return
            self._failures = 0

    def record_failure(self) -> None:
        opened = False
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_inflight = max(0, self._half_open_inflight - 1)
                self._open_locked()
                opened = True
            else:
                self._failures += 1
                if self._state == CircuitState.CLOSED and self._failures >= self.failure_threshold:
                    self._open_locked()
                    opened = True
        if opened:
            self._log("opened")

    def execute_sync(self, primary: Callable[[], T], fallback: Callable[[], T] | None = None) -> T:
        if not self.allow_request():
            self._log("rejected")
            return self._fallback_sync(fallback)
        try:
            result = primary()
        except Exception as exc:
            self.record_failure()
            self._log("failure", error=str(exc))
            if fallback is None:
                raise
            self._log("fallback")
            return fallback()
        self.record_success()
        return result

    async def execute(self, primary: Callable[[], Awaitable[T] | T], fallback: Callable[[], Awaitable[T] | T] | None = None) -> T:
        if not self.allow_request():
            self._log("rejected")
            return await self._fallback_async(fallback)
        try:
            result = primary()
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            self.record_failure()
            self._log("failure", error=str(exc))
            if fallback is None:
                raise
            self._log("fallback")
            result = fallback()
            if inspect.isawaitable(result):
                return await result
            return result
        self.record_success()
        return result

    def _fallback_sync(self, fallback: Callable[[], T] | None) -> T:
        if fallback is None:
            raise CircuitOpenError(self.name, self.retry_after)
        self._log("fallback")
        return fallback()

    async def _fallback_async(self, fallback: Callable[[], Awaitable[T] | T] | None) -> T:
        if fallback is None:
            raise CircuitOpenError(self.name, self.retry_after)
        self._log("fallback")
        result = fallback()
        if inspect.isawaitable(result):
            return await result
        return result

    def _transition_locked(self) -> None:
        if self._state == CircuitState.OPEN and self._clock() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            self._successes = 0
            self._half_open_inflight = 0

    def _open_locked(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._half_open_inflight = 0
        self._successes = 0

    def _close_locked(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0
        self._half_open_inflight = 0

    def _log(self, event: str, **values: Any) -> None:
        logger.warning(
            "circuit.%s",
            event,
            extra=extra(span=f"circuit.{event}", circuit=self.name, state=str(self._state), failures=self._failures, **values),
        )


_DEFAULT_CIRCUITS = ("minio", "redis", "ai-stt", "ai-vision", "ai-llm", "ai-llm-backup")


class CircuitRegistry:
    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        breaker = self._breakers.get(name)
        if breaker is None:
            breaker = CircuitBreaker(name)
            self._breakers[name] = breaker
        return breaker

    def snapshot(self) -> list[dict[str, Any]]:
        for name in _DEFAULT_CIRCUITS:
            self.get(name)
        return [breaker.snapshot() for breaker in self._breakers.values()]

    def reset(self) -> None:
        self._breakers.clear()


circuits = CircuitRegistry()
