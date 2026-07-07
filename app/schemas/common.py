"""Shared response schemas."""

from typing import Any, Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class TablesResponse(BaseModel):
    data: list[str]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool


class TableMetadataResponse(BaseModel):
    table: str
    columns: list[ColumnInfo]
    has_active_column: bool


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class ListResponse(BaseModel):
    data: list[dict[str, Any]]
    pagination: PaginationMeta


class DeleteResponse(BaseModel):
    status: Literal["deleted"] = "deleted"
    id: int | str


class ErrorResponse(BaseModel):
    detail: str
