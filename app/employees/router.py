"""Explicit employee routes. No dynamic table names anywhere."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.employees import service
from app.employees.schemas import (
    DeleteResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeTypesResponse,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["employees"])
types_router = APIRouter(tags=["employee-types"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

GateFilter = Annotated[int | None, Query(ge=0, le=2, description="0, 1, or 2 = all")]


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    session: SessionDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    forename: str | None = None,
    surname: str | None = None,
    employee_type: Annotated[str | None, Query(alias="type")] = None,
    rfid: str | None = None,
    rfid_gate: GateFilter = None,
    rfid_littlegate: GateFilter = None,
    ecv: str | None = None,
    note: str | None = None,
    bozp_state: str | None = None,
    object_id: int | None = None,
) -> Any:
    rows, pagination = await service.list_employees(
        session,
        settings,
        page=page,
        page_size=page_size,
        forename=forename,
        surname=surname,
        employee_type=employee_type,
        rfid=rfid,
        rfid_gate=rfid_gate,
        rfid_littlegate=rfid_littlegate,
        ecv=ecv,
        note=note,
        bozp_state=bozp_state,
        object_id=object_id,
    )
    return {"data": rows, "pagination": pagination}


@router.get("/{employee_id}")
async def get_employee(employee_id: int, session: SessionDep) -> dict[str, Any]:
    return await service.get_employee(session, employee_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate, session: SessionDep, settings: SettingsDep
) -> dict[str, Any]:
    return await service.create_employee(session, settings, payload)


@router.put("/{employee_id}")
async def replace_employee(
    employee_id: int, payload: EmployeeUpdate, session: SessionDep
) -> dict[str, Any]:
    return await service.update_employee(session, employee_id, payload)


@router.patch("/{employee_id}")
async def patch_employee(
    employee_id: int, payload: EmployeeUpdate, session: SessionDep
) -> dict[str, Any]:
    return await service.update_employee(session, employee_id, payload)


@router.delete("/{employee_id}", response_model=DeleteResponse)
async def soft_delete_employee(employee_id: int, session: SessionDep) -> Any:
    deleted_id = await service.soft_delete_employee(session, employee_id)
    return {"status": "deleted", "id": deleted_id}


@types_router.get("/employee-types", response_model=EmployeeTypesResponse)
async def list_employee_types(session: SessionDep, settings: SettingsDep) -> Any:
    rows = await service.list_employee_types(session, settings)
    return {"data": rows}
