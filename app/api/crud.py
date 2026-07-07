"""Generic CRUD routes over whitelisted tables.

Route order matters: ``/tables`` must be registered before ``/{table}`` and
``/{table}/metadata`` before ``/{table}/{record_id}``.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.schemas.common import (
    DeleteResponse,
    ListResponse,
    TableMetadataResponse,
    TablesResponse,
)
from app.services import crud_service

router = APIRouter(tags=["crud"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
PayloadDep = Annotated[dict[str, Any], Body()]


@router.get("/tables", response_model=TablesResponse)
async def list_allowed_tables(settings: SettingsDep) -> Any:
    return {"data": settings.allowed_tables_list}


@router.get("/{table}/metadata", response_model=TableMetadataResponse)
async def get_table_metadata(table: str, settings: SettingsDep) -> Any:
    return await crud_service.get_table_metadata(table, settings)


@router.get("/{table}", response_model=ListResponse)
async def list_records(
    table: str,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1)] = None,
    sort: str | None = None,
    order: Literal["asc", "desc"] = "asc",
    include_inactive: bool = False,
) -> Any:
    filters = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in crud_service.RESERVED_QUERY_PARAMS
    ]
    rows, pagination = await crud_service.list_records(
        session,
        table,
        settings,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
        include_inactive=include_inactive,
        filters=filters,
    )
    return {"data": rows, "pagination": pagination}


@router.get("/{table}/{record_id}")
async def get_record(
    table: str,
    record_id: str,
    session: SessionDep,
    settings: SettingsDep,
    include_inactive: bool = False,
) -> dict[str, Any]:
    return await crud_service.get_record(
        session, table, record_id, settings, include_inactive=include_inactive
    )


@router.post("/{table}", status_code=status.HTTP_201_CREATED)
async def create_record(
    table: str,
    payload: PayloadDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return await crud_service.create_record(session, table, payload, settings)


@router.put("/{table}/{record_id}")
async def replace_record(
    table: str,
    record_id: str,
    payload: PayloadDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return await crud_service.update_record(session, table, record_id, payload, settings)


@router.patch("/{table}/{record_id}")
async def patch_record(
    table: str,
    record_id: str,
    payload: PayloadDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    return await crud_service.update_record(session, table, record_id, payload, settings)


@router.delete("/{table}/{record_id}", response_model=DeleteResponse)
async def soft_delete_record(
    table: str,
    record_id: str,
    session: SessionDep,
    settings: SettingsDep,
) -> Any:
    deleted_id = await crud_service.soft_delete_record(session, table, record_id, settings)
    return {"status": "deleted", "id": deleted_id}
