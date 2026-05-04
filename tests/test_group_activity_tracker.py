from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import OperationalError

from app.services.group_activity_tracker import GroupActivityTracker


class GroupActivityTrackerTests(unittest.IsolatedAsyncioTestCase):
    """验证群活跃聚合刷新器的关键行为。"""

    async def test_enqueue_should_keep_max_timestamp_for_same_group(self) -> None:
        tracker = GroupActivityTracker()

        earlier = datetime(2026, 5, 4, 10, 0, 0, tzinfo=timezone.utc)
        later = datetime(2026, 5, 4, 10, 0, 2, tzinfo=timezone.utc)

        await tracker.enqueue(telegram_group_id=-1001, last_message_at=earlier)
        await tracker.enqueue(telegram_group_id=-1001, last_message_at=later)
        await tracker.enqueue(telegram_group_id=-1001, last_message_at=earlier)

        batch = await tracker._pop_batch()  # type: ignore[attr-defined]
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0][0], -1001)
        self.assertEqual(batch[0][1], later.replace(tzinfo=None))

    async def test_update_with_retry_should_retry_on_mysql_deadlock(self) -> None:
        tracker = GroupActivityTracker()

        deadlock_error = OperationalError(
            statement="UPDATE groups ...",
            params={},
            orig=Exception(1213, "Deadlock found when trying to get lock; try restarting transaction"),
        )

        fake_sessions = []

        class _FakeSession:
            def __init__(self) -> None:
                self.commit = AsyncMock()
                self.rollback = AsyncMock()
                self.close = AsyncMock()

        def _fake_session_factory_callable():
            session = _FakeSession()
            fake_sessions.append(session)
            return session

        class _FakeRepository:
            calls = 0

            def __init__(self, _session) -> None:
                self._session = _session

            async def UpdateLastMessageAtByTelegramGroupId(self, telegram_group_id: int, last_message_at: datetime) -> int:
                _FakeRepository.calls += 1
                if _FakeRepository.calls == 1:
                    raise deadlock_error
                return 1

        with patch(
            "app.services.group_activity_tracker.get_session_factory",
            return_value=_fake_session_factory_callable,
        ), patch(
            "app.services.group_activity_tracker.GroupRepository",
            new=_FakeRepository,
        ):
            ok, retries = await tracker._update_last_message_at_with_retry(  # type: ignore[attr-defined]
                telegram_group_id=-1001,
                last_message_at=datetime.now(timezone.utc),
            )

        self.assertTrue(ok)
        self.assertEqual(retries, 1)
        self.assertEqual(_FakeRepository.calls, 2)
        self.assertEqual(len(fake_sessions), 2)
        fake_sessions[0].rollback.assert_awaited_once()
        fake_sessions[1].commit.assert_awaited_once()

    async def test_flush_once_should_aggregate_multiple_groups(self) -> None:
        tracker = GroupActivityTracker()
        now = datetime.now(timezone.utc)

        await tracker.enqueue(telegram_group_id=-1001, last_message_at=now)
        await tracker.enqueue(telegram_group_id=-1002, last_message_at=now)

        with patch.object(
            tracker,
            "_update_last_message_at_with_retry",
            new=AsyncMock(return_value=(True, 0)),
        ) as mock_update:
            result = await tracker.flush_once()

        self.assertEqual(result.attempted_groups, 2)
        self.assertEqual(result.success_groups, 2)
        self.assertEqual(result.failed_groups, 0)
        self.assertEqual(result.deadlock_retries, 0)
        self.assertEqual(mock_update.await_count, 2)

    async def test_flush_once_should_not_raise_when_update_failed(self) -> None:
        tracker = GroupActivityTracker()
        await tracker.enqueue(telegram_group_id=-1001, last_message_at=datetime.now(timezone.utc))

        with patch.object(
            tracker,
            "_update_last_message_at_with_retry",
            new=AsyncMock(return_value=(False, 2)),
        ):
            result = await tracker.flush_once()

        self.assertEqual(result.attempted_groups, 1)
        self.assertEqual(result.success_groups, 0)
        self.assertEqual(result.failed_groups, 1)
        self.assertEqual(result.deadlock_retries, 2)

    async def test_update_with_retry_should_return_false_when_non_deadlock_operational_error(self) -> None:
        tracker = GroupActivityTracker()

        non_deadlock_error = OperationalError(
            statement="UPDATE groups ...",
            params={},
            orig=Exception(1205, "Lock wait timeout exceeded; try restarting transaction"),
        )

        class _FakeSession:
            def __init__(self) -> None:
                self.commit = AsyncMock()
                self.rollback = AsyncMock()
                self.close = AsyncMock()

        fake_session = _FakeSession()

        class _FakeRepository:
            def __init__(self, _session) -> None:
                self._session = _session

            async def UpdateLastMessageAtByTelegramGroupId(self, telegram_group_id: int, last_message_at: datetime) -> int:
                raise non_deadlock_error

        with patch(
            "app.services.group_activity_tracker.get_session_factory",
            return_value=lambda: fake_session,
        ), patch(
            "app.services.group_activity_tracker.GroupRepository",
            new=_FakeRepository,
        ), patch(
            "app.services.group_activity_tracker.log_exception",
            new=lambda *args, **kwargs: None,
        ):
            ok, retries = await tracker._update_last_message_at_with_retry(  # type: ignore[attr-defined]
                telegram_group_id=-1001,
                last_message_at=datetime.now(timezone.utc),
            )

        self.assertFalse(ok)
        self.assertEqual(retries, 0)
        fake_session.rollback.assert_awaited_once()
        fake_session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
