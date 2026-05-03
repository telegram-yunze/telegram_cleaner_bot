from __future__ import annotations

import re
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.deps import get_db
from app.exceptions import ResourceNotFoundError
from app.main import app

_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


async def _override_get_db():
    """测试阶段注入空会话，避免真实数据库连接。"""
    yield None


class _GroupServiceNotFound:
    """模拟群组不存在的 service，固定返回 None。"""

    async def FindById(self, group_id: int):
        return None


class RequestIdIntegrationTests(unittest.TestCase):
    """验证 X-Request-ID 在中间件与错误响应体中的透传行为。"""

    def setUp(self) -> None:
        # 注入空 DB 会话，防止测试触发真实数据库
        app.dependency_overrides[get_db] = _override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_response_header_has_auto_request_id(self) -> None:
        """未提供 X-Request-ID 时，响应头应自动生成 32 位 hex。"""
        with TestClient(app) as client:
            response = client.get("/health")

        request_id = response.headers.get("X-Request-ID")
        self.assertIsNotNone(request_id)
        self.assertRegex(request_id, _UUID_HEX_RE)

    def test_response_header_echoes_incoming_request_id(self) -> None:
        """提供 X-Request-ID 时，响应头应回写相同 ID。"""
        custom_id = "abc123def456789012345678901234ab"
        with TestClient(app) as client:
            response = client.get("/health", headers={"X-Request-ID": custom_id})

        self.assertEqual(response.headers.get("X-Request-ID"), custom_id)

    def test_error_body_request_id_matches_response_header(self) -> None:
        """404 错误响应体内的 request_id 与响应头应一致。"""
        custom_id = "deadbeefdeadbeefdeadbeefdeadbeef"
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get(
                    "/groups/99999999",
                    headers={"X-Request-ID": custom_id},
                )

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body.get("request_id"), custom_id)
        self.assertEqual(response.headers.get("X-Request-ID"), custom_id)

    def test_auto_request_id_consistent_in_body_and_header(self) -> None:
        """自动生成的 request_id 在响应体与响应头中应一致。"""
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get("/groups/99999999")

        self.assertEqual(response.status_code, 404)
        body_id = response.json().get("request_id")
        header_id = response.headers.get("X-Request-ID")
        self.assertIsNotNone(body_id)
        self.assertEqual(body_id, header_id)

    def test_error_body_has_all_required_fields(self) -> None:
        """404 错误响应体应包含 code/message/request_id/timestamp/path。"""
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get("/groups/99999999")

        body = response.json()
        for field in ("code", "message", "request_id", "timestamp", "path"):
            self.assertIn(field, body, msg=f"缺少字段: {field}")
        self.assertEqual(body["code"], "RESOURCE_NOT_FOUND")
        self.assertEqual(body["path"], "/groups/99999999")


if __name__ == "__main__":
    unittest.main()