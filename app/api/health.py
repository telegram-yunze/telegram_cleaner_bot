from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="健康检查",
    description="返回服务健康状态，用于网关探活和部署后快速联通性检查。",
    operation_id="health_check",
)
async def health_check() -> dict[str, str]:
    """返回应用存活状态。"""

    return {"status": "ok"}
