"""Application errors that map directly to HTTP responses.

Every error carries a safe, user-facing ``detail`` message so handlers never
need to expose internals or stack traces.
"""


class AppError(Exception):
    """Base application error rendered as ``{"detail": ...}``."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class RecordNotFoundError(AppError):
    """No matching record for the given identifier."""

    status_code = 404


class UnprocessableError(AppError):
    """Request carries invalid values or no usable fields."""

    status_code = 422


class DatabaseUnavailableError(AppError):
    """The database cannot be reached."""

    status_code = 503
