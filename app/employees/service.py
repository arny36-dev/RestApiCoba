"""Biznis pravidlá pre zamestnancov — správanie prevzaté zo starého CakePHP.

- Zoznam vracia VŠETKY aktívne (``active = 1``) záznamy objektu z DEFAULT_OBJECT_ID,
  bez akýchkoľvek filtrov, zoradené podľa priezviska, mena a id.
- ``object_id`` sa pri zápise vždy nastaví na DEFAULT_OBJECT_ID.
- DELETE je len soft delete: nastaví ``active = 0``, záznam ostáva v databáze.
"""

import logging
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


def _stamp_timestamps(table: Table, values: dict[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        column = table.columns.get(name)
        if column is not None and name not in values:
            values[name] = _now(column)


async def _ensure_valid_type(
    session: AsyncSession, settings: Settings, values: dict[str, Any]
) -> None:
    """``type`` musí byť názov existujúceho aktívneho typu z er_reg_employee_types.

    Kontroluje sa iba keď je ``type`` v požiadavke a nie je prázdny. Rozsah je
    rovnaký ako pri zozname typov: aktívne typy pre nastavený objekt.
    """
    type_value = values.get("type")
    if type_value is None:
        return

    types_table = await repository.employee_types_table()
    conditions: list[ColumnElement[bool]] = [types_table.c.name == type_value]
    if "active" in types_table.columns:
        conditions.append(types_table.c.active == 1)
    if settings.default_object_id is not None and "object_id" in types_table.columns:
        conditions.append(types_table.c.object_id == settings.default_object_id)

    if not await repository.employee_type_exists(session, types_table, conditions):
        raise UnprocessableError(
            f"Neplatný typ zamestnanca: '{type_value}'. "
            "Použite niektorý z názvov z GET /api/v1/employee-types."
        )


def _apply_object_id_default(table: Table, values: dict[str, Any], settings: Settings) -> None:
    # object_id sa neprijíma od klienta (nie je v EmployeeCreate) — vždy sa
    # nastaví na DEFAULT_OBJECT_ID.
    if "object_id" in table.columns:
        values["object_id"] = settings.default_object_id


async def list_employees(
    session: AsyncSession,
    settings: Settings,
) -> list[dict[str, Any]]:
    table = await repository.employees_table()

    # Žiadne filtre, žiadne stránkovanie — iba pevné obmedzenia:
    # aktívne záznamy pre nastavený objekt.
    conditions: list[ColumnElement[bool]] = [table.c.active == 1]
    if settings.default_object_id is not None and "object_id" in table.columns:
        conditions.append(table.c.object_id == settings.default_object_id)

    rows = await repository.list_employees(session, table, conditions)
    logger.info("Zoznam zamestnancov: vrátených %d (všetky, bez stránkovania)", len(rows))
    return rows


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

    await _ensure_valid_type(session, settings, values)
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
    session: AsyncSession, settings: Settings, employee_id: int, payload: EmployeeUpdate
) -> dict[str, Any]:
    """Spoločná implementácia pre PUT aj PATCH: upraví len zadané polia."""
    table = await repository.employees_table()
    values: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not values:
        raise UnprocessableError("Telo požiadavky musí obsahovať aspoň jedno upraviteľné pole")

    await _ensure_valid_type(session, settings, values)
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
