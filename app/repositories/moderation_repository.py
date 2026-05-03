from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ModerationStatus
from app.models.json_types import ModerationResultDetail
from app.models.moderation_record import ModerationRecord


class ModerationRepositoryProtocol(Protocol):
	"""审核记录仓库接口，负责处置记录写入和状态追踪。"""

	async def Save(self, entity: ModerationRecord) -> ModerationRecord: ...

	async def FindById(self, moderation_record_id: int) -> ModerationRecord | None: ...

	async def FindLatestByMessageId(self, message_id: int) -> ModerationRecord | None: ...

	async def FindAllOrderByCreatedAtDesc(
		self,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]: ...

	async def FindAllByGroupIdOrderByCreatedAtDesc(
		self,
		group_id: int,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]: ...

	async def FindAllByGroupIdAndStatusOrderByCreatedAtDesc(
		self,
		group_id: int,
		status: ModerationStatus,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]: ...

	async def CountByGroupIdAndStatus(self, group_id: int, status: ModerationStatus) -> int: ...

	async def CountByRuleId(self, rule_id: int) -> int: ...

	async def UpdateStatusById(
		self,
		moderation_record_id: int,
		status: ModerationStatus,
		result_detail: ModerationResultDetail | None = None,
	) -> int: ...


class ModerationRepository(ModerationRepositoryProtocol):
	"""审核记录仓库实现，封装处置记录的列表、统计和状态更新。"""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def Save(self, entity: ModerationRecord) -> ModerationRecord:
		"""保存审核记录，并刷新数据库生成字段。"""

		merged_entity = await self._session.merge(entity)
		await self._session.flush()
		await self._session.refresh(merged_entity)
		return merged_entity

	async def FindById(self, moderation_record_id: int) -> ModerationRecord | None:
		"""按主键查询审核记录。"""

		return await self._session.get(ModerationRecord, moderation_record_id)

	async def FindLatestByMessageId(self, message_id: int) -> ModerationRecord | None:
		"""查询某条消息最近一次产生的处置记录。"""

		stmt = (
			select(ModerationRecord)
			.where(ModerationRecord.message_id == message_id)
			.order_by(ModerationRecord.created_at.desc(), ModerationRecord.id.desc())
			.limit(1)
		)
		return await self._session.scalar(stmt)

	async def FindAllOrderByCreatedAtDesc(
		self,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]:
		"""按创建时间倒序查询全部处置记录。"""

		stmt = (
			select(ModerationRecord)
			.order_by(ModerationRecord.created_at.desc(), ModerationRecord.id.desc())
			.limit(limit)
			.offset(offset)
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def FindAllByGroupIdOrderByCreatedAtDesc(
		self,
		group_id: int,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]:
		"""按创建时间倒序查询群组处置记录。"""

		stmt = (
			select(ModerationRecord)
			.where(ModerationRecord.group_id == group_id)
			.order_by(ModerationRecord.created_at.desc(), ModerationRecord.id.desc())
			.limit(limit)
			.offset(offset)
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def FindAllByGroupIdAndStatusOrderByCreatedAtDesc(
		self,
		group_id: int,
		status: ModerationStatus,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[ModerationRecord]:
		"""按群组和执行状态倒序查询处置记录。"""

		stmt = (
			select(ModerationRecord)
			.where(ModerationRecord.group_id == group_id, ModerationRecord.status == status)
			.order_by(ModerationRecord.created_at.desc(), ModerationRecord.id.desc())
			.limit(limit)
			.offset(offset)
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def CountByGroupIdAndStatus(self, group_id: int, status: ModerationStatus) -> int:
		"""统计群组下指定执行状态的处置记录数量。"""

		stmt = select(func.count(ModerationRecord.id)).where(
			ModerationRecord.group_id == group_id,
			ModerationRecord.status == status,
		)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def CountByRuleId(self, rule_id: int) -> int:
		"""统计某条规则关联的处置记录数量。"""

		stmt = select(func.count(ModerationRecord.id)).where(ModerationRecord.rule_id == rule_id)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def UpdateStatusById(
		self,
		moderation_record_id: int,
		status: ModerationStatus,
		result_detail: ModerationResultDetail | None = None,
	) -> int:
		"""更新处置记录执行状态，并可选覆盖执行结果细节。"""

		values: dict[str, Any] = {"status": status}
		if result_detail is not None:
			values["result_detail"] = result_detail

		stmt = update(ModerationRecord).where(ModerationRecord.id == moderation_record_id).values(**values)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)


__all__ = ["ModerationRepositoryProtocol", "ModerationRepository"]
