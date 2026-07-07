"""FastAPI application factory, routers, and exception handlers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api import health
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.session import dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(debug=settings.debug)

    app = FastAPI(title=settings.app_name, debug=False, lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=409, content={"detail": "Database constraint violated"})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces; log server-side and return a generic message.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        detail = str(exc) if get_settings().debug else "Internal server error"
        return JSONResponse(status_code=500, content={"detail": detail})

    return app


app = create_app()
