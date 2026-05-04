from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram.types import Message

from app.cache import (
    get_group_access_cache,
    get_group_user_cache,
    set_group_user_cache_found,
    set_group_user_cache_missing,
    try_acquire_group_user_profile_refresh_suppress,
)
from app.config import get_settings
from app.db.session import get_db_session
from app.models.enums import GroupUserRole, GroupUserStatus, MessageType
from app.models.group_message import GroupMessage
from app.models.group_user import GroupUser
from app.models.json_types import GroupUserProfileExtra, MessageContentExtra, TelegramRawPayload
from app.repositories.group_repository import (
    GroupRepository,
    GroupUserRepository,
    GroupMessageRepositoryProtocol,
    GroupRepositoryProtocol,
    GroupUserRepositoryProtocol,
)
from app.services.group_activity_tracker import enqueue_group_activity
from app.services.group_auto_register_service import GroupAutoRegisterServiceProtocol
from app.services.bot_flow_models import ParsedMessageContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
        settings = get_settings()
        self._group_user_cache_ttl_seconds = settings.group_user_cache_ttl_seconds
        self._group_user_missing_cache_ttl_seconds = settings.group_user_missing_cache_ttl_seconds
        self._group_user_profile_stale_timedelta = timedelta(days=settings.group_user_profile_stale_days)
        self._group_user_profile_refresh_suppress_seconds = (
            settings.group_user_profile_refresh_suppress_seconds
        )

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
        try:
            # 群活跃时间更新与消息主事务解耦，避免高并发下因死锁导致整笔消息回滚。
            await enqueue_group_activity(
                telegram_group_id=telegram_group_id,
                last_message_at=sent_at,
            )
        except Exception as exc:
            logger.warning(
                "群活跃触达入队失败，已降级不阻断主流程: telegram_group_id=%s message_id=%s error=%s",
                telegram_group_id,
                telegram_message_id,
                str(exc),
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
        cached_group_user = await get_group_user_cache(group_id, telegram_user_id)
        if cached_group_user is not None:
            if bool(cached_group_user.get("exists")):
                group_user_id = int(cached_group_user["group_user_id"])
                profile_updated_at = self._timestamp_to_utc_datetime(
                    cached_group_user.get("profile_updated_at_ts")
                )
                if self._is_profile_stale(profile_updated_at):
                    await self._schedule_group_user_profile_refresh(
                        group_id=group_id,
                        group_user_id=group_user_id,
                        telegram_user_id=telegram_user_id,
                        message=message,
                    )
                return group_user_id, telegram_user_id

            group_user = await self._create_group_user_from_message_sender(group_id=group_id, message=message)
            if group_user is None:
                return None, telegram_user_id
            if getattr(message, "bot", None) is not None:
                await self._schedule_group_user_profile_refresh(
                    group_id=group_id,
                    group_user_id=group_user.id,
                    telegram_user_id=telegram_user_id,
                    message=message,
                )
            return group_user.id, telegram_user_id

        group_user = await self._group_user_repository.FindByGroupIdAndTelegramUserId(group_id, telegram_user_id)
        if group_user is None:
            await set_group_user_cache_missing(
                group_id,
                telegram_user_id,
                ttl_seconds=self._group_user_missing_cache_ttl_seconds,
            )
            created_group_user = await self._create_group_user_from_message_sender(
                group_id=group_id,
                message=message,
            )
            if created_group_user is None:
                return None, telegram_user_id
            if getattr(message, "bot", None) is not None:
                await self._schedule_group_user_profile_refresh(
                    group_id=group_id,
                    group_user_id=created_group_user.id,
                    telegram_user_id=telegram_user_id,
                    message=message,
                )
            return created_group_user.id, telegram_user_id

        await self._cache_group_user_snapshot(group_user)
        if self._is_profile_stale(group_user.profile_updated_at):
            await self._schedule_group_user_profile_refresh(
                group_id=group_id,
                group_user_id=group_user.id,
                telegram_user_id=telegram_user_id,
                message=message,
            )
        return group_user.id, telegram_user_id

    async def _create_group_user_from_message_sender(
        self,
        *,
        group_id: int,
        message: Message,
    ) -> GroupUser | None:
        """根据消息发送者自动建档群成员，并把 profile_updated_at 初始化为当前时间。"""

        if message.from_user is None:
            return None

        now = self._now_utc_naive()
        username = self._normalize_optional_str(getattr(message.from_user, "username", None))
        first_name = self._normalize_optional_str(getattr(message.from_user, "first_name", None))
        last_name = self._normalize_optional_str(getattr(message.from_user, "last_name", None))
        language_code = self._normalize_optional_str(getattr(message.from_user, "language_code", None))
        is_bot = bool(getattr(message.from_user, "is_bot", False))
        is_deactivated = bool(getattr(message.from_user, "is_deleted", False))

        entity = GroupUser(
            group_id=group_id,
            telegram_user_id=int(message.from_user.id),
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            role=GroupUserRole.MEMBER,
            status=GroupUserStatus.ACTIVE,
            is_bot=is_bot,
            is_whitelisted=False,
            joined_at=None,
            left_at=None,
            profile_extra=GroupUserProfileExtra(),
            profile_updated_at=now,
            is_deactivated=is_deactivated,
            warn_count=0,
            muted_until=None,
            restriction_until=None,
            kicked_at=None,
            ban_reason=None,
        )
        saved = await self._group_user_repository.Save(entity)
        await self._cache_group_user_snapshot(saved)
        return saved

    async def _schedule_group_user_profile_refresh(
        self,
        *,
        group_id: int,
        group_user_id: int,
        telegram_user_id: int,
        message: Message,
    ) -> None:
        """按抑制窗口调度异步资料刷新，避免高频消息重复打库。"""

        allowed = await try_acquire_group_user_profile_refresh_suppress(
            group_id,
            telegram_user_id,
            suppress_ttl_seconds=self._group_user_profile_refresh_suppress_seconds,
        )
        if not allowed:
            return
        sender_snapshot = self._build_sender_snapshot(message)
        bot = getattr(message, "bot", None)
        asyncio.create_task(
            self._refresh_group_user_profile_async(
                group_id=group_id,
                group_user_id=group_user_id,
                telegram_user_id=telegram_user_id,
                sender_snapshot=sender_snapshot,
                bot=bot,
            )
        )

    async def _refresh_group_user_profile_async(
        self,
        *,
        group_id: int,
        group_user_id: int,
        telegram_user_id: int,
        sender_snapshot: dict[str, Any] | None,
        bot: Any,
    ) -> None:
        """异步刷新用户资料：先更新消息内字段，再尝试调用 Telegram API 补充资料。"""

        try:
            async for session in get_db_session():
                repository = GroupUserRepository(session)
                group_user = await repository.FindById(group_user_id)
                if group_user is None:
                    return

                now = self._now_utc_naive()
                role: GroupUserRole | None = None
                if bot is not None:
                    group_repository = GroupRepository(session)
                    group_entity = await group_repository.FindById(group_id)
                    if group_entity is not None:
                        try:
                            member = await bot.get_chat_member(group_entity.telegram_group_id, telegram_user_id)
                            role = self._map_chat_member_status_to_role(str(getattr(member, "status", "")))
                        except Exception as exc:
                            logger.warning(
                                "群成员角色查询失败，保持当前 role: group_id=%s user_id=%s error=%s",
                                group_id,
                                telegram_user_id,
                                str(exc),
                            )

                if sender_snapshot is not None:
                    await repository.UpdateProfileByGroupIdAndTelegramUserId(
                        group_id,
                        telegram_user_id,
                        username=self._normalize_optional_str(sender_snapshot.get("username")),
                        first_name=self._normalize_optional_str(sender_snapshot.get("first_name")),
                        last_name=self._normalize_optional_str(sender_snapshot.get("last_name")),
                        language_code=self._normalize_optional_str(sender_snapshot.get("language_code")),
                        is_bot=bool(sender_snapshot.get("is_bot", False)),
                        is_deactivated=bool(sender_snapshot.get("is_deactivated", False)),
                        profile_updated_at=now,
                        role=role,
                    )

                if bot is not None:
                    try:
                        chat = await bot.get_chat(telegram_user_id)
                        bio = self._normalize_optional_str(getattr(chat, "bio", None))
                        if bio is not None:
                            profile_extra = group_user.profile_extra or GroupUserProfileExtra()
                            profile_extra.bio = bio
                            await repository.UpdateProfileExtraByGroupIdAndTelegramUserId(
                                group_id,
                                telegram_user_id,
                                profile_extra=profile_extra,
                                profile_updated_at=now,
                            )
                    except Exception as exc:
                        logger.warning(
                            "群成员资料 API 补全失败，已保留基础字段刷新: group_id=%s user_id=%s error=%s",
                            group_id,
                            telegram_user_id,
                            str(exc),
                        )

                refreshed_group_user = await repository.FindById(group_user_id)
                if refreshed_group_user is not None:
                    await self._cache_group_user_snapshot(refreshed_group_user)
                return
        except Exception as exc:
            logger.warning(
                "异步刷新群成员资料失败: group_id=%s group_user_id=%s user_id=%s error=%s",
                group_id,
                group_user_id,
                telegram_user_id,
                str(exc),
            )

    def _map_chat_member_status_to_role(self, status: str) -> GroupUserRole | None:
        """把 Telegram 成员状态映射为系统群成员角色。"""

        if status == "creator":
            return GroupUserRole.OWNER
        if status == "administrator":
            return GroupUserRole.ADMIN
        if status == "member":
            return GroupUserRole.MEMBER
        if status == "restricted":
            return GroupUserRole.RESTRICTED
        return None

    def _build_sender_snapshot(self, message: Message) -> dict[str, Any] | None:
        """提取可跨任务传递的发送者快照，避免后台任务引用原始对象。"""

        if message.from_user is None:
            return None
        return {
            "username": getattr(message.from_user, "username", None),
            "first_name": getattr(message.from_user, "first_name", None),
            "last_name": getattr(message.from_user, "last_name", None),
            "language_code": getattr(message.from_user, "language_code", None),
            "is_bot": bool(getattr(message.from_user, "is_bot", False)),
            "is_deactivated": bool(getattr(message.from_user, "is_deleted", False)),
        }

    async def _cache_group_user_snapshot(self, group_user: GroupUser) -> None:
        """回填群成员快照缓存，减少后续消息重复查库。"""

        await set_group_user_cache_found(
            group_user.group_id,
            group_user.telegram_user_id,
            group_user_id=group_user.id,
            status=group_user.status.value if hasattr(group_user.status, "value") else str(group_user.status),
            profile_updated_at=group_user.profile_updated_at,
            ttl_seconds=self._group_user_cache_ttl_seconds,
        )

    def _is_profile_stale(self, profile_updated_at: datetime | None) -> bool:
        """判断资料是否过期：空值或超过配置阈值视为过期。"""

        if profile_updated_at is None:
            return True

        candidate = profile_updated_at
        if candidate.tzinfo is not None:
            candidate = candidate.astimezone(timezone.utc).replace(tzinfo=None)
        threshold = self._now_utc_naive() - self._group_user_profile_stale_timedelta
        return candidate <= threshold

    def _timestamp_to_utc_datetime(self, value: object) -> datetime | None:
        """把缓存中的秒级时间戳转换为 UTC 时间。"""

        if not isinstance(value, int):
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)

    def _now_utc_naive(self) -> datetime:
        """返回当前 UTC 时间（去除 tzinfo，兼容当前数据库字段类型）。"""

        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _normalize_optional_str(self, value: object) -> str | None:
        """把可选字符串标准化为空值或去首尾空白后的文本。"""

        if value is None:
            return None
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

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
