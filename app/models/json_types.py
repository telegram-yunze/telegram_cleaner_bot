from __future__ import annotations

# 本文件用途：集中定义 JSON 列对应的结构体类型与 SQLAlchemy 适配器，
# 避免业务层直接操作 dict[str, Any] 导致语义不清。

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.types import JSON, TypeDecorator


class JsonStructBase(BaseModel):
    """JSON 结构体基类，默认允许扩展字段，兼容历史数据。"""

    model_config = ConfigDict(extra="allow")


class GroupSettings(JsonStructBase):
    """群组维度设置。"""

    ad_detection_enabled: bool | None = None
    auto_delete_enabled: bool | None = None
    mute_duration_seconds: int | None = None


class BotPermissions(JsonStructBase):
    """机器人在群内的权限快照。"""

    can_manage_chat: bool | None = None
    can_delete_messages: bool | None = None
    can_restrict_members: bool | None = None
    can_invite_users: bool | None = None
    can_pin_messages: bool | None = None
    can_manage_topics: bool | None = None


class RuleOptions(JsonStructBase):
    """规则扩展选项。"""

    threshold: float | None = None
    keywords: list[str] | None = None
    whitelist: list[str] | None = None


class ModerationResultDetail(JsonStructBase):
    """处置执行结果详情。"""

    success: bool | None = None
    provider: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class GroupUserProfileExtra(JsonStructBase):
    """群成员扩展资料。"""

    bio: str | None = None
    region: str | None = None
    tags: list[str] | None = None


class MessageContentExtra(JsonStructBase):
    """消息补充内容。"""

    links: list[str] | None = None
    mentions: list[str] | None = None
    media_type: str | None = None


class TelegramRawPayload(JsonStructBase):
    """Telegram 原始更新片段。"""

    update_id: int | None = None
    message: dict[str, Any] | None = None
    edited_message: dict[str, Any] | None = None


class PydanticJsonType(TypeDecorator[BaseModel | None]):
    """在 ORM 层把 Pydantic 结构体与 JSON 字段做双向转换。"""

    impl = JSON
    cache_ok = True

    def __init__(self, model_cls: type[JsonStructBase]) -> None:
        super().__init__()
        self._model_cls = model_cls

    def process_bind_param(self, value: Any, dialect: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, Mapping):
            return dict(value)
        raise TypeError(f"不支持的 JSON 绑定值类型: {type(value)!r}")

    def process_result_value(self, value: Any, dialect: Any) -> JsonStructBase | None:
        if value is None:
            return None
        if isinstance(value, self._model_cls):
            return value
        if isinstance(value, Mapping):
            try:
                return self._model_cls.model_validate(value)
            except ValidationError:
                # 历史脏数据兼容：解析失败时降级为空结构体，避免查询链路中断。
                return self._model_cls()
        return self._model_cls()


__all__ = [
    "JsonStructBase",
    "GroupSettings",
    "BotPermissions",
    "RuleOptions",
    "ModerationResultDetail",
    "GroupUserProfileExtra",
    "MessageContentExtra",
    "TelegramRawPayload",
    "PydanticJsonType",
]
