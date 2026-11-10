"""AI provider status for the header (provider badge, demo mode, daily counter)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from postulo.config import load_settings
from postulo.services.llm import registry, usage
from postulo.services.llm.base import LLMError

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LLMStatus(BaseModel):
    provider: str
    demo_mode: bool
    available: bool
    reason: str
    calls_today: int


@router.get("/status")
def llm_status() -> LLMStatus:
    settings = load_settings()
    try:
        available, reason = registry.get_provider(settings).available()
    except LLMError as exc:
        available, reason = False, exc.message
    return LLMStatus(
        provider=settings.ai.provider,
        demo_mode=settings.demo_mode,
        available=available,
        reason=reason,
        calls_today=usage.calls_today(),
    )
