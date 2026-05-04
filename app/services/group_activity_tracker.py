from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db.session import get_session_factory
from app.repositories.group_repository import GroupRepository
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)


@dataclass(slots=True)
class GroupActivityFlushResult:
    """一次批量刷新结果，用于日志观测。"""

    attempted_groups: int = 0
    success_groups: int = 0
    failed_groups: int = 0
    deadlock_retries: int = 0


class GroupActivityTracker:
    """聚合群活跃触达事件，并异步刷新到 groups.last_message_at。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._flush_interval_seconds = settings.group_activity_flush_interval_seconds
        self._flush_batch_size = settings.group_activity_flush_batch_size
        self._deadlock_retry_attempts = settings.group_activity_deadlock_retry_attempts
        self._deadlock_retry_base_delay_seconds = settings.group_activity_deadlock_retry_base_delay_seconds

        self._bound_loop: asyncio.AbstractEventLoop | None = None
        self._lock = asyncio.Lock()
        self._pending: dict[int, datetime] = {}
        self._stop_event = asyncio.Event()
        self._loop_task: asyncio.Task[None] | None = None

    def _ensure_loop_context(self) -> None:
        """确保同步原语绑定到当前事件循环。

        TestClient 等场景会频繁创建新事件循环；全局单例若复用旧 loop 绑定的
        Event/Lock 会触发 "bound to a different event loop"。这里按需重建原语。
        """

        current_loop = asyncio.get_running_loop()
        if self._bound_loop is current_loop:
            return
        self._bound_loop = current_loop
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

    async def enqueue(self, telegram_group_id: int, last_message_at: datetime) -> None:
        """记录一次群消息触达，仅保留同群最大时间戳。"""

        self._ensure_loop_context()
        normalized = self._normalize_to_utc_naive(last_message_at)
        async with self._lock:
            existing = self._pending.get(telegram_group_id)
            if existing is None or normalized > existing:
                self._pending[telegram_group_id] = normalized

    async def start(self) -> None:
        """启动后台刷新循环。"""

        self._ensure_loop_context()
        if self._loop_task is not None and not self._loop_task.done():
            return
        self._stop_event.clear()
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info(
            "群活跃聚合刷新任务已启动: interval=%.3fs batch_size=%s",
            self._flush_interval_seconds,
            self._flush_batch_size,
        )

    async def stop(self) -> None:
        """停止后台刷新循环，并尽力执行一次最终 flush。"""

        self._ensure_loop_context()
        self._stop_event.set()
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                logger.info("群活跃聚合刷新任务已取消")
        self._loop_task = None

        # 停机时做一次尽力刷新，避免进程退出前缓冲丢失。
        await self.flush_once()

    async def flush_once(self) -> GroupActivityFlushResult:
        """刷新当前缓冲中的群活跃时间，失败仅告警不抛出。"""

        self._ensure_loop_context()
        batch = await self._pop_batch()
        result = GroupActivityFlushResult(attempted_groups=len(batch))
        if not batch:
            return result

        for telegram_group_id, last_message_at in batch:
            ok, retries = await self._update_last_message_at_with_retry(
                telegram_group_id=telegram_group_id,
                last_message_at=last_message_at,
            )
            result.deadlock_retries += retries
            if ok:
                result.success_groups += 1
            else:
                result.failed_groups += 1

        logger.info(
            "群活跃聚合刷新完成: attempted=%s success=%s failed=%s deadlock_retries=%s",
            result.attempted_groups,
            result.success_groups,
            result.failed_groups,
            result.deadlock_retries,
        )
        return result

    async def _run_loop(self) -> None:
        """后台循环：周期性 flush，异常仅记录。"""

        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._flush_interval_seconds,
                    )
                except TimeoutError:
                    pass

                if self._stop_event.is_set():
                    break
                await self.flush_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_exception(logger, message="群活跃聚合刷新循环异常", exc=exc)

    async def _pop_batch(self) -> list[tuple[int, datetime]]:
        """从缓冲区取一批待刷新数据。"""

        async with self._lock:
            if not self._pending:
                return []
            items = list(self._pending.items())[: self._flush_batch_size]
            for telegram_group_id, _ in items:
                self._pending.pop(telegram_group_id, None)
            return items

    async def _update_last_message_at_with_retry(
        self,
        *,
        telegram_group_id: int,
        last_message_at: datetime,
    ) -> tuple[bool, int]:
        """更新 groups.last_message_at，遇到 1213 死锁时做有限重试。"""

        retries = 0
        for attempt in range(1, self._deadlock_retry_attempts + 1):
            session = get_session_factory()()
            try:
                repository = GroupRepository(session)
                await repository.UpdateLastMessageAtByTelegramGroupId(
                    telegram_group_id=telegram_group_id,
                    last_message_at=last_message_at,
                )
                await session.commit()
                return True, retries
            except OperationalError as exc:
                await session.rollback()
                if self._is_mysql_deadlock_error(exc) and attempt < self._deadlock_retry_attempts:
                    retries += 1
                    delay = self._deadlock_retry_base_delay_seconds * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
                log_exception(
                    logger,
                    message="刷新群活跃时间失败",
                    exc=exc,
                    extra={"telegram_group_id": telegram_group_id},
                )
                return False, retries
            except Exception as exc:
                await session.rollback()
                log_exception(
                    logger,
                    message="刷新群活跃时间失败",
                    exc=exc,
                    extra={"telegram_group_id": telegram_group_id},
                )
                return False, retries
            finally:
                await session.close()
        return False, retries

    def _normalize_to_utc_naive(self, value: datetime) -> datetime:
        """统一时间为 UTC naive，便于与数据库 datetime 对齐。"""

        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def _is_mysql_deadlock_error(self, exc: OperationalError) -> bool:
        """判断是否为 MySQL deadlock(1213)。"""

        orig = getattr(exc, "orig", None)
        args = getattr(orig, "args", ())
        if not args:
            return False
        try:
            return int(args[0]) == 1213
        except (TypeError, ValueError):
            return False


_TRACKER = GroupActivityTracker()


def get_group_activity_tracker() -> GroupActivityTracker:
    """获取全局群活跃聚合刷新器。"""

    return _TRACKER


async def enqueue_group_activity(telegram_group_id: int, last_message_at: datetime) -> None:
    """对外暴露的轻量入队方法。"""

    await _TRACKER.enqueue(telegram_group_id=telegram_group_id, last_message_at=last_message_at)


__all__ = [
    "GroupActivityTracker",
    "GroupActivityFlushResult",
    "get_group_activity_tracker",
    "enqueue_group_activity",
]
