from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.models.enums import MessageType
from app.services.bot_message_parser import BotMessageParserService


class _FakeGroupRepository:
    def __init__(self, group: SimpleNamespace | None) -> None:
        self._group = group
        self.updated_last_message = False

    async def FindByTelegramGroupId(self, telegram_group_id: int):
        return self._group

    async def UpdateLastMessageAtByTelegramGroupId(self, telegram_group_id: int, last_message_at: datetime):
        self.updated_last_message = True
        return 1


class _FakeGroupUserRepository:
    def __init__(self, group_user: SimpleNamespace | None) -> None:
        self._group_user = group_user

    async def FindByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int):
        return self._group_user


class _FakeGroupMessageRepository:
    def __init__(self, existing: SimpleNamespace | None = None) -> None:
        self._existing = existing
        self.saved_entity = None
        self.updated_hit_result = None

    async def FindByGroupIdAndTelegramMessageId(self, group_id: int, telegram_message_id: int):
        return self._existing

    async def Save(self, entity):
        entity.id = 9527
        self.saved_entity = entity
        return entity

    async def UpdateHitResultById(self, message_id: int, hit_rule_code: str | None, risk_score: float | None):
        self.updated_hit_result = (message_id, hit_rule_code, risk_score)
        return 1


class BotMessageParserTests(unittest.IsolatedAsyncioTestCase):
    """验证消息解析与最小落库骨架。"""

    async def test_parse_and_save_skips_when_group_not_registered(self) -> None:
        service = BotMessageParserService(
            group_repository=_FakeGroupRepository(group=None),
            group_user_repository=_FakeGroupUserRepository(group_user=None),
            group_message_repository=_FakeGroupMessageRepository(),
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1001, type="supergroup"),
            message_id=10,
            from_user=SimpleNamespace(id=2001),
            text="hello",
            caption=None,
            photo=None,
            video=None,
            document=None,
            sticker=None,
            forward_origin=None,
            reply_to_message=None,
            date=datetime.now(timezone.utc),
            model_dump=lambda exclude_none=True: {"message_id": 10},
        )

        context = await service.ParseAndSave(message)
        self.assertTrue(context.should_skip)
        self.assertEqual(context.skip_reason, "group_not_registered")

    async def test_parse_and_save_saves_new_group_text_message(self) -> None:
        group_repo = _FakeGroupRepository(group=SimpleNamespace(id=11))
        msg_repo = _FakeGroupMessageRepository()
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=_FakeGroupUserRepository(group_user=SimpleNamespace(id=22)),
            group_message_repository=msg_repo,
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1002, type="group"),
            message_id=99,
            from_user=SimpleNamespace(id=3003),
            text="访问 https://example.com 联系 @alice",
            caption=None,
            photo=None,
            video=None,
            document=None,
            sticker=None,
            forward_origin=None,
            reply_to_message=None,
            date=datetime.now(timezone.utc),
            model_dump=lambda exclude_none=True: {"message_id": 99},
        )

        context = await service.ParseAndSave(message)
        self.assertFalse(context.should_skip)
        self.assertEqual(context.message_type, MessageType.TEXT)
        self.assertEqual(context.persisted_message_id, 9527)
        self.assertIn("https://example.com", context.links)
        self.assertIn("@alice", context.mentions)
        self.assertTrue(group_repo.updated_last_message)
        self.assertIsNotNone(msg_repo.saved_entity)

    async def test_update_match_result_by_message_id(self) -> None:
        msg_repo = _FakeGroupMessageRepository()
        service = BotMessageParserService(
            group_repository=_FakeGroupRepository(group=SimpleNamespace(id=11)),
            group_user_repository=_FakeGroupUserRepository(group_user=None),
            group_message_repository=msg_repo,
        )

        affected = await service.UpdateMatchResultByMessageId(
            message_id=9527,
            hit_rule_code="kw_ad",
            risk_score=1.0,
        )
        self.assertEqual(affected, 1)
        self.assertEqual(msg_repo.updated_hit_result, (9527, "kw_ad", 1.0))


if __name__ == "__main__":
    unittest.main()
