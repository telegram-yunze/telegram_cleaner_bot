from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.exceptions import AppException, BotProcessingError
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


async def run_bot(main_loop: Callable[[], Awaitable[None]]) -> None:
	"""Bot 顶层运行入口，统一兜底未处理异常。"""

	try:
		await main_loop()
	except AppException as exc:
		log_exception(logger, message="Bot 运行出现业务异常", exc=exc)
		raise
	except Exception as exc:
		log_exception(logger, message="Bot 运行出现未捕获异常", exc=exc)
		raise BotProcessingError(detail={"stage": "runner"}) from exc


__all__ = ["run_bot"]
