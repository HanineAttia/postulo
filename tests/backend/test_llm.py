from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from postulo.config import Settings
from postulo.services.llm import json_utils, registry, usage
from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider, parse_task
from postulo.services.llm.json_utils import JSONExtractionError, complete_json, extract_json
from postulo.services.llm.providers.mock import MockProvider

pytestmark = pytest.mark.anyio


class Answer(BaseModel):
    title: str
    score: int


# --- parse_task -----------------------------------------------------------------


def test_parse_task() -> None:
    assert parse_task("TASK: cv_draft\nrest") == "cv_draft"
    assert parse_task("\n  TASK:jury \n") == "jury"
    assert parse_task("no marker") == "unknown"


# --- extract_json ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('Voici :\n```json\n{"a": 2}\n```\nFin.', {"a": 2}),
        ('```\n{"a": 3}\n```', {"a": 3}),
        (
            'Texte avant {"a": "accolade } dans { une chaîne"} après',
            {"a": "accolade } dans { une chaîne"},
        ),
        ("liste : [1, 2, 3] et puis", [1, 2, 3]),
        ('{cassé} puis {"ok": true}', {"ok": True}),
        ('```json\n{invalide\n```\n{"b": 1}', {"b": 1}),
    ],
)
def test_extract_json(text: str, expected: object) -> None:
    assert extract_json(text) == expected


def test_extract_json_failure() -> None:
    with pytest.raises(JSONExtractionError):
        extract_json("pas de JSON ici")


# --- MockProvider ---------------------------------------------------------------


async def test_mock_is_deterministic_and_a_provider() -> None:
    provider = MockProvider()
    assert isinstance(provider, LLMProvider)
    assert provider.available()[0] is True
    first = await provider.complete("TASK: demo\n...")
    assert first == await provider.complete("TASK: demo\nautre contenu")
    assert await provider.complete("TASK: ping") == "pong"
    assert provider.calls == ["demo", "demo", "ping"]


async def test_mock_unknown_task_returns_json() -> None:
    assert extract_json(await MockProvider().complete("TASK: whatever")) == {
        "task": "whatever",
        "mock": True,
    }


# --- complete_json + usage --------------------------------------------------------


async def test_complete_json_success_records_usage(migrated_db: Path) -> None:
    provider = MockProvider({"t": '{"title": "Data", "score": 7}'})
    result = await complete_json(provider, "TASK: t", Answer)
    assert result == Answer(title="Data", score=7)
    assert usage.calls_today() == 1


async def test_complete_json_retries_once_with_reminder(migrated_db: Path) -> None:
    prompts: list[str] = []

    def responder(prompt: str) -> str:
        prompts.append(prompt)
        return "oops" if len(prompts) == 1 else '{"title": "x", "score": 1}'

    result = await complete_json(MockProvider({"t": responder}), "TASK: t", Answer)
    assert result.score == 1
    assert len(prompts) == 2
    assert "RAPPEL DE FORMAT" in prompts[1]
    assert usage.calls_today() == 2


async def test_complete_json_gives_up_after_one_retry(migrated_db: Path) -> None:
    provider = MockProvider({"t": '{"title": "x"}'})  # missing "score"
    with pytest.raises(LLMError) as info:
        await complete_json(provider, "TASK: t", Answer)
    assert info.value.kind is LLMErrorKind.INVALID_RESPONSE
    assert "score" in info.value.detail
    assert provider.calls == ["t", "t"]


async def test_provider_errors_are_logged(migrated_db: Path) -> None:
    class Failing(MockProvider):
        async def complete(self, prompt: str, *, web: bool = False, timeout: int = 300) -> str:
            raise RuntimeError("boom")

    with pytest.raises(LLMError) as info:
        await usage.tracked_complete(Failing(), "TASK: x")
    assert info.value.kind is LLMErrorKind.UNKNOWN
    assert usage.calls_today() == 1


def test_json_utils_reminder_is_french() -> None:
    assert "JSON" in json_utils.FORMAT_REMINDER


# --- registry ---------------------------------------------------------------------


def test_registry_returns_mock_by_default() -> None:
    assert registry.get_provider(Settings()).name == "mock"


def test_registry_rejects_unimplemented_provider() -> None:
    settings = Settings()
    settings.ai.provider = "anthropic_api"
    with pytest.raises(LLMError) as info:
        registry.get_provider(settings)
    assert info.value.kind is LLMErrorKind.NOT_AVAILABLE
