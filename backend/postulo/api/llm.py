"""AI provider: status for the header, connection test, API key (never returned)."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from postulo.config import ProviderName, load_settings
from postulo.services.llm import registry, usage
from postulo.services.llm.base import LLMError
from postulo.services.llm.providers.anthropic_api import DEFAULT_MODEL, SUGGESTED_MODELS
from postulo.services.secrets import Secret, SecretStoreError, delete_secret, has_secret, set_secret

router = APIRouter(prefix="/api/llm", tags=["llm"])

PING_PROMPT = "TASK: ping\nRéponds uniquement par le mot : pong\n"


class LLMStatus(BaseModel):
    provider: ProviderName
    model: str | None
    demo_mode: bool
    available: bool
    reason: str
    calls_today: int
    has_api_key: bool


class ProviderInfo(BaseModel):
    name: ProviderName
    implemented: bool
    personal_use_only: bool
    default_model: str | None
    suggested_models: list[str]


class TestResult(BaseModel):
    ok: bool
    provider: ProviderName
    duration_ms: int
    message: str
    detail: str = ""


class ApiKeyBody(BaseModel):
    api_key: str = Field(min_length=10, max_length=500)


@router.get("/status")
def llm_status() -> LLMStatus:
    settings = load_settings()
    try:
        available, reason = registry.get_provider(settings).available()
    except LLMError as exc:
        available, reason = False, exc.message
    return LLMStatus(
        provider=settings.ai.provider,
        model=settings.ai.model,
        demo_mode=settings.demo_mode,
        available=available,
        reason=reason,
        calls_today=usage.calls_today(),
        has_api_key=has_secret(Secret.ANTHROPIC_API_KEY),
    )


@router.get("/providers")
def list_providers() -> list[ProviderInfo]:
    return [
        ProviderInfo(
            name="mock",
            implemented=True,
            personal_use_only=False,
            default_model=None,
            suggested_models=[],
        ),
        ProviderInfo(
            name="anthropic_api",
            implemented=True,
            personal_use_only=False,
            default_model=DEFAULT_MODEL,
            suggested_models=list(SUGGESTED_MODELS),
        ),
        ProviderInfo(
            name="claude_code_cli",
            implemented=True,
            personal_use_only=True,
            default_model=None,
            suggested_models=["sonnet", "opus", "haiku"],
        ),
        ProviderInfo(
            name="openai_compatible",
            implemented=False,
            personal_use_only=False,
            default_model=None,
            suggested_models=[],
        ),
    ]


@router.post("/test")
async def test_connection() -> TestResult:
    """Send one tiny `ping` prompt to the configured provider (counts as one AI call)."""
    settings = load_settings()
    started = time.perf_counter()
    try:
        provider = registry.get_provider(settings)
        available, reason = provider.available()
        if not available:
            return TestResult(
                ok=False, provider=settings.ai.provider, duration_ms=0, message=reason
            )
        answer = await usage.tracked_complete(
            provider, PING_PROMPT, timeout=min(settings.ai.timeout_seconds, 120)
        )
    except LLMError as exc:
        return TestResult(
            ok=False,
            provider=settings.ai.provider,
            duration_ms=int((time.perf_counter() - started) * 1000),
            message=exc.message,
            detail=exc.detail,
        )
    duration = int((time.perf_counter() - started) * 1000)
    ok = "pong" in answer.lower()
    return TestResult(
        ok=ok,
        provider=settings.ai.provider,
        duration_ms=duration,
        message="Connexion réussie." if ok else "L'IA a répondu, mais pas comme prévu.",
        detail="" if ok else answer[:500],
    )


@router.put("/api-key", status_code=status.HTTP_204_NO_CONTENT)
def save_api_key(body: ApiKeyBody) -> None:
    try:
        set_secret(Secret.ANTHROPIC_API_KEY, body.api_key.strip())
    except SecretStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.delete("/api-key", status_code=status.HTTP_204_NO_CONTENT)
def remove_api_key() -> None:
    delete_secret(Secret.ANTHROPIC_API_KEY)
