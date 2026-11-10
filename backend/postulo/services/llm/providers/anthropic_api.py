"""Anthropic API provider, with the user's own API key (docs/SPEC.md section 5.2).

Uses the official `anthropic` SDK. The model is configurable (default: Claude
Sonnet 5.5, for its cost and quality balance). Server-side fallback ("default")
is requested so a policy decline is retried on Anthropic's recommended model;
on models without fallback support the request simply runs alone.
"""

from __future__ import annotations

from typing import Any

import anthropic
import httpx2

from postulo.services.llm.base import LLMError, LLMErrorKind

DEFAULT_MODEL = "claude-sonnet-5-5"
SUGGESTED_MODELS = ("claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5")
MAX_TOKENS = 16_000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_MAX_CONTINUATIONS = 4  # `pause_turn` continuations of a long server-side web search
# Models that support the dynamic-filtering web search tool; others get the basic one.
_DYNAMIC_WEB_SEARCH_PREFIXES = (
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-fable-5",
)


def web_search_tool(model: str) -> dict[str, Any]:
    if model.startswith(_DYNAMIC_WEB_SEARCH_PREFIXES):
        return {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}
    return {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


class AnthropicAPIProvider:
    name = "anthropic_api"

    def __init__(
        self,
        api_key: str | None,
        model: str | None = None,
        *,
        http_client: httpx2.AsyncClient | None = None,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self.model = model or DEFAULT_MODEL
        self._http_client = http_client  # tests inject a mock transport
        self._max_retries = max_retries

    def available(self) -> tuple[bool, str]:
        if not self._api_key:
            return False, "Ajoute ta clé API Anthropic dans Réglages."
        return True, f"API Anthropic, modèle {self.model}."

    async def complete(self, prompt: str, *, web: bool = False, timeout: int = 300) -> str:
        if not self._api_key:
            raise LLMError(LLMErrorKind.NOT_LOGGED_IN, self.available()[1])
        client = anthropic.AsyncAnthropic(
            api_key=self._api_key,
            timeout=float(timeout),
            max_retries=self._max_retries,
            http_client=self._http_client,
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        extra: dict[str, Any] = {"tools": [web_search_tool(self.model)]} if web else {}
        texts: list[str] = []
        try:
            for _ in range(_MAX_CONTINUATIONS + 1):
                response = await client.beta.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    messages=messages,  # type: ignore[arg-type]
                    betas=[FALLBACK_BETA],
                    fallbacks="default",
                    **extra,
                )
                if response.stop_reason == "refusal":
                    raise LLMError(
                        LLMErrorKind.INVALID_RESPONSE,
                        "L'IA a refusé de traiter cette demande.",
                        str(response.stop_details),
                    )
                texts += [block.text for block in response.content if block.type == "text"]
                if response.stop_reason != "pause_turn":
                    break
                # Long server-side tool use: send the partial turn back to let it finish.
                messages.append({"role": "assistant", "content": response.content})
        except anthropic.AuthenticationError as exc:
            raise LLMError(
                LLMErrorKind.NOT_LOGGED_IN,
                "Ta clé API Anthropic est refusée. Vérifie-la dans Réglages.",
                _detail(exc),
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMError(
                LLMErrorKind.NOT_AVAILABLE,
                "Ta clé API n'a pas accès à ce modèle ou à cette fonction.",
                _detail(exc),
            ) from exc
        except anthropic.NotFoundError as exc:
            raise LLMError(
                LLMErrorKind.NOT_AVAILABLE,
                f"Le modèle « {self.model} » est introuvable. Choisis un autre modèle dans "
                "Réglages.",
                _detail(exc),
            ) from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(LLMErrorKind.USAGE_LIMIT, detail=_detail(exc)) from exc
        except anthropic.APITimeoutError as exc:
            raise LLMError(LLMErrorKind.TIMEOUT, detail=_detail(exc)) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(
                LLMErrorKind.NOT_AVAILABLE,
                "Impossible de joindre l'API Anthropic. Vérifie ta connexion internet.",
                _detail(exc),
            ) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(
                LLMErrorKind.UNKNOWN,
                "L'API Anthropic a renvoyé une erreur. Réessaie dans un moment.",
                _detail(exc),
            ) from exc
        finally:
            await client.close()
        text = "".join(texts).strip()
        if not text:
            raise LLMError(LLMErrorKind.INVALID_RESPONSE, "L'IA n'a rien répondu.")
        return text


def _detail(exc: anthropic.APIError) -> str:
    status = getattr(exc, "status_code", None)
    prefix = f"HTTP {status}: " if status else ""
    return (prefix + str(exc.message))[:1500]
