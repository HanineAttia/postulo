"""Select the AI provider from the user settings."""

from __future__ import annotations

from postulo.config import Settings, load_settings
from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider
from postulo.services.llm.providers.anthropic_api import AnthropicAPIProvider
from postulo.services.llm.providers.claude_code_cli import ClaudeCodeCLIProvider
from postulo.services.llm.providers.mock import MockProvider
from postulo.services.secrets import Secret, get_secret

# openai_compatible arrives in phase 6.
IMPLEMENTED_PROVIDERS = ("mock", "claude_code_cli", "anthropic_api")


def get_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or load_settings()
    provider = settings.ai.provider
    if provider == "mock":
        return MockProvider()
    if provider == "claude_code_cli":
        return ClaudeCodeCLIProvider(model=settings.ai.model)
    if provider == "anthropic_api":
        return AnthropicAPIProvider(get_secret(Secret.ANTHROPIC_API_KEY), settings.ai.model)
    raise LLMError(
        LLMErrorKind.NOT_AVAILABLE,
        f"Le fournisseur « {provider} » n'est pas encore disponible.",
    )
