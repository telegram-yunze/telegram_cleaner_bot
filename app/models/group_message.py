from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.group_user import GroupUser
    from app.models.moderation_record import ModerationRecord


class GroupMessage(Base, TimestampMixin):
    """群组消息表，保存机器人识别和处置所需的消息快照。"""

    __tablename__ = "group_messages"
    __table_args__ = (
        UniqueConstraint("group_id", "telegram_message_id", name="uq_group_messages_group_msg"),
        Index("ix_group_messages_group_sent_at", "group_id", "sent_at"),
        Index("ix_group_messages_group_deleted", "group_id", "is_deleted"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键 ID")
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属群组主键",
    )
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("group_users.id", ondelete="SET NULL"),
        nullable=True,
        comment="发送者群组用户主键",
    )
    telegram_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Telegram 消息 ID",
    )
    telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="发送者 Telegram 用户 ID",
    )
    reply_to_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="被回复消息 ID",
    )
    message_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="text",
        server_default="text",
        comment="消息类型",
    )
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文本内容")
    content_extra: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="媒体、链接、按钮等补充内容",
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Telegram 原始更新片段",
    )
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True, comment="广告风险分")
    hit_rule_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="命中的规则编码",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否已删除",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="删除时间")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="消息发送时间",
    )

    group: Mapped["Group"] = relationship(back_populates="messages")
    sender: Mapped["GroupUser | None"] = relationship(back_populates="messages")
    moderation_records: Mapped[list["ModerationRecord"]] = relationship(back_populates="message")