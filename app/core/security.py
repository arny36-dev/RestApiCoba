"""API-key authentication for protected endpoints.

Clients must send the key in the ``X-API-Key`` header. The expected value comes
from the ``API_KEY`` setting. Comparison is constant-time to avoid leaking the
key through timing. If no key is configured the endpoint fails closed: every
request is rejected with 401 rather than left open.
"""

import logging
import secrets
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

API_KEY_HEADER_NAME = "X-API-Key"

# auto_error=False: we raise our own AuthenticationError (401 with a Slovak
# message) instead of Starlette's default 403, and keep logging consistent.
_api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


async def require_api_key(
    provided: Annotated[str | None, Security(_api_key_header)],
    settings: Annotated[Settings, Security(get_settings)],
) -> None:
    """FastAPI dependency: allow the request only with a valid API key."""
    expected = settings.api_key
    if not expected:
        # Misconfiguration — never silently leave a protected route open.
        logger.error("API_KEY nie je nastavený — všetky chránené požiadavky sú odmietnuté")
        raise AuthenticationError("Autentifikácia nie je nakonfigurovaná")
    if not provided or not secrets.compare_digest(provided, expected):
        raise AuthenticationError("Chýbajúci alebo neplatný API kľúč")
