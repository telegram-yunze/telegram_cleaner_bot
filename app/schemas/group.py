from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GroupChatType
from app.models.json_types import BotPermissions, GroupSettings


class GroupSchemaBase(BaseModel):
	"""群组公共字段。"""

	model_config = ConfigDict(from_attributes=True)

	title: str = Field(..., max_length=255, description="群组名称")
	username: str | None = Field(default=None, max_length=255, description="群组公开用户名")
	chat_type: GroupChatType = Field(default=GroupChatType.SUPERGROUP, description="群组类型")
	description: str | None = Field(default=None, description="群组描述")
	owner_telegram_user_id: int | None = Field(default=None, description="群主 Telegram 用户 ID")
	is_active: bool = Field(default=True, description="是否启用清理")
	settings: GroupSettings | None = Field(default=None, description="群组维度配置")
	bot_permissions: BotPermissions | None = Field(default=None, description="机器人在群里的权限配置")


class GroupCreate(GroupSchemaBase):
	"""创建群组请求。"""

	telegram_group_id: int = Field(..., description="Telegram 群组 ID")


class GroupUpdate(BaseModel):
	"""更新群组请求。"""

	model_config = ConfigDict(from_attributes=True)

	title: str | None = Field(default=None, max_length=255, description="群组名称")
	username: str | None = Field(default=None, max_length=255, description="群组公开用户名")
	chat_type: GroupChatType | None = Field(default=None, description="群组类型")
	description: str | None = Field(default=None, description="群组描述")
	owner_telegram_user_id: int | None = Field(default=None, description="群主 Telegram 用户 ID")
	is_active: bool | None = Field(default=None, description="是否启用清理")
	settings: GroupSettings | None = Field(default=None, description="群组维度配置")
	bot_permissions: BotPermissions | None = Field(default=None, description="机器人在群里的权限配置")


class GroupRead(GroupSchemaBase):
	"""群组详情响应。"""

	id: int = Field(..., description="群组主键 ID")
	telegram_group_id: int = Field(..., description="Telegram 群组 ID")
	last_message_at: datetime | None = Field(default=None, description="最近消息时间")
	active_rules_count: int = Field(default=0, ge=0, description="启用规则数量")
	pending_moderation_count: int = Field(default=0, ge=0, description="待处理处置数量")
	message_count: int = Field(default=0, ge=0, description="消息总数")
	created_at: datetime = Field(..., description="创建时间")
	updated_at: datetime = Field(..., description="更新时间")


class GroupListItem(BaseModel):
	"""群组列表项。"""

	model_config = ConfigDict(from_attributes=True)

	id: int = Field(..., description="群组主键 ID")
	telegram_group_id: int = Field(..., description="Telegram 群组 ID")
	title: str = Field(..., description="群组名称")
	username: str | None = Field(default=None, description="群组公开用户名")
	chat_type: GroupChatType = Field(..., description="群组类型")
	is_active: bool = Field(..., description="是否启用清理")
	last_message_at: datetime | None = Field(default=None, description="最近消息时间")
	active_rules_count: int = Field(default=0, ge=0, description="启用规则数量")
	pending_moderation_count: int = Field(default=0, ge=0, description="待处理处置数量")
	message_count: int = Field(default=0, ge=0, description="消息总数")
	created_at: datetime = Field(..., description="创建时间")


class GroupListResponse(BaseModel):
	"""群组列表响应。"""

	items: list[GroupListItem] = Field(default_factory=list, description="群组列表")
	total: int = Field(default=0, ge=0, description="总记录数")
	limit: int = Field(default=20, ge=1, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


class GroupQuery(BaseModel):
	"""群组列表查询参数。"""

	is_active: bool | None = Field(default=None, description="是否启用过滤")
	limit: int = Field(default=20, ge=1, le=200, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


__all__ = [
	"GroupSchemaBase",
	"GroupCreate",
	"GroupUpdate",
	"GroupRead",
	"GroupListItem",
	"GroupListResponse",
	"GroupQuery",
]
