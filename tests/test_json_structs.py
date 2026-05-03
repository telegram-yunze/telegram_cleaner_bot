from __future__ import annotations

import unittest

from app.models.json_types import (
    BotPermissions,
    GroupSettings,
    ModerationResultDetail,
    PydanticJsonType,
    RuleOptions,
)
from app.schemas.group import GroupCreate
from app.schemas.moderation import ModerationRecordCreate
from app.schemas.rule import RuleCreate


class PydanticJsonTypeTests(unittest.TestCase):
    """验证 JSON 结构体在 ORM 适配器中的双向转换行为。"""

    def test_bind_param_supports_model_and_mapping(self) -> None:
        column_type = PydanticJsonType(GroupSettings)

        from_model = column_type.process_bind_param(GroupSettings(ad_detection_enabled=True), None)
        self.assertEqual(from_model, {"ad_detection_enabled": True, "auto_delete_enabled": None, "mute_duration_seconds": None})

        from_mapping = column_type.process_bind_param({"auto_delete_enabled": False}, None)
        self.assertEqual(from_mapping, {"auto_delete_enabled": False})

        from_none = column_type.process_bind_param(None, None)
        self.assertIsNone(from_none)

    def test_bind_param_rejects_invalid_type(self) -> None:
        column_type = PydanticJsonType(GroupSettings)
        with self.assertRaises(TypeError):
            column_type.process_bind_param("invalid", None)

    def test_result_value_converts_to_model(self) -> None:
        column_type = PydanticJsonType(BotPermissions)

        parsed = column_type.process_result_value({"can_delete_messages": True}, None)
        self.assertIsInstance(parsed, BotPermissions)
        self.assertTrue(parsed.can_delete_messages)

        parsed_none = column_type.process_result_value(None, None)
        self.assertIsNone(parsed_none)


class SchemaJsonStructTests(unittest.TestCase):
    """验证 API schema 对结构体字段的解析与类型收敛。"""

    def test_group_create_accepts_struct_payload(self) -> None:
        payload = GroupCreate(
            telegram_group_id=10001,
            title="test-group",
            settings={"ad_detection_enabled": True},
            bot_permissions={"can_delete_messages": True},
        )

        self.assertIsInstance(payload.settings, GroupSettings)
        self.assertIsInstance(payload.bot_permissions, BotPermissions)
        self.assertTrue(payload.settings.ad_detection_enabled)
        self.assertTrue(payload.bot_permissions.can_delete_messages)

    def test_rule_create_accepts_struct_payload(self) -> None:
        payload = RuleCreate(
            group_id=1,
            code="spam_1",
            name="spam",
            rule_type="keyword",
            options={"threshold": 0.9},
        )

        self.assertIsInstance(payload.options, RuleOptions)
        self.assertAlmostEqual(payload.options.threshold or 0.0, 0.9)

    def test_moderation_create_accepts_struct_payload(self) -> None:
        payload = ModerationRecordCreate(
            group_id=1,
            action="warn",
            result_detail={"success": True, "provider": "telegram"},
        )

        self.assertIsInstance(payload.result_detail, ModerationResultDetail)
        self.assertTrue(payload.result_detail.success)
        self.assertEqual(payload.result_detail.provider, "telegram")


if __name__ == "__main__":
    unittest.main()
