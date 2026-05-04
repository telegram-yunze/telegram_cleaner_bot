from __future__ import annotations

# 本文件用途：全局配置管理，使用 pydantic-settings 从环境变量和 .env 文件读取配置，
# 并通过 get_settings() 提供全局单例，避免重复解析。

from functools import lru_cache
from secrets import token_urlsafe

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
    # uvicorn 监听地址与端口；启动脚本优先读取这两个值
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Telegram Bot ─────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_run_mode: str = "both"
    webhook_secret_token: str = ""
    webhook_base_url: str = ""
    webhook_path: str = "/webhook/telegram"
    telegram_polling_timeout: int = 30
    telegram_action_dry_run: bool = True
    # 代理地址（仅 polling/both 模式下生效）；留空表示不使用代理
    # 支持 HTTP/HTTPS 代理，格式如 http://127.0.0.1:7890
    # SOCKS5 代理需额外安装 aiohttp-socks，格式如 socks5://127.0.0.1:1080
    telegram_proxy_url: str = ""
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

    @field_validator("telegram_run_mode")
    @classmethod
    def validate_telegram_run_mode(cls, v: str) -> str:
        """校验 Telegram 运行模式。"""

        allowed = {"webhook", "polling", "both", "disabled"}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"telegram_run_mode 只允许 {allowed}，当前值: {v!r}")
        return normalized

    @field_validator("webhook_path")
    @classmethod
    def validate_webhook_path(cls, v: str) -> str:
        """确保 Webhook 路径以 / 开头。"""

        if not v.startswith("/"):
            raise ValueError(f"webhook_path 必须以 / 开头，当前值: {v!r}")
        return v

    @field_validator("telegram_polling_timeout")
    @classmethod
    def validate_telegram_polling_timeout(cls, v: int) -> int:
        """限制轮询超时必须为正整数。"""

        if v <= 0:
            raise ValueError(f"telegram_polling_timeout 必须大于 0，当前值: {v}")
        return v

    @property
    def webhook_url(self) -> str:
        """组合完整的 Webhook URL。"""
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"

    @property
    def is_sqlite(self) -> bool:
        """判断当前数据库是否为 SQLite。"""
        return self.database_url.startswith("sqlite")

    @property
    def has_telegram_bot_token(self) -> bool:
        """判断是否配置了 Telegram Bot Token。"""

        return bool(self.telegram_bot_token.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回全局单例配置对象；第一次调用时从环境变量和 .env 文件加载。"""
    return Settings()


@lru_cache(maxsize=1)
def _resolve_runtime_api_secret() -> tuple[str, str]:
    """解析运行时 API 密钥。

    - 若环境变量/API 配置中有值，则直接使用（source=env）。
    - 若为空，则为当前进程随机生成一次（source=generated）。
    """

    configured_secret = get_settings().api_secret_key.strip()
    if configured_secret:
        return configured_secret, "env"
    return token_urlsafe(32), "generated"


def get_runtime_api_secret_key() -> str:
    """获取运行时 API 密钥（进程内稳定）。"""

    secret, _ = _resolve_runtime_api_secret()
    return secret


def get_runtime_api_secret_source() -> str:
    """获取运行时 API 密钥来源：env 或 generated。"""

    _, source = _resolve_runtime_api_secret()
    return source


__all__ = [
    "Settings",
    "get_settings",
    "get_runtime_api_secret_key",
    "get_runtime_api_secret_source",
]
