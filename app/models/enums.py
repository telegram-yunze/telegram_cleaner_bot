from enum import StrEnum


class GroupChatType(StrEnum):
    """Telegram 群会话类型。"""

    # 普通群
    GROUP = "group"
    # 超级群
    SUPERGROUP = "supergroup"


class GroupUserRole(StrEnum):
    """群成员角色。"""

    # 群主
    OWNER = "owner"
    # 管理员
    ADMIN = "admin"
    # 普通成员
    MEMBER = "member"
    # 受限成员（如被限制发言）
    RESTRICTED = "restricted"


class GroupUserStatus(StrEnum):
    """群成员状态。"""

    # 正常在群
    ACTIVE = "active"
    # 主动离群
    LEFT = "left"
    # 被移出群组
    KICKED = "kicked"
    # 被封禁
    BANNED = "banned"


class MessageType(StrEnum):
    """消息类型。"""

    # 文本消息
    TEXT = "text"
    # 图片消息
    PHOTO = "photo"
    # 视频消息
    VIDEO = "video"
    # 文件消息
    DOCUMENT = "document"
    # 贴纸消息
    STICKER = "sticker"
    # 转发消息
    FORWARDED = "forwarded"
    # 其他类型消息
    OTHER = "other"


class RuleType(StrEnum):
    """规则类型。"""

    # 关键词规则
    KEYWORD = "keyword"
    # 正则规则
    REGEX = "regex"
    # 链接规则
    URL = "url"
    # 用户名规则
    USERNAME = "username"
    # 联系方式规则
    CONTACT = "contact"
    # AI 检测规则
    AI = "ai"


class ModerationAction(StrEnum):
    """命中规则后可执行的动作。"""

    # 删除消息（不对用户做其他处置）
    DELETE = "delete"
    # 警告用户（发送提示，不限制操作，累计次数可触发升级惩罚）
    WARN = "warn"
    # 临时禁言（限制发言一段时间，时长由规则 options 或群组策略决定）
    MUTE = "mute"
    # 永久禁言（revoke 发言权限，不踢出群，仍可阅读消息）
    PERMANENT_MUTE = "permanent_mute"
    # 限制权限（仅限发文字或禁止发媒体，粒度比禁言更细，时长可配置）
    RESTRICT = "restrict"
    # 踢出群组（可重新加入，不加入黑名单，适用于首次严重违规）
    KICK = "kick"
    # 封禁用户（踢出并拉入黑名单，无法通过链接重新加入）
    BAN = "ban"
    # 进入人工复核（暂不自动处置，由管理员手动决定）
    REVIEW = "review"
    # 忽略不处理（命中规则但主动跳过，用于白名单场景）
    IGNORE = "ignore"


class ModerationStatus(StrEnum):
    """处置执行状态。"""

    # 等待执行
    PENDING = "pending"
    # 执行成功
    SUCCESS = "success"
    # 执行失败
    FAILED = "failed"
    # 跳过执行
    SKIPPED = "skipped"


class NotificationRecallStatus(StrEnum):
    """通知消息自动撤回状态。"""

    # 等待撤回执行
    PENDING = "pending"
    # 撤回成功
    SUCCESS = "success"
    # 撤回失败
    FAILED = "failed"
    # 已取消撤回
    CANCELED = "canceled"
