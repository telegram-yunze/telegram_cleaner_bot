from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings
from app.db.session import dispose_engine
from app.exception_handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.utils.logger import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """管理应用生命周期，关闭时释放数据库连接。"""

    try:
        yield
    finally:
        await dispose_engine()


app = FastAPI(title="Telegram Cleaner Bot API", version="0.1.0", lifespan=lifespan)
configure_logging(get_settings().log_level)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/", summary="根路径")
async def root() -> dict[str, str]:
    """返回应用根路径信息。"""

    return {"name": "telegram_cleaner_bot", "status": "ok"}
