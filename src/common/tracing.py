from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.responses import Response

from src.common.logger import logger, log_context_var


def bind_log_context(**values: Any) -> None:
    current = dict(log_context_var.get())
    for key, value in values.items():
        if value is not None:
            current[key] = value
    log_context_var.set(current)


def extra(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


@asynccontextmanager
async def traced(span_name: str, **values: Any) -> AsyncIterator[None]:
    fields = extra(span=span_name, **values)
    started = perf_counter()
    logger.info("%s.start", span_name, extra=fields)
    try:
        yield
    except Exception as exc:
        logger.warning(
            "%s.error",
            span_name,
            extra=extra(**fields, duration_ms=_elapsed_ms(started), error=str(exc)),
        )
        raise
    else:
        logger.info("%s.end", span_name, extra=extra(**fields, duration_ms=_elapsed_ms(started)))


async def attach_trace_id(response: Response, trace_id: str) -> Response:
    headers = MutableHeaders(response.headers)
    headers["x-trace-id"] = trace_id
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.encode() if isinstance(chunk, str) else chunk)
    body = b"".join(chunks)
    content_type = headers.get("content-type", "")
    if "application/json" in content_type and body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and not payload.get("trace_id"):
            payload["trace_id"] = trace_id
            body = json.dumps(payload, ensure_ascii=False, default=str).encode()
            headers["content-length"] = str(len(body))
    return Response(
        content=body,
        status_code=response.status_code,
        headers=dict(headers),
        media_type=content_type.split(";")[0] or None,
        background=response.background,
    )


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)
