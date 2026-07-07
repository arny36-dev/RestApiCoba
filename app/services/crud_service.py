"""Validation and business rules for the generic CRUD operations.

Every table name is checked against the ALLOWED_TABLES whitelist and every
column name (filters, sort, insert/update fields) against the reflected table
metadata before any SQL statement is built.
"""

import math
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import Column, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from app.core.config import Settings
from app.core.exceptions import (
    BadRequestError,
    RecordNotFoundError,
    TableNotAllowedError,
    UnprocessableError,
)
from app.db import repository
from app.db.metadata import get_table

RESERVED_QUERY_PARAMS = frozenset({"page", "page_size", "sort", "order", "include_inactive"})
CREATE_TIMESTAMP_COLUMNS = ("created", "created_at", "modified", "updated_at")
UPDATE_TIMESTAMP_COLUMNS = ("modified", "updated_at")


async def resolve_table(table_name: str, settings: Settings) -> Table:
    """Validate the table against the whitelist and return its reflected metadata."""
    if table_name not in settings.allowed_tables_list:
        raise TableNotAllowedError(f"Table '{table_name}' is not allowed")
    return await get_table(table_name)


def _python_type(column: Column[Any]) -> type | None:
    try:
        return column.type.python_type
    except NotImplementedError:
        return None


def _primary_key_column(table: Table) -> Column[Any]:
    pk_columns = list(table.primary_key.columns)
    if len(pk_columns) != 1:
        raise BadRequestError(f"Table '{table.name}' does not have a single-column primary key")
    return pk_columns[0]


def _active_column(table: Table) -> Column[Any] | None:
    return table.columns.get("active")


def _active_value(column: Column[Any], flag: bool) -> Any:
    """The value representing active/inactive for this column (bool or 1/0)."""
    if _python_type(column) is bool:
        return flag
    return 1 if flag else 0


def _timestamp_value(column: Column[Any]) -> Any:
    now = datetime.now(UTC)
    if _python_type(column) is date:
        return now.date()
    if getattr(column.type, "timezone", False):
        return now
    return now.replace(tzinfo=None)


def _coerce_value(column: Column[Any], raw: Any) -> Any:
    """Coerce a raw query/body value into the column's Python type."""
    if raw is None:
        return None
    python_type = _python_type(column)
    try:
        if python_type is bool:
            if isinstance(raw, bool):
                return raw
            text = str(raw).strip().lower()
            if text in {"1", "true", "t", "yes"}:
                return True
            if text in {"0", "false", "f", "no"}:
                return False
            raise ValueError(text)
        if python_type is int and not isinstance(raw, bool):
            return int(raw)
        if python_type is float:
            return float(raw)
        if python_type is Decimal:
            return Decimal(str(raw))
        if python_type is datetime and not isinstance(raw, datetime):
            return datetime.fromisoformat(str(raw))
        if python_type is date and not isinstance(raw, date):
            return date.fromisoformat(str(raw))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise UnprocessableError(f"Invalid value for column '{column.name}': {raw!r}") from exc
    return raw


def _is_temporal(column: Column[Any]) -> bool:
    return _python_type(column) in {date, datetime}


def _filter_condition(column: Column[Any], raw: str) -> ColumnElement[bool]:
    """Text columns match case-insensitive partial; other types match exactly."""
    if _python_type(column) is str:
        pattern = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return column.ilike(f"%{pattern}%", escape="\\")
    return column == _coerce_value(column, raw)


def _range_condition(table: Table, key: str, raw: str) -> ColumnElement[bool] | None:
    """Support ``{field}_from`` / ``{field}_to`` filters on date/datetime columns."""
    for suffix in ("_from", "_to"):
        if not key.endswith(suffix):
            continue
        column = table.columns.get(key.removesuffix(suffix))
        if column is None or not _is_temporal(column):
            return None
        value = _coerce_value(column, raw)
        return column >= value if suffix == "_from" else column <= value
    return None


def _build_filters(table: Table, filters: list[tuple[str, str]]) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for key, raw in filters:
        column = table.columns.get(key)
        if column is not None:
            conditions.append(_filter_condition(column, raw))
            continue
        range_condition = _range_condition(table, key, raw)
        if range_condition is None:
            raise UnprocessableError(f"Unknown filter column: '{key}'")
        conditions.append(range_condition)
    return conditions


def _validate_payload_columns(table: Table, payload: dict[str, Any]) -> None:
    if not payload:
        raise UnprocessableError("Request body must contain at least one column")
    unknown = sorted(set(payload) - set(table.columns.keys()))
    if unknown:
        raise UnprocessableError(f"Unknown columns: {', '.join(unknown)}")


def _coerce_payload(table: Table, payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _coerce_value(table.columns[key], value) for key, value in payload.items()}


async def get_table_metadata(table_name: str, settings: Settings) -> dict[str, Any]:
    table = await resolve_table(table_name, settings)
    columns = [
        {
            "name": column.name,
            "type": str(column.type).lower(),
            "nullable": bool(column.nullable),
            "primary_key": column.primary_key,
        }
        for column in table.columns
    ]
    return {
        "table": table.name,
        "columns": columns,
        "has_active_column": _active_column(table) is not None,
    }


async def list_records(
    session: AsyncSession,
    table_name: str,
    settings: Settings,
    *,
    page: int,
    page_size: int | None,
    sort: str | None,
    order: str,
    include_inactive: bool,
    filters: list[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    table = await resolve_table(table_name, settings)

    # page_size is clamped to MAX_PAGE_SIZE (documented behavior, not an error).
    size = min(page_size or settings.default_page_size, settings.max_page_size)

    conditions = _build_filters(table, filters)
    active = _active_column(table)
    if active is not None and not include_inactive:
        conditions.append(active == _active_value(active, True))

    order_by: UnaryExpression[Any] | None = None
    if sort is not None:
        sort_column = table.columns.get(sort)
        if sort_column is None:
            raise UnprocessableError(f"Unknown sort column: '{sort}'")
        order_by = sort_column.desc() if order == "desc" else sort_column.asc()

    total = await repository.count_rows(session, table, conditions)
    rows = await repository.list_rows(
        session, table, conditions, order_by=order_by, limit=size, offset=(page - 1) * size
    )
    pagination = {
        "page": page,
        "page_size": size,
        "total": total,
        "pages": math.ceil(total / size) if total else 0,
    }
    return rows, pagination


async def get_record(
    session: AsyncSession,
    table_name: str,
    record_id: str,
    settings: Settings,
    *,
    include_inactive: bool,
) -> dict[str, Any]:
    table = await resolve_table(table_name, settings)
    pk = _primary_key_column(table)
    conditions: list[ColumnElement[bool]] = [pk == _coerce_value(pk, record_id)]
    active = _active_column(table)
    if active is not None and not include_inactive:
        conditions.append(active == _active_value(active, True))
    row = await repository.get_row(session, table, conditions)
    if row is None:
        raise RecordNotFoundError(f"Record '{record_id}' not found in '{table_name}'")
    return row


async def create_record(
    session: AsyncSession,
    table_name: str,
    payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    table = await resolve_table(table_name, settings)
    _validate_payload_columns(table, payload)

    autoincrement = table.autoincrement_column
    if autoincrement is not None and autoincrement.name in payload:
        raise UnprocessableError(
            f"Column '{autoincrement.name}' is auto-generated and cannot be set"
        )

    pk = _primary_key_column(table)
    values = _coerce_payload(table, payload)

    active = _active_column(table)
    if active is not None and "active" not in values:
        values["active"] = _active_value(active, True)

    for name in CREATE_TIMESTAMP_COLUMNS:
        column = table.columns.get(name)
        if column is not None and name not in values:
            values[name] = _timestamp_value(column)

    pk_value = await repository.insert_row(session, table, values)
    await session.commit()

    if pk_value is None:
        pk_value = values.get(pk.name)
    row = await repository.get_row(session, table, [pk == pk_value])
    if row is None:
        raise RecordNotFoundError("Created record could not be reloaded")
    return row


async def update_record(
    session: AsyncSession,
    table_name: str,
    record_id: str,
    payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """Shared implementation for PUT and PATCH: update only the provided fields."""
    table = await resolve_table(table_name, settings)
    _validate_payload_columns(table, payload)

    pk = _primary_key_column(table)
    if pk.name in payload:
        raise UnprocessableError(f"Primary key column '{pk.name}' cannot be changed")

    values = _coerce_payload(table, payload)
    for name in UPDATE_TIMESTAMP_COLUMNS:
        column = table.columns.get(name)
        if column is not None:
            values[name] = _timestamp_value(column)

    pk_value = _coerce_value(pk, record_id)
    updated = await repository.update_rows(session, table, [pk == pk_value], values)
    if updated == 0:
        raise RecordNotFoundError(f"Record '{record_id}' not found in '{table_name}'")
    await session.commit()

    row = await repository.get_row(session, table, [pk == pk_value])
    if row is None:
        raise RecordNotFoundError("Updated record could not be reloaded")
    return row


async def soft_delete_record(
    session: AsyncSession,
    table_name: str,
    record_id: str,
    settings: Settings,
) -> Any:
    """Soft delete only: set ``active = 0``. Physical DELETE is never issued."""
    table = await resolve_table(table_name, settings)
    active = _active_column(table)
    if active is None:
        raise BadRequestError(
            f"Table '{table_name}' has no 'active' column and does not support soft delete"
        )

    pk = _primary_key_column(table)
    pk_value = _coerce_value(pk, record_id)

    values: dict[str, Any] = {"active": _active_value(active, False)}
    for name in UPDATE_TIMESTAMP_COLUMNS:
        column = table.columns.get(name)
        if column is not None:
            values[name] = _timestamp_value(column)

    updated = await repository.update_rows(session, table, [pk == pk_value], values)
    if updated == 0:
        raise RecordNotFoundError(f"Record '{record_id}' not found in '{table_name}'")
    await session.commit()
    return pk_value
