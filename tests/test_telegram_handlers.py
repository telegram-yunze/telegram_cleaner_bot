from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.bot.telegram_handlers import (
    _should_auto_register_my_chat_member_status,
    _sync_group_from_my_chat_member,
)


class _FakeAutoRegisterService:
    def __init__(self) -> None:
        self.calls = 0

    async def EnsureGroupRegisteredByChat(self, chat):
        self.calls += 1
        return SimpleNamespace(id=11, telegram_group_id=int(chat.id), is_authorized=False)


async def _fake_get_db_session_once():
    """测试用 DB 依赖：只产出一次空 session。"""

    yield None


class TelegramHandlersTests(unittest.IsolatedAsyncioTestCase):
    """验证入群事件自动建档逻辑。"""

    def test_should_auto_register_status(self) -> None:
        self.assertTrue(_should_auto_register_my_chat_member_status("member"))
        self.assertTrue(_should_auto_register_my_chat_member_status("administrator"))
        self.assertFalse(_should_auto_register_my_chat_member_status("left"))

    async def test_sync_group_from_my_chat_member_registers_on_member_status(self) -> None:
        service = _FakeAutoRegisterService()
        update = SimpleNamespace(
            chat=SimpleNamespace(id=-10001),
            new_chat_member=SimpleNamespace(status="member"),
        )

        with patch("app.bot.telegram_handlers.get_db_session", return_value=_fake_get_db_session_once()):
            with patch("app.bot.telegram_handlers.get_group_auto_register_service", return_value=service):
                await _sync_group_from_my_chat_member(update)

        self.assertEqual(service.calls, 1)

    async def test_sync_group_from_my_chat_member_skips_on_left_status(self) -> None:
        service = _FakeAutoRegisterService()
        update = SimpleNamespace(
            chat=SimpleNamespace(id=-10001),
            new_chat_member=SimpleNamespace(status="left"),
        )

        with patch("app.bot.telegram_handlers.get_db_session", return_value=_fake_get_db_session_once()):
            with patch("app.bot.telegram_handlers.get_group_auto_register_service", return_value=service):
                await _sync_group_from_my_chat_member(update)

        self.assertEqual(service.calls, 0)


if __name__ == "__main__":
    unittest.main()
