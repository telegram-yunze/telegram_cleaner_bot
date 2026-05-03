from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.exceptions import AppException, BotProcessingError
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


@dataclass(slots=True)
class HandlerResult:
	"""Bot handler 执行结果。"""

	success: bool
	error_code: str | None = None
	error_message: str | None = None


async def execute_handler_safely(
	handler_name: str,
	handler: Callable[..., Awaitable[Any]],
	*args: Any,
	**kwargs: Any,
) -> HandlerResult:
	"""统一包装 handler 执行，防止异常向上层裸抛。"""

	try:
		await handler(*args, **kwargs)
		return HandlerResult(success=True)
	except AppException as exc:
		log_exception(
			logger,
			message="Bot handler 业务异常",
			exc=exc,
			extra={"handler": handler_name, "code": exc.code},
		)
		return HandlerResult(success=False, error_code=exc.code, error_message=exc.message)
	except Exception as exc:
		mapped_error = BotProcessingError(detail={"handler": handler_name})
		log_exception(
			logger,
			message="Bot handler 未捕获异常",
			exc=exc,
			extra={"handler": handler_name},
		)
		return HandlerResult(
			success=False,
			error_code=mapped_error.code,
			error_message=mapped_error.message,
		)


__all__ = ["HandlerResult", "execute_handler_safely"]
