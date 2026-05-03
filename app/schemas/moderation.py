from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModerationAction, ModerationStatus


class ModerationRecordSchemaBase(BaseModel):
	"""审核记录公共字段。"""

	model_config = ConfigDict(from_attributes=True)

	action: ModerationAction = Field(..., description="执行动作")
	status: ModerationStatus = Field(default=ModerationStatus.PENDING, description="执行状态")
	reason: str | None = Field(default=None, description="处置原因")
	result_detail: dict[str, Any] | None = Field(default=None, description="执行结果详情")


class ModerationRecordCreate(ModerationRecordSchemaBase):
	"""创建审核记录请求。"""

	group_id: int = Field(..., description="所属群组主键")
	message_id: int | None = Field(default=None, description="关联消息主键")
	target_user_id: int | None = Field(default=None, description="被处置成员主键")
	rule_id: int | None = Field(default=None, description="命中规则主键")


class ModerationRecordUpdate(BaseModel):
	"""更新审核记录请求。"""

	model_config = ConfigDict(from_attributes=True)

	action: ModerationAction | None = Field(default=None, description="执行动作")
	status: ModerationStatus | None = Field(default=None, description="执行状态")
	reason: str | None = Field(default=None, description="处置原因")
	result_detail: dict[str, Any] | None = Field(default=None, description="执行结果详情")


class ModerationRecordRead(ModerationRecordSchemaBase):
	"""审核记录详情响应。"""

	id: int = Field(..., description="审核记录主键 ID")
	group_id: int = Field(..., description="所属群组主键")
	message_id: int | None = Field(default=None, description="关联消息主键")
	target_user_id: int | None = Field(default=None, description="被处置成员主键")
	rule_id: int | None = Field(default=None, description="命中规则主键")
	target_telegram_user_id: int | None = Field(default=None, description="被处置成员 Telegram 用户 ID")
	rule_code: str | None = Field(default=None, description="命中规则编码")
	created_at: datetime = Field(..., description="创建时间")
	updated_at: datetime = Field(..., description="更新时间")


class ModerationRecordListItem(BaseModel):
	"""审核记录列表项。"""

	model_config = ConfigDict(from_attributes=True)

	id: int = Field(..., description="审核记录主键 ID")
	group_id: int = Field(..., description="所属群组主键")
	message_id: int | None = Field(default=None, description="关联消息主键")
	target_user_id: int | None = Field(default=None, description="被处置成员主键")
	rule_id: int | None = Field(default=None, description="命中规则主键")
	action: ModerationAction = Field(..., description="执行动作")
	status: ModerationStatus = Field(..., description="执行状态")
	reason: str | None = Field(default=None, description="处置原因")
	target_telegram_user_id: int | None = Field(default=None, description="被处置成员 Telegram 用户 ID")
	rule_code: str | None = Field(default=None, description="命中规则编码")
	created_at: datetime = Field(..., description="创建时间")


class ModerationRecordListResponse(BaseModel):
	"""审核记录列表响应。"""

	items: list[ModerationRecordListItem] = Field(default_factory=list, description="审核记录列表")
	total: int = Field(default=0, ge=0, description="总记录数")
	limit: int = Field(default=20, ge=1, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


class ModerationRecordQuery(BaseModel):
	"""审核记录列表查询参数。"""

	group_id: int | None = Field(default=None, description="所属群组主键")
	status: ModerationStatus | None = Field(default=None, description="执行状态")
	limit: int = Field(default=20, ge=1, le=200, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


__all__ = [
	"ModerationRecordSchemaBase",
	"ModerationRecordCreate",
	"ModerationRecordUpdate",
	"ModerationRecordRead",
	"ModerationRecordListItem",
	"ModerationRecordListResponse",
	"ModerationRecordQuery",
]
