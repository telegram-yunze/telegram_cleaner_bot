from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.cache import setup_cache, cache
from app.config import (
    get_runtime_api_secret_key,
    get_runtime_api_secret_source,
    get_settings,
)
from app.db.session import dispose_engine
from app.exception_handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.utils.logger import configure_logging, get_logger


OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "健康检查接口，用于探活与部署后联通性校验。",
    },
    {
        "name": "groups",
        "description": "群组管理接口，负责群组信息的创建、查询、更新与删除。",
    },
    {
        "name": "rules",
        "description": "规则管理接口，负责风控规则的维护与检索。",
    },
    {
        "name": "moderation",
        "description": "处置记录接口，负责审核动作记录的创建、查询与状态更新。",
    },
]

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """管理应用生命周期：启动时初始化缓存，关闭时释放缓存和数据库连接。"""

    runtime_secret = get_runtime_api_secret_key()
    source = get_runtime_api_secret_source()
    secret_hint = (
        f"{runtime_secret[:4]}...{runtime_secret[-4:]}"
        if len(runtime_secret) >= 8
        else "长度不足，已隐藏"
    )
    logger.info(
        "API 密钥已就绪: source=%s hint=%s header=%s",
        source,
        secret_hint,
        "X-API-Key",
    )
    if source == "generated":
        logger.warning(
            "检测到 API_SECRET_KEY 为空，已为当前进程随机生成临时密钥: key=%s header=%s",
            runtime_secret,
            "X-API-Key",
        )

    await setup_cache()
    try:
        yield
    finally:
        await cache.close()
        await dispose_engine()


app = FastAPI(
    title="Telegram Cleaner Bot API",
    summary="Telegram 群组清理与审核管理 API",
    description=(
        "用于 Telegram 群组治理的后端 API。\n\n"
        "- 提供群组、规则、处置记录三类核心资源管理能力\n"
        "- 统一返回结构化错误体，便于前端与 AI 调用端稳定解析\n"
        "- 列表接口均采用 limit/offset 分页语义\n\n"
        "鉴权约定（前端调用必读）\n"
        "- 受保护路由：/groups、/rules、/moderation（必须带 X-API-Key）\n"
        "- 公开路由：/、/health（无需鉴权）\n"
        "- 请求头示例：X-API-Key: your_api_secret_key\n"
        "- curl 示例：curl -H \"X-API-Key: your_api_secret_key\" "
        "http://localhost:8000/groups?limit=10&offset=0\n"
        "- 鉴权失败：返回 401，错误码 UNAUTHORIZED。"
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
configure_logging(get_settings().log_level)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)
app.include_router(api_router)


@app.get(
    "/",
    summary="服务基础信息",
    description="返回服务名称与运行状态，可用于最基础联通性检查。",
    operation_id="get_service_root",
)
async def root() -> dict[str, str]:
    """返回应用根路径信息。"""

    return {"name": "telegram_cleaner_bot", "status": "ok"}
