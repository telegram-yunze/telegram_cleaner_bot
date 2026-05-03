from __future__ import annotations

# 本文件用途：全局缓存实例管理。
# 使用 cashews 库，支持纯内存（mem://）和 Redis（redis://...）两种后端，
# 通过 config.cache_url 动态切换，无需修改业务代码。

from cashews import cache

from app.config import get_settings


async def setup_cache() -> None:
    """根据配置初始化缓存连接。
    
    内存模式（mem://）无需外部服务，适合开发/测试。
    Redis 模式（redis://host:6379）适合生产，只需修改 .env 中的 CACHE_URL 即可切换。
    """
    settings = get_settings()
    cache.setup(settings.cache_url)


__all__ = ["cache", "setup_cache"]
