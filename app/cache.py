from __future__ import annotations

# 本文件用途：全局缓存实例管理。
# 使用 cashews 库，支持纯内存（mem://）和 Redis（redis://...）两种后端，
# 通过 config.cache_url 动态切换，无需修改业务代码。

from typing import Any

from cashews import cache

from app.config import get_settings

# 群组访问快照缓存 TTL（秒）。
GROUP_ACCESS_CACHE_TTL_SECONDS = 600


def _build_group_access_cache_key(telegram_group_id: int) -> str:
    """构建群组访问快照缓存键。"""

    return f"group:access:{telegram_group_id}"


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
    "GROUP_ACCESS_CACHE_TTL_SECONDS",
]
