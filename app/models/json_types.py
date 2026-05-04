from __future__ import annotations

# 本文件用途：集中定义 JSON 列对应的结构体类型与 SQLAlchemy 适配器，
# 避免业务层直接操作 dict[str, Any] 导致语义不清。

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from sqlalchemy.types import JSON, TypeDecorator


class JsonStructBase(BaseModel):
    """JSON 结构体基类，默认允许扩展字段，兼容历史数据。"""

    model_config = ConfigDict(extra="allow")


class PunishmentPolicy(JsonStructBase):
    """群组级别的自动惩罚升级策略配置。"""

    # 是否启用自动升级惩罚（False 时每次固定执行规则指定动作）
    auto_escalate: bool | None = None
    # 最多警告多少次后自动升级为禁言（达到阈值时触发 MUTE）
    warn_threshold: int | None = None
    # 最多禁言多少次后自动升级为踢出（达到阈值时触发 KICK）
    mute_threshold: int | None = None
    # 最多踢出多少次后自动升级为封禁（达到阈值时触发 BAN）
    kick_threshold: int | None = None
    # 临时禁言默认时长（秒），为 None 时由规则 options.mute_duration_seconds 决定
    default_mute_seconds: int | None = None
    # 权限限制默认时长（秒），为 None 时由规则 options 决定
    default_restrict_seconds: int | None = None


class GroupSettings(JsonStructBase):
    """群组维度设置。"""

    # 是否开启广告检测功能
    ad_detection_enabled: bool | None = None
    # 是否开启自动删除违规消息
    auto_delete_enabled: bool | None = None
    # 禁言时长（秒），为 None 时使用系统默认
    mute_duration_seconds: int | None = None
    # 自动惩罚升级策略，为 None 时使用系统默认策略（不自动升级）
    punishment_policy: PunishmentPolicy | None = None
    # 是否在处置后发送提示消息；False 时静默处置
    notify_enabled: bool | None = None
    # 提示消息是否自动撤回；仅在 notify_enabled=True 时有意义
    notify_auto_recall: bool | None = None
    # 自动撤回延迟秒数，默认 5 秒，最小 5 秒
    notify_recall_delay_seconds: int = 5

    @field_validator("notify_recall_delay_seconds", mode="before")
    @classmethod
    def normalize_notify_recall_delay_seconds(cls, value: Any) -> int:
        """把提示消息撤回延迟归一化为不小于 5 秒。"""

        if value is None or value == "":
            return 5
        delay = int(value)
        if delay < 5:
            return 5
        return delay


class BotPermissions(JsonStructBase):
    """机器人在群内的权限快照，由 Telegram API 同步写入。"""

    # 是否拥有群组管理权限
    can_manage_chat: bool | None = None
    # 是否可以删除消息
    can_delete_messages: bool | None = None
    # 是否可以限制或封禁成员
    can_restrict_members: bool | None = None
    # 是否可以邀请新成员
    can_invite_users: bool | None = None
    # 是否可以置顶消息
    can_pin_messages: bool | None = None
    # 是否可以管理话题（超级群 Forum 模式）
    can_manage_topics: bool | None = None


class RuleOptions(JsonStructBase):
    """规则扩展选项，用于精细化控制规则的匹配行为。"""

    # 命中阈值（0.0～1.0），低于此值不触发动作
    threshold: float | None = None
    # 关键词列表，规则类型为 KEYWORD 时生效
    keywords: list[str] | None = None
    # 白名单关键词，命中后跳过处置
    whitelist: list[str] | None = None


class ModerationResultDetail(JsonStructBase):
    """处置执行结果详情，记录执行成功与否及惩罚细节。"""

    # 执行是否成功
    success: bool | None = None
    # 执行动作的服务提供方，如 telegram、manual
    provider: str | None = None
    # 失败时的错误码（由下游服务返回）
    error_code: str | None = None
    # 失败时的错误描述文本
    error_message: str | None = None
    # 本次是否已将用户踢出群组
    kicked: bool | None = None
    # 禁言到期时间（ISO8601 格式字符串），None 表示永久禁言或未禁言，需结合 action 判断
    muted_until: str | None = None
    # 权限限制到期时间（ISO8601 格式字符串），None 表示未限制或已解除
    restricted_until: str | None = None
    # 本次处置触发的自动升级动作（如从 WARN 升级为 MUTE），None 表示无升级
    escalated_to: str | None = None
    # 命中的规则原因文案，便于详情接口展示结构化决策依据
    rule_reason: str | None = None
    # 检测器返回的结构化原因列表（例如 contains_link、ad_keywords_detected）
    # 标准 token 集合：contains_link、contains_mention、ad_keywords_detected、short_text_with_link、empty_text、base_score
    detector_reasons: list[str] | None = None
    # 检测器计算得到的风险分（0~1）
    risk_score: float | None = None


class GroupUserProfileExtra(JsonStructBase):
    """群成员扩展资料，用于补充 Telegram 未直接提供的信息。"""

    # 用户个人简介
    bio: str | None = None
    # 用户所在地区（由业务系统录入，非 Telegram 官方字段）
    region: str | None = None
    # 用户标签列表，用于分类管理
    tags: list[str] | None = None


class MessageContentExtra(JsonStructBase):
    """消息补充内容，保存消息中附加的结构化数据。"""

    # 消息中提取的链接列表
    links: list[str] | None = None
    # 消息中提取的 @用户名 列表
    mentions: list[str] | None = None
    # 媒体类型，如 photo、video、document
    media_type: str | None = None


class TelegramRawPayload(JsonStructBase):
    """Telegram 原始更新片段，用于调试和事件溯源。"""

    # Telegram Update ID，全局唯一自增
    update_id: int | None = None
    # 原始 message 对象（来自 Telegram Update）
    message: dict[str, Any] | None = None
    # 被编辑消息对象（来自 Telegram Update）
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
    "PunishmentPolicy",
    "GroupSettings",
    "BotPermissions",
    "RuleOptions",
    "ModerationResultDetail",
    "GroupUserProfileExtra",
    "MessageContentExtra",
    "TelegramRawPayload",
    "PydanticJsonType",
]
