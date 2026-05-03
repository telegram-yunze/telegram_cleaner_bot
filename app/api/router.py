from __future__ import annotations

from fastapi import APIRouter

from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.moderation import router as moderation_router
from app.api.rules import router as rules_router
from app.schemas.error import ErrorResponse

# 各业务路由公共错误响应文档，注册到 OpenAPI schema，便于前端 AI 一致理解错误结构
_COMMON_RESPONSES: dict = {
    400: {"model": ErrorResponse, "description": "请求参数错误"},
    401: {"model": ErrorResponse, "description": "鉴权失败"},
    404: {"model": ErrorResponse, "description": "资源不存在"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败"},
    500: {"model": ErrorResponse, "description": "服务器内部错误"},
}

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(groups_router, responses=_COMMON_RESPONSES)
api_router.include_router(rules_router, responses=_COMMON_RESPONSES)
api_router.include_router(moderation_router, responses=_COMMON_RESPONSES)

__all__ = ["api_router"]
