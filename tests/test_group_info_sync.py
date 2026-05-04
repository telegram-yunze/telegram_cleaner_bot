from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.tasks.group_info_sync import _sync_single_group_info


class _FakeGroupRepository:
    def __init__(self) -> None:
        self.last_kwargs = None

    async def UpdateGroupInfoById(self, group_id, title, username, description, info_updated_at, *, owner_telegram_user_id=None):
        self.last_kwargs = {
            "group_id": group_id,
            "title": title,
            "username": username,
            "description": description,
            "info_updated_at": info_updated_at,
            "owner_telegram_user_id": owner_telegram_user_id,
        }
        return 1


class _FakeBot:
    async def get_chat(self, telegram_group_id):
        return SimpleNamespace(title="测试群", username="test_group", description="desc")

    async def get_chat_administrators(self, telegram_group_id):
        return [
            SimpleNamespace(status="administrator", user=SimpleNamespace(id=2001)),
            SimpleNamespace(status="creator", user=SimpleNamespace(id=9001)),
        ]


class GroupInfoSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_single_group_info_updates_owner_telegram_user_id(self) -> None:
        repository = _FakeGroupRepository()
        bot = _FakeBot()

        await _sync_single_group_info(
            bot=bot,
            repository=repository,
            group_id=11,
            telegram_group_id=-10001,
        )

        self.assertIsNotNone(repository.last_kwargs)
        self.assertEqual(repository.last_kwargs["owner_telegram_user_id"], 9001)


if __name__ == "__main__":
    unittest.main()
