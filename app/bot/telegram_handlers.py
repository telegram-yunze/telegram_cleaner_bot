from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.handlers import execute_handler_safely
from app.config import get_settings
from app.db.session import get_db_session
from app.deps import (
    get_bot_message_parser_service,
    get_moderation_action_executor_service,
    get_rule_matcher_service,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _reply_start_message(message: Message) -> None:
    """处理 /start 指令，返回最小可用提示。"""

    await message.answer("机器人基础框架已就绪，功能正在逐步接入。")


async def _reply_default_message(message: Message) -> None:
    """处理普通消息：执行解析、落库、匹配与占位处置。"""

    async for session in get_db_session():
        settings = get_settings()
        parser_service = get_bot_message_parser_service(session)
        matcher_service = get_rule_matcher_service(session)
        executor_service = get_moderation_action_executor_service(
            session,
            dry_run=settings.telegram_action_dry_run,
        )

        context = await parser_service.ParseAndSave(message)
        if context.should_skip:
            logger.info("消息已跳过: reason=%s message_id=%s", context.skip_reason, context.telegram_message_id)
            return

        match_result = await matcher_service.MatchFirstRuleByMessageContext(context)
        if not match_result.hit:
            logger.info(
                "消息未命中规则: group_id=%s message_id=%s",
                context.group_id,
                context.telegram_message_id,
            )
            return

        await parser_service.UpdateMatchResultByMessageId(
            message_id=context.persisted_message_id,
            hit_rule_code=match_result.rule_code,
            risk_score=match_result.risk_score,
        )
        logger.info(
            "命中明细: rule_code=%s risk_score=%s detect_reason=%s",
            match_result.rule_code,
            match_result.risk_score,
            match_result.detect_reason,
        )

        execution_result = await executor_service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )
        logger.info(
            "占位处置已执行: record_id=%s status=%s success=%s",
            execution_result.moderation_record_id,
            execution_result.status.value,
            execution_result.success,
        )

        if match_result.action is not None:
            await message.answer(f"已命中规则 {match_result.rule_code}，动作 {match_result.action.value} 已进入处理流程。")
        return


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
