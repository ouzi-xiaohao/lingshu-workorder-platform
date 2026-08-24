from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.common.logger import logger
from src.common.tracing import extra
from src.core.error_code import ErrorCode


class BusinessError(Exception):
    def __init__(self, message: str, code: ErrorCode = ErrorCode.CONFLICT, status_code: int = 409):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _trace_id(request: Request) -> str | None:
    return getattr(request.state, "trace_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        logger.info("business.error", extra=extra(span="business.error", http_status=exc.status_code, error_code=str(exc.code), detail=exc.message))
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "trace_id": _trace_id(request)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": ErrorCode.VALIDATION_ERROR, "message": "请求参数校验失败", "detail": exc.errors(), "trace_id": _trace_id(request)},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = {
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            429: ErrorCode.RATE_LIMITED,
            503: ErrorCode.INFRASTRUCTURE_UNAVAILABLE,
        }.get(exc.status_code, ErrorCode.CONFLICT)
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message, "trace_id": _trace_id(request)},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled.error", extra=extra(span="unhandled.error", error=str(exc)))
        return JSONResponse(
            status_code=500,
            content={"code": ErrorCode.INTERNAL_ERROR, "message": "服务器内部错误", "trace_id": _trace_id(request)},
        )
