from __future__ import annotations

import logging
import re
from typing import Any


class HealthEndpointAccessFilter(logging.Filter):
	"""过滤健康检查访问日志，避免高频探活刷屏。"""

	_HEALTH_PATHS = {"/api/health", "/health"}
	_REQUEST_LINE_PATTERN = re.compile(
		r'"\w+\s+(/api/health|/health)(?:\?[^\s"]*)?\s+HTTP/\d(?:\.\d)?"'
	)

	def filter(self, record: logging.LogRecord) -> bool:
		# uvicorn.access 的参数通常包含 method/path/status，优先使用结构化参数判断。
		if isinstance(record.args, tuple) and len(record.args) >= 3:
			path = record.args[2]
			if isinstance(path, str) and path.split("?", 1)[0] in self._HEALTH_PATHS:
				return False

		message = record.getMessage()
		return self._REQUEST_LINE_PATTERN.search(message) is None


def configure_logging(level: str = "INFO") -> None:
	"""初始化全局日志配置。"""

	logging.basicConfig(
		level=getattr(logging, level.upper(), logging.INFO),
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)

	access_logger = logging.getLogger("uvicorn.access")
	health_filter = HealthEndpointAccessFilter()
	if not any(isinstance(existing_filter, HealthEndpointAccessFilter) for existing_filter in access_logger.filters):
		access_logger.addFilter(health_filter)


def get_logger(name: str) -> logging.Logger:
	"""获取命名 logger。"""

	return logging.getLogger(name)


def log_exception(
	logger: logging.Logger,
	*,
	message: str,
	exc: Exception,
	extra: dict[str, Any] | None = None,
) -> None:
	"""统一记录带堆栈的异常日志。"""

	if extra:
		logger.exception("%s | extra=%s", message, extra, exc_info=exc)
		return
	logger.exception(message, exc_info=exc)


__all__ = ["configure_logging", "get_logger", "log_exception"]
