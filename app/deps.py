from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db_session
from app.repositories.group_repository import GroupMessageRepository, GroupRepository, GroupUserRepository
from app.repositories.moderation_repository import ModerationRepository
from app.repositories.rule_repository import RuleRepository
from app.services.bot_message_parser import BotMessageParserService
from app.services.group_service import GroupService
from app.services.moderation_action_executor import ModerationActionExecutorService
from app.services.moderation_service import ModerationService
from app.services.rule_matcher_service import RuleMatcherService
from app.services.rule_service import RuleService


async def get_db() -> AsyncIterator[AsyncSession]:
    """对外暴露数据库会话依赖。"""

    async for session in get_db_session():
        yield session


def get_group_service(session: AsyncSession) -> GroupService:
    """装配群组服务及其依赖仓库。"""

    rule_repository = RuleRepository(session)
    moderation_repository = ModerationRepository(session)
    return GroupService(
        group_repository=GroupRepository(session),
        group_user_repository=GroupUserRepository(session),
        group_message_repository=GroupMessageRepository(session),
        rule_repository=rule_repository,
        moderation_repository=moderation_repository,
    )


def get_rule_service(session: AsyncSession) -> RuleService:
    """装配规则服务及其依赖仓库。"""

    return RuleService(
        rule_repository=RuleRepository(session),
        moderation_repository=ModerationRepository(session),
    )


def get_moderation_service(session: AsyncSession) -> ModerationService:
    """装配审核记录服务及其依赖仓库。"""

    return ModerationService(
        moderation_repository=ModerationRepository(session),
        group_user_repository=GroupUserRepository(session),
        rule_repository=RuleRepository(session),
    )


def get_bot_message_parser_service(session: AsyncSession) -> BotMessageParserService:
    """装配 Bot 消息解析服务。"""

    return BotMessageParserService(
        group_repository=GroupRepository(session),
        group_user_repository=GroupUserRepository(session),
        group_message_repository=GroupMessageRepository(session),
    )


def get_rule_matcher_service(session: AsyncSession) -> RuleMatcherService:
    """装配规则匹配入口服务。"""

    return RuleMatcherService(rule_service=get_rule_service(session))


def get_moderation_action_executor_service(
    session: AsyncSession,
    *,
    dry_run: bool | None = None,
) -> ModerationActionExecutorService:
    """装配审核动作占位执行服务。"""

    resolved_dry_run = get_settings().telegram_action_dry_run if dry_run is None else dry_run

    return ModerationActionExecutorService(
        moderation_service=get_moderation_service(session),
        dry_run=resolved_dry_run,
    )


__all__ = [
    "get_db",
    "get_group_service",
    "get_rule_service",
    "get_moderation_service",
    "get_bot_message_parser_service",
    "get_rule_matcher_service",
    "get_moderation_action_executor_service",
]
