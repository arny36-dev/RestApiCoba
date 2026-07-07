"""Low-level SQLAlchemy Core operations.

All table and column identifiers are validated by the service layer before
they reach this module, and all values are passed as bound parameters.
There is no physical DELETE here by design — soft delete is an UPDATE.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, Table, Update, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression


def _apply_where(statement: Select[Any] | Update, conditions: Sequence[ColumnElement[bool]]) -> Any:
    for condition in conditions:
        statement = statement.where(condition)
    return statement


async def count_rows(
    session: AsyncSession, table: Table, conditions: Sequence[ColumnElement[bool]]
) -> int:
    statement = _apply_where(select(func.count()).select_from(table), conditions)
    return (await session.execute(statement)).scalar_one()


async def list_rows(
    session: AsyncSession,
    table: Table,
    conditions: Sequence[ColumnElement[bool]],
    *,
    order_by: UnaryExpression[Any] | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    statement = _apply_where(select(table), conditions).limit(limit).offset(offset)
    if order_by is not None:
        statement = statement.order_by(order_by)
    result = await session.execute(statement)
    return [dict(row) for row in result.mappings()]


async def get_row(
    session: AsyncSession, table: Table, conditions: Sequence[ColumnElement[bool]]
) -> dict[str, Any] | None:
    statement = _apply_where(select(table), conditions).limit(1)
    row = (await session.execute(statement)).mappings().first()
    return dict(row) if row is not None else None


async def insert_row(session: AsyncSession, table: Table, values: dict[str, Any]) -> Any | None:
    """Insert one row and return its primary key value, if determinable."""
    result = await session.execute(insert(table).values(values))
    inserted = result.inserted_primary_key
    if inserted is None or len(inserted) != 1:
        return None
    return inserted[0]


async def update_rows(
    session: AsyncSession,
    table: Table,
    conditions: Sequence[ColumnElement[bool]],
    values: dict[str, Any],
) -> int:
    """Update matching rows and return the affected row count."""
    statement = _apply_where(update(table), conditions).values(values)
    result = await session.execute(statement)
    return result.rowcount
