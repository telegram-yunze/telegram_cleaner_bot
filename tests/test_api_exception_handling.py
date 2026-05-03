from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.deps import get_db
from app.main import app


async def _override_get_db():
    """测试阶段注入空会话，路由中的 service 工厂会被 mock。"""

    yield None


class _GroupServiceNotFound:
    async def FindById(self, group_id: int):
        return None


class _GroupServiceBoom:
    async def FindById(self, group_id: int):
        raise RuntimeError("boom")


class ApiExceptionHandlingTests(unittest.TestCase):
    """覆盖 API 全局异常处理的关键路径。"""

    def setUp(self) -> None:
        app.dependency_overrides[get_db] = _override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_not_found_error_response_shape(self) -> None:
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get("/groups/10086")

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["code"], "RESOURCE_NOT_FOUND")
        self.assertEqual(payload["message"], "群组不存在")
        self.assertEqual(payload["path"], "/groups/10086")
        self.assertTrue(payload.get("request_id"))
        self.assertTrue(payload.get("timestamp"))

    def test_validation_error_response_shape(self) -> None:
        with TestClient(app) as client:
            response = client.post("/groups", json={})

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["code"], "REQUEST_VALIDATION_ERROR")
        self.assertEqual(payload["message"], "请求参数校验失败")
        self.assertEqual(payload["path"], "/groups")
        self.assertIsInstance(payload.get("detail"), list)

    def test_unexpected_error_response_shape(self) -> None:
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceBoom()):
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/groups/10010")

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["code"], "INTERNAL_SERVER_ERROR")
        self.assertEqual(payload["message"], "服务器内部错误")
        self.assertEqual(payload["path"], "/groups/10010")


if __name__ == "__main__":
    unittest.main()
