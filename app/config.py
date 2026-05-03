from __future__ import annotations

# 本文件用途：全局配置管理，使用 pydantic-settings 从环境变量和 .env 文件读取配置，
# 并通过 get_settings() 提供全局单例，避免重复解析。

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置。字段优先从环境变量读取，未配置时使用安全的默认值。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 数据库 ───────────────────────────────────────────────────────────────
    # 数据库连接串；默认本地 SQLite，生产应替换为 MySQL/PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./telegram_cleaner_bot.db"
    # 是否在日志中打印 SQL 语句（仅调试环境开启）
    sqlalchemy_echo: bool = False

    # ── 应用运行 ─────────────────────────────────────────────────────────────
    debug: bool = False
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # ── Telegram Bot ─────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    webhook_base_url: str = ""
    webhook_path: str = "/webhook/telegram"
    # ── 缓存 ─────────────────────────────────────────────────────────────
    # cashews 缓存连接串；"mem://" 表示纯内存，生产可改为 "redis://host:6379"
    cache_url: str = "mem://"
    # ── 安全 ─────────────────────────────────────────────────────────────────
    # API 鉴权密钥；生产必须设置为足够随机的字符串
    api_secret_key: str = ""

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """校验日志级别只允许标准值。"""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized not in allowed:
            raise ValueError(f"log_level 只允许 {allowed}，当前值: {v!r}")
        return normalized

    @property
    def webhook_url(self) -> str:
        """组合完整的 Webhook URL。"""
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"

    @property
    def is_sqlite(self) -> bool:
        """判断当前数据库是否为 SQLite。"""
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局单例配置对象；第一次调用时从环境变量和 .env 文件加载。"""
    return Settings()


__all__ = ["Settings", "get_settings"]
