from __future__ import annotations

# 本文件用途：管理 SQLAlchemy 异步引擎与 Session 工厂，提供请求级数据库会话。

from collections.abc import AsyncIterator

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.exceptions import DatabaseOperationError
from app.utils.logger import get_logger, log_exception

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """延迟创建异步引擎，避免模块导入阶段强依赖数据库驱动。"""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.sqlalchemy_echo,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """返回全局复用的异步 Session 工厂。"""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """为请求生命周期提供数据库会话，并在异常时回滚。"""

    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        log_exception(
            logger,
            message="数据库约束冲突，事务已回滚",
            exc=exc,
        )
        raise DatabaseOperationError(detail={"reason": "integrity_error"}) from exc
    except OperationalError as exc:
        await session.rollback()
        log_exception(
            logger,
            message="数据库连接或执行异常，事务已回滚",
            exc=exc,
        )
        raise DatabaseOperationError(detail={"reason": "operational_error"}) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        log_exception(
            logger,
            message="数据库访问异常，事务已回滚",
            exc=exc,
        )
        raise DatabaseOperationError(detail={"reason": "sqlalchemy_error"}) from exc
    except Exception as exc:
        await session.rollback()
        log_exception(
            logger,
            message="请求事务发生未预期异常，事务已回滚",
            exc=exc,
        )
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """关闭全局异步引擎，供应用停机时清理连接池。"""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


__all__ = [
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "dispose_engine",
]
