from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
import sys

from fastapi import FastAPI

# 兼容直接执行 `python app/main.py` 的场景：
# 脚本直跑时 Python 搜索路径会落在 app/ 目录，导致 `from app...` 导入失败。
# 这里将项目根目录注入 sys.path，保证绝对导入可用。
if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.api.router import api_router
from app.bot.dispatcher import (
    initialize_telegram_runtime,
    shutdown_telegram_runtime,
    start_polling_if_needed,
)
from app.cache import setup_cache, cache
from app.config import (
    get_runtime_api_secret_key,
    get_runtime_api_secret_source,
    get_settings,
)
from app.db.session import dispose_engine
from app.exception_handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.tasks.group_info_sync import run_group_info_sync_loop
from app.services.group_activity_tracker import get_group_activity_tracker
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
    {
        "name": "webhook",
        "description": "Telegram Webhook 回调接口，用于接收机器人更新事件。",
    },
]

logger = get_logger(__name__)
_group_info_sync_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """管理应用生命周期：启动时初始化缓存，关闭时释放缓存和数据库连接。"""

    global _group_info_sync_task

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

    settings = get_settings()
    await setup_cache()
    await get_group_activity_tracker().start()
    telegram_runtime = await initialize_telegram_runtime(settings)
    await start_polling_if_needed(settings, telegram_runtime)
    if telegram_runtime.bot is not None:
        _group_info_sync_task = asyncio.create_task(run_group_info_sync_loop(telegram_runtime.bot))
        logger.info("群组信息定时同步任务已挂载")
    try:
        yield
    finally:
        if _group_info_sync_task is not None and not _group_info_sync_task.done():
            _group_info_sync_task.cancel()
            try:
                await _group_info_sync_task
            except asyncio.CancelledError:
                logger.info("群组信息定时同步任务已停止")
        _group_info_sync_task = None

        await get_group_activity_tracker().stop()

        await shutdown_telegram_runtime()
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
        '- curl 示例：curl -H "X-API-Key: your_api_secret_key" '
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
app.include_router(api_router, prefix=get_settings().api_prefix)


@app.get(
    "/",
    summary="服务基础信息",
    description="返回服务名称与运行状态，可用于最基础联通性检查。",
    operation_id="get_service_root",
)
async def root() -> dict[str, str]:
    """返回应用根路径信息。"""

    return {"name": "telegram_cleaner_bot", "status": "ok"}
