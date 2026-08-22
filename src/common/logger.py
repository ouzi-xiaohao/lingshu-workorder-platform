import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone


trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
log_context_var: ContextVar[dict[str, object]] = ContextVar("log_context", default={})

_RESERVED_RECORD_FIELDS = {
    "name", "msg", "args", "created", "filename", "funcName", "levelname", "levelno",
    "lineno", "module", "msecs", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "exc_info", "exc_text", "thread", "threadName", "taskName", "message",
    "asctime", "trace_id",
}


class TraceContextFilter(logging.Filter):
    """Copy the current request trace onto the log record at emit time."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        for key, value in log_context_var.get().items():
            if key not in _RESERVED_RECORD_FIELDS:
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", trace_id_var.get()),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


_trace_filter = TraceContextFilter()
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
handler.addFilter(_trace_filter)
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

logger = logging.getLogger("lingshu")
logger.addFilter(_trace_filter)
