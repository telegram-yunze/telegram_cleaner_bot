from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch


class MainLifespanGroupActivityTests(unittest.IsolatedAsyncioTestCase):
    """验证应用生命周期对群活跃追踪器的启动与停止。"""

    async def test_lifespan_should_start_and_stop_group_activity_tracker(self) -> None:
        fake_tracker = type(
            "_FakeTracker",
            (),
            {
                "start": AsyncMock(),
                "stop": AsyncMock(),
            },
        )()

        with patch("app.main.get_group_activity_tracker", return_value=fake_tracker), patch(
            "app.main.setup_cache", new=AsyncMock()
        ), patch("app.main.initialize_telegram_runtime", new=AsyncMock(return_value=type("_R", (), {"bot": None})())), patch(
            "app.main.start_polling_if_needed", new=AsyncMock()
        ), patch("app.main.shutdown_telegram_runtime", new=AsyncMock()), patch(
            "app.main.dispose_engine", new=AsyncMock()
        ), patch("app.main.cache.close", new=AsyncMock()):
            from app.main import lifespan

            async with lifespan(None):
                pass

        fake_tracker.start.assert_awaited_once()
        fake_tracker.stop.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
