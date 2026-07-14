"""Pydantic schemas for the employee endpoints.

``extra="forbid"`` on the write schemas rejects unknown fields with 422 and
also blocks writing ``id``, ``active``, or any other non-editable column.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

GateFlag = Annotated[int, Field(ge=0, le=1, description="0 or 1")]


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surname: str = Field(min_length=1, max_length=50)
    forename: str | None = Field(None, max_length=50)
    type: str | None = Field(None, max_length=50)
    rfid: str | None = Field(None, max_length=50)
    rfid_gate: GateFlag | None = None
    rfid_littlegate: GateFlag | None = None
    ecv: str | None = Field(None, max_length=50)
    allowed_from: datetime | None = None
    allowed_to: datetime | None = None
    note: str | None = Field(None, max_length=200)
    # object_id sa neprijíma od klienta — vždy sa nastaví na DEFAULT_OBJECT_ID (127).


class EmployeeUpdate(BaseModel):
    """Editable fields for PUT/PATCH. ``id`` and ``active`` are not editable."""

    model_config = ConfigDict(extra="forbid")

    surname: str | None = Field(None, min_length=1, max_length=50)
    forename: str | None = Field(None, max_length=50)
    type: str | None = Field(None, max_length=50)
    rfid: str | None = Field(None, max_length=50)
    rfid_gate: GateFlag | None = None
    rfid_littlegate: GateFlag | None = None
    ecv: str | None = Field(None, max_length=50)
    allowed_from: datetime | None = None
    allowed_to: datetime | None = None
    note: str | None = Field(None, max_length=200)


class EmployeeListResponse(BaseModel):
    data: list[dict[str, Any]]


class EmployeeTypesResponse(BaseModel):
    data: list[dict[str, Any]]


class DeleteResponse(BaseModel):
    status: Literal["deleted"] = "deleted"
    id: int
