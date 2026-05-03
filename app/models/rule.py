from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ModerationAction, RuleType

if TYPE_CHECKING:
	from app.models.group import Group
	from app.models.moderation_record import ModerationRecord


class Rule(Base, TimestampMixin):
	"""群组规则表，定义广告识别和处置策略。"""

	__tablename__ = "rules"
	__table_args__ = (
		UniqueConstraint("group_id", "code", name="uq_rules_group_code"),
		CheckConstraint("priority >= 0", name="ck_rules_priority_non_negative"),
	)

	id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键 ID")
	group_id: Mapped[int] = mapped_column(
		ForeignKey("groups.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
		comment="所属群组主键",
	)
	code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="规则编码")
	name: Mapped[str] = mapped_column(String(255), nullable=False, comment="规则名称")
	rule_type: Mapped[RuleType] = mapped_column(
		SQLEnum(
			RuleType,
			name="enum_rule_type",
			native_enum=False,
			validate_strings=True,
			create_constraint=True,
		),
		nullable=False,
		comment="规则类型",
	)
	pattern: Mapped[str | None] = mapped_column(Text, nullable=True, comment="关键词或正则")
	action: Mapped[ModerationAction] = mapped_column(
		SQLEnum(
			ModerationAction,
			name="enum_rule_action",
			native_enum=False,
			validate_strings=True,
			create_constraint=True,
		),
		nullable=False,
		default=ModerationAction.DELETE,
		server_default=ModerationAction.DELETE.value,
		comment="命中后动作",
	)
	priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100", comment="优先级")
	is_enabled: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=True,
		server_default="1",
		comment="是否启用",
	)
	options: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="规则额外配置")

	group: Mapped["Group"] = relationship(back_populates="rules")
	moderation_records: Mapped[list["ModerationRecord"]] = relationship(back_populates="rule")
