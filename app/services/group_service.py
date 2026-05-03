from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.models.enums import ModerationStatus
from app.models.group import Group
from app.repositories.group_repository import (
    GroupMessageRepositoryProtocol,
    GroupRepositoryProtocol,
    GroupUserRepositoryProtocol,
)
from app.repositories.moderation_repository import ModerationRepositoryProtocol
from app.repositories.rule_repository import RuleRepositoryProtocol
from app.schemas.group import (
    GroupCreate,
    GroupListItem,
    GroupListResponse,
    GroupQuery,
    GroupRead,
    GroupUpdate,
)


class GroupService:
    """群组应用服务，编排群组与统计相关的业务流程。"""

    def __init__(
        self,
        group_repository: GroupRepositoryProtocol,
        group_user_repository: GroupUserRepositoryProtocol,
        group_message_repository: GroupMessageRepositoryProtocol,
        rule_repository: RuleRepositoryProtocol,
        moderation_repository: ModerationRepositoryProtocol,
    ) -> None:
        self._group_repository = group_repository
        self._group_user_repository = group_user_repository
        self._group_message_repository = group_message_repository
        self._rule_repository = rule_repository
        self._moderation_repository = moderation_repository

    async def Create(self, payload: GroupCreate) -> GroupRead:
        """创建群组并返回带统计信息的详情。"""

        entity = Group(**payload.model_dump())
        saved_entity = await self._group_repository.Save(entity)
        return await self._to_group_read(saved_entity)

    async def FindById(self, group_id: int) -> GroupRead | None:
        """按主键查询群组详情。"""

        entity = await self._group_repository.FindById(group_id)
        if entity is None:
            return None
        return await self._to_group_read(entity)

    async def FindByTelegramGroupId(self, telegram_group_id: int) -> GroupRead | None:
        """按 Telegram 群组 ID 查询群组详情。"""

        entity = await self._group_repository.FindByTelegramGroupId(telegram_group_id)
        if entity is None:
            return None
        return await self._to_group_read(entity)

    async def FindAll(self, query: GroupQuery) -> GroupListResponse:
        """查询群组列表，并补齐常用统计字段。"""

        entities = await self._find_groups_by_query(query)
        items = [await self._to_group_list_item(entity) for entity in entities]
        return GroupListResponse(
            items=items,
            total=await self._count_groups(query),
            limit=query.limit,
            offset=query.offset,
        )

    async def UpdateById(self, group_id: int, payload: GroupUpdate) -> GroupRead | None:
        """按主键更新群组基础信息。"""

        entity = await self._group_repository.FindById(group_id)
        if entity is None:
            return None

        update_values = payload.model_dump(exclude_unset=True)
        for field_name, field_value in update_values.items():
            setattr(entity, field_name, field_value)

        saved_entity = await self._group_repository.Save(entity)
        return await self._to_group_read(saved_entity)

    async def UpdateLastMessageAtByTelegramGroupId(
        self,
        telegram_group_id: int,
        last_message_at: datetime,
    ) -> int:
        """更新群组最近消息时间。"""

        return await self._group_repository.UpdateLastMessageAtByTelegramGroupId(
            telegram_group_id=telegram_group_id,
            last_message_at=last_message_at,
        )

    async def DeleteById(self, group_id: int) -> bool:
        """按主键删除群组。"""

        return await self._group_repository.DeleteById(group_id)

    async def _find_groups_by_query(self, query: GroupQuery) -> Sequence[Group]:
        """按查询条件返回群组实体集合。"""

        if query.is_active is None:
            active_entities = await self._group_repository.FindAllByIsActive(True)
            inactive_entities = await self._group_repository.FindAllByIsActive(False)
            all_entities = sorted(
                [*active_entities, *inactive_entities],
                key=lambda entity: entity.id,
            )
        else:
            all_entities = list(await self._group_repository.FindAllByIsActive(query.is_active))

        return all_entities[query.offset : query.offset + query.limit]

    async def _count_groups(self, query: GroupQuery) -> int:
        """按查询条件统计群组数量。"""

        if query.is_active is None:
            active_count = await self._group_repository.CountByIsActive(True)
            inactive_count = await self._group_repository.CountByIsActive(False)
            return active_count + inactive_count
        return await self._group_repository.CountByIsActive(query.is_active)

    async def _to_group_read(self, entity: Group) -> GroupRead:
        """把群组实体转换为详情响应。"""

        statistics = await self._collect_group_statistics(entity.id)
        return GroupRead.model_validate(
            {
                **entity.__dict__,
                **statistics,
            }
        )

    async def _to_group_list_item(self, entity: Group) -> GroupListItem:
        """把群组实体转换为列表项响应。"""

        statistics = await self._collect_group_statistics(entity.id)
        return GroupListItem.model_validate(
            {
                **entity.__dict__,
                **statistics,
            }
        )

    async def _collect_group_statistics(self, group_id: int) -> dict[str, int]:
        """收集群组详情和列表都需要的聚合统计。"""

        active_rules_count = await self._rule_repository.CountByGroupIdAndIsEnabled(group_id, True)
        pending_moderation_count = await self._moderation_repository.CountByGroupIdAndStatus(
            group_id,
            ModerationStatus.PENDING,
        )
        undeleted_message_count = await self._group_message_repository.CountByGroupIdAndIsDeleted(group_id, False)
        deleted_message_count = await self._group_message_repository.CountByGroupIdAndIsDeleted(group_id, True)
        return {
            "active_rules_count": active_rules_count,
            "pending_moderation_count": pending_moderation_count,
            "message_count": undeleted_message_count + deleted_message_count,
        }


__all__ = ["GroupService"]
