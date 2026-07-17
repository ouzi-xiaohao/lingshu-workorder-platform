from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.error_code import ErrorCode


class BusinessError(Exception):
    def __init__(self, message: str, code: ErrorCode = ErrorCode.CONFLICT, status_code: int = 409):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "trace_id": getattr(request.state, "trace_id", None)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": ErrorCode.VALIDATION_ERROR, "message": "请求参数校验失败", "detail": exc.errors(), "trace_id": getattr(request.state, "trace_id", None)},
        )
