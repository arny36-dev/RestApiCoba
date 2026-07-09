"""Biznis pravidlá pre zamestnancov — správanie prevzaté zo starého CakePHP.

- Zoznamy vždy filtrujú ``active = 1`` a radia podľa priezviska a mena.
- Textové filtre hľadajú čiastočnú zhodu (LIKE %hodnota%).
- ``rfid_gate`` / ``rfid_littlegate`` filtrujú len pri hodnote 0 alebo 1 (2 = všetko).
- ``object_id`` sa dopĺňa z DEFAULT_OBJECT_ID v .env.
- DELETE je len soft delete: nastaví ``active = 0``, záznam ostáva v databáze.
"""

import logging
import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import Settings
from app.core.exceptions import RecordNotFoundError, UnprocessableError
from app.employees import repository
from app.employees.schemas import EmployeeCreate, EmployeeUpdate

logger = logging.getLogger(__name__)

CREATE_TIMESTAMP_COLUMNS = ("created", "created_at")
UPDATE_TIMESTAMP_COLUMNS = ("modified", "modified_at", "updated_at")

# Skutočný stĺpec er_reg_employees.bozp_state je ENUM, ktorého hodnota
# "bez školenia" je 'NO BOZP' (s medzerou); stĺpec bozp_status neexistuje.
BOZP_STATE_COLUMN = "bozp_state"
BOZP_STATE_DEFAULT = "NO BOZP"
BOZP_REQUIRED_COLUMN = "bozp_required"

# Slovenské názvy polí pre logy.
FIELD_NAMES_SK = {
    "forename": "meno",
    "surname": "priezvisko",
    "type": "typ",
    "rfid": "RFID",
    "rfid_gate": "brána",
    "rfid_littlegate": "malá brána",
    "ecv": "EČV",
    "allowed_from": "platné od",
    "allowed_to": "platné do",
    "note": "poznámka",
    "object_id": "objekt",
    "bozp_state": "stav BOZP",
}


def _sk(field: str) -> str:
    return FIELD_NAMES_SK.get(field, field)


def _full_name(row: dict[str, Any]) -> str:
    return f"{row.get('surname') or ''} {row.get('forename') or ''}".strip() or "(bez mena)"


def _now(column: Column[Any]) -> datetime:
    now = datetime.now(UTC)
    if getattr(column.type, "timezone", False):
        return now
    return now.replace(tzinfo=None)


def _partial_match(column: Column[Any], raw: str) -> ColumnElement[bool]:
    pattern = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.ilike(f"%{pattern}%", escape="\\")


def _resolve_page_size(page_size: int | None, settings: Settings) -> int:
    if page_size is None:
        return settings.default_page_size
    if page_size > settings.max_page_size:
        raise UnprocessableError(
            f"page_size nesmie byť väčšie ako {settings.max_page_size} (zadané {page_size})"
        )
    return page_size


def _stamp_timestamps(table: Table, values: dict[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        column = table.columns.get(name)
        if column is not None and name not in values:
            values[name] = _now(column)


def _apply_object_id_default(table: Table, values: dict[str, Any], settings: Settings) -> None:
    if "object_id" not in table.columns:
        return
    if values.get("object_id") is None:
        values["object_id"] = settings.default_object_id


async def list_employees(
    session: AsyncSession,
    settings: Settings,
    *,
    page: int,
    page_size: int | None,
    forename: str | None,
    surname: str | None,
    employee_type: str | None,
    rfid: str | None,
    rfid_gate: int | None,
    rfid_littlegate: int | None,
    ecv: str | None,
    note: str | None,
    bozp_state: str | None,
    object_id: int | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    table = await repository.employees_table()
    size = _resolve_page_size(page_size, settings)

    conditions: list[ColumnElement[bool]] = [table.c.active == 1]
    applied_filters: list[str] = []

    effective_object_id = object_id if object_id is not None else settings.default_object_id
    if effective_object_id is not None and "object_id" in table.columns:
        conditions.append(table.c.object_id == effective_object_id)

    text_values = {
        "forename": forename,
        "surname": surname,
        "type": employee_type,
        "rfid": rfid,
        "ecv": ecv,
        "note": note,
        "bozp_state": bozp_state,
    }
    for name, value in text_values.items():
        column = table.columns.get(name)
        if value is not None and column is not None:
            conditions.append(_partial_match(column, value))
            applied_filters.append(f"{_sk(name)} obsahuje '{value}'")

    # 2 znamená "všetko" — filtruje sa len 0 alebo 1.
    if rfid_gate is not None and rfid_gate != 2:
        conditions.append(table.c.rfid_gate == rfid_gate)
        applied_filters.append(f"brána = {rfid_gate}")
    if rfid_littlegate is not None and rfid_littlegate != 2:
        conditions.append(table.c.rfid_littlegate == rfid_littlegate)
        applied_filters.append(f"malá brána = {rfid_littlegate}")

    total = await repository.count_employees(session, table, conditions)
    rows = await repository.list_employees(
        session, table, conditions, limit=size, offset=(page - 1) * size
    )

    filters_text = f" | filtre: {', '.join(applied_filters)}" if applied_filters else ""
    logger.info(
        "Zoznam zamestnancov: nájdených %d, zobrazená strana %d (%d na stranu)%s",
        total,
        page,
        size,
        filters_text,
    )

    pagination = {
        "page": page,
        "page_size": size,
        "total": total,
        "pages": math.ceil(total / size) if total else 0,
    }
    return rows, pagination


async def get_employee(session: AsyncSession, employee_id: int) -> dict[str, Any]:
    table = await repository.employees_table()
    row = await repository.get_employee(
        session, table, [table.c.id == employee_id, table.c.active == 1]
    )
    if row is None:
        raise RecordNotFoundError(f"Zamestnanec {employee_id} neexistuje alebo je neaktívny")
    logger.info("Zobrazený detail zamestnanca ID %d: %s", employee_id, _full_name(row))
    return row


async def create_employee(
    session: AsyncSession, settings: Settings, payload: EmployeeCreate
) -> dict[str, Any]:
    table = await repository.employees_table()
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)

    _apply_object_id_default(table, values, settings)
    values["active"] = 1
    if BOZP_STATE_COLUMN in table.columns:
        values[BOZP_STATE_COLUMN] = BOZP_STATE_DEFAULT
    if BOZP_REQUIRED_COLUMN in table.columns:
        values[BOZP_REQUIRED_COLUMN] = 0
    _stamp_timestamps(table, values, CREATE_TIMESTAMP_COLUMNS)
    _stamp_timestamps(table, values, UPDATE_TIMESTAMP_COLUMNS)

    employee_id = await repository.insert_employee(session, table, values)
    await session.commit()

    row = await repository.get_employee(session, table, [table.c.id == employee_id])
    if row is None:
        raise RecordNotFoundError("Vytvoreného zamestnanca sa nepodarilo načítať späť")
    logger.info("Vytvorený nový zamestnanec ID %s: %s", row.get("id"), _full_name(row))
    return row


async def update_employee(
    session: AsyncSession, employee_id: int, payload: EmployeeUpdate
) -> dict[str, Any]:
    """Spoločná implementácia pre PUT aj PATCH: upraví len zadané polia."""
    table = await repository.employees_table()
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not values:
        raise UnprocessableError("Telo požiadavky musí obsahovať aspoň jedno upraviteľné pole")

    changed_fields = [_sk(name) for name in values]
    _stamp_timestamps(table, values, UPDATE_TIMESTAMP_COLUMNS)

    conditions = [table.c.id == employee_id, table.c.active == 1]
    updated = await repository.update_employees(session, table, conditions, values)
    if updated == 0:
        raise RecordNotFoundError(f"Zamestnanec {employee_id} neexistuje alebo je neaktívny")
    await session.commit()

    row = await repository.get_employee(session, table, [table.c.id == employee_id])
    if row is None:
        raise RecordNotFoundError("Upraveného zamestnanca sa nepodarilo načítať späť")
    logger.info(
        "Upravený zamestnanec ID %d (%s) | zmenené: %s",
        employee_id,
        _full_name(row),
        ", ".join(changed_fields),
    )
    return row


async def soft_delete_employee(session: AsyncSession, employee_id: int) -> int:
    """Len soft delete: nastaví ``active = 0``. Fyzické mazanie sa nikdy nevykoná."""
    table = await repository.employees_table()
    values: dict[str, Any] = {"active": 0}
    _stamp_timestamps(table, values, UPDATE_TIMESTAMP_COLUMNS)

    conditions = [table.c.id == employee_id, table.c.active == 1]
    updated = await repository.update_employees(session, table, conditions, values)
    if updated == 0:
        raise RecordNotFoundError(f"Zamestnanec {employee_id} neexistuje alebo je neaktívny")
    await session.commit()
    logger.info(
        "Zamestnanec ID %d označený ako neaktívny (active = 0) — záznam ostáva v databáze",
        employee_id,
    )
    return employee_id


async def list_employee_types(session: AsyncSession, settings: Settings) -> list[dict[str, Any]]:
    table = await repository.employee_types_table()
    conditions: list[ColumnElement[bool]] = []
    if "active" in table.columns:
        conditions.append(table.c.active == 1)
    if settings.default_object_id is not None and "object_id" in table.columns:
        conditions.append(table.c.object_id == settings.default_object_id)
    rows = await repository.list_employee_types(session, table, conditions)
    logger.info("Načítané typy zamestnancov: %d", len(rows))
    return rows
