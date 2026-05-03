from __future__ import annotations

import re

from app.models.enums import RuleType
from app.schemas.rule import RuleRead
from app.services.bot_flow_models import ParsedMessageContext, RuleMatchResult
from app.services.rule_service import RuleService


class RuleMatcherService:
    """规则匹配入口服务：按优先级返回首条命中规则。"""

    def __init__(self, rule_service: RuleService) -> None:
        self._rule_service = rule_service

    async def MatchFirstRuleByMessageContext(self, context: ParsedMessageContext) -> RuleMatchResult:
        """按优先级尝试匹配，返回首条命中结果。"""

        if context.group_id is None:
            return RuleMatchResult(hit=False, reason="missing_group_id")

        text = context.content_text or ""
        rules = await self._rule_service.FindEnabledByGroupId(context.group_id)
        for rule in rules:
            if self._is_match(rule, text, context.links):
                return RuleMatchResult(
                    hit=True,
                    rule_id=rule.id,
                    rule_code=rule.code,
                    rule_type=rule.rule_type,
                    action=rule.action,
                    reason=f"命中规则 {rule.code}",
                    risk_score=1.0,
                )

        return RuleMatchResult(hit=False, reason="no_rule_matched")

    def _is_match(self, rule: RuleRead, text: str, links: list[str]) -> bool:
        """根据规则类型执行对应匹配逻辑。"""

        if rule.rule_type is RuleType.KEYWORD:
            return self._match_keyword(rule, text)
        if rule.rule_type is RuleType.REGEX:
            return self._match_regex(rule, text)
        if rule.rule_type is RuleType.URL:
            return self._match_url(rule, text, links)
        return False

    def _match_keyword(self, rule: RuleRead, text: str) -> bool:
        """关键词匹配：优先使用 options.keywords，其次回退 pattern。"""

        if not text:
            return False

        keywords = list(rule.options.keywords or []) if rule.options else []
        if not keywords and rule.pattern:
            keywords = [item.strip() for item in rule.pattern.split(",") if item.strip()]

        lower_text = text.lower()
        return any(keyword.lower() in lower_text for keyword in keywords)

    def _match_regex(self, rule: RuleRead, text: str) -> bool:
        """正则匹配。"""

        if not text or not rule.pattern:
            return False
        try:
            return re.search(rule.pattern, text, flags=re.IGNORECASE) is not None
        except re.error:
            return False

    def _match_url(self, rule: RuleRead, text: str, links: list[str]) -> bool:
        """链接匹配：优先用已提取链接，回退文本中的 URL 片段。"""

        if links:
            if not rule.pattern:
                return True
            pattern = rule.pattern.lower()
            return any(pattern in link.lower() for link in links)

        if not text:
            return False
        if rule.pattern:
            return rule.pattern.lower() in text.lower()
        return "http://" in text.lower() or "https://" in text.lower()


__all__ = ["RuleMatcherService"]
