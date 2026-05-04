from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def _api(path: str) -> str:
    """按配置拼接 API 路径，保证测试与 API_PREFIX 一致。"""

    prefix = get_settings().api_prefix
    if not prefix:
        return path
    return f"{prefix}{path}"


class WebhookAuthTests(unittest.TestCase):
    """验证 Telegram webhook 的签名鉴权行为。"""

    def test_webhook_without_secret_header_returns_401(self) -> None:
        """未携带 secret token 头时，应返回 401。"""

        with TestClient(app) as client:
            response = client.post(_api("/webhook/telegram"), json={"update_id": 1})

        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
