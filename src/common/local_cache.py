from __future__ import annotations

from time import monotonic
from typing import Any


class LocalTTLCache:
    """Process-local L1 cache with TTL and a hard size cap."""

    def __init__(self, max_items: int = 2048):
        self._max_items = max_items
        self._data: dict[str, tuple[float, Any]] = {}

    def lookup(self, key: str) -> tuple[bool, Any]:
        item = self._data.get(key)
        if item is None:
            return False, None
        expires_at, value = item
        if expires_at < monotonic():
            self._data.pop(key, None)
            return False, None
        return True, value

    def get(self, key: str) -> Any | None:
        hit, value = self.lookup(key)
        return value if hit else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        if ttl <= 0:
            self._data.pop(key, None)
            return
        if len(self._data) >= self._max_items and key not in self._data:
            self._evict()
        self._data[key] = (monotonic() + ttl, value)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        for key in [item for item in self._data if item.startswith(prefix)]:
            self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def _evict(self) -> None:
        now = monotonic()
        expired = [key for key, (expires_at, _) in self._data.items() if expires_at < now]
        for key in expired:
            self._data.pop(key, None)
        if len(self._data) < self._max_items:
            return
        oldest = min(self._data, key=lambda item: self._data[item][0])
        self._data.pop(oldest, None)
