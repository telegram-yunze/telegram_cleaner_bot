from __future__ import annotations

import unittest

from app.bot.dispatcher import initialize_telegram_runtime, shutdown_telegram_runtime
from app.config import Settings


class TelegramRuntimeTests(unittest.IsolatedAsyncioTestCase):
    """验证 Telegram 运行时初始化策略。"""

    async def asyncTearDown(self) -> None:
        await shutdown_telegram_runtime()

    async def test_initialize_runtime_skips_when_token_missing(self) -> None:
        """当 token 为空时，应跳过机器人初始化。"""

        settings = Settings(
            telegram_bot_token="",
            telegram_run_mode="webhook",
        )
        runtime = await initialize_telegram_runtime(settings)
        self.assertFalse(runtime.is_enabled)


if __name__ == "__main__":
    unittest.main()
