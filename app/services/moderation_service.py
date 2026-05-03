from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.models.moderation_record import ModerationRecord
from app.repositories.group_repository import GroupUserRepositoryProtocol
from app.repositories.moderation_repository import ModerationRepositoryProtocol
from app.repositories.rule_repository import RuleRepositoryProtocol
from app.schemas.moderation import (
    ModerationRecordCreate,
    ModerationRecordListItem,
    ModerationRecordListResponse,
    ModerationRecordQuery,
    ModerationRecordRead,
    ModerationRecordUpdate,
)


class ModerationService:
    """审核记录应用服务，编排处置记录查询和状态更新。"""

    def __init__(
        self,
        moderation_repository: ModerationRepositoryProtocol,
        group_user_repository: GroupUserRepositoryProtocol,
        rule_repository: RuleRepositoryProtocol,
    ) -> None:
        self._moderation_repository = moderation_repository
        self._group_user_repository = group_user_repository
        self._rule_repository = rule_repository

    async def Create(self, payload: ModerationRecordCreate) -> ModerationRecordRead:
        """创建审核记录并返回详情。"""

        entity = ModerationRecord(**payload.model_dump())
        saved_entity = await self._moderation_repository.Save(entity)
        return await self._to_moderation_read(saved_entity)

    async def FindById(self, moderation_record_id: int) -> ModerationRecordRead | None:
        """按主键查询审核记录详情。"""

        entity = await self._moderation_repository.FindById(moderation_record_id)
        if entity is None:
            return None
        return await self._to_moderation_read(entity)

    async def FindAll(self, query: ModerationRecordQuery) -> ModerationRecordListResponse:
        """按查询条件查询审核记录列表。"""

        entities = await self._find_moderation_records_by_query(query)
        items = [await self._to_moderation_list_item(entity) for entity in entities]
        return ModerationRecordListResponse(
            items=items,
            total=await self._count_moderation_records(query),
            limit=query.limit,
            offset=query.offset,
        )

    async def UpdateById(
        self,
        moderation_record_id: int,
        payload: ModerationRecordUpdate,
    ) -> ModerationRecordRead | None:
        """按主键更新审核记录。"""

        entity = await self._moderation_repository.FindById(moderation_record_id)
        if entity is None:
            return None

        update_values = payload.model_dump(exclude_unset=True)
        for field_name, field_value in update_values.items():
            setattr(entity, field_name, field_value)

        saved_entity = await self._moderation_repository.Save(entity)
        return await self._to_moderation_read(saved_entity)

    async def UpdateStatusById(
        self,
        moderation_record_id: int,
        payload: ModerationRecordUpdate,
    ) -> ModerationRecordRead | None:
        """只更新审核记录状态和结果详情。"""

        if payload.status is None:
            return await self.FindById(moderation_record_id)

        await self._moderation_repository.UpdateStatusById(
            moderation_record_id=moderation_record_id,
            status=payload.status,
            result_detail=payload.result_detail,
        )
        return await self.FindById(moderation_record_id)

    async def _find_moderation_records_by_query(
        self,
        query: ModerationRecordQuery,
    ) -> Sequence[ModerationRecord]:
        """按查询条件返回审核记录实体集合。"""

        if query.group_id is None:
            return await self._moderation_repository.FindAllOrderByCreatedAtDesc(query.limit, query.offset)
        if query.status is None:
            return await self._moderation_repository.FindAllByGroupIdOrderByCreatedAtDesc(
                query.group_id,
                query.limit,
                query.offset,
            )
        return await self._moderation_repository.FindAllByGroupIdAndStatusOrderByCreatedAtDesc(
            query.group_id,
            query.status,
            query.limit,
            query.offset,
        )

    async def _count_moderation_records(self, query: ModerationRecordQuery) -> int:
        """按查询条件统计审核记录数量。"""

        entities = await self._find_moderation_records_by_query(
            ModerationRecordQuery(
                group_id=query.group_id,
                status=query.status,
                limit=10_000,
                offset=0,
            )
        )
        return len(entities)

    async def _to_moderation_read(self, entity: ModerationRecord) -> ModerationRecordRead:
        """把审核记录实体转换为详情响应。"""

        extra_fields = await self._collect_extra_fields(entity)
        return ModerationRecordRead.model_validate({**entity.__dict__, **extra_fields})

    async def _to_moderation_list_item(self, entity: ModerationRecord) -> ModerationRecordListItem:
        """把审核记录实体转换为列表项。"""

        extra_fields = await self._collect_extra_fields(entity)
        return ModerationRecordListItem.model_validate({**entity.__dict__, **extra_fields})

    async def _collect_extra_fields(self, entity: ModerationRecord) -> dict[str, Any]:
        """补齐展示层需要的轻量附加字段。"""

        target_telegram_user_id: int | None = None
        rule_code: str | None = None

        if entity.target_user_id is not None:
            target_user = await self._group_user_repository.FindById(entity.target_user_id)
            if target_user is not None:
                target_telegram_user_id = target_user.telegram_user_id

        if entity.rule_id is not None:
            rule = await self._rule_repository.FindById(entity.rule_id)
            if rule is not None:
                rule_code = rule.code

        return {
            "target_telegram_user_id": target_telegram_user_id,
            "rule_code": rule_code,
        }


__all__ = ["ModerationService"]
