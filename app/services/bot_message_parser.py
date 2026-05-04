from __future__ import annotations

import re
from datetime import timezone

from aiogram.types import Message

from app.cache import get_group_access_cache
from app.models.enums import MessageType
from app.models.group_message import GroupMessage
from app.models.json_types import MessageContentExtra, TelegramRawPayload
from app.repositories.group_repository import (
    GroupMessageRepositoryProtocol,
    GroupRepositoryProtocol,
    GroupUserRepositoryProtocol,
)
from app.services.group_auto_register_service import GroupAutoRegisterServiceProtocol
from app.services.bot_flow_models import ParsedMessageContext


class BotMessageParserService:
    """消息解析服务：负责解析 Telegram 消息并执行最小落库。"""

    def __init__(
        self,
        group_repository: GroupRepositoryProtocol,
        group_user_repository: GroupUserRepositoryProtocol,
        group_message_repository: GroupMessageRepositoryProtocol,
        group_auto_register_service: GroupAutoRegisterServiceProtocol,
    ) -> None:
        self._group_repository = group_repository
        self._group_user_repository = group_user_repository
        self._group_message_repository = group_message_repository
        self._group_auto_register_service = group_auto_register_service

    async def ParseAndSave(self, message: Message) -> ParsedMessageContext:
        """解析并落库群消息；不满足处理条件时返回可短路上下文。"""

        if message.chat is None or message.chat.id is None:
            return self._skip_context(reason="missing_chat")

        if message.chat.type not in {"group", "supergroup"}:
            return self._skip_context(
                reason="not_group_chat",
                telegram_group_id=int(message.chat.id),
                telegram_message_id=message.message_id,
            )

        telegram_group_id = int(message.chat.id)
        access_profile = await get_group_access_cache(telegram_group_id)
        if access_profile is None:
            group = await self._group_auto_register_service.EnsureGroupRegisteredByChat(message.chat)
            access_profile = {
                "group_id": group.id,
                "is_authorized": bool(group.is_authorized),
            }

        group_id = int(access_profile["group_id"])
        if not bool(access_profile["is_authorized"]):
            return self._skip_context(
                reason="group_not_authorized",
                telegram_group_id=telegram_group_id,
                telegram_message_id=message.message_id,
                group_id=group_id,
            )

        telegram_message_id = int(message.message_id)
        existing = await self._group_message_repository.FindByGroupIdAndTelegramMessageId(
            group_id,
            telegram_message_id,
        )
        if existing is not None:
            return ParsedMessageContext(
                group_id=group_id,
                telegram_group_id=telegram_group_id,
                persisted_message_id=existing.id,
                sender_id=existing.sender_id,
                telegram_user_id=existing.telegram_user_id,
                telegram_message_id=telegram_message_id,
                message_type=existing.message_type,
                content_text=existing.content_text,
                mentions=existing.content_extra.mentions if existing.content_extra and existing.content_extra.mentions else [],
                links=existing.content_extra.links if existing.content_extra and existing.content_extra.links else [],
                should_skip=True,
                skip_reason="duplicate_message",
            )

        sender_id, telegram_user_id = await self._resolve_sender(group_id, message)
        message_type = self._resolve_message_type(message)
        content_text = (message.text or message.caption or "").strip() or None
        links = self._extract_links(content_text)
        mentions = self._extract_mentions(content_text)

        extra = MessageContentExtra(
            links=links or None,
            mentions=mentions or None,
            media_type=message_type.value if message_type is not MessageType.TEXT else None,
        )
        payload = TelegramRawPayload(
            update_id=None,
            message=message.model_dump(exclude_none=True),
            edited_message=None,
        )

        sent_at = message.date
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)

        entity = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            telegram_message_id=telegram_message_id,
            telegram_user_id=telegram_user_id,
            reply_to_message_id=(
                message.reply_to_message.message_id if message.reply_to_message is not None else None
            ),
            message_type=message_type,
            content_text=content_text,
            content_extra=extra,
            raw_payload=payload,
            sent_at=sent_at,
            risk_score=None,
            hit_rule_code=None,
            is_deleted=False,
            deleted_at=None,
        )
        saved = await self._group_message_repository.Save(entity)
        await self._group_repository.UpdateLastMessageAtByTelegramGroupId(
            telegram_group_id=telegram_group_id,
            last_message_at=sent_at,
        )

        return ParsedMessageContext(
            group_id=group_id,
            telegram_group_id=telegram_group_id,
            persisted_message_id=saved.id,
            sender_id=sender_id,
            telegram_user_id=telegram_user_id,
            telegram_message_id=telegram_message_id,
            message_type=message_type,
            content_text=content_text,
            mentions=mentions,
            links=links,
            should_skip=False,
            skip_reason=None,
        )

    async def UpdateMatchResultByMessageId(
        self,
        *,
        message_id: int | None,
        hit_rule_code: str | None,
        risk_score: float | None,
    ) -> int:
        """回写消息命中结果。"""

        if message_id is None:
            return 0
        return await self._group_message_repository.UpdateHitResultById(
            message_id=message_id,
            hit_rule_code=hit_rule_code,
            risk_score=risk_score,
        )

    async def _resolve_sender(self, group_id: int, message: Message) -> tuple[int | None, int | None]:
        """解析发送者并映射到群成员主键。"""

        if message.from_user is None:
            return None, None

        telegram_user_id = int(message.from_user.id)
        group_user = await self._group_user_repository.FindByGroupIdAndTelegramUserId(group_id, telegram_user_id)
        if group_user is None:
            return None, telegram_user_id
        return group_user.id, telegram_user_id

    def _resolve_message_type(self, message: Message) -> MessageType:
        """根据 Telegram message 内容推导消息类型。"""

        if message.text:
            return MessageType.TEXT
        if message.photo:
            return MessageType.PHOTO
        if message.video:
            return MessageType.VIDEO
        if message.document:
            return MessageType.DOCUMENT
        if message.sticker:
            return MessageType.STICKER
        if message.forward_origin is not None:
            return MessageType.FORWARDED
        return MessageType.OTHER

    def _extract_links(self, content_text: str | None) -> list[str]:
        """提取文本中的 URL 列表。"""

        if not content_text:
            return []
        return re.findall(r"https?://[^\s]+", content_text)

    def _extract_mentions(self, content_text: str | None) -> list[str]:
        """提取文本中的 @ 提及。"""

        if not content_text:
            return []
        return re.findall(r"@[A-Za-z0-9_]{3,32}", content_text)

    def _skip_context(
        self,
        *,
        reason: str,
        telegram_group_id: int | None = None,
        telegram_message_id: int | None = None,
        group_id: int | None = None,
    ) -> ParsedMessageContext:
        """构造短路上下文。"""

        return ParsedMessageContext(
            group_id=group_id,
            telegram_group_id=telegram_group_id,
            persisted_message_id=None,
            sender_id=None,
            telegram_user_id=None,
            telegram_message_id=telegram_message_id,
            message_type=MessageType.OTHER,
            content_text=None,
            mentions=[],
            links=[],
            should_skip=True,
            skip_reason=reason,
        )


__all__ = ["BotMessageParserService"]
