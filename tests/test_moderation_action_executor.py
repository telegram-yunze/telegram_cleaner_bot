from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.models.enums import MessageType, ModerationAction, ModerationStatus
from app.services.bot_flow_models import ParsedMessageContext, RuleMatchResult
from app.services.moderation_action_executor import ModerationActionExecutorService


class _FakeModerationService:
    def __init__(self) -> None:
        self.updated_status = None

    async def Create(self, payload):
        return SimpleNamespace(id=101)

    async def UpdateStatusById(self, record_id: int, payload):
        self.updated_status = payload.status
        return SimpleNamespace(id=record_id)


class ModerationActionExecutorTests(unittest.IsolatedAsyncioTestCase):
    """验证审核动作占位执行服务。"""

    async def test_execute_placeholder_action_in_dry_run_mode(self) -> None:
        service = ModerationActionExecutorService(_FakeModerationService(), dry_run=True)
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
            risk_score=1.0,
        )

        result = await service.ExecutePlaceholderAction(
            message=message,
            context=context,
            match_result=match_result,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.status, ModerationStatus.SUCCESS)

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

    async def _noop(self, *args, **kwargs):
        return None


if __name__ == "__main__":
    unittest.main()
