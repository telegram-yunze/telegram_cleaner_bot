from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule


class RuleRepositoryProtocol(Protocol):
	"""规则仓库接口，负责规则查询、排序和持久化。"""

	async def Save(self, entity: Rule) -> Rule: ...

	async def FindById(self, rule_id: int) -> Rule | None: ...

	async def FindByGroupIdAndCode(self, group_id: int, code: str) -> Rule | None: ...

	async def FindAllOrderByPriorityAscIdAsc(self) -> Sequence[Rule]: ...

	async def FindAllByGroupIdOrderByPriorityAscIdAsc(self, group_id: int) -> Sequence[Rule]: ...

	async def FindAllByGroupIdAndIsEnabledTrueOrderByPriorityAscIdAsc(self, group_id: int) -> Sequence[Rule]: ...

	async def ExistsByGroupIdAndCode(self, group_id: int, code: str) -> bool: ...

	async def CountByGroupIdAndIsEnabled(self, group_id: int, is_enabled: bool = True) -> int: ...

	async def DeleteById(self, rule_id: int) -> bool: ...


class RuleRepository(RuleRepositoryProtocol):
	"""规则仓库实现，供规则管理和命中检测流程复用。"""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def Save(self, entity: Rule) -> Rule:
		"""保存规则，并刷新数据库生成字段。"""

		merged_entity = await self._session.merge(entity)
		await self._session.flush()
		await self._session.refresh(merged_entity)
		return merged_entity

	async def FindById(self, rule_id: int) -> Rule | None:
		"""按主键查询规则。"""

		return await self._session.get(Rule, rule_id)

	async def FindByGroupIdAndCode(self, group_id: int, code: str) -> Rule | None:
		"""按群组和规则编码查询规则。"""

		stmt = select(Rule).where(Rule.group_id == group_id, Rule.code == code)
		return await self._session.scalar(stmt)

	async def FindAllOrderByPriorityAscIdAsc(self) -> Sequence[Rule]:
		"""按优先级升序查询全部规则。"""

		stmt = select(Rule).order_by(Rule.priority.asc(), Rule.id.asc())
		result = await self._session.scalars(stmt)
		return result.all()

	async def FindAllByGroupIdOrderByPriorityAscIdAsc(self, group_id: int) -> Sequence[Rule]:
		"""按优先级升序查询群组下全部规则。"""

		stmt = select(Rule).where(Rule.group_id == group_id).order_by(Rule.priority.asc(), Rule.id.asc())
		result = await self._session.scalars(stmt)
		return result.all()

	async def FindAllByGroupIdAndIsEnabledTrueOrderByPriorityAscIdAsc(self, group_id: int) -> Sequence[Rule]:
		"""查询群组下已启用规则，并按优先级排序。"""

		stmt = (
			select(Rule)
			.where(Rule.group_id == group_id, Rule.is_enabled.is_(True))
			.order_by(Rule.priority.asc(), Rule.id.asc())
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def ExistsByGroupIdAndCode(self, group_id: int, code: str) -> bool:
		"""判断指定规则编码是否已存在。"""

		stmt = select(func.count(Rule.id)).where(Rule.group_id == group_id, Rule.code == code)
		count = await self._session.scalar(stmt)
		return (count or 0) > 0

	async def CountByGroupIdAndIsEnabled(self, group_id: int, is_enabled: bool = True) -> int:
		"""统计群组下启用或停用的规则数量。"""

		stmt = select(func.count(Rule.id)).where(Rule.group_id == group_id, Rule.is_enabled == is_enabled)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def DeleteById(self, rule_id: int) -> bool:
		"""按主键删除规则。"""

		entity = await self.FindById(rule_id)
		if entity is None:
			return False

		await self._session.delete(entity)
		await self._session.flush()
		return True


__all__ = ["RuleRepositoryProtocol", "RuleRepository"]
