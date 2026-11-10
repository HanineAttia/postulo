"""Claude Code CLI provider (docs/SPEC.md sections 5.2 and 5.3).

Uses the `claude` command that the user installed and logged into themselves.
Personal use only, off by default: Anthropic's terms do not allow third-party
products to offer claude.ai login or subscription limits without approval.
TODO(anthropic): ask Anthropic to confirm this use before promoting it publicly.

Safety: the prompt goes on stdin (no Windows command-line length limit), the
process runs in an empty temporary directory, with no tools at all (Claude can
neither read nor modify files), except WebSearch/WebFetch when `web=True`.
Flags checked against `claude --help` (Claude Code 2.1.319).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
import tempfile

from postulo.services.llm.base import LLMError, LLMErrorKind

INSTALL_URL = "https://code.claude.com/docs/en/setup"  # TODO(verify): official install page
TASK_INSTRUCTION = "Réalise la tâche décrite dans le texte fourni en entrée."

# Error detection is pattern-based: the CLI does not document its error messages.
# TODO(verify): confirm these patterns against real CLI outputs when they occur.
_USAGE_LIMIT_RE = re.compile(
    r"usage limit|limit reached|rate.?limit|quota|too many requests|\b429\b|limite", re.I
)
_NOT_LOGGED_IN_RE = re.compile(
    r"not logged in|log ?in|/login|authenticat|unauthori[sz]ed|invalid api key|\b401\b|"
    r"oauth token|credentials",
    re.I,
)


def build_command(prefix: list[str], *, web: bool, model: str | None) -> list[str]:
    command = [
        *prefix,
        "-p",
        TASK_INSTRUCTION,
        "--output-format",
        "text",
        "--no-session-persistence",
        "--disallowedTools",
        "mcp__*",
    ]
    if web:
        command += ["--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch"]
    else:
        command += ["--tools", ""]
    if model:
        command += ["--model", model]
    return command


def classify_failure(returncode: int, stdout: str, stderr: str) -> LLMError:
    output = f"{stderr}\n{stdout}".strip()
    detail = f"exit code {returncode}: {output[-1500:]}"
    if _USAGE_LIMIT_RE.search(output):
        return LLMError(
            LLMErrorKind.USAGE_LIMIT,
            "Ta limite d'utilisation de Claude Code est atteinte. Réessaie plus tard.",
            detail,
        )
    if _NOT_LOGGED_IN_RE.search(output):
        return LLMError(
            LLMErrorKind.NOT_LOGGED_IN,
            "Claude Code n'est pas connecté. Ouvre un terminal, lance `claude` puis connecte-toi.",
            detail,
        )
    return LLMError(LLMErrorKind.UNKNOWN, "Claude Code a renvoyé une erreur.", detail)


class ClaudeCodeCLIProvider:
    name = "claude_code_cli"

    def __init__(self, model: str | None = None, command_prefix: list[str] | None = None) -> None:
        self._model = model or None
        self._prefix = command_prefix  # tests run a fake `claude` written in Python

    def _resolve(self) -> list[str] | None:
        if self._prefix:
            return self._prefix
        executable = shutil.which("claude")
        return [executable] if executable else None

    def available(self) -> tuple[bool, str]:
        if self._resolve() is None:
            return False, (
                f"La commande `claude` est introuvable. Installe Claude Code ({INSTALL_URL}), "
                "puis relance Postulo."
            )
        return True, "Claude Code est installé (usage personnel)."

    async def complete(self, prompt: str, *, web: bool = False, timeout: int = 300) -> str:
        prefix = self._resolve()
        if prefix is None:
            raise LLMError(LLMErrorKind.NOT_AVAILABLE, self.available()[1])
        command = build_command(prefix, web=web, model=self._model)
        with tempfile.TemporaryDirectory(prefix="postulo-claude-") as workdir:
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=workdir,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "NO_COLOR": "1"},
                )
            except OSError as exc:
                raise LLMError(
                    LLMErrorKind.NOT_AVAILABLE,
                    "Claude Code n'a pas pu être lancé.",
                    repr(exc),
                ) from exc
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(prompt.encode("utf-8")), timeout=timeout
                )
            except TimeoutError as exc:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
                raise LLMError(LLMErrorKind.TIMEOUT, detail=f"no answer after {timeout} s") from exc
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            raise classify_failure(process.returncode or -1, stdout, stderr)
        if not stdout:
            raise LLMError(
                LLMErrorKind.INVALID_RESPONSE, "Claude Code n'a rien répondu.", stderr[-1500:]
            )
        return stdout
