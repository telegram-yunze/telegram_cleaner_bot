from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ModerationAction, ModerationStatus
from app.models.json_types import ModerationResultDetail, PydanticJsonType

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.group_message import GroupMessage
    from app.models.group_user import GroupUser
    from app.models.notification_recall_record import NotificationRecallRecord
    from app.models.rule import Rule


class ModerationRecord(Base, TimestampMixin):
    """审核处置记录表，保存命中规则后的执行结果。"""

    __tablename__ = "moderation_records"
    __table_args__ = (
        Index("ix_moderation_records_group_status", "group_id", "status"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键 ID"
    )
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
    action: Mapped[ModerationAction] = mapped_column(
        SQLEnum(
            ModerationAction,
            name="enum_moderation_action",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        comment="执行动作",
    )
    status: Mapped[ModerationStatus] = mapped_column(
        SQLEnum(
            ModerationStatus,
            name="enum_moderation_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=ModerationStatus.PENDING,
        server_default=ModerationStatus.PENDING.value,
        comment="执行状态",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处置原因")
    result_detail: Mapped[ModerationResultDetail | None] = mapped_column(
        PydanticJsonType(ModerationResultDetail),
        nullable=True,
        comment="执行结果和补充细节",
    )

    group: Mapped["Group"] = relationship(back_populates="moderation_records")
    message: Mapped["GroupMessage | None"] = relationship(
        back_populates="moderation_records"
    )
    target_user: Mapped["GroupUser | None"] = relationship(
        back_populates="moderation_records"
    )
    rule: Mapped["Rule | None"] = relationship(back_populates="moderation_records")
    notification_recall_records: Mapped[list["NotificationRecallRecord"]] = (
        relationship(back_populates="moderation_record")
    )
