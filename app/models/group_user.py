from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, JSON, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import GroupUserRole, GroupUserStatus

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.group_message import GroupMessage
    from app.models.moderation_record import ModerationRecord


class GroupUser(Base, TimestampMixin):
    """群组用户表，记录成员在具体群内的资料和身份。"""

    __tablename__ = "group_users"
    __table_args__ = (
        UniqueConstraint("group_id", "telegram_user_id", name="uq_group_users_group_user"),
        Index("ix_group_users_group_role", "group_id", "role"),
        Index("ix_group_users_group_status", "group_id", "status"),
        CheckConstraint(
            "left_at IS NULL OR joined_at IS NULL OR left_at >= joined_at",
            name="ck_group_users_left_after_joined",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键 ID")
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属群组主键",
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Telegram 用户 ID",
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="用户名")
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="名")
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="姓")
    language_code: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="语言代码",
    )
    role: Mapped[GroupUserRole] = mapped_column(
        SQLEnum(
            GroupUserRole,
            name="enum_group_user_role",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=GroupUserRole.MEMBER,
        server_default=GroupUserRole.MEMBER.value,
        comment="群内角色",
    )
    status: Mapped[GroupUserStatus] = mapped_column(
        SQLEnum(
            GroupUserStatus,
            name="enum_group_user_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=GroupUserStatus.ACTIVE,
        server_default=GroupUserStatus.ACTIVE.value,
        comment="成员状态",
    )
    is_bot: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否机器人账号",
    )
    is_whitelisted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否白名单成员",
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="入群时间")
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="离群时间")
    profile_extra: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="补充资料",
    )

    group: Mapped["Group"] = relationship(back_populates="users")
    messages: Mapped[list["GroupMessage"]] = relationship(back_populates="sender")
    moderation_records: Mapped[list["ModerationRecord"]] = relationship(back_populates="target_user")