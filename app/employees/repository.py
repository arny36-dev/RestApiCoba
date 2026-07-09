"""SQLAlchemy Core operations for the employee tables.

Only two fixed tables are ever touched: ``er_reg_employees`` (read/write) and
``er_reg_employee_types`` (read-only). There is no physical DELETE here by
design — soft delete is an UPDATE performed by the service layer.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Table, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.metadata import get_table

EMPLOYEES_TABLE = "er_reg_employees"
EMPLOYEE_TYPES_TABLE = "er_reg_employee_types"


async def employees_table() -> Table:
    return await get_table(EMPLOYEES_TABLE)


async def employee_types_table() -> Table:
    return await get_table(EMPLOYEE_TYPES_TABLE)


def _apply_where(statement: Any, conditions: Sequence[ColumnElement[bool]]) -> Any:
    for condition in conditions:
        statement = statement.where(condition)
    return statement


async def count_employees(
    session: AsyncSession, table: Table, conditions: Sequence[ColumnElement[bool]]
) -> int:
    statement = _apply_where(select(func.count()).select_from(table), conditions)
    return (await session.execute(statement)).scalar_one()


async def list_employees(
    session: AsyncSession,
    table: Table,
    conditions: Sequence[ColumnElement[bool]],
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    statement = (
        _apply_where(select(table), conditions)
        .order_by(table.c.surname.asc(), table.c.forename.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(statement)
    return [dict(row) for row in result.mappings()]


async def get_employee(
    session: AsyncSession, table: Table, conditions: Sequence[ColumnElement[bool]]
) -> dict[str, Any] | None:
    statement = _apply_where(select(table), conditions).limit(1)
    row = (await session.execute(statement)).mappings().first()
    return dict(row) if row is not None else None


async def insert_employee(
    session: AsyncSession, table: Table, values: dict[str, Any]
) -> Any | None:
    """Insert one employee and return its primary key value."""
    result = await session.execute(insert(table).values(values))
    inserted = result.inserted_primary_key
    if inserted is None or len(inserted) != 1:
        return None
    return inserted[0]


async def update_employees(
    session: AsyncSession,
    table: Table,
    conditions: Sequence[ColumnElement[bool]],
    values: dict[str, Any],
) -> int:
    """Update matching employees and return the affected row count."""
    statement = _apply_where(update(table), conditions).values(values)
    result = await session.execute(statement)
    return result.rowcount


async def list_employee_types(
    session: AsyncSession, table: Table, conditions: Sequence[ColumnElement[bool]]
) -> list[dict[str, Any]]:
    statement = _apply_where(select(table), conditions).order_by(table.c.name.asc())
    result = await session.execute(statement)
    return [dict(row) for row in result.mappings()]
