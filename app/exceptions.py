from __future__ import annotations

from typing import Any


class AppException(Exception):
    """应用统一异常基类，承载错误码、状态码与附加细节。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        detail: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ResourceNotFoundError(AppException):
    """资源不存在异常。"""

    def __init__(self, *, resource: str, detail: Any | None = None) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource}不存在",
            status_code=404,
            detail=detail,
        )


class RequestValidationAppError(AppException):
    """请求参数校验失败异常。"""

    def __init__(self, *, detail: Any | None = None) -> None:
        super().__init__(
            code="REQUEST_VALIDATION_ERROR",
            message="请求参数校验失败",
            status_code=422,
            detail=detail,
        )


class UnauthorizedError(AppException):
    """鉴权失败异常。"""

    def __init__(self, *, message: str = "鉴权失败", detail: Any | None = None) -> None:
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
            detail=detail,
        )


class DatabaseOperationError(AppException):
    """数据库操作异常。"""

    def __init__(self, *, detail: Any | None = None) -> None:
        super().__init__(
            code="DATABASE_OPERATION_ERROR",
            message="数据库操作失败",
            status_code=500,
            detail=detail,
        )


class ExternalDependencyError(AppException):
    """外部依赖调用失败异常。"""

    def __init__(self, *, message: str = "外部服务调用失败", detail: Any | None = None) -> None:
        super().__init__(
            code="EXTERNAL_DEPENDENCY_ERROR",
            message=message,
            status_code=502,
            detail=detail,
        )


class BotProcessingError(AppException):
    """Bot 消息处理异常。"""

    def __init__(self, *, message: str = "Bot 消息处理失败", detail: Any | None = None) -> None:
        super().__init__(
            code="BOT_PROCESSING_ERROR",
            message=message,
            status_code=500,
            detail=detail,
        )


__all__ = [
    "AppException",
    "ResourceNotFoundError",
    "RequestValidationAppError",
    "UnauthorizedError",
    "DatabaseOperationError",
    "ExternalDependencyError",
    "BotProcessingError",
]
