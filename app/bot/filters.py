from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


def evaluate_filter_safely(
	*,
	filter_name: str,
	predicate: Callable[[dict[str, Any]], bool],
	payload: dict[str, Any],
) -> bool:
	"""安全执行过滤函数，异常时默认不放行并记录日志。"""

	try:
		return bool(predicate(payload))
	except Exception as exc:
		log_exception(
			logger,
			message="Bot 过滤器执行异常",
			exc=exc,
			extra={"filter": filter_name},
		)
		return False


__all__ = ["evaluate_filter_safely"]
