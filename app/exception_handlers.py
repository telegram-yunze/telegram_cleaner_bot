from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppException, RequestValidationAppError
from app.schemas.error import ErrorResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


HTTP_ERROR_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "REQUEST_VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}


def _resolve_request_id(request: Request) -> str:
    """从请求上下文中提取 request_id，不存在时生成降级值。"""

    state_request_id = getattr(request.state, "request_id", None)
    if isinstance(state_request_id, str) and state_request_id:
        return state_request_id
    return uuid4().hex


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    detail: object | None,
) -> JSONResponse:
    """统一构建 JSON 错误响应。"""

    payload = ErrorResponse.build(
        code=code,
        message=message,
        request_id=_resolve_request_id(request),
        path=request.url.path,
        detail=detail,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "应用异常: code=%s status=%s path=%s message=%s",
            exc.code,
            exc.status_code,
            request.url.path,
            exc.message,
        )
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_ERROR_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
        message = str(exc.detail) if exc.detail else "请求处理失败"
        logger.warning(
            "HTTP 异常: code=%s status=%s path=%s message=%s",
            code,
            exc.status_code,
            request.url.path,
            message,
        )
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=message,
            detail={"http_detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
        validation_error = RequestValidationAppError(detail=exc.errors())
        logger.warning(
            "请求校验失败: path=%s errors=%s",
            request.url.path,
            exc.errors(),
        )
        return _error_response(
            request=request,
            status_code=validation_error.status_code,
            code=validation_error.code,
            message=validation_error.message,
            detail=validation_error.detail,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "未捕获异常: path=%s type=%s",
            request.url.path,
            type(exc).__name__,
        )
        return _error_response(
            request=request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="服务器内部错误",
            detail=None,
        )


__all__ = ["register_exception_handlers"]
