from __future__ import annotations

from aiogram.types import ChatPermissions, Message

from app.models.enums import ModerationAction, ModerationStatus
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

        created = await self._moderation_service.Create(
            ModerationRecordCreate(
                group_id=context.group_id,
                message_id=context.persisted_message_id,
                target_user_id=context.sender_id,
                rule_id=match_result.rule_id,
                action=match_result.action,
                status=ModerationStatus.PENDING,
                reason=match_result.reason,
                result_detail=None,
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
            ModerationRecordUpdate(status=status, result_detail=detail),
        )

        return ActionExecutionResult(
            moderation_record_id=created.id,
            status=status,
            success=status is ModerationStatus.SUCCESS,
        )

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
