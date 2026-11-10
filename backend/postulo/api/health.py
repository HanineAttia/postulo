"""Liveness endpoint, also used by `postulo` to detect an already running instance."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from postulo import APP_NAME, __version__

router = APIRouter(prefix="/api", tags=["health"])


class Health(BaseModel):
    app: str
    version: str
    status: str


@router.get("/health")
def health() -> Health:
    return Health(app=APP_NAME, version=__version__, status="ok")
