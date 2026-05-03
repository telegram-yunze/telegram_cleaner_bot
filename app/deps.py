from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.group_repository import GroupMessageRepository, GroupRepository, GroupUserRepository
from app.repositories.moderation_repository import ModerationRepository
from app.repositories.rule_repository import RuleRepository
from app.services.group_service import GroupService
from app.services.moderation_service import ModerationService
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


__all__ = [
    "get_db",
    "get_group_service",
    "get_rule_service",
    "get_moderation_service",
]
