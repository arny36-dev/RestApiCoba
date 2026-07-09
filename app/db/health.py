"""Kontrola pripojenia k databáze pre GET /api/v1/db/health."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


async def check_database_connection(engine: AsyncEngine) -> None:
    """Vykoná skutočný ``SELECT 1``; pri zlyhaní vráti 503 s bezpečnou hláškou."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        url = engine.url
        safe_error = str(exc)
        if url.password:
            safe_error = safe_error.replace(url.password, "***")
        logger.error(
            "Nepodarilo sa pripojiť k databáze (%s na %s, schéma %s, užívateľ %s): %s",
            url.get_backend_name(),
            url.host,
            url.database,
            url.username,
            safe_error,
        )
        raise DatabaseUnavailableError(f"Pripojenie k databáze zlyhalo: {safe_error}") from exc
