from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import GroupChatType
from app.models.json_types import BotPermissions, GroupSettings, PydanticJsonType

if TYPE_CHECKING:
    from app.models.group_message import GroupMessage
    from app.models.group_user import GroupUser
    from app.models.moderation_record import ModerationRecord
    from app.models.notification_recall_record import NotificationRecallRecord
    from app.models.rule import Rule


class Group(Base, TimestampMixin):
    """群组表，保存接入机器人的 Telegram 群信息。"""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键 ID"
    )
    telegram_group_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="Telegram 群组 ID",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="群组名称")
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="群组公开用户名",
    )
    chat_type: Mapped[GroupChatType] = mapped_column(
        SQLEnum(
            GroupChatType,
            name="enum_group_chat_type",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        default=GroupChatType.SUPERGROUP,
        server_default=GroupChatType.SUPERGROUP.value,
        comment="群组类型",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="群组描述"
    )
    owner_telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="群主 Telegram 用户 ID",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="是否启用清理",
    )
    settings: Mapped[GroupSettings | None] = mapped_column(
        PydanticJsonType(GroupSettings),
        nullable=True,
        comment="群组维度的检测和处置配置",
    )
    bot_permissions: Mapped[BotPermissions | None] = mapped_column(
        PydanticJsonType(BotPermissions),
        nullable=True,
        comment="机器人在群里的权限配置",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="最近一条消息时间",
    )
    is_authorized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否已授权使用机器人",
    )
    info_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="上次从 Telegram 同步群组信息的时间",
    )

    users: Mapped[list["GroupUser"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["GroupMessage"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    moderation_records: Mapped[list["ModerationRecord"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )
    notification_recall_records: Mapped[list["NotificationRecallRecord"]] = (
        relationship(
            back_populates="group",
            cascade="all, delete-orphan",
        )
    )
