from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from src.common.logger import log_context_var, trace_id_var
from src.common.tracing import attach_trace_id


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid4().hex
        request.state.trace_id = trace_id
        trace_token = trace_id_var.set(trace_id)
        context_token = log_context_var.set({})
        try:
            response = await call_next(request)
            return await attach_trace_id(response, trace_id)
        finally:
            trace_id_var.reset(trace_token)
            log_context_var.reset(context_token)
