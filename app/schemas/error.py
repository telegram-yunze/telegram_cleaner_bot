from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """统一错误响应结构。"""

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
