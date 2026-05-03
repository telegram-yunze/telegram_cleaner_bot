from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import NotificationRecallStatus

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.moderation_record import ModerationRecord


class NotificationRecallRecord(Base, TimestampMixin):
    """通知消息撤回记录表，专门跟踪需要自动撤回的提示消息。"""

    __tablename__ = "notification_recall_records"
    __table_args__ = (
        Index(
            "ix_notification_recalls_status_scheduled", "status", "scheduled_recall_at"
        ),
        Index("ix_notification_recalls_group_status", "group_id", "status"),
        CheckConstraint(
            "recall_after_seconds >= 5", name="ck_notification_recalls_min_delay_5"
        ),
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
    moderation_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("moderation_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联处置记录主键",
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Telegram chat_id"
    )
    notification_message_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="待撤回的通知消息 ID"
    )
    recall_after_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        comment="延迟撤回秒数，默认 5 秒，最小 5 秒",
    )
    scheduled_recall_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="计划撤回时间"
    )
    recalled_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="实际撤回时间"
    )
    status: Mapped[NotificationRecallStatus] = mapped_column(
        SQLEnum(
            NotificationRecallStatus,
            name="enum_notification_recall_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=NotificationRecallStatus.PENDING,
        server_default=NotificationRecallStatus.PENDING.value,
        comment="撤回执行状态",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="撤回执行尝试次数",
    )
    fail_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="撤回失败原因"
    )

    group: Mapped["Group"] = relationship(back_populates="notification_recall_records")
    moderation_record: Mapped["ModerationRecord | None"] = relationship(
        back_populates="notification_recall_records"
    )
