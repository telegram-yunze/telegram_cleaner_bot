from __future__ import annotations

import logging
from typing import Any


def configure_logging(level: str = "INFO") -> None:
	"""初始化全局日志配置。"""

	logging.basicConfig(
		level=getattr(logging, level.upper(), logging.INFO),
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)


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
