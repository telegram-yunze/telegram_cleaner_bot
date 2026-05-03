from __future__ import annotations

from collections.abc import Sequence

from app.models.rule import Rule
from app.repositories.moderation_repository import ModerationRepositoryProtocol
from app.repositories.rule_repository import RuleRepositoryProtocol
from app.schemas.rule import RuleCreate, RuleListItem, RuleListResponse, RuleQuery, RuleRead, RuleUpdate


class RuleService:
    """规则应用服务，编排规则增删改查与轻量统计。"""

    def __init__(
        self,
        rule_repository: RuleRepositoryProtocol,
        moderation_repository: ModerationRepositoryProtocol,
    ) -> None:
        self._rule_repository = rule_repository
        self._moderation_repository = moderation_repository

    async def Create(self, payload: RuleCreate) -> RuleRead:
        """创建规则并返回详情。"""

        entity = Rule(**payload.model_dump())
        saved_entity = await self._rule_repository.Save(entity)
        return await self._to_rule_read(saved_entity)

    async def FindById(self, rule_id: int) -> RuleRead | None:
        """按主键查询规则详情。"""

        entity = await self._rule_repository.FindById(rule_id)
        if entity is None:
            return None
        return await self._to_rule_read(entity)

    async def FindAll(self, query: RuleQuery) -> RuleListResponse:
        """按查询条件返回规则列表。"""

        entities = await self._find_rules_by_query(query)
        items = [await self._to_rule_list_item(entity) for entity in entities]
        return RuleListResponse(
            items=items,
            total=await self._count_rules(query),
            limit=query.limit,
            offset=query.offset,
        )

    async def FindEnabledByGroupId(self, group_id: int) -> Sequence[RuleRead]:
        """查询群组下启用中的规则列表。"""

        entities = await self._rule_repository.FindAllByGroupIdAndIsEnabledTrueOrderByPriorityAscIdAsc(group_id)
        return [await self._to_rule_read(entity) for entity in entities]

    async def UpdateById(self, rule_id: int, payload: RuleUpdate) -> RuleRead | None:
        """按主键更新规则。"""

        entity = await self._rule_repository.FindById(rule_id)
        if entity is None:
            return None

        update_values = payload.model_dump(exclude_unset=True)
        for field_name, field_value in update_values.items():
            setattr(entity, field_name, field_value)

        saved_entity = await self._rule_repository.Save(entity)
        return await self._to_rule_read(saved_entity)

    async def DeleteById(self, rule_id: int) -> bool:
        """按主键删除规则。"""

        return await self._rule_repository.DeleteById(rule_id)

    async def _find_rules_by_query(self, query: RuleQuery) -> Sequence[Rule]:
        """按查询条件过滤规则。"""

        if query.group_id is None:
            entities = list(await self._rule_repository.FindAllOrderByPriorityAscIdAsc())
        else:
            entities = list(await self._rule_repository.FindAllByGroupIdOrderByPriorityAscIdAsc(query.group_id))

        if query.is_enabled is not None:
            entities = [entity for entity in entities if entity.is_enabled == query.is_enabled]
        if query.rule_type is not None:
            entities = [entity for entity in entities if entity.rule_type == query.rule_type]
        return entities[query.offset : query.offset + query.limit]

    async def _count_rules(self, query: RuleQuery) -> int:
        """按查询条件统计规则数量。"""

        entities = await self._find_rules_by_query(
            RuleQuery(
                group_id=query.group_id,
                is_enabled=query.is_enabled,
                rule_type=query.rule_type,
                limit=10_000,
                offset=0,
            )
        )
        return len(entities)

    async def _to_rule_read(self, entity: Rule) -> RuleRead:
        """把规则实体转换为详情响应。"""

        related_moderation_count = await self._moderation_repository.CountByRuleId(entity.id)
        return RuleRead.model_validate(
            {
                **entity.__dict__,
                "related_moderation_count": related_moderation_count,
                "hit_count": related_moderation_count,
            }
        )

    async def _to_rule_list_item(self, entity: Rule) -> RuleListItem:
        """把规则实体转换为列表项。"""

        related_moderation_count = await self._moderation_repository.CountByRuleId(entity.id)
        return RuleListItem.model_validate(
            {
                **entity.__dict__,
                "related_moderation_count": related_moderation_count,
                "hit_count": related_moderation_count,
            }
        )


__all__ = ["RuleService"]
