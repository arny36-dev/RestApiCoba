"""Main API router mounted under API_PREFIX."""

from fastapi import APIRouter

from app.api import health
from app.employees import router as employees

api_router = APIRouter()
api_router.include_router(health.db_router)
api_router.include_router(employees.router)
api_router.include_router(employees.types_router)
