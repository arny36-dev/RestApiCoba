"""Explicit employee routes. No dynamic table names anywhere."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import require_api_key
from app.db.session import get_session
from app.employees import service
from app.employees.schemas import (
    DeleteResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeTypesResponse,
    EmployeeUpdate,
)

# All employee and employee-type routes require a valid X-API-Key header.
router = APIRouter(
    prefix="/employees", tags=["employees"], dependencies=[Depends(require_api_key)]
)
types_router = APIRouter(tags=["employee-types"], dependencies=[Depends(require_api_key)])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

@router.get("", response_model=EmployeeListResponse)
async def list_employees(session: SessionDep, settings: SettingsDep) -> Any:
    # Bez filtrov a bez stránkovania: vráti VŠETKY aktívne (active=1) záznamy objektu 127.
    rows = await service.list_employees(session, settings)
    return {"data": rows}


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
    employee_id: int, payload: EmployeeUpdate, session: SessionDep, settings: SettingsDep
) -> dict[str, Any]:
    return await service.update_employee(session, settings, employee_id, payload)


@router.patch("/{employee_id}")
async def patch_employee(
    employee_id: int, payload: EmployeeUpdate, session: SessionDep, settings: SettingsDep
) -> dict[str, Any]:
    return await service.update_employee(session, settings, employee_id, payload)


@router.delete("/{employee_id}", response_model=DeleteResponse)
async def soft_delete_employee(employee_id: int, session: SessionDep) -> Any:
    deleted_id = await service.soft_delete_employee(session, employee_id)
    return {"status": "deleted", "id": deleted_id}


@types_router.get("/employee-types", response_model=EmployeeTypesResponse)
async def list_employee_types(session: SessionDep, settings: SettingsDep) -> Any:
    rows = await service.list_employee_types(session, settings)
    return {"data": rows}
