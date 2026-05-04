from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.models.enums import GroupUserRole, MessageType
from app.services.bot_message_parser import BotMessageParserService


class _FakeGroupRepository:
    def __init__(self) -> None:
        self.updated_last_message = False

    async def UpdateLastMessageAtByTelegramGroupId(self, telegram_group_id: int, last_message_at: datetime):
        self.updated_last_message = True
        return 1


class _FakeGroupUserRepository:
    def __init__(self, group_user: SimpleNamespace | None) -> None:
        self._group_user = group_user
        self.saved_entity = None
        self.updated_profile = None
        self.updated_profile_extra = None
        self.updated_role = None

    async def FindByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int):
        return self._group_user

    async def Save(self, entity):
        entity.id = getattr(entity, "id", 2233) or 2233
        self.saved_entity = entity
        self._group_user = entity
        return entity

    async def FindById(self, group_user_id: int):
        if self._group_user is None:
            return None
        if getattr(self._group_user, "id", None) != group_user_id:
            return None
        return self._group_user

    async def UpdateProfileByGroupIdAndTelegramUserId(
        self,
        group_id: int,
        telegram_user_id: int,
        *,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        is_bot: bool,
        is_deactivated: bool,
        profile_updated_at: datetime,
        role=None,
    ):
        self.updated_profile = {
            "group_id": group_id,
            "telegram_user_id": telegram_user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_bot": is_bot,
            "is_deactivated": is_deactivated,
            "profile_updated_at": profile_updated_at,
            "role": role,
        }
        self.updated_role = role
        if self._group_user is not None:
            self._group_user.username = username
            self._group_user.first_name = first_name
            self._group_user.last_name = last_name
            self._group_user.language_code = language_code
            self._group_user.is_bot = is_bot
            self._group_user.is_deactivated = is_deactivated
            self._group_user.profile_updated_at = profile_updated_at
        return 1

    async def UpdateProfileExtraByGroupIdAndTelegramUserId(
        self,
        group_id: int,
        telegram_user_id: int,
        *,
        profile_extra,
        profile_updated_at: datetime,
    ):
        self.updated_profile_extra = {
            "group_id": group_id,
            "telegram_user_id": telegram_user_id,
            "profile_extra": profile_extra,
            "profile_updated_at": profile_updated_at,
        }
        if self._group_user is not None:
            self._group_user.profile_extra = profile_extra
            self._group_user.profile_updated_at = profile_updated_at
        return 1


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


class _FakeGroupAutoRegisterService:
    def __init__(self, group: SimpleNamespace) -> None:
        self._group = group
        self.calls = 0

    async def EnsureGroupRegisteredByChat(self, chat):
        self.calls += 1
        return self._group


class BotMessageParserTests(unittest.IsolatedAsyncioTestCase):
    """验证消息解析与最小落库骨架。"""

    async def test_parse_and_save_skips_when_group_not_registered(self) -> None:
        group_repo = _FakeGroupRepository()
        auto_register_service = _FakeGroupAutoRegisterService(
            group=SimpleNamespace(id=11, telegram_group_id=-1001, is_authorized=False)
        )
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=_FakeGroupUserRepository(group_user=None),
            group_message_repository=_FakeGroupMessageRepository(),
            group_auto_register_service=auto_register_service,
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

        with patch(
            "app.services.bot_message_parser.get_group_access_cache",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.services.bot_message_parser.get_group_user_cache",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_found",
            new=AsyncMock(),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_missing",
            new=AsyncMock(),
        ):
            context = await service.ParseAndSave(message)

        self.assertTrue(context.should_skip)
        self.assertEqual(context.skip_reason, "group_not_authorized")
        self.assertEqual(auto_register_service.calls, 1)
        self.assertFalse(group_repo.updated_last_message)

    async def test_parse_and_save_saves_new_group_text_message(self) -> None:
        group_repo = _FakeGroupRepository()
        msg_repo = _FakeGroupMessageRepository()
        auto_register_service = _FakeGroupAutoRegisterService(
            group=SimpleNamespace(id=11, telegram_group_id=-1002, is_authorized=True)
        )
        group_user = SimpleNamespace(
            id=22,
            group_id=11,
            telegram_user_id=3003,
            status=SimpleNamespace(value="active"),
            profile_updated_at=datetime.now(timezone.utc),
        )
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=_FakeGroupUserRepository(group_user=group_user),
            group_message_repository=msg_repo,
            group_auto_register_service=auto_register_service,
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

        with patch(
            "app.services.bot_message_parser.get_group_access_cache",
            new=AsyncMock(return_value={"group_id": 11, "is_authorized": True}),
        ), patch(
            "app.services.bot_message_parser.get_group_user_cache",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_found",
            new=AsyncMock(),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_missing",
            new=AsyncMock(),
        ), patch(
            "app.services.bot_message_parser.try_acquire_group_user_profile_refresh_suppress",
            new=AsyncMock(return_value=False),
        ):
            context = await service.ParseAndSave(message)

        self.assertFalse(context.should_skip)
        self.assertEqual(context.message_type, MessageType.TEXT)
        self.assertEqual(context.persisted_message_id, 9527)
        self.assertIn("https://example.com", context.links)
        self.assertIn("@alice", context.mentions)
        self.assertTrue(group_repo.updated_last_message)
        self.assertIsNotNone(msg_repo.saved_entity)
        self.assertEqual(auto_register_service.calls, 0)

    async def test_update_match_result_by_message_id(self) -> None:
        msg_repo = _FakeGroupMessageRepository()
        service = BotMessageParserService(
            group_repository=_FakeGroupRepository(),
            group_user_repository=_FakeGroupUserRepository(group_user=None),
            group_message_repository=msg_repo,
            group_auto_register_service=_FakeGroupAutoRegisterService(
                group=SimpleNamespace(id=11, telegram_group_id=-1001, is_authorized=True)
            ),
        )

        affected = await service.UpdateMatchResultByMessageId(
            message_id=9527,
            hit_rule_code="kw_ad",
            risk_score=1.0,
        )
        self.assertEqual(affected, 1)
        self.assertEqual(msg_repo.updated_hit_result, (9527, "kw_ad", 1.0))

    async def test_parse_and_save_creates_group_user_when_not_exists(self) -> None:
        group_repo = _FakeGroupRepository()
        msg_repo = _FakeGroupMessageRepository()
        user_repo = _FakeGroupUserRepository(group_user=None)
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=user_repo,
            group_message_repository=msg_repo,
            group_auto_register_service=_FakeGroupAutoRegisterService(
                group=SimpleNamespace(id=11, telegram_group_id=-1001, is_authorized=True)
            ),
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1001, type="supergroup"),
            message_id=101,
            from_user=SimpleNamespace(
                id=9001,
                username="alice",
                first_name="Alice",
                last_name="Wonder",
                language_code="zh-hans",
                is_bot=False,
            ),
            text="hi",
            caption=None,
            photo=None,
            video=None,
            document=None,
            sticker=None,
            forward_origin=None,
            reply_to_message=None,
            date=datetime.now(timezone.utc),
            model_dump=lambda exclude_none=True: {"message_id": 101},
        )

        with patch(
            "app.services.bot_message_parser.get_group_access_cache",
            new=AsyncMock(return_value={"group_id": 11, "is_authorized": True}),
        ), patch(
            "app.services.bot_message_parser.get_group_user_cache",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_found",
            new=AsyncMock(),
        ), patch(
            "app.services.bot_message_parser.set_group_user_cache_missing",
            new=AsyncMock(),
        ):
            context = await service.ParseAndSave(message)

        self.assertFalse(context.should_skip)
        self.assertIsNotNone(context.sender_id)
        self.assertIsNotNone(user_repo.saved_entity)
        self.assertIsNotNone(user_repo.saved_entity.profile_updated_at)


    async def test_parse_and_save_admin_user_refreshes_role_to_admin(self) -> None:
        group_repo = _FakeGroupRepository()
        msg_repo = _FakeGroupMessageRepository()
        user_repo = _FakeGroupUserRepository(group_user=None)
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=user_repo,
            group_message_repository=msg_repo,
            group_auto_register_service=_FakeGroupAutoRegisterService(
                group=SimpleNamespace(id=11, telegram_group_id=-1003, is_authorized=True)
            ),
        )

        refreshed_user_repo = _FakeGroupUserRepository(
            group_user=SimpleNamespace(
                id=2233,
                group_id=11,
                telegram_user_id=9002,
                username='bob',
                first_name='Bob',
                last_name='Admin',
                language_code='en',
                is_bot=False,
                is_deactivated=False,
                profile_extra=None,
                status=SimpleNamespace(value='active'),
                profile_updated_at=datetime.now(timezone.utc),
            )
        )

        group_entity = SimpleNamespace(id=11, telegram_group_id=-1003)
        mock_bot = AsyncMock()
        mock_bot.get_chat_member = AsyncMock(return_value=SimpleNamespace(status='administrator'))
        mock_bot.get_chat = AsyncMock(return_value=SimpleNamespace(bio=None))

        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1003, type='supergroup'),
            message_id=103,
            from_user=SimpleNamespace(
                id=9002,
                username='bob',
                first_name='Bob',
                last_name='Admin',
                language_code='en',
                is_bot=False,
            ),
            bot=mock_bot,
            text='admin speaking',
            caption=None,
            photo=None,
            video=None,
            document=None,
            sticker=None,
            forward_origin=None,
            reply_to_message=None,
            date=datetime.now(timezone.utc),
            model_dump=lambda exclude_none=True: {'message_id': 103},
        )

        scheduled = []

        def _capture_create_task(coro):
            scheduled.append(coro)
            return SimpleNamespace(done=lambda: False)

        async def _fake_get_db_session():
            yield object()

        with patch(
            'app.services.bot_message_parser.get_group_access_cache',
            new=AsyncMock(return_value={'group_id': 11, 'is_authorized': True}),
        ), patch(
            'app.services.bot_message_parser.get_group_user_cache',
            new=AsyncMock(return_value=None),
        ), patch(
            'app.services.bot_message_parser.set_group_user_cache_found',
            new=AsyncMock(),
        ), patch(
            'app.services.bot_message_parser.set_group_user_cache_missing',
            new=AsyncMock(),
        ), patch(
            'app.services.bot_message_parser.try_acquire_group_user_profile_refresh_suppress',
            new=AsyncMock(return_value=True),
        ), patch(
            'app.services.bot_message_parser.asyncio.create_task',
            side_effect=_capture_create_task,
        ), patch(
            'app.services.bot_message_parser.get_db_session',
            new=_fake_get_db_session,
        ), patch(
            'app.services.bot_message_parser.GroupUserRepository',
            return_value=refreshed_user_repo,
        ), patch(
            'app.services.bot_message_parser.GroupRepository',
            return_value=SimpleNamespace(FindById=AsyncMock(return_value=group_entity)),
        ):
            context = await service.ParseAndSave(message)
            self.assertFalse(context.should_skip)
            self.assertEqual(user_repo.saved_entity.role, GroupUserRole.MEMBER)
            self.assertEqual(len(scheduled), 1)
            await scheduled[0]

        self.assertEqual(refreshed_user_repo.updated_role, GroupUserRole.ADMIN)
        mock_bot.get_chat_member.assert_called_once_with(-1003, 9002)


    async def test_parse_and_save_member_user_keeps_member_role(self) -> None:
        group_repo = _FakeGroupRepository()
        msg_repo = _FakeGroupMessageRepository()
        user_repo = _FakeGroupUserRepository(group_user=None)
        service = BotMessageParserService(
            group_repository=group_repo,
            group_user_repository=user_repo,
            group_message_repository=msg_repo,
            group_auto_register_service=_FakeGroupAutoRegisterService(
                group=SimpleNamespace(id=11, telegram_group_id=-1004, is_authorized=True)
            ),
        )

        refreshed_user_repo = _FakeGroupUserRepository(
            group_user=SimpleNamespace(
                id=2233,
                group_id=11,
                telegram_user_id=9003,
                username='tom',
                first_name='Tom',
                last_name='Member',
                language_code='en',
                is_bot=False,
                is_deactivated=False,
                profile_extra=None,
                status=SimpleNamespace(value='active'),
                profile_updated_at=datetime.now(timezone.utc),
            )
        )

        group_entity = SimpleNamespace(id=11, telegram_group_id=-1004)
        mock_bot = AsyncMock()
        mock_bot.get_chat_member = AsyncMock(return_value=SimpleNamespace(status='member'))
        mock_bot.get_chat = AsyncMock(return_value=SimpleNamespace(bio=None))

        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1004, type='supergroup'),
            message_id=104,
            from_user=SimpleNamespace(
                id=9003,
                username='tom',
                first_name='Tom',
                last_name='Member',
                language_code='en',
                is_bot=False,
            ),
            bot=mock_bot,
            text='normal member speaking',
            caption=None,
            photo=None,
            video=None,
            document=None,
            sticker=None,
            forward_origin=None,
            reply_to_message=None,
            date=datetime.now(timezone.utc),
            model_dump=lambda exclude_none=True: {'message_id': 104},
        )

        scheduled = []

        def _capture_create_task(coro):
            scheduled.append(coro)
            return SimpleNamespace(done=lambda: False)

        async def _fake_get_db_session():
            yield object()

        with patch(
            'app.services.bot_message_parser.get_group_access_cache',
            new=AsyncMock(return_value={'group_id': 11, 'is_authorized': True}),
        ), patch(
            'app.services.bot_message_parser.get_group_user_cache',
            new=AsyncMock(return_value=None),
        ), patch(
            'app.services.bot_message_parser.set_group_user_cache_found',
            new=AsyncMock(),
        ), patch(
            'app.services.bot_message_parser.set_group_user_cache_missing',
            new=AsyncMock(),
        ), patch(
            'app.services.bot_message_parser.try_acquire_group_user_profile_refresh_suppress',
            new=AsyncMock(return_value=True),
        ), patch(
            'app.services.bot_message_parser.asyncio.create_task',
            side_effect=_capture_create_task,
        ), patch(
            'app.services.bot_message_parser.get_db_session',
            new=_fake_get_db_session,
        ), patch(
            'app.services.bot_message_parser.GroupUserRepository',
            return_value=refreshed_user_repo,
        ), patch(
            'app.services.bot_message_parser.GroupRepository',
            return_value=SimpleNamespace(FindById=AsyncMock(return_value=group_entity)),
        ):
            context = await service.ParseAndSave(message)
            self.assertFalse(context.should_skip)
            self.assertEqual(user_repo.saved_entity.role, GroupUserRole.MEMBER)
            self.assertEqual(len(scheduled), 1)
            await scheduled[0]

        self.assertEqual(refreshed_user_repo.updated_role, GroupUserRole.MEMBER)
        self.assertNotEqual(refreshed_user_repo.updated_role, GroupUserRole.ADMIN)
        mock_bot.get_chat_member.assert_called_once_with(-1004, 9003)


if __name__ == "__main__":
    unittest.main()
