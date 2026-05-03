from __future__ import annotations

from secrets import compare_digest

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import get_runtime_api_secret_key
from app.exceptions import UnauthorizedError

# 通过 Security + APIKeyHeader 让 OpenAPI 自动生成 securitySchemes。
_api_key_header = APIKeyHeader(
	name="X-API-Key",
	scheme_name="ApiKeyAuth",
	auto_error=False,
	description=(
		"服务 API 鉴权密钥。\n\n"
		"受保护路由：/groups、/rules、/moderation。\n"
		"公开路由：/、/health。\n\n"
		"请求头格式：X-API-Key: <API_SECRET_KEY>\n\n"
		"若 API_SECRET_KEY 为空，服务启动时会随机生成一个进程内有效密钥（重启后变化）。"
	),
)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
	"""校验 API 密钥。

	缺失或不匹配都返回统一 401，避免泄漏更多鉴权细节。
	"""

	expected = get_runtime_api_secret_key()
	if not api_key or not compare_digest(api_key, expected):
		raise UnauthorizedError(message="API 密钥无效")


__all__ = ["verify_api_key"]
