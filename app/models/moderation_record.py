from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
	from app.models.group import Group
	from app.models.group_message import GroupMessage
	from app.models.group_user import GroupUser
	from app.models.rule import Rule


class ModerationRecord(Base, TimestampMixin):
	"""审核处置记录表，保存命中规则后的执行结果。"""

	__tablename__ = "moderation_records"

	id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键 ID")
	group_id: Mapped[int] = mapped_column(
		ForeignKey("groups.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
		comment="所属群组主键",
	)
	message_id: Mapped[int | None] = mapped_column(
		ForeignKey("group_messages.id", ondelete="SET NULL"),
		nullable=True,
		comment="关联消息主键",
	)
	target_user_id: Mapped[int | None] = mapped_column(
		ForeignKey("group_users.id", ondelete="SET NULL"),
		nullable=True,
		comment="被处置成员主键",
	)
	rule_id: Mapped[int | None] = mapped_column(
		ForeignKey("rules.id", ondelete="SET NULL"),
		nullable=True,
		comment="命中规则主键",
	)
	action: Mapped[str] = mapped_column(String(32), nullable=False, comment="执行动作")
	status: Mapped[str] = mapped_column(
		String(32),
		nullable=False,
		default="pending",
		server_default="pending",
		comment="执行状态",
	)
	reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处置原因")
	result_detail: Mapped[dict[str, Any] | None] = mapped_column(
		JSON,
		nullable=True,
		comment="执行结果和补充细节",
	)

	group: Mapped["Group"] = relationship(back_populates="moderation_records")
	message: Mapped["GroupMessage | None"] = relationship(back_populates="moderation_records")
	target_user: Mapped["GroupUser | None"] = relationship(back_populates="moderation_records")
	rule: Mapped["Rule | None"] = relationship(back_populates="moderation_records")
