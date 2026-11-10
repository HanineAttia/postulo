"""Provider-agnostic AI interface (docs/SPEC.md section 5.1)."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Protocol, runtime_checkable

_TASK_RE = re.compile(r"^\s*TASK:\s*([A-Za-z0-9_.-]+)", re.MULTILINE)


class LLMErrorKind(StrEnum):
    """Stable error codes. The frontend translates them; `message` is a French fallback."""

    NOT_AVAILABLE = "not_available"
    NOT_LOGGED_IN = "not_logged_in"
    USAGE_LIMIT = "usage_limit"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


_DEFAULT_MESSAGES: dict[LLMErrorKind, str] = {
    LLMErrorKind.NOT_AVAILABLE: "Le fournisseur IA choisi n'est pas disponible.",
    LLMErrorKind.NOT_LOGGED_IN: "Le fournisseur IA demande une connexion.",
    LLMErrorKind.USAGE_LIMIT: "Limite d'utilisation de l'IA atteinte. Réessaie plus tard.",
    LLMErrorKind.TIMEOUT: "L'IA a mis trop de temps à répondre. Réessaie.",
    LLMErrorKind.INVALID_RESPONSE: "La réponse de l'IA était inutilisable, même après une "
    "nouvelle tentative. Réessaie.",
    LLMErrorKind.UNKNOWN: "Erreur inattendue du fournisseur IA.",
}


class LLMError(Exception):
    """User-facing AI error. Never carries secrets or raw tracebacks in `message`."""

    def __init__(self, kind: LLMErrorKind, message: str | None = None, detail: str = "") -> None:
        self.kind = kind
        self.message = message or _DEFAULT_MESSAGES[kind]
        self.detail = detail  # technical detail, shown behind a "details" button
        super().__init__(self.message)


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def available(self) -> tuple[bool, str]:
        """Return (is_available, human-readable reason)."""
        ...

    async def complete(self, prompt: str, *, web: bool = False, timeout: int = 300) -> str:
        """Return the raw text answer for `prompt`. Raise LLMError on failure."""
        ...


def parse_task(prompt: str) -> str:
    """Extract the `TASK: <name>` marker every prompt starts with (SPEC 5.4)."""
    match = _TASK_RE.search(prompt)
    return match.group(1) if match else "unknown"
