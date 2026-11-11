"""Deterministic fake provider, for tests and demo mode.

Answers are selected by the `TASK: <name>` marker at the top of the prompt. It
never touches the network and never consumes any quota.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any

from postulo.services.llm.base import parse_task
from postulo.services.llm.providers.mock_application import (
    mock_application_draft,
    mock_application_revision,
    mock_jury,
    mock_offer_meta,
)
from postulo.services.llm.providers.mock_cv import mock_cv_extract

Responder = Callable[[str], str]


def _json(payload: Any) -> Responder:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return lambda _prompt: f"```json\n{text}\n```"


DEFAULT_RESPONSES: dict[str, Responder] = {
    "ping": lambda _prompt: "pong",
    "demo": _json(
        {
            "headline": "Stage de fin d'études en data science, 6 mois, dès février 2027",
            "summary": "Réponse simulée par le mode démo de Postulo.",
            "score": 82,
        }
    ),
    "cv_extract": mock_cv_extract,
    "application_draft": mock_application_draft,
    "application_revision": mock_application_revision,
    "jury": mock_jury,
    "offer_meta": mock_offer_meta,
}


def _constant(text: str) -> Responder:
    def respond(_prompt: str) -> str:
        return text

    return respond


class MockProvider:
    name = "mock"

    def __init__(
        self,
        responses: Mapping[str, Responder | str] | None = None,
        *,
        delay: float = 0.0,
    ) -> None:
        self._responses: dict[str, Responder] = dict(DEFAULT_RESPONSES)
        for task, value in (responses or {}).items():
            self._responses[task] = value if callable(value) else _constant(value)
        self._delay = delay
        self.calls: list[str] = []

    def available(self) -> tuple[bool, str]:
        return True, "Mode démo : réponses simulées, sans appel à une IA."

    async def complete(self, prompt: str, *, web: bool = False, timeout: int = 300) -> str:
        task = parse_task(prompt)
        self.calls.append(task)
        if self._delay:
            await asyncio.sleep(self._delay)
        responder = self._responses.get(task)
        if responder is None:
            return json.dumps({"task": task, "mock": True})
        return responder(prompt)
