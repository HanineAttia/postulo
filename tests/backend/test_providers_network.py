"""Real provider calls. Disabled by default: run with `uv run pytest -m network`.

Each test sends one tiny `ping` prompt (it uses a little of your quota or credit).
"""

from __future__ import annotations

import os
import shutil

import pytest

from postulo.services.llm.providers.anthropic_api import AnthropicAPIProvider
from postulo.services.llm.providers.claude_code_cli import ClaudeCodeCLIProvider

pytestmark = [pytest.mark.network, pytest.mark.anyio]

PING = "TASK: ping\nRéponds uniquement par le mot : pong\n"


@pytest.mark.skipif(shutil.which("claude") is None, reason="Claude Code is not installed")
async def test_claude_code_cli_ping() -> None:
    answer = await ClaudeCodeCLIProvider().complete(PING, timeout=120)
    assert "pong" in answer.lower()


async def test_anthropic_api_ping() -> None:
    # The autouse fixture hides ANTHROPIC_API_KEY; use POSTULO_TEST_ANTHROPIC_KEY instead.
    key = os.environ.get("POSTULO_TEST_ANTHROPIC_KEY")
    if not key:
        pytest.skip("set POSTULO_TEST_ANTHROPIC_KEY to run this test")
    answer = await AnthropicAPIProvider(key).complete(PING, timeout=120)
    assert "pong" in answer.lower()
