from __future__ import annotations

import unittest

from app.bot.handlers import execute_handler_safely
from app.bot.runner import run_bot
from app.bot.webhook import process_webhook_safely
from app.exceptions import ResourceNotFoundError


class BotExceptionFrameworkTests(unittest.IsolatedAsyncioTestCase):
    """验证 BOT 异常处理骨架的核心行为。"""

    async def test_execute_handler_safely_success(self) -> None:
        async def ok_handler() -> None:
            return None

        result = await execute_handler_safely("ok_handler", ok_handler)
        self.assertTrue(result.success)
        self.assertIsNone(result.error_code)

    async def test_execute_handler_safely_app_exception(self) -> None:
        async def app_error_handler() -> None:
            raise ResourceNotFoundError(resource="消息")

        result = await execute_handler_safely("app_error_handler", app_error_handler)
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "RESOURCE_NOT_FOUND")

    async def test_execute_handler_safely_unknown_exception(self) -> None:
        async def boom_handler() -> None:
            raise RuntimeError("boom")

        result = await execute_handler_safely("boom_handler", boom_handler)
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "BOT_PROCESSING_ERROR")

    async def test_process_webhook_safely_validation_failed(self) -> None:
        async def dummy_handler(payload: dict) -> None:
            return None

        status_code, payload = await process_webhook_safely(
            payload="not-dict",  # type: ignore[arg-type]
            handler=dummy_handler,
        )
        self.assertEqual(status_code, 422)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "REQUEST_VALIDATION_ERROR")

    async def test_process_webhook_safely_signature_failed(self) -> None:
        async def dummy_handler(payload: dict) -> None:
            return None

        status_code, payload = await process_webhook_safely(
            payload={"update_id": 1},
            handler=dummy_handler,
            validate_signature=lambda _: False,
        )
        self.assertEqual(status_code, 401)
        self.assertEqual(payload["error"]["code"], "UNAUTHORIZED")

    async def test_process_webhook_safely_unknown_exception(self) -> None:
        async def boom_handler(payload: dict) -> None:
            raise RuntimeError("boom")

        status_code, payload = await process_webhook_safely(
            payload={"update_id": 1},
            handler=boom_handler,
        )
        self.assertEqual(status_code, 500)
        self.assertEqual(payload["error"]["code"], "BOT_PROCESSING_ERROR")

    async def test_run_bot_wraps_unknown_exception(self) -> None:
        async def boom_loop() -> None:
            raise RuntimeError("boom")

        with self.assertRaises(Exception):
            await run_bot(boom_loop)


if __name__ == "__main__":
    unittest.main()
