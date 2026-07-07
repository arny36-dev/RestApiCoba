"""Async SQLAlchemy engine, sessionmaker, and the FastAPI session dependency."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _engine_options(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        # SQLite (used in tests) does not play well with cross-loop pooled connections.
        return {"poolclass": NullPool}
    return {"pool_pre_ping": True}


def get_engine() -> AsyncEngine:
    """Create the engine lazily so importing the app never requires a database."""
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _engine = create_async_engine(url, **_engine_options(url))
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine and reset cached state (used on shutdown and in tests)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
