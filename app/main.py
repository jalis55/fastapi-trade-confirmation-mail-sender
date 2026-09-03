"""
Application entry point.

Run locally with:

    uvicorn app.main:app --reload
"""
from fastapi import FastAPI

from app.api.v1.endpoints import account, health, reports
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(health.router)
app.include_router(account.router)
app.include_router(reports.router)