from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ModerationAction, RuleType
from app.models.json_types import RuleOptions


class RuleSchemaBase(BaseModel):
	"""规则公共字段。"""

	model_config = ConfigDict(from_attributes=True)

	code: str = Field(..., max_length=64, description="规则编码")
	name: str = Field(..., max_length=255, description="规则名称")
	rule_type: RuleType = Field(..., description="规则类型")
	pattern: str | None = Field(default=None, description="关键词或正则")
	action: ModerationAction = Field(default=ModerationAction.DELETE, description="命中后动作")
	priority: int = Field(default=100, ge=0, description="优先级")
	is_enabled: bool = Field(default=True, description="是否启用")
	options: RuleOptions | None = Field(default=None, description="规则扩展配置")


class RuleCreate(RuleSchemaBase):
	"""创建规则请求。"""

	group_id: int = Field(..., description="所属群组主键")


class RuleUpdate(BaseModel):
	"""更新规则请求。"""

	model_config = ConfigDict(from_attributes=True)

	code: str | None = Field(default=None, max_length=64, description="规则编码")
	name: str | None = Field(default=None, max_length=255, description="规则名称")
	rule_type: RuleType | None = Field(default=None, description="规则类型")
	pattern: str | None = Field(default=None, description="关键词或正则")
	action: ModerationAction | None = Field(default=None, description="命中后动作")
	priority: int | None = Field(default=None, ge=0, description="优先级")
	is_enabled: bool | None = Field(default=None, description="是否启用")
	options: RuleOptions | None = Field(default=None, description="规则扩展配置")


class RuleRead(RuleSchemaBase):
	"""规则详情响应。"""

	id: int = Field(..., description="规则主键 ID")
	group_id: int = Field(..., description="所属群组主键")
	related_moderation_count: int = Field(default=0, ge=0, description="关联处置记录数")
	hit_count: int = Field(default=0, ge=0, description="命中次数")
	created_at: datetime = Field(..., description="创建时间")
	updated_at: datetime = Field(..., description="更新时间")


class RuleListItem(BaseModel):
	"""规则列表项。"""

	model_config = ConfigDict(from_attributes=True)

	id: int = Field(..., description="规则主键 ID")
	group_id: int = Field(..., description="所属群组主键")
	code: str = Field(..., description="规则编码")
	name: str = Field(..., description="规则名称")
	rule_type: RuleType = Field(..., description="规则类型")
	action: ModerationAction = Field(..., description="命中后动作")
	priority: int = Field(..., ge=0, description="优先级")
	is_enabled: bool = Field(..., description="是否启用")
	related_moderation_count: int = Field(default=0, ge=0, description="关联处置记录数")
	hit_count: int = Field(default=0, ge=0, description="命中次数")
	created_at: datetime = Field(..., description="创建时间")


class RuleListResponse(BaseModel):
	"""规则列表响应。"""

	items: list[RuleListItem] = Field(default_factory=list, description="规则列表")
	total: int = Field(default=0, ge=0, description="总记录数")
	limit: int = Field(default=20, ge=1, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


class RuleQuery(BaseModel):
	"""规则列表查询参数。"""

	group_id: int | None = Field(default=None, description="所属群组主键")
	is_enabled: bool | None = Field(default=None, description="是否启用")
	rule_type: RuleType | None = Field(default=None, description="规则类型")
	limit: int = Field(default=20, ge=1, le=200, description="分页大小")
	offset: int = Field(default=0, ge=0, description="分页偏移")


__all__ = [
	"RuleSchemaBase",
	"RuleCreate",
	"RuleUpdate",
	"RuleRead",
	"RuleListItem",
	"RuleListResponse",
	"RuleQuery",
]
