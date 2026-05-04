from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from app.db.session import get_db_session
from app.repositories.group_repository import GroupRepository
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)

GROUP_INFO_SYNC_INTERVAL_SECONDS = 5 * 60
GROUP_INFO_STALE_DAYS = 1


async def _sync_single_group_info(bot: Bot, repository: GroupRepository, group_id: int, telegram_group_id: int) -> None:
    """同步单个群组信息；即使拉取失败也会刷新 info_updated_at。"""

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    title: str | None = None
    username: str | None = None
    description: str | None = None
    owner_telegram_user_id: int | None = None

    try:
        chat = await bot.get_chat(telegram_group_id)
        title = (chat.title or "").strip() or None
        username = (chat.username or "").strip() or None
        description = (getattr(chat, "description", None) or "").strip() or None

        try:
            administrators = await bot.get_chat_administrators(telegram_group_id)
            for admin in administrators:
                if str(getattr(admin, "status", "")) == "creator":
                    owner_telegram_user_id = int(admin.user.id)
                    break
        except Exception as exc:
            logger.warning(
                "群主查询失败，跳过 owner_telegram_user_id 更新: group_id=%s telegram_group_id=%s error=%s",
                group_id,
                telegram_group_id,
                str(exc),
            )

        logger.info(
            "群组信息拉取成功: group_id=%s telegram_group_id=%s",
            group_id,
            telegram_group_id,
        )
    except Exception as exc:
        logger.warning(
            "群组信息拉取失败，将仅刷新 info_updated_at: group_id=%s telegram_group_id=%s error=%s",
            group_id,
            telegram_group_id,
            str(exc),
        )

    await repository.UpdateGroupInfoById(
        group_id=group_id,
        title=title,
        username=username,
        description=description,
        info_updated_at=now,
        owner_telegram_user_id=owner_telegram_user_id,
    )


async def sync_stale_group_info_once(bot: Bot) -> None:
    """执行一次群组信息同步：扫描超 1 天未更新的群组并逐个刷新。"""

    threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=GROUP_INFO_STALE_DAYS)

    async for session in get_db_session():
        repository = GroupRepository(session)
        stale_groups = await repository.FindAllByInfoUpdatedAtBefore(threshold)

        if not stale_groups:
            continue

        logger.info("群组信息同步开始：待刷新数量=%s", len(stale_groups))
        for group in stale_groups:
            await _sync_single_group_info(
                bot=bot,
                repository=repository,
                group_id=group.id,
                telegram_group_id=group.telegram_group_id,
            )


async def run_group_info_sync_loop(bot: Bot) -> None:
    """后台定时任务：每 5 分钟刷新一次过期群组信息。"""

    logger.info(
        "群组信息定时同步任务已启动: interval_seconds=%s stale_days=%s",
        GROUP_INFO_SYNC_INTERVAL_SECONDS,
        GROUP_INFO_STALE_DAYS,
    )

    while True:
        try:
            await sync_stale_group_info_once(bot)
        except asyncio.CancelledError:
            logger.info("群组信息定时同步任务已取消")
            raise
        except Exception as exc:
            log_exception(logger, message="群组信息定时同步任务执行失败", exc=exc)

        await asyncio.sleep(GROUP_INFO_SYNC_INTERVAL_SECONDS)


__all__ = [
    "run_group_info_sync_loop",
    "sync_stale_group_info_once",
]
