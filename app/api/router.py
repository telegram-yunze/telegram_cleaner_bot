from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth import verify_api_key
from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.moderation import router as moderation_router
from app.api.rules import router as rules_router
from app.api.webhook import router as webhook_router
from app.schemas.error import ErrorResponse


_ERROR_EXAMPLE = {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "request_id": "c6f7f8c4a0c346f28fe5d4c0fcab0d72",
    "timestamp": "2026-05-04T08:00:00Z",
    "path": "/api/groups/999",
    "detail": None,
}

_UNAUTHORIZED_EXAMPLE = {
    "code": "UNAUTHORIZED",
    "message": "API 密钥无效",
    "request_id": "a29f13f9a8d24e6da3a6c4d9ce80f641",
    "timestamp": "2026-05-04T08:00:00Z",
    "path": "/groups/1",
    "detail": None,
}

# 各业务路由公共错误响应文档，注册到 OpenAPI schema，便于前端 AI 一致理解错误结构
_COMMON_RESPONSES: dict = {
    400: {
        "model": ErrorResponse,
        "description": "请求参数错误",
        "content": {"application/json": {"example": _ERROR_EXAMPLE}},
    },
    401: {
        "model": ErrorResponse,
        "description": "鉴权失败：缺失或无效的 X-API-Key 请求头",
        "content": {"application/json": {"example": _UNAUTHORIZED_EXAMPLE}},
    },
    404: {
        "model": ErrorResponse,
        "description": "资源不存在",
        "content": {"application/json": {"example": _ERROR_EXAMPLE}},
    },
    422: {
        "model": ErrorResponse,
        "description": "请求参数校验失败",
        "content": {"application/json": {"example": _ERROR_EXAMPLE}},
    },
    500: {
        "model": ErrorResponse,
        "description": "服务器内部错误",
        "content": {"application/json": {"example": _ERROR_EXAMPLE}},
    },
}

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(webhook_router)
api_router.include_router(
    groups_router,
    responses=_COMMON_RESPONSES,
    dependencies=[Depends(verify_api_key)],
)
api_router.include_router(
    rules_router,
    responses=_COMMON_RESPONSES,
    dependencies=[Depends(verify_api_key)],
)
api_router.include_router(
    moderation_router,
    responses=_COMMON_RESPONSES,
    dependencies=[Depends(verify_api_key)],
)

__all__ = ["api_router"]
