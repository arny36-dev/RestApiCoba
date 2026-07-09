"""Table reflection with a safe in-process cache.

Tables are reflected from the live database on first access and cached for the
lifetime of the process. Reflection is guarded by an asyncio lock so concurrent
first requests do not reflect the same table twice.
"""

import asyncio

from sqlalchemy import MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from app.core.exceptions import AppError
from app.db.session import get_engine

_metadata = MetaData()
_tables: dict[str, Table] = {}
_lock = asyncio.Lock()


async def get_table(name: str) -> Table:
    """Return the reflected table for ``name``, reflecting it on first access.

    Callers must validate ``name`` against ALLOWED_TABLES before calling —
    this module never receives unchecked user input.
    """
    table = _tables.get(name)
    if table is not None:
        return table

    async with _lock:
        table = _tables.get(name)
        if table is not None:
            return table

        engine = get_engine()
        try:
            async with engine.connect() as connection:
                table = await connection.run_sync(
                    lambda sync_connection: Table(name, _metadata, autoload_with=sync_connection)
                )
        except NoSuchTableError as exc:
            raise AppError(f"Tabuľka '{name}' v databáze neexistuje") from exc

        _tables[name] = table
        return table


def clear_cache() -> None:
    """Drop all cached reflection state (used in tests)."""
    _tables.clear()
    _metadata.clear()
