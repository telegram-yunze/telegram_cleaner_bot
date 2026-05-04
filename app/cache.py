from __future__ import annotations

# 本文件用途：全局缓存实例管理。
# 使用 cashews 库，支持纯内存（mem://）和 Redis（redis://...）两种后端，
# 通过 config.cache_url 动态切换，无需修改业务代码。

from datetime import datetime, timezone
from typing import Any

from cashews import cache

from app.config import get_settings

# 群组访问快照缓存 TTL（秒）。
GROUP_ACCESS_CACHE_TTL_SECONDS = 600
# 群成员快照缓存 TTL（秒）。
GROUP_USER_CACHE_TTL_SECONDS = 300
# 群成员不存在哨兵缓存 TTL（秒）。
GROUP_USER_MISSING_CACHE_TTL_SECONDS = 30
# 群成员资料异步刷新抑制窗口（秒）。
GROUP_USER_PROFILE_REFRESH_SUPPRESS_SECONDS = 120


def _build_group_access_cache_key(telegram_group_id: int) -> str:
    """构建群组访问快照缓存键。"""

    return f"group:access:{telegram_group_id}"


def _build_group_user_cache_key(group_id: int, telegram_user_id: int) -> str:
    """构建群成员快照缓存键。"""

    return f"group:user:{group_id}:{telegram_user_id}"


def _build_group_user_refresh_suppress_key(group_id: int, telegram_user_id: int) -> str:
    """构建群成员资料刷新抑制键。"""

    return f"group:user:refresh-suppress:{group_id}:{telegram_user_id}"


async def get_group_access_cache(telegram_group_id: int) -> dict[str, Any] | None:
    """读取群组访问快照缓存。"""

    key = _build_group_access_cache_key(telegram_group_id)
    cached = await cache.get(key, default=None)
    if not isinstance(cached, dict):
        return None
    group_id = cached.get("group_id")
    is_authorized = cached.get("is_authorized")
    if not isinstance(group_id, int) or not isinstance(is_authorized, bool):
        return None
    return {"group_id": group_id, "is_authorized": is_authorized}


async def set_group_access_cache(
    telegram_group_id: int,
    *,
    group_id: int,
    is_authorized: bool,
    ttl_seconds: int = GROUP_ACCESS_CACHE_TTL_SECONDS,
) -> None:
    """写入群组访问快照缓存。"""

    key = _build_group_access_cache_key(telegram_group_id)
    await cache.set(
        key,
        {"group_id": group_id, "is_authorized": is_authorized},
        expire=max(ttl_seconds, 1),
    )


async def invalidate_group_access_cache(telegram_group_id: int) -> None:
    """删除群组访问快照缓存。"""

    key = _build_group_access_cache_key(telegram_group_id)
    await cache.delete(key)


async def get_group_user_cache(group_id: int, telegram_user_id: int) -> dict[str, Any] | None:
    """读取群成员快照缓存。"""

    key = _build_group_user_cache_key(group_id, telegram_user_id)
    cached = await cache.get(key, default=None)
    if not isinstance(cached, dict):
        return None

    exists = cached.get("exists")
    if not isinstance(exists, bool):
        return None
    if not exists:
        return {"exists": False}

    group_user_id = cached.get("group_user_id")
    status = cached.get("status")
    profile_updated_at_ts = cached.get("profile_updated_at_ts")
    if not isinstance(group_user_id, int):
        return None
    if status is not None and not isinstance(status, str):
        return None
    if profile_updated_at_ts is not None and not isinstance(profile_updated_at_ts, int):
        return None
    return {
        "exists": True,
        "group_user_id": group_user_id,
        "status": status,
        "profile_updated_at_ts": profile_updated_at_ts,
    }


async def set_group_user_cache_found(
    group_id: int,
    telegram_user_id: int,
    *,
    group_user_id: int,
    status: str | None,
    profile_updated_at: datetime | None,
    ttl_seconds: int = GROUP_USER_CACHE_TTL_SECONDS,
) -> None:
    """写入群成员存在快照。"""

    profile_updated_at_ts: int | None = None
    if profile_updated_at is not None:
        normalized = profile_updated_at
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        profile_updated_at_ts = int(normalized.timestamp())

    key = _build_group_user_cache_key(group_id, telegram_user_id)
    await cache.set(
        key,
        {
            "exists": True,
            "group_user_id": group_user_id,
            "status": status,
            "profile_updated_at_ts": profile_updated_at_ts,
        },
        expire=max(ttl_seconds, 1),
    )


async def set_group_user_cache_missing(
    group_id: int,
    telegram_user_id: int,
    *,
    ttl_seconds: int = GROUP_USER_MISSING_CACHE_TTL_SECONDS,
) -> None:
    """写入群成员不存在哨兵缓存，降低缓存穿透。"""

    key = _build_group_user_cache_key(group_id, telegram_user_id)
    await cache.set(key, {"exists": False}, expire=max(ttl_seconds, 1))


async def invalidate_group_user_cache(group_id: int, telegram_user_id: int) -> None:
    """删除群成员快照缓存。"""

    key = _build_group_user_cache_key(group_id, telegram_user_id)
    await cache.delete(key)


async def try_acquire_group_user_profile_refresh_suppress(
    group_id: int,
    telegram_user_id: int,
    *,
    suppress_ttl_seconds: int = GROUP_USER_PROFILE_REFRESH_SUPPRESS_SECONDS,
) -> bool:
    """尝试获取群成员资料刷新抑制键。返回 True 表示允许触发刷新。"""

    key = _build_group_user_refresh_suppress_key(group_id, telegram_user_id)
    cached = await cache.get(key, default=None)
    if cached is not None:
        return False
    await cache.set(key, 1, expire=max(suppress_ttl_seconds, 1))
    return True


async def setup_cache() -> None:
    """根据配置初始化缓存连接。
    
    内存模式（mem://）无需外部服务，适合开发/测试。
    Redis 模式（redis://host:6379）适合生产，只需修改 .env 中的 CACHE_URL 即可切换。
    """
    settings = get_settings()
    cache.setup(settings.cache_url)


__all__ = [
    "cache",
    "setup_cache",
    "get_group_access_cache",
    "set_group_access_cache",
    "invalidate_group_access_cache",
    "get_group_user_cache",
    "set_group_user_cache_found",
    "set_group_user_cache_missing",
    "invalidate_group_user_cache",
    "try_acquire_group_user_profile_refresh_suppress",
    "GROUP_ACCESS_CACHE_TTL_SECONDS",
    "GROUP_USER_CACHE_TTL_SECONDS",
    "GROUP_USER_MISSING_CACHE_TTL_SECONDS",
    "GROUP_USER_PROFILE_REFRESH_SUPPRESS_SECONDS",
]
