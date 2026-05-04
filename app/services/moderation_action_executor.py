from __future__ import annotations

from aiogram.types import ChatPermissions, Message

from app.models.enums import DetectorReasonToken, ModerationAction, ModerationStatus
from app.models.json_types import ModerationResultDetail
from app.schemas.moderation import ModerationRecordCreate, ModerationRecordUpdate
from app.services.bot_flow_models import ActionExecutionResult, ParsedMessageContext, RuleMatchResult
from app.services.moderation_service import ModerationService
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


class ModerationActionExecutorService:
    """审核动作执行服务：创建处置记录并执行动作分发占位。"""

    def __init__(self, moderation_service: ModerationService, *, dry_run: bool = True) -> None:
        self._moderation_service = moderation_service
        self._dry_run = dry_run

    async def ExecutePlaceholderAction(
        self,
        *,
        message: Message,
        context: ParsedMessageContext,
        match_result: RuleMatchResult,
    ) -> ActionExecutionResult:
        """执行占位动作并更新处置记录状态。"""

        if context.group_id is None or match_result.action is None:
            raise ValueError("执行审核动作缺少必要上下文")

        moderation_reason = self._build_moderation_reason(match_result)
        base_detail = self._build_base_result_detail(match_result)

        created = await self._moderation_service.Create(
            ModerationRecordCreate(
                group_id=context.group_id,
                message_id=context.persisted_message_id,
                target_user_id=context.sender_id,
                rule_id=match_result.rule_id,
                action=match_result.action,
                status=ModerationStatus.PENDING,
                reason=moderation_reason,
                result_detail=base_detail,
            )
        )

        status = ModerationStatus.FAILED
        detail = ModerationResultDetail(success=False, provider="telegram")
        try:
            status, detail = await self._dispatch_action(message=message, action=match_result.action)
        except Exception as exc:
            log_exception(
                logger,
                message="审核动作执行失败",
                exc=exc,
                extra={"action": match_result.action.value, "record_id": created.id},
            )
            detail = ModerationResultDetail(
                success=False,
                provider="telegram",
                error_code="ACTION_EXECUTION_FAILED",
                error_message=str(exc),
            )
            status = ModerationStatus.FAILED

        await self._moderation_service.UpdateStatusById(
            created.id,
            ModerationRecordUpdate(status=status, result_detail=self._merge_result_detail(base_detail, detail)),
        )

        return ActionExecutionResult(
            moderation_record_id=created.id,
            status=status,
            success=status is ModerationStatus.SUCCESS,
        )

    def _build_moderation_reason(self, match_result: RuleMatchResult) -> str | None:
        """组合落库原因，统一保留规则命中说明与风险依据。"""

        rule_reason = (match_result.reason or "").strip()
        detect_reason = (match_result.detect_reason or "").strip()

        if rule_reason and detect_reason:
            if detect_reason in rule_reason:
                return rule_reason
            return f"{rule_reason} | 风险依据: {detect_reason}"
        if rule_reason:
            return rule_reason
        if detect_reason:
            return f"风险依据: {detect_reason}"
        return None

    def _build_base_result_detail(self, match_result: RuleMatchResult) -> ModerationResultDetail:
        """构建基础结构化详情，保存规则与检测器元数据。"""

        return ModerationResultDetail(
            rule_reason=(match_result.reason or None),
            detector_reasons=self._normalize_detector_reasons(match_result.detect_reason),
            risk_score=match_result.risk_score,
        )

    def _normalize_detector_reasons(self, detect_reason: str | None) -> list[str] | None:
        """把检测原因字符串归一化为列表，去空白与重复。"""

        if not detect_reason:
            return None

        valid_tokens = {token.value for token in DetectorReasonToken}
        normalized: list[str] = []
        for item in detect_reason.split(","):
            token = item.strip()
            if not token:
                continue

            # 保持向后兼容：未知 token 不丢弃，仅记录告警。
            if token not in valid_tokens:
                logger.warning("检测到非标准 detector token: %s", token)

            if token not in normalized:
                normalized.append(token)
        return normalized or None

    def _merge_result_detail(
        self,
        base_detail: ModerationResultDetail,
        action_detail: ModerationResultDetail,
    ) -> ModerationResultDetail:
        """合并检测元数据与动作执行结果，避免结构化原因在状态更新时丢失。"""

        merged_data = base_detail.model_dump(exclude_none=True)
        merged_data.update(action_detail.model_dump(exclude_none=True))
        return ModerationResultDetail(**merged_data)

    async def _dispatch_action(
        self,
        *,
        message: Message,
        action: ModerationAction,
    ) -> tuple[ModerationStatus, ModerationResultDetail]:
        """分发并执行占位动作。"""

        provider = "telegram_dry_run" if self._dry_run else "telegram"

        if action is ModerationAction.IGNORE:
            return ModerationStatus.SKIPPED, ModerationResultDetail(success=True, provider=provider)

        if action is ModerationAction.REVIEW:
            return ModerationStatus.SKIPPED, ModerationResultDetail(success=True, provider=provider)

        if self._dry_run:
            return ModerationStatus.SUCCESS, ModerationResultDetail(success=True, provider=provider)

        if action is ModerationAction.DELETE:
            await message.delete()
            return ModerationStatus.SUCCESS, ModerationResultDetail(success=True, provider=provider)

        if action is ModerationAction.WARN:
            await message.reply("检测到疑似违规内容，已记录审核。")
            return ModerationStatus.SUCCESS, ModerationResultDetail(success=True, provider=provider)

        if action in {ModerationAction.MUTE, ModerationAction.PERMANENT_MUTE, ModerationAction.RESTRICT}:
            if message.from_user is None:
                return ModerationStatus.FAILED, ModerationResultDetail(
                    success=False,
                    provider=provider,
                    error_code="MISSING_TARGET_USER",
                    error_message="缺少目标用户，无法执行限制动作",
                )
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            return ModerationStatus.SUCCESS, ModerationResultDetail(success=True, provider=provider)

        if action in {ModerationAction.KICK, ModerationAction.BAN}:
            if message.from_user is None:
                return ModerationStatus.FAILED, ModerationResultDetail(
                    success=False,
                    provider=provider,
                    error_code="MISSING_TARGET_USER",
                    error_message="缺少目标用户，无法执行封禁动作",
                )
            await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
            return ModerationStatus.SUCCESS, ModerationResultDetail(success=True, provider=provider, kicked=True)

        return ModerationStatus.SKIPPED, ModerationResultDetail(
            success=True,
            provider=provider,
            error_code="ACTION_NOT_IMPLEMENTED",
            error_message=f"动作 {action.value} 暂未实现",
        )


__all__ = ["ModerationActionExecutorService"]
