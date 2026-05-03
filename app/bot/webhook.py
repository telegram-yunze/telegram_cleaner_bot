from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.exceptions import AppException, BotProcessingError, RequestValidationAppError, UnauthorizedError
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


def _build_error_body(exc: AppException) -> dict[str, Any]:
	"""构建 Bot Webhook 统一错误结构。"""

	return {
		"ok": False,
		"error": {
			"code": exc.code,
			"message": exc.message,
			"detail": exc.detail,
		},
	}


async def process_webhook_safely(
	*,
	payload: dict[str, Any],
	handler: Callable[[dict[str, Any]], Awaitable[None]],
	validate_signature: Callable[[dict[str, Any]], bool] | None = None,
) -> tuple[int, dict[str, Any]]:
	"""Webhook 统一异常入口：解析、鉴权、处理失败都映射为标准输出。"""

	try:
		if not isinstance(payload, dict):
			raise RequestValidationAppError(detail={"reason": "payload_not_dict"})

		if validate_signature is not None and not validate_signature(payload):
			raise UnauthorizedError(message="Webhook 签名校验失败")

		await handler(payload)
		return 200, {"ok": True}
	except AppException as exc:
		log_exception(logger, message="Webhook 业务异常", exc=exc)
		return exc.status_code, _build_error_body(exc)
	except Exception as exc:
		mapped_error = BotProcessingError(detail={"stage": "webhook"})
		log_exception(logger, message="Webhook 未捕获异常", exc=exc)
		return mapped_error.status_code, _build_error_body(mapped_error)


__all__ = ["process_webhook_safely"]
