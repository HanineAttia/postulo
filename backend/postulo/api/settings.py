"""Non-secret user settings. Secrets (API keys, passwords) never transit here."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from postulo.config import AISettings, Settings, UISettings, load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRead(BaseModel):
    ai: AISettings
    ui: UISettings
    demo_mode: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> SettingsRead:
        return cls(ai=settings.ai, ui=settings.ui, demo_mode=settings.demo_mode)


@router.get("")
def read_settings() -> SettingsRead:
    return SettingsRead.from_settings(load_settings())


@router.put("")
def update_settings(body: Settings) -> SettingsRead:
    """Replace the editable settings (the frontend sends the full object)."""
    save_settings(body)
    return SettingsRead.from_settings(body)
