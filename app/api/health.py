from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="健康检查")
async def health_check() -> dict[str, str]:
    """返回应用存活状态。"""

    return {"status": "ok"}
