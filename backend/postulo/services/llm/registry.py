"""Select the AI provider from the user settings."""

from __future__ import annotations

from postulo.config import Settings, load_settings
from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider
from postulo.services.llm.providers.mock import MockProvider

# Real providers (claude_code_cli, anthropic_api) arrive in phase 1, openai_compatible in phase 6.
IMPLEMENTED_PROVIDERS = ("mock",)


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or load_settings()
    if settings.ai.provider == "mock":
        return MockProvider()
    raise LLMError(
        LLMErrorKind.NOT_AVAILABLE,
        f"Le fournisseur « {settings.ai.provider} » n'est pas encore disponible.",
    )
