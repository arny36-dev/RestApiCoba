"""Main API router mounted under API_PREFIX."""

from fastapi import APIRouter

from app.api import crud

api_router = APIRouter()
api_router.include_router(crud.router)
