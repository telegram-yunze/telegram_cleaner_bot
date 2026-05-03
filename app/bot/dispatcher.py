from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app.bot.runner import run_bot
from app.bot.telegram_handlers import build_telegram_router
from app.config import Settings
from app.exceptions import ExternalDependencyError
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


@dataclass(slots=True)
class TelegramRuntime:
    """封装 aiogram 运行时对象，便于在生命周期内统一管理。"""

    bot: Bot | None = None
    dispatcher: Dispatcher | None = None
    polling_task: asyncio.Task[None] | None = None

    @property
    def is_enabled(self) -> bool:
        """当前运行时是否可用。"""

        return self.bot is not None and self.dispatcher is not None


_RUNTIME = TelegramRuntime()


def get_telegram_runtime() -> TelegramRuntime:
    """获取全局 Telegram 运行时对象。"""

    return _RUNTIME


def _replace_runtime(runtime: TelegramRuntime) -> None:
    """替换全局运行时引用。"""

    global _RUNTIME
    _RUNTIME = runtime


async def initialize_telegram_runtime(settings: Settings) -> TelegramRuntime:
    """初始化 Bot/Dispatcher；未配置 token 时跳过初始化。"""

    if settings.telegram_run_mode == "disabled":
        logger.info("telegram_run_mode=disabled，已跳过机器人初始化")
        runtime = TelegramRuntime()
        _replace_runtime(runtime)
        return runtime

    token = settings.telegram_bot_token.strip()
    if not token:
        logger.warning("未配置 TELEGRAM_BOT_TOKEN，已跳过机器人初始化")
        runtime = TelegramRuntime()
        _replace_runtime(runtime)
        return runtime

    bot = Bot(token=token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_telegram_router())

    runtime = TelegramRuntime(bot=bot, dispatcher=dispatcher)
    _replace_runtime(runtime)
    logger.info("Telegram 运行时初始化完成: mode=%s", settings.telegram_run_mode)
    return runtime


async def start_polling_if_needed(settings: Settings, runtime: TelegramRuntime) -> None:
    """按配置启动轮询协程（可选）。"""

    if not runtime.is_enabled:
        return

    if settings.telegram_run_mode not in {"polling", "both"}:
        return

    assert runtime.dispatcher is not None
    assert runtime.bot is not None

    async def _polling_loop() -> None:
        await runtime.dispatcher.start_polling(
            runtime.bot,
            polling_timeout=settings.telegram_polling_timeout,
        )

    runtime.polling_task = asyncio.create_task(run_bot(_polling_loop))
    logger.info("Telegram polling 已启动: timeout=%s", settings.telegram_polling_timeout)


async def dispatch_telegram_update(payload: dict) -> None:
    """将 webhook payload 转换为 aiogram Update 并投递到 dispatcher。"""

    runtime = get_telegram_runtime()
    if not runtime.is_enabled:
        raise ExternalDependencyError(message="机器人未初始化，无法处理 webhook")

    assert runtime.dispatcher is not None
    assert runtime.bot is not None

    update = Update.model_validate(payload)
    await runtime.dispatcher.feed_update(runtime.bot, update)


async def shutdown_telegram_runtime() -> None:
    """关闭 polling 任务与 Bot session，避免资源泄露。"""

    runtime = get_telegram_runtime()

    polling_task = runtime.polling_task
    if polling_task is not None and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("Telegram polling 已取消")
        except Exception as exc:
            log_exception(logger, message="关闭 Telegram polling 失败", exc=exc)

    if runtime.bot is not None:
        await runtime.bot.session.close()

    _replace_runtime(TelegramRuntime())


__all__ = [
    "TelegramRuntime",
    "dispatch_telegram_update",
    "get_telegram_runtime",
    "initialize_telegram_runtime",
    "shutdown_telegram_runtime",
    "start_polling_if_needed",
]
