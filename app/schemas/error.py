from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """统一错误响应结构。"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "request_id": "af6a7f9b0b0d4cb6bd23e9a06e18a3f5",
                "timestamp": "2026-05-04T08:00:00Z",
                "path": "/api/rules",
                "detail": [{"loc": ["body", "code"], "msg": "Field required"}],
            }
        }
    )

    code: str = Field(description="业务错误码")
    message: str = Field(description="对外可读的错误说明")
    request_id: str = Field(description="请求追踪 ID")
    timestamp: datetime = Field(description="错误响应生成时间")
    path: str = Field(description="请求路径")
    detail: Any | None = Field(default=None, description="错误附加信息")

    @classmethod
    def build(
        cls,
        *,
        code: str,
        message: str,
        request_id: str,
        path: str,
        detail: Any | None = None,
    ) -> "ErrorResponse":
        """构建标准错误响应对象。"""

        return cls(
            code=code,
            message=message,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
            path=path,
            detail=detail,
        )


__all__ = ["ErrorResponse"]
