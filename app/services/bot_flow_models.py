from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import MessageType, ModerationAction, ModerationStatus, RuleType


@dataclass(slots=True)
class ParsedMessageContext:
    """机器人处理链路中的消息上下文。"""

    group_id: int | None
    telegram_group_id: int | None
    persisted_message_id: int | None
    sender_id: int | None
    telegram_user_id: int | None
    telegram_message_id: int | None
    message_type: MessageType
    content_text: str | None
    mentions: list[str]
    links: list[str]
    should_skip: bool = False
    skip_reason: str | None = None


@dataclass(slots=True)
class RuleMatchResult:
    """规则匹配结果。"""

    hit: bool
    rule_id: int | None = None
    rule_code: str | None = None
    rule_type: RuleType | None = None
    action: ModerationAction | None = None
    reason: str | None = None
    detect_reason: str | None = None
    risk_score: float | None = None


@dataclass(slots=True)
class ActionExecutionResult:
    """动作执行结果。"""

    moderation_record_id: int
    status: ModerationStatus
    success: bool


__all__ = [
    "ActionExecutionResult",
    "ParsedMessageContext",
    "RuleMatchResult",
]
