from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GroupUserStatus
from app.models.group import Group
from app.models.group_message import GroupMessage
from app.models.group_user import GroupUser


class GroupRepositoryProtocol(Protocol):
	"""群组仓库接口，约束群组维度的读写能力。"""

	async def Save(self, entity: Group) -> Group: ...

	async def FindById(self, group_id: int) -> Group | None: ...

	async def FindByTelegramGroupId(self, telegram_group_id: int) -> Group | None: ...

	async def FindAllByIsActive(self, is_active: bool = True) -> Sequence[Group]: ...

	async def ExistsByTelegramGroupId(self, telegram_group_id: int) -> bool: ...

	async def CountByIsActive(self, is_active: bool = True) -> int: ...

	async def UpdateLastMessageAtByTelegramGroupId(
		self,
		telegram_group_id: int,
		last_message_at: datetime,
	) -> int: ...

	async def FindAllByInfoUpdatedAtBefore(self, threshold: datetime) -> Sequence[Group]: ...

	async def UpdateGroupInfoById(
		self,
		group_id: int,
		title: str | None,
		username: str | None,
		description: str | None,
		info_updated_at: datetime,
	) -> int: ...

	async def DeleteById(self, group_id: int) -> bool: ...


class GroupUserRepositoryProtocol(Protocol):
	"""群成员仓库接口，负责群成员状态和资料查询。"""

	async def Save(self, entity: GroupUser) -> GroupUser: ...

	async def FindById(self, group_user_id: int) -> GroupUser | None: ...

	async def FindByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int) -> GroupUser | None: ...

	async def FindAllByGroupIdAndStatus(
		self,
		group_id: int,
		status: GroupUserStatus = GroupUserStatus.ACTIVE,
	) -> Sequence[GroupUser]: ...

	async def ExistsByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int) -> bool: ...

	async def CountByGroupIdAndStatus(self, group_id: int, status: GroupUserStatus = GroupUserStatus.ACTIVE) -> int: ...

	async def UpdateStatusByGroupIdAndTelegramUserId(
		self,
		group_id: int,
		telegram_user_id: int,
		status: GroupUserStatus,
	) -> int: ...


class GroupMessageRepositoryProtocol(Protocol):
	"""群消息仓库接口，负责消息快照查询和删除状态更新。"""

	async def Save(self, entity: GroupMessage) -> GroupMessage: ...

	async def FindById(self, message_id: int) -> GroupMessage | None: ...

	async def FindByGroupIdAndTelegramMessageId(self, group_id: int, telegram_message_id: int) -> GroupMessage | None: ...

	async def FindAllByGroupIdOrderBySentAtDesc(
		self,
		group_id: int,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[GroupMessage]: ...

	async def FindAllByGroupIdAndIsDeleted(self, group_id: int, is_deleted: bool) -> Sequence[GroupMessage]: ...

	async def ExistsByGroupIdAndTelegramMessageId(self, group_id: int, telegram_message_id: int) -> bool: ...

	async def CountByGroupIdAndIsDeleted(self, group_id: int, is_deleted: bool) -> int: ...

	async def UpdateHitResultById(
		self,
		message_id: int,
		hit_rule_code: str | None,
		risk_score: float | None,
	) -> int: ...

	async def MarkDeletedByGroupIdAndTelegramMessageId(
		self,
		group_id: int,
		telegram_message_id: int,
		deleted_at: datetime,
	) -> int: ...


class GroupRepository(GroupRepositoryProtocol):
	"""群组仓库实现，提供群组维度的常用持久化操作。"""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def Save(self, entity: Group) -> Group:
		"""保存群组实体，并在当前事务中刷新主键和默认值。"""

		merged_entity = await self._session.merge(entity)
		await self._session.flush()
		await self._session.refresh(merged_entity)
		return merged_entity

	async def FindById(self, group_id: int) -> Group | None:
		"""按主键查询群组。"""

		return await self._session.get(Group, group_id)

	async def FindByTelegramGroupId(self, telegram_group_id: int) -> Group | None:
		"""按 Telegram 群 ID 查询群组。"""

		stmt = select(Group).where(Group.telegram_group_id == telegram_group_id)
		return await self._session.scalar(stmt)

	async def FindAllByIsActive(self, is_active: bool = True) -> Sequence[Group]:
		"""按启用状态查询群组列表。"""

		stmt = select(Group).where(Group.is_active == is_active).order_by(Group.id.asc())
		result = await self._session.scalars(stmt)
		return result.all()

	async def ExistsByTelegramGroupId(self, telegram_group_id: int) -> bool:
		"""判断指定 Telegram 群是否已接入。"""

		stmt = select(func.count(Group.id)).where(Group.telegram_group_id == telegram_group_id)
		count = await self._session.scalar(stmt)
		return (count or 0) > 0

	async def CountByIsActive(self, is_active: bool = True) -> int:
		"""统计指定启用状态的群组数量。"""

		stmt = select(func.count(Group.id)).where(Group.is_active == is_active)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def UpdateLastMessageAtByTelegramGroupId(
		self,
		telegram_group_id: int,
		last_message_at: datetime,
	) -> int:
		"""更新群组最近消息时间，用于活跃度统计和增量同步。"""

		stmt = (
			update(Group)
			.where(Group.telegram_group_id == telegram_group_id)
			.values(last_message_at=last_message_at)
		)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)

	async def FindAllByInfoUpdatedAtBefore(self, threshold: datetime) -> Sequence[Group]:
		"""查询信息更新时间早于阈值（含未同步）的群组列表。"""

		stmt = (
			select(Group)
			.where(
				(Group.info_updated_at.is_(None)) | (Group.info_updated_at < threshold)
			)
			.order_by(Group.id.asc())
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def UpdateGroupInfoById(
		self,
		group_id: int,
		title: str | None,
		username: str | None,
		description: str | None,
		info_updated_at: datetime,
	) -> int:
		"""按主键更新群组资料字段，并刷新信息更新时间。"""

		values: dict[str, object] = {
			"info_updated_at": info_updated_at,
		}
		if title is not None:
			values["title"] = title
		if username is not None:
			values["username"] = username
		if description is not None:
			values["description"] = description

		stmt = update(Group).where(Group.id == group_id).values(**values)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)

	async def DeleteById(self, group_id: int) -> bool:
		"""按主键删除群组。"""

		entity = await self.FindById(group_id)
		if entity is None:
			return False

		await self._session.delete(entity)
		await self._session.flush()
		return True


class GroupUserRepository(GroupUserRepositoryProtocol):
	"""群成员仓库实现，封装群成员的常用查询和状态变更。"""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def Save(self, entity: GroupUser) -> GroupUser:
		"""保存群成员实体，并刷新数据库生成字段。"""

		merged_entity = await self._session.merge(entity)
		await self._session.flush()
		await self._session.refresh(merged_entity)
		return merged_entity

	async def FindById(self, group_user_id: int) -> GroupUser | None:
		"""按主键查询群成员。"""

		return await self._session.get(GroupUser, group_user_id)

	async def FindByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int) -> GroupUser | None:
		"""按群组和 Telegram 用户 ID 查询成员。"""

		stmt = select(GroupUser).where(
			GroupUser.group_id == group_id,
			GroupUser.telegram_user_id == telegram_user_id,
		)
		return await self._session.scalar(stmt)

	async def FindAllByGroupIdAndStatus(
		self,
		group_id: int,
		status: GroupUserStatus = GroupUserStatus.ACTIVE,
	) -> Sequence[GroupUser]:
		"""按群组和成员状态查询成员列表。"""

		stmt = (
			select(GroupUser)
			.where(GroupUser.group_id == group_id, GroupUser.status == status)
			.order_by(GroupUser.id.asc())
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def ExistsByGroupIdAndTelegramUserId(self, group_id: int, telegram_user_id: int) -> bool:
		"""判断成员是否已经在指定群组中建档。"""

		stmt = select(func.count(GroupUser.id)).where(
			GroupUser.group_id == group_id,
			GroupUser.telegram_user_id == telegram_user_id,
		)
		count = await self._session.scalar(stmt)
		return (count or 0) > 0

	async def CountByGroupIdAndStatus(self, group_id: int, status: GroupUserStatus = GroupUserStatus.ACTIVE) -> int:
		"""统计群内指定状态的成员数量。"""

		stmt = select(func.count(GroupUser.id)).where(GroupUser.group_id == group_id, GroupUser.status == status)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def UpdateStatusByGroupIdAndTelegramUserId(
		self,
		group_id: int,
		telegram_user_id: int,
		status: GroupUserStatus,
	) -> int:
		"""更新成员状态，供离群、封禁、恢复等场景复用。"""

		stmt = (
			update(GroupUser)
			.where(GroupUser.group_id == group_id, GroupUser.telegram_user_id == telegram_user_id)
			.values(status=status)
		)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)


class GroupMessageRepository(GroupMessageRepositoryProtocol):
	"""群消息仓库实现，负责消息去重、查询和删除状态维护。"""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def Save(self, entity: GroupMessage) -> GroupMessage:
		"""保存消息快照，并刷新数据库生成字段。"""

		merged_entity = await self._session.merge(entity)
		await self._session.flush()
		await self._session.refresh(merged_entity)
		return merged_entity

	async def FindById(self, message_id: int) -> GroupMessage | None:
		"""按主键查询消息。"""

		return await self._session.get(GroupMessage, message_id)

	async def FindByGroupIdAndTelegramMessageId(self, group_id: int, telegram_message_id: int) -> GroupMessage | None:
		"""按群组和 Telegram 消息 ID 查询消息，用于去重。"""

		stmt = select(GroupMessage).where(
			GroupMessage.group_id == group_id,
			GroupMessage.telegram_message_id == telegram_message_id,
		)
		return await self._session.scalar(stmt)

	async def FindAllByGroupIdOrderBySentAtDesc(
		self,
		group_id: int,
		limit: int = 50,
		offset: int = 0,
	) -> Sequence[GroupMessage]:
		"""按发送时间倒序查询群消息列表，便于后台列表和最近消息分析。"""

		stmt = (
			select(GroupMessage)
			.where(GroupMessage.group_id == group_id)
			.order_by(GroupMessage.sent_at.desc(), GroupMessage.id.desc())
			.limit(limit)
			.offset(offset)
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def FindAllByGroupIdAndIsDeleted(self, group_id: int, is_deleted: bool) -> Sequence[GroupMessage]:
		"""按群组和删除状态查询消息。"""

		stmt = (
			select(GroupMessage)
			.where(GroupMessage.group_id == group_id, GroupMessage.is_deleted == is_deleted)
			.order_by(GroupMessage.sent_at.desc(), GroupMessage.id.desc())
		)
		result = await self._session.scalars(stmt)
		return result.all()

	async def ExistsByGroupIdAndTelegramMessageId(self, group_id: int, telegram_message_id: int) -> bool:
		"""判断消息快照是否已存在。"""

		stmt = select(func.count(GroupMessage.id)).where(
			GroupMessage.group_id == group_id,
			GroupMessage.telegram_message_id == telegram_message_id,
		)
		count = await self._session.scalar(stmt)
		return (count or 0) > 0

	async def CountByGroupIdAndIsDeleted(self, group_id: int, is_deleted: bool) -> int:
		"""统计群组下已删除或未删除的消息数量。"""

		stmt = select(func.count(GroupMessage.id)).where(
			GroupMessage.group_id == group_id,
			GroupMessage.is_deleted == is_deleted,
		)
		count = await self._session.scalar(stmt)
		return int(count or 0)

	async def UpdateHitResultById(
		self,
		message_id: int,
		hit_rule_code: str | None,
		risk_score: float | None,
	) -> int:
		"""按消息主键回写命中规则与风险分。"""

		stmt = (
			update(GroupMessage)
			.where(GroupMessage.id == message_id)
			.values(hit_rule_code=hit_rule_code, risk_score=risk_score)
		)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)

	async def MarkDeletedByGroupIdAndTelegramMessageId(
		self,
		group_id: int,
		telegram_message_id: int,
		deleted_at: datetime,
	) -> int:
		"""将消息标记为已删除，而不是物理删除记录。"""

		stmt = (
			update(GroupMessage)
			.where(
				GroupMessage.group_id == group_id,
				GroupMessage.telegram_message_id == telegram_message_id,
			)
			.values(is_deleted=True, deleted_at=deleted_at)
		)
		result = cast(CursorResult[object], await self._session.execute(stmt))
		await self._session.flush()
		return int(result.rowcount or 0)


__all__ = [
	"GroupRepositoryProtocol",
	"GroupUserRepositoryProtocol",
	"GroupMessageRepositoryProtocol",
	"GroupRepository",
	"GroupUserRepository",
	"GroupMessageRepository",
]
