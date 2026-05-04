from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.models.enums import MessageType, ModerationAction, ModerationStatus
from app.services.bot_flow_models import ParsedMessageContext, RuleMatchResult
from app.services.moderation_action_executor import ModerationActionExecutorService


class _FakeModerationService:
    def __init__(self) -> None:
        self.updated_status = None
        self.created_payload = None
        self.updated_payload = None

    async def Create(self, payload):
        self.created_payload = payload
        return SimpleNamespace(id=101)

    async def UpdateStatusById(self, record_id: int, payload):
        self.updated_status = payload.status
        self.updated_payload = payload
        return SimpleNamespace(id=record_id)


class ModerationActionExecutorTests(unittest.IsolatedAsyncioTestCase):
    """验证审核动作占位执行服务。"""

    async def test_execute_placeholder_action_in_dry_run_mode(self) -> None:
        fake_moderation_service = _FakeModerationService()
        service = ModerationActionExecutorService(fake_moderation_service, dry_run=True)
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-100),
            from_user=SimpleNamespace(id=88),
            delete=self._noop,
            reply=self._noop,
            bot=SimpleNamespace(
                restrict_chat_member=self._noop,
                ban_chat_member=self._noop,
            ),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=33,
            telegram_user_id=88,
            telegram_message_id=99,
            message_type=MessageType.TEXT,
            content_text="疑似广告",
            mentions=[],
            links=[],
        )
        match_result = RuleMatchResult(
            hit=True,
            rule_id=1,
            rule_code="kw_ad",
            action=ModerationAction.DELETE,
            reason="命中规则",
            detect_reason="contains_link",
            risk_score=1.0,
        )

        result = await service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.status, ModerationStatus.SUCCESS)
        self.assertEqual(fake_moderation_service.created_payload.reason, "命中规则 | 风险依据: contains_link")
        self.assertEqual(fake_moderation_service.created_payload.result_detail.rule_reason, "命中规则")
        self.assertEqual(fake_moderation_service.created_payload.result_detail.detector_reasons, ["contains_link"])
        self.assertEqual(fake_moderation_service.created_payload.result_detail.risk_score, 1.0)
        self.assertEqual(fake_moderation_service.updated_payload.result_detail.detector_reasons, ["contains_link"])
        self.assertTrue(fake_moderation_service.updated_payload.result_detail.success)

    async def test_execute_placeholder_action_review_should_skip(self) -> None:
        fake_moderation_service = _FakeModerationService()
        service = ModerationActionExecutorService(fake_moderation_service, dry_run=True)
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-100),
            from_user=SimpleNamespace(id=88),
            delete=self._noop,
            reply=self._noop,
            bot=SimpleNamespace(
                restrict_chat_member=self._noop,
                ban_chat_member=self._noop,
            ),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=33,
            telegram_user_id=88,
            telegram_message_id=99,
            message_type=MessageType.TEXT,
            content_text="疑似广告",
            mentions=[],
            links=[],
        )
        match_result = RuleMatchResult(
            hit=True,
            rule_id=1,
            rule_code="review_rule",
            action=ModerationAction.REVIEW,
            reason="命中规则",
            detect_reason="contains_mention",
            risk_score=1.0,
        )

        result = await service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, ModerationStatus.SKIPPED)
        self.assertEqual(fake_moderation_service.updated_status, ModerationStatus.SKIPPED)
        self.assertEqual(
            fake_moderation_service.updated_payload.result_detail.detector_reasons,
            ["contains_mention"],
        )

    async def test_execute_delete_action_in_non_dry_run_mode(self) -> None:
        fake_moderation_service = _FakeModerationService()
        service = ModerationActionExecutorService(fake_moderation_service, dry_run=False)

        delete_called = {"value": False}

        async def _delete():
            delete_called["value"] = True

        message = SimpleNamespace(
            chat=SimpleNamespace(id=-100),
            from_user=SimpleNamespace(id=88),
            delete=_delete,
            reply=self._noop,
            bot=SimpleNamespace(
                restrict_chat_member=self._noop,
                ban_chat_member=self._noop,
            ),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=33,
            telegram_user_id=88,
            telegram_message_id=99,
            message_type=MessageType.TEXT,
            content_text="疑似广告",
            mentions=[],
            links=[],
        )
        match_result = RuleMatchResult(
            hit=True,
            rule_id=1,
            rule_code="kw_ad",
            action=ModerationAction.DELETE,
            reason="命中规则",
            detect_reason="short_text_with_link",
            risk_score=1.0,
        )

        result = await service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )
        self.assertTrue(delete_called["value"])
        self.assertTrue(result.success)
        self.assertEqual(result.status, ModerationStatus.SUCCESS)
        self.assertEqual(
            fake_moderation_service.updated_payload.result_detail.detector_reasons,
            ["short_text_with_link"],
        )

    async def test_legacy_detector_token_kept_for_compatibility(self) -> None:
        fake_moderation_service = _FakeModerationService()
        service = ModerationActionExecutorService(fake_moderation_service, dry_run=True)
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-100),
            from_user=SimpleNamespace(id=88),
            delete=self._noop,
            reply=self._noop,
            bot=SimpleNamespace(
                restrict_chat_member=self._noop,
                ban_chat_member=self._noop,
            ),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=33,
            telegram_user_id=88,
            telegram_message_id=99,
            message_type=MessageType.TEXT,
            content_text="疑似广告",
            mentions=[],
            links=[],
        )
        match_result = RuleMatchResult(
            hit=True,
            rule_id=1,
            rule_code="legacy_rule",
            action=ModerationAction.DELETE,
            reason="命中规则",
            detect_reason="legacy_unknown_token",
            risk_score=0.9,
        )

        result = await service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            fake_moderation_service.created_payload.result_detail.detector_reasons,
            ["legacy_unknown_token"],
        )

    async def _noop(self, *args, **kwargs):
        return None


if __name__ == "__main__":
    unittest.main()
