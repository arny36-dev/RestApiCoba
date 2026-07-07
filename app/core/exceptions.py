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


class TableNotAllowedError(AppError):
    """Requested table is not present in the ALLOWED_TABLES whitelist."""

    status_code = 404


class RecordNotFoundError(AppError):
    """No matching record for the given primary key."""

    status_code = 404


class BadRequestError(AppError):
    """Operation is not supported for the target table."""

    status_code = 400


class UnprocessableError(AppError):
    """Request references unknown columns or carries invalid values."""

    status_code = 422
