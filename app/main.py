"""FastAPI aplikácia: routre, spracovanie chýb a jednoduché slovenské logovanie."""

import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.api import health
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.session import dispose_engine

logger = logging.getLogger(__name__)

STATUS_TEXTS = {
    200: "v poriadku",
    201: "vytvorené",
    400: "zlá požiadavka",
    404: "nenájdené",
    405: "nepovolená metóda",
    409: "konflikt v databáze",
    422: "neplatné údaje",
    500: "chyba servera",
    503: "databáza nedostupná",
}


def _status_text(code: int) -> str:
    default = "v poriadku" if code < 400 else "chyba"
    return STATUS_TEXTS.get(code, default)


def _error_reason(body: bytes) -> str | None:
    """Z odpovede vytiahne zrozumiteľný dôvod chyby."""
    try:
        detail = json.loads(body).get("detail")
    except (ValueError, AttributeError):
        return None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        # Validačné chyby od Pydanticu — stačí vymenovať chybné polia.
        fields = ", ".join(
            ".".join(str(part) for part in error.get("loc", [])[1:]) or "telo požiadavky"
            for error in detail
        )
        return f"chybné polia: {fields}"
    return None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Bezpečný výpis konfigurácie — heslo sa nikdy neloguje.
    url = make_url(settings.database_url)
    logger.info(
        "Aplikácia %s spustená | databáza: %s na %s:%s, schéma %s, užívateľ %s"
        " | predvolený objekt: %s",
        settings.app_name,
        url.get_backend_name(),
        url.host,
        url.port,
        url.database,
        url.username,
        settings.default_object_id,
    )
    yield
    await dispose_engine()
    logger.info("Aplikácia vypnutá")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(log_dir=settings.log_dir, log_sql=settings.log_sql)

    app = FastAPI(title=settings.app_name, debug=False, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)

        # Odpoveď treba prečítať, aby sa pri chybe dal zalogovať jej dôvod.
        chunks = [chunk async for chunk in response.body_iterator]  # type: ignore[attr-defined]
        response_body = b"".join(chunks)
        duration_ms = (time.perf_counter() - start) * 1000

        query = f"?{request.url.query}" if request.url.query else ""
        status = response.status_code
        line = (
            f"{request.method} {request.url.path}{query}"
            f" → {status} ({_status_text(status)}, {duration_ms:.0f} ms)"
        )
        if response.status_code >= 400:
            reason = _error_reason(response_body)
            if reason:
                line += f" | dôvod: {reason}"
            logger.warning(line)
        else:
            logger.info(line)

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Databáza odmietla zápis (%s %s): %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=409, content={"detail": "Databáza odmietla zápis (porušenie obmedzení)"}
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Klient nikdy nedostane technické detaily; celý traceback ide do logu.
        logger.exception("Neočakávaná chyba pri %s %s", request.method, request.url.path)
        detail = str(exc) if get_settings().debug else "Interná chyba servera"
        return JSONResponse(status_code=500, content={"detail": detail})

    return app


app = create_app()
