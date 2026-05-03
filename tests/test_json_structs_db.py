from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import GroupChatType, MessageType, ModerationAction, ModerationStatus, RuleType
from app.models.group import Group
from app.models.group_message import GroupMessage
from app.models.group_user import GroupUser
from app.models.json_types import (
    BotPermissions,
    GroupSettings,
    GroupUserProfileExtra,
    MessageContentExtra,
    ModerationResultDetail,
    RuleOptions,
    TelegramRawPayload,
)
from app.models.moderation_record import ModerationRecord
from app.models.rule import Rule


def _build_test_engine() -> AsyncEngine:
    """创建共享内存 SQLite 引擎，避免磁盘文件锁定问题。"""

    return create_async_engine(
        "sqlite+aiosqlite:///file:test_json_structs_db?mode=memory&cache=shared&uri=true",
        future=True,
    )


class JsonStructDatabaseRoundtripTests(unittest.IsolatedAsyncioTestCase):
    """验证结构体字段在数据库层的真实落盘与回读。"""

    async def asyncSetUp(self) -> None:
        self.engine = _build_test_engine()
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_group_struct_fields_roundtrip(self) -> None:
        async with self.session_factory() as session:
            await self._insert_group(session)
            await session.commit()

            saved_group = await session.get(Group, 1)
            self.assertIsNotNone(saved_group)
            assert saved_group is not None
            self.assertIsInstance(saved_group.settings, GroupSettings)
            self.assertIsInstance(saved_group.bot_permissions, BotPermissions)
            assert saved_group.settings is not None
            assert saved_group.bot_permissions is not None
            self.assertTrue(saved_group.settings.ad_detection_enabled)
            self.assertTrue(saved_group.bot_permissions.can_delete_messages)

    async def test_all_struct_fields_roundtrip(self) -> None:
        async with self.session_factory() as session:
            await self._insert_group(session)
            await self._insert_rule(session)
            await self._insert_group_user(session)
            await self._insert_group_message(session)
            await self._insert_moderation_record(session)
            await session.commit()

            rule = (await session.execute(select(Rule).where(Rule.id == 1))).scalar_one()
            self.assertIsInstance(rule.options, RuleOptions)
            assert rule.options is not None
            self.assertAlmostEqual(rule.options.threshold or 0.0, 0.8)

            user = (await session.execute(select(GroupUser).where(GroupUser.id == 1))).scalar_one()
            self.assertIsInstance(user.profile_extra, GroupUserProfileExtra)
            assert user.profile_extra is not None
            self.assertEqual(user.profile_extra.region, "CN")

            message = (await session.execute(select(GroupMessage).where(GroupMessage.id == 1))).scalar_one()
            self.assertIsInstance(message.content_extra, MessageContentExtra)
            self.assertIsInstance(message.raw_payload, TelegramRawPayload)
            assert message.content_extra is not None
            assert message.raw_payload is not None
            self.assertEqual(message.content_extra.media_type, "photo")
            self.assertEqual(message.raw_payload.update_id, 100)

            moderation = (await session.execute(select(ModerationRecord).where(ModerationRecord.id == 1))).scalar_one()
            self.assertIsInstance(moderation.result_detail, ModerationResultDetail)
            assert moderation.result_detail is not None
            self.assertTrue(moderation.result_detail.success)

    @staticmethod
    async def _insert_group(session: AsyncSession) -> None:
        session.add(
            Group(
                id=1,
                telegram_group_id=10001,
                title="test-group",
                chat_type=GroupChatType.SUPERGROUP,
                settings=GroupSettings(ad_detection_enabled=True, auto_delete_enabled=True),
                bot_permissions=BotPermissions(can_delete_messages=True, can_restrict_members=True),
            )
        )

    @staticmethod
    async def _insert_rule(session: AsyncSession) -> None:
        session.add(
            Rule(
                id=1,
                group_id=1,
                code="spam_001",
                name="spam-rule",
                rule_type=RuleType.KEYWORD,
                action=ModerationAction.DELETE,
                options=RuleOptions(threshold=0.8, keywords=["spam", "promo"]),
            )
        )

    @staticmethod
    async def _insert_group_user(session: AsyncSession) -> None:
        session.add(
            GroupUser(
                id=1,
                group_id=1,
                telegram_user_id=20001,
                profile_extra=GroupUserProfileExtra(region="CN", tags=["new"]),
            )
        )

    @staticmethod
    async def _insert_group_message(session: AsyncSession) -> None:
        session.add(
            GroupMessage(
                id=1,
                group_id=1,
                sender_id=1,
                telegram_message_id=30001,
                message_type=MessageType.PHOTO,
                content_extra=MessageContentExtra(media_type="photo", links=["https://example.com"]),
                raw_payload=TelegramRawPayload(update_id=100, message={"message_id": 30001}),
                sent_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    async def _insert_moderation_record(session: AsyncSession) -> None:
        session.add(
            ModerationRecord(
                id=1,
                group_id=1,
                message_id=1,
                target_user_id=1,
                rule_id=1,
                action=ModerationAction.WARN,
                status=ModerationStatus.SUCCESS,
                result_detail=ModerationResultDetail(success=True, provider="telegram"),
            )
        )


if __name__ == "__main__":
    unittest.main()
