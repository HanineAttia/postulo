"""Real AI providers, tested offline: a fake `claude` script and a mocked HTTP transport."""

from __future__ import annotations

import json
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import anyio
import httpx
import httpx2
import pytest

from postulo.app import create_app
from postulo.config import AISettings, Settings, save_settings
from postulo.services.llm import registry
from postulo.services.llm.base import LLMError, LLMErrorKind
from postulo.services.llm.providers.anthropic_api import (
    DEFAULT_MODEL,
    FALLBACK_BETA,
    AnthropicAPIProvider,
    web_search_tool,
)
from postulo.services.llm.providers.claude_code_cli import (
    ClaudeCodeCLIProvider,
    build_command,
    classify_failure,
)
from postulo.services.llm.providers.mock import MockProvider
from postulo.services.secrets import Secret, get_secret, set_secret

pytestmark = pytest.mark.anyio

FAKE_CLAUDE = r"""
import json, os, sys, time
mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
prompt = sys.stdin.buffer.read().decode("utf-8")
if mode == "limit":
    print("Claude AI usage limit reached|1767225600", file=sys.stderr); sys.exit(1)
if mode == "login":
    print("Invalid API key · Please run /login"); sys.exit(1)
if mode == "crash":
    print("boom", file=sys.stderr); sys.exit(2)
if mode == "sleep":
    time.sleep(30)
if mode == "empty":
    sys.exit(0)
print(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "files": os.listdir("."),
                  "prompt": prompt}))
"""


# --- Claude Code CLI ----------------------------------------------------------------------


@pytest.fixture
def fake_claude(tmp_path: Path) -> list[str]:
    script = tmp_path / "fake_claude.py"
    script.write_text(FAKE_CLAUDE, encoding="utf-8")
    return [sys.executable, str(script)]


def test_build_command_matches_spec() -> None:
    assert build_command(["claude"], web=False, model=None) == [
        "claude",
        "-p",
        "Réalise la tâche décrite dans le texte fourni en entrée.",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--disallowedTools",
        "mcp__*",
        "--tools",
        "",
    ]
    web = build_command(["claude"], web=True, model="sonnet")
    assert web[-6:] == [
        "--tools",
        "WebSearch,WebFetch",
        "--allowedTools",
        "WebSearch,WebFetch",
        "--model",
        "sonnet",
    ]


async def test_cli_sends_prompt_on_stdin_in_empty_dir(fake_claude: list[str]) -> None:
    provider = ClaudeCodeCLIProvider(command_prefix=fake_claude)
    assert provider.available()[0]
    prompt = "TASK: ping\nAccents : é à ç — et une ligne très longue " + "x" * 50_000
    data = json.loads(await provider.complete(prompt, timeout=30))
    assert data["prompt"].strip() == prompt
    assert data["files"] == []
    assert "postulo-claude-" in data["cwd"]
    assert not await anyio.Path(data["cwd"]).exists()  # temporary directory removed
    assert data["argv"][data["argv"].index("--tools") + 1] == ""


@pytest.mark.parametrize(
    ("mode", "kind"),
    [
        ("limit", LLMErrorKind.USAGE_LIMIT),
        ("login", LLMErrorKind.NOT_LOGGED_IN),
        ("crash", LLMErrorKind.UNKNOWN),
        ("empty", LLMErrorKind.INVALID_RESPONSE),
    ],
)
async def test_cli_errors(
    fake_claude: list[str], monkeypatch: pytest.MonkeyPatch, mode: str, kind: LLMErrorKind
) -> None:
    monkeypatch.setenv("FAKE_CLAUDE_MODE", mode)
    with pytest.raises(LLMError) as excinfo:
        await ClaudeCodeCLIProvider(command_prefix=fake_claude).complete("TASK: ping", timeout=30)
    assert excinfo.value.kind == kind
    assert "Traceback" not in excinfo.value.message


async def test_cli_timeout(fake_claude: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_CLAUDE_MODE", "sleep")
    with pytest.raises(LLMError) as excinfo:
        await ClaudeCodeCLIProvider(command_prefix=fake_claude).complete("TASK: x", timeout=1)
    assert excinfo.value.kind == LLMErrorKind.TIMEOUT


async def test_cli_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    provider = ClaudeCodeCLIProvider()
    available, reason = provider.available()
    assert not available
    assert "introuvable" in reason
    with pytest.raises(LLMError) as excinfo:
        await provider.complete("TASK: ping")
    assert excinfo.value.kind == LLMErrorKind.NOT_AVAILABLE


def test_classify_failure_keeps_detail() -> None:
    error = classify_failure(1, "", "weekly limit reached")
    assert error.kind == LLMErrorKind.USAGE_LIMIT
    assert "weekly limit" in error.detail


# --- Anthropic API ------------------------------------------------------------------------


def _message(text: str, stop_reason: str = "end_turn", **extra: Any) -> dict[str, Any]:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": DEFAULT_MODEL,
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 3, "output_tokens": 1},
        **extra,
    }


def _provider(
    handler: Callable[[httpx2.Request], httpx2.Response], key: str | None = "sk-ant-test-key"
) -> AnthropicAPIProvider:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return AnthropicAPIProvider(key, None, http_client=client, max_retries=0)


async def test_api_success_sends_expected_request() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json=_message("pong"))

    provider = _provider(handler)
    assert provider.available() == (True, f"API Anthropic, modèle {DEFAULT_MODEL}.")
    assert await provider.complete("TASK: ping\nRéponds pong") == "pong"
    request = seen[0]
    body = json.loads(request.content)
    assert request.headers["authorization"] == "Bearer sk-ant-test-key"
    assert FALLBACK_BETA in request.headers["anthropic-beta"]
    assert body["model"] == DEFAULT_MODEL
    assert body["fallbacks"] == "default"
    assert body["messages"] == [{"role": "user", "content": "TASK: ping\nRéponds pong"}]
    assert "tools" not in body


async def test_api_web_search_and_pause_turn() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx2.Response(200, json=_message("Début. ", stop_reason="pause_turn"))
        return httpx2.Response(200, json=_message("Fin."))

    assert await _provider(handler).complete("TASK: x", web=True) == "Début. Fin."
    assert bodies[0]["tools"][0]["type"] == "web_search_20260209"
    assert bodies[1]["messages"][1]["role"] == "assistant"
    assert web_search_tool("claude-haiku-5-5")["type"] == "web_search_20250305"


@pytest.mark.parametrize(
    ("status", "error_type", "kind"),
    [
        (401, "authentication_error", LLMErrorKind.NOT_LOGGED_IN),
        (403, "permission_error", LLMErrorKind.NOT_AVAILABLE),
        (404, "not_found_error", LLMErrorKind.NOT_AVAILABLE),
        (429, "rate_limit_error", LLMErrorKind.USAGE_LIMIT),
        (500, "api_error", LLMErrorKind.UNKNOWN),
    ],
)
async def test_api_errors(status: int, error_type: str, kind: LLMErrorKind) -> None:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status, json={"type": "error", "error": {"type": error_type, "message": "nope"}}
        )

    with pytest.raises(LLMError) as excinfo:
        await _provider(handler).complete("TASK: ping")
    assert excinfo.value.kind == kind
    assert "sk-ant" not in excinfo.value.message + excinfo.value.detail


async def test_api_timeout_connection_refusal_and_missing_key() -> None:
    def timeout(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    def refused(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("offline", request=request)

    def refusal(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=_message("", stop_reason="refusal"))

    for handler, kind in (
        (timeout, LLMErrorKind.TIMEOUT),
        (refused, LLMErrorKind.NOT_AVAILABLE),
        (refusal, LLMErrorKind.INVALID_RESPONSE),
    ):
        with pytest.raises(LLMError) as excinfo:
            await _provider(handler).complete("TASK: ping")
        assert excinfo.value.kind == kind

    no_key = _provider(lambda _r: httpx2.Response(200, json=_message("pong")), key=None)
    assert not no_key.available()[0]
    with pytest.raises(LLMError) as excinfo:
        await no_key.complete("TASK: ping")
    assert excinfo.value.kind == LLMErrorKind.NOT_LOGGED_IN


# --- registry, secrets, API endpoints -------------------------------------------------------


def test_registry_builds_each_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(registry.get_provider(Settings()), MockProvider)
    cli = registry.get_provider(Settings(ai=AISettings(provider="claude_code_cli")))
    assert isinstance(cli, ClaudeCodeCLIProvider)
    set_secret(Secret.ANTHROPIC_API_KEY, "sk-ant-from-keyring")
    api = registry.get_provider(Settings(ai=AISettings(provider="anthropic_api", model="m")))
    assert isinstance(api, AnthropicAPIProvider)
    assert api.model == "m"
    with pytest.raises(LLMError):
        registry.get_provider(Settings(ai=AISettings(provider="openai_compatible")))


def test_secret_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_secret(Secret.ANTHROPIC_API_KEY) is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    assert get_secret(Secret.ANTHROPIC_API_KEY) == "sk-ant-env"
    set_secret(Secret.ANTHROPIC_API_KEY, "sk-ant-keyring")
    assert get_secret(Secret.ANTHROPIC_API_KEY) == "sk-ant-keyring"


@pytest.fixture
async def client(postulo_home: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(frontend_dir=None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c


async def test_connection_test_in_demo_mode(client: httpx.AsyncClient) -> None:
    result = (await client.post("/api/llm/test")).json()
    assert result["ok"] is True
    assert result["provider"] == "mock"
    assert (await client.get("/api/llm/status")).json()["calls_today"] == 1


async def test_connection_test_reports_missing_key(client: httpx.AsyncClient) -> None:
    save_settings(Settings(ai=AISettings(provider="anthropic_api")))
    result = (await client.post("/api/llm/test")).json()
    assert result["ok"] is False
    assert "clé API" in result["message"]


async def test_api_key_is_stored_but_never_returned(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/llm/status")).json()["has_api_key"] is False
    short = await client.put("/api/llm/api-key", json={"api_key": "x"})
    assert short.status_code == 422
    saved = await client.put("/api/llm/api-key", json={"api_key": "sk-ant-secret-123456"})
    assert saved.status_code == 204
    status = (await client.get("/api/llm/status")).json()
    assert status["has_api_key"] is True
    assert "sk-ant-secret" not in json.dumps(status)
    assert "sk-ant-secret" not in (await client.get("/api/settings")).text
    assert (await client.delete("/api/llm/api-key")).status_code == 204
    assert (await client.get("/api/llm/status")).json()["has_api_key"] is False


async def test_providers_list(client: httpx.AsyncClient) -> None:
    providers = {p["name"]: p for p in (await client.get("/api/llm/providers")).json()}
    assert providers["claude_code_cli"]["personal_use_only"] is True
    assert providers["anthropic_api"]["default_model"] == "claude-sonnet-5-5"
    assert providers["openai_compatible"]["implemented"] is False
