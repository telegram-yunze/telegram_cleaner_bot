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

    # 删除消息
    DELETE = "delete"
    # 警告用户
    WARN = "warn"
    # 禁言用户
    MUTE = "mute"
    # 封禁用户
    BAN = "ban"
    # 进入人工复核
    REVIEW = "review"
    # 忽略不处理
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