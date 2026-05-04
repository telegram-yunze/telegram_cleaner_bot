from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import get_runtime_api_secret_key
from app.deps import get_db
from app.main import app
from app.models.enums import ModerationAction, ModerationStatus
from app.models.json_types import ModerationResultDetail
from app.schemas.moderation import ModerationRecordListItem, ModerationRecordListResponse, ModerationRecordRead


async def _override_get_db():
    """测试阶段注入空会话，路由中的 service 工厂会被 mock。"""

    yield None


class _GroupServiceNotFound:
    async def FindById(self, group_id: int):
        return None


class _GroupServiceBoom:
    async def FindById(self, group_id: int):
        raise RuntimeError("boom")


class _ModerationServiceStub:
    async def FindAll(self, query):
        return ModerationRecordListResponse(
            items=[
                ModerationRecordListItem(
                    id=1,
                    group_id=10,
                    message_id=123,
                    target_user_id=33,
                    rule_id=9,
                    action=ModerationAction.DELETE,
                    status=ModerationStatus.SUCCESS,
                    reason="命中规则 kw_ad | 风险依据: fake_detector",
                    target_telegram_user_id=88,
                    rule_code="kw_ad",
                    created_at=datetime.now(timezone.utc),
                )
            ],
            total=1,
            limit=20,
            offset=0,
        )

    async def FindById(self, moderation_record_id: int):
        return ModerationRecordRead(
            id=moderation_record_id,
            group_id=10,
            message_id=123,
            target_user_id=33,
            rule_id=9,
            action=ModerationAction.DELETE,
            status=ModerationStatus.SUCCESS,
            reason="命中规则 kw_ad | 风险依据: contains_link,ad_keywords_detected",
            result_detail=ModerationResultDetail(
                success=True,
                provider="telegram_dry_run",
                rule_reason="命中规则 kw_ad",
                detector_reasons=["contains_link", "ad_keywords_detected"],
                risk_score=0.95,
            ),
            target_telegram_user_id=88,
            rule_code="kw_ad",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


class ApiExceptionHandlingTests(unittest.TestCase):
    """覆盖 API 全局异常处理的关键路径。"""

    def setUp(self) -> None:
        app.dependency_overrides[get_db] = _override_get_db
        self.auth_headers = {"X-API-Key": get_runtime_api_secret_key()}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_not_found_error_response_shape(self) -> None:
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceNotFound()):
            with TestClient(app) as client:
                response = client.get("/groups/10086", headers=self.auth_headers)

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["code"], "RESOURCE_NOT_FOUND")
        self.assertEqual(payload["message"], "群组不存在")
        self.assertEqual(payload["path"], "/groups/10086")
        self.assertTrue(payload.get("request_id"))
        self.assertTrue(payload.get("timestamp"))

    def test_validation_error_response_shape(self) -> None:
        with TestClient(app) as client:
            response = client.post("/groups", json={}, headers=self.auth_headers)

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["code"], "REQUEST_VALIDATION_ERROR")
        self.assertEqual(payload["message"], "请求参数校验失败")
        self.assertEqual(payload["path"], "/groups")
        self.assertIsInstance(payload.get("detail"), list)

    def test_unexpected_error_response_shape(self) -> None:
        with patch("app.api.groups.get_group_service", return_value=_GroupServiceBoom()):
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/groups/10010", headers=self.auth_headers)

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["code"], "INTERNAL_SERVER_ERROR")
        self.assertEqual(payload["message"], "服务器内部错误")
        self.assertEqual(payload["path"], "/groups/10010")

    def test_moderation_list_reason_exposed(self) -> None:
        with patch("app.api.moderation.get_moderation_service", return_value=_ModerationServiceStub()):
            with TestClient(app) as client:
                response = client.get("/moderation", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["reason"], "命中规则 kw_ad | 风险依据: fake_detector")

    def test_moderation_detail_exposes_structured_result_detail(self) -> None:
        with patch("app.api.moderation.get_moderation_service", return_value=_ModerationServiceStub()):
            with TestClient(app) as client:
                response = client.get("/moderation/1", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reason"], "命中规则 kw_ad | 风险依据: contains_link,ad_keywords_detected")
        self.assertEqual(payload["result_detail"]["rule_reason"], "命中规则 kw_ad")
        self.assertEqual(payload["result_detail"]["detector_reasons"], ["contains_link", "ad_keywords_detected"])
        self.assertEqual(payload["result_detail"]["risk_score"], 0.95)


if __name__ == "__main__":
    unittest.main()
