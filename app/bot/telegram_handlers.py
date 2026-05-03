from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.handlers import execute_handler_safely
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _reply_start_message(message: Message) -> None:
    """处理 /start 指令，返回最小可用提示。"""

    await message.answer("机器人基础框架已就绪，功能正在逐步接入。")


async def _reply_default_message(message: Message) -> None:
    """处理普通消息，当前阶段返回占位提示。"""

    await message.answer("收到消息，后续将接入具体治理逻辑。")


def build_telegram_router() -> Router:
    """构建 Telegram 路由并复用统一异常处理封装。"""

    router = Router(name="telegram_default")

    @router.message(CommandStart())
    async def handle_start(message: Message) -> None:
        """入口命令处理。"""

        result = await execute_handler_safely("handle_start", _reply_start_message, message)
        if not result.success:
            logger.warning(
                "Telegram /start 处理失败: code=%s message=%s",
                result.error_code,
                result.error_message,
            )

    @router.message()
    async def handle_default(message: Message) -> None:
        """默认消息处理。"""

        result = await execute_handler_safely("handle_default", _reply_default_message, message)
        if not result.success:
            logger.warning(
                "Telegram 默认消息处理失败: code=%s message=%s",
                result.error_code,
                result.error_message,
            )

    return router


__all__ = ["build_telegram_router"]
