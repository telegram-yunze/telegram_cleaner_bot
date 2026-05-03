from __future__ import annotations

from fastapi import APIRouter

from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.moderation import router as moderation_router
from app.api.rules import router as rules_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(groups_router)
api_router.include_router(rules_router)
api_router.include_router(moderation_router)

__all__ = ["api_router"]
