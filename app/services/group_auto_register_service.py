from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from aiogram.types import Chat

from app.cache import set_group_access_cache
from app.models.enums import GroupChatType
from app.models.group import Group
from app.repositories.group_repository import GroupRepositoryProtocol


class GroupAutoRegisterServiceProtocol(Protocol):
    """群组自动建档服务接口。"""

    async def EnsureGroupRegisteredByChat(self, chat: Chat) -> Group: ...


class GroupAutoRegisterService(GroupAutoRegisterServiceProtocol):
    """群组自动建档服务，实现入群和消息兜底的幂等建档。"""

    def __init__(self, group_repository: GroupRepositoryProtocol) -> None:
        self._group_repository = group_repository

    async def EnsureGroupRegisteredByChat(self, chat: Chat) -> Group:
        """确保指定 chat 在数据库中存在群组记录。"""

        telegram_group_id = int(chat.id)
        existing = await self._group_repository.FindByTelegramGroupId(telegram_group_id)
        if existing is not None:
            await set_group_access_cache(
                telegram_group_id,
                group_id=existing.id,
                is_authorized=bool(existing.is_authorized),
            )
            return existing

        title = (chat.title or "").strip() or f"telegram_group_{telegram_group_id}"
        username = (chat.username or "").strip() or None
        description = (chat.description or "").strip() or None
        chat_type = self._resolve_chat_type(chat.type)

        entity = Group(
            telegram_group_id=telegram_group_id,
            title=title,
            username=username,
            description=description,
            chat_type=chat_type,
            owner_telegram_user_id=None,
            is_active=True,
            is_authorized=False,
            settings=None,
            bot_permissions=None,
            # 首次建档即视为完成一次信息同步，避免刚入库就被定时任务重复扫描。
            info_updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        saved = await self._group_repository.Save(entity)
        await set_group_access_cache(
            telegram_group_id,
            group_id=saved.id,
            is_authorized=bool(saved.is_authorized),
        )
        return saved

    def _resolve_chat_type(self, chat_type: str | None) -> GroupChatType:
        """把 Telegram chat.type 归一化为系统枚举。"""

        if chat_type == GroupChatType.GROUP.value:
            return GroupChatType.GROUP
        return GroupChatType.SUPERGROUP


__all__ = ["GroupAutoRegisterService", "GroupAutoRegisterServiceProtocol"]
