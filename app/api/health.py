"""Health endpoints: app liveness and a real database connectivity check."""

from typing import Any

from fastapi import APIRouter

from app.db.health import check_database_connection
from app.db.session import get_engine

router = APIRouter(tags=["health"])
db_router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@db_router.get("/db/health")
async def database_health() -> dict[str, Any]:
    """Open a real connection and run SELECT 1; 503 with a safe message on failure."""
    await check_database_connection(get_engine())
    return {"status": "ok", "database": "connected"}
