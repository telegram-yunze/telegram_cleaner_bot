from __future__ import annotations

from datetime import datetime, timezone
import unittest

from app.models.enums import MessageType, ModerationAction, RuleType
from app.services.ad_detector import AdDetectResult
from app.services.bot_flow_models import ParsedMessageContext
from app.services.rule_matcher_service import RuleMatcherService
from app.schemas.rule import RuleRead


class _FakeRuleService:
    def __init__(self, rules: list[RuleRead]) -> None:
        self._rules = rules

    async def FindEnabledByGroupId(self, group_id: int):
        return self._rules


class _FakeAdDetectorService:
    def __init__(self, fixed_score: float) -> None:
        self._fixed_score = fixed_score

    async def ScoreText(self, text: str | None) -> AdDetectResult:
        return AdDetectResult(score=self._fixed_score, reason="contains_link")


class RuleMatcherServiceTests(unittest.IsolatedAsyncioTestCase):
    """验证规则匹配入口服务。"""

    async def test_match_first_rule_by_keyword(self) -> None:
        rule = RuleRead(
            id=1,
            group_id=10,
            code="kw_ad",
            name="关键词广告",
            rule_type=RuleType.KEYWORD,
            pattern="赌博",
            action=ModerationAction.DELETE,
            priority=1,
            is_enabled=True,
            options=None,
            related_moderation_count=0,
            hit_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        matcher = RuleMatcherService(
            rule_service=_FakeRuleService([rule]),
            ad_detector_service=_FakeAdDetectorService(0.88),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=9,
            telegram_user_id=99,
            telegram_message_id=66,
            message_type=MessageType.TEXT,
            content_text="这是赌博推广",
            mentions=[],
            links=[],
        )

        result = await matcher.MatchFirstRuleByMessageContext(context)
        self.assertTrue(result.hit)
        self.assertEqual(result.rule_code, "kw_ad")
        self.assertEqual(result.action, ModerationAction.DELETE)
        self.assertEqual(result.risk_score, 0.88)
        self.assertEqual(result.detect_reason, "contains_link")

    async def test_match_first_rule_returns_no_hit(self) -> None:
        matcher = RuleMatcherService(
            rule_service=_FakeRuleService([]),
            ad_detector_service=_FakeAdDetectorService(0.66),
        )
        context = ParsedMessageContext(
            group_id=10,
            telegram_group_id=-100,
            persisted_message_id=123,
            sender_id=9,
            telegram_user_id=99,
            telegram_message_id=66,
            message_type=MessageType.TEXT,
            content_text="正常消息",
            mentions=[],
            links=[],
        )

        result = await matcher.MatchFirstRuleByMessageContext(context)
        self.assertFalse(result.hit)
        self.assertEqual(result.reason, "no_rule_matched")


if __name__ == "__main__":
    unittest.main()
