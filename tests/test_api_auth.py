from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.config as config_module
from app.deps import get_db
from app.main import app


async def _override_get_db():
    """测试阶段注入空会话，避免真实数据库连接。"""

    yield None


class _GroupServiceNotFound:
    async def FindById(self, group_id: int):
        return None


class ApiAuthTests(unittest.TestCase):
    """验证 API Key 鉴权行为。"""

    def setUp(self) -> None:
        app.dependency_overrides[get_db] = _override_get_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_protected_endpoint_without_api_key_returns_401(self) -> None:
        with TestClient(app) as client:
            response = client.get("/groups/1")

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["code"], "UNAUTHORIZED")
        self.assertEqual(payload["message"], "API 密钥无效")

    def test_protected_endpoint_with_wrong_api_key_returns_401(self) -> None:
        with TestClient(app) as client:
            response = client.get("/groups/1", headers={"X-API-Key": "wrong-key"})

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertEqual(payload["code"], "UNAUTHORIZED")

    def test_protected_endpoint_with_valid_api_key_reaches_business_logic(self) -> None:
        valid_key = config_module.get_runtime_api_secret_key()
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get("/groups/1", headers={"X-API-Key": valid_key})

        # 鉴权通过后才会进入业务层，当前 mock 返回不存在，因此应为 404 而非 401
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["code"], "RESOURCE_NOT_FOUND")

    def test_public_endpoints_do_not_require_api_key(self) -> None:
        with TestClient(app) as client:
            root_response = client.get("/")
            health_response = client.get("/health")

        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(health_response.status_code, 200)

    def test_empty_env_secret_generates_runtime_secret_and_keeps_stable(self) -> None:
        with patch("app.config.get_settings", return_value=SimpleNamespace(api_secret_key="")):
            config_module._resolve_runtime_api_secret.cache_clear()
            first = config_module.get_runtime_api_secret_key()
            second = config_module.get_runtime_api_secret_key()
            source = config_module.get_runtime_api_secret_source()

        config_module._resolve_runtime_api_secret.cache_clear()

        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(source, "generated")


if __name__ == "__main__":
    unittest.main()