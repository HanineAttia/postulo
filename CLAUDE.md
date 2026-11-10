# CLAUDE.md

Guide for Claude Code (and humans) working on Postulo. The source of truth for features is
[docs/SPEC.md](docs/SPEC.md); sources are in [docs/research.md](docs/research.md). Keep this file
up to date (commands, architecture, conventions, decisions).

## Status

- **Phase 0 (foundations): done.** Backend, frontend shell, demo mode, background jobs with SSE, CI.
- Next: phase 1 (career library, CV import, `claude_code_cli` and `anthropic_api` providers, onboarding).

## Working rules (SPEC section 0, summarized)

1. Work phase by phase (SPEC section 14). Never start a phase before the previous one meets its acceptance criteria.
2. Start each phase in plan mode: short plan (files, steps, risks), wait for validation, then code.
3. Never guess an external API (France Travail, ATS boards, Typst, Claude Code CLI...). Check the
   official docs, then write an integration test marked `@pytest.mark.network` (disabled by default).
   If it cannot be verified, leave an explicit `TODO(verify)` and report it.
4. Tests are mandatory. Every backend module has pytest tests that run offline, with no quota, via
   `MockProvider`. Frontend: vitest on critical components, plus a Playwright end-to-end journey.
5. Small Conventional Commits. Run ruff, mypy, pytest, `pnpm lint` and `pnpm test` before each commit.
   **No AI attribution** in commits or PRs (no `Co-Authored-By`, no "Generated with"): the maintainer
   is the sole author. `.claude/settings.json` enforces this.
6. Languages: code, identifiers and comments in English. UI strings only in i18n files
   (`frontend/src/i18n/{fr,en}.json`, French by default). User docs in French, English summary in README.en.md.
7. Keep CLAUDE.md up to date.
8. Save the user's quota: no real AI calls in tests; do not re-read files without reason.
9. **Never**: bypass anti-bot protections or CAPTCHAs, scrape LinkedIn or Indeed, send a message or an
   application automatically, invent any career element, mass-collect third-party personal data.

Product principles: honesty (nothing invented), the human sends, respect websites (public APIs and
authorized feeds only), local and private (127.0.0.1, no telemetry), no mandatory cost, sober UI
with no emojis.

## Environment (maintainer's machine)

- Windows 11, native (not WSL), VS Code, Git for Windows, PowerShell 5.1.
- Python 3.13 from python.org (signed installer), uv, Node.js LTS, pnpm 12.
- **Smart App Control was disabled** on 2026-11-10 because it blocked SQLAlchemy's and mypy's compiled
  DLLs (see docs/dev-windows.md). If a library is blocked on another machine: stop and report the
  exact error, do not work around it.
- Never use PowerShell activation scripts: call `uv run ...` or `.venv\Scripts\python.exe` directly.
- `github.com:443` is intermittently unreachable from the maintainer's network (api.github.com works):
  if `git push` times out, retry later.

## Commands

Run from the repository root unless noted.

| Task | Command |
|---|---|
| Install / update Python deps | `uv sync` |
| Install frontend deps | `pnpm -C frontend install` |
| Build the frontend | `pnpm -C frontend build` |
| Run the app (opens the browser) | `uv run postulo` (or `.venv\Scripts\python.exe -m postulo`) |
| Options | `uv run postulo --port 8800 --no-browser` |
| Dev mode (backend reload + Vite HMR) | `uv run python scripts/dev.py`, then open http://localhost:5173 |
| API docs (when running) | http://127.0.0.1:8765/api/docs |
| Backend lint / format / types | `uv run ruff check .` · `uv run ruff format .` · `uv run mypy` |
| Backend tests (offline) | `uv run pytest` |
| Network tests (opt-in) | `uv run pytest -m network` |
| Frontend lint / types / tests | `pnpm -C frontend lint` · `pnpm -C frontend typecheck` · `pnpm -C frontend test` |
| End-to-end (build first) | `pnpm -C frontend build` then `pnpm -C frontend e2e` |
| E2E with installed Edge | set `PLAYWRIGHT_CHANNEL=msedge` before `pnpm -C frontend e2e` |
| New DB migration | `uv run alembic -c backend/postulo/db/alembic.ini revision --autogenerate -m "..."` |

`pnpm -C frontend e2e` starts the real backend itself (`uv run postulo` on port 8790, throwaway
`POSTULO_HOME`), so `uv` must be on PATH.

## Architecture

Single process: FastAPI serves the API under `/api` and the compiled frontend (`frontend/dist`) under `/`.
Bound to `127.0.0.1` only. Node.js is only needed to develop, not to use the app.

```
backend/postulo/
  __init__.py        APP_NAME, __version__, USER_AGENT (rename the app here + logo)
  __main__.py        `postulo` CLI: free port from 8765, opens browser, detects a running instance
  app.py             create_app(): routers, LLMError handler, TrustedHost, dev-only CORS, SPA serving
  config.py          data dir (%APPDATA%/Postulo, ~/.local/share/postulo, POSTULO_HOME), settings.json
  db/models.py       SQLModel tables: job, llm_usage, profile (+ UTCDateTime column type)
  db/session.py      engine cache, Alembic upgrade at startup, interrupted-job cleanup
  db/migrations/     Alembic (render_as_batch for SQLite)
  api/               one router per domain: health, settings, llm, jobs
  services/llm/      base.py (LLMProvider protocol, LLMError), providers/mock.py, json_utils.py
                     (extract_json, complete_json), usage.py (llm_usage logging), registry.py
  services/jobs.py   JobManager: asyncio tasks persisted in `job`, fan-out queues for SSE
  services/demo.py   demo job (5 steps: draft, layout, ats_check, jury, revision) using MockProvider
  services/<domain>/ empty packages for later phases (profile, sources, matching, documents...)
frontend/src/
  app/               Providers, routes, navigation (SPEC 12.2 sidebar), layout (Sidebar, Header)
  pages/             DashboardPage, PlaceholderPage (empty state per future page), NotFoundPage
  features/jobs/     useJobEvents (EventSource hook), DemoJobCard
  features/llm/      useLLMStatus (header counter and provider badge)
  components/ui/     shadcn/ui-style components on `radix-ui` (button, card, badge, progress, tooltip, skeleton)
  i18n/              fr.json (default), en.json, typed keys
  lib/               api.ts (typed client), theme.ts, preferences.ts (localStorage, never throws)
  styles/index.css   design tokens (SPEC 12.1) as CSS variables, dark mode via `.dark` class
tests/backend/       pytest; conftest gives every test a fresh POSTULO_HOME
frontend/e2e/        Playwright journey against the real backend in demo mode
scripts/dev.py       dev launcher (Python, not .ps1: execution policies block scripts)
```

### Background jobs and SSE
`JobManager.start(type, step_keys, func)` persists a `job` row and runs `func(ctx)` as an asyncio task.
`ctx.start_step / finish_step / set_progress` update the row and push a `JobRead` snapshot to
subscribers. `GET /api/jobs/{id}/events` streams `progress` events then one `end` event, replaying the
current state on connection (so EventSource reconnection just works), with keep-alive comments every
15 s. Job errors: `LLMError.message` is shown; other exceptions show a generic message (no traceback).
Jobs still running at startup or shutdown become `interrupted`.

### AI layer
Every prompt starts with `TASK: <name>`. `MockProvider` answers by task name (deterministic, offline).
Always call providers through `tracked_complete` / `complete_json` so each call lands in `llm_usage`
(header counter). `complete_json` extracts JSON (```json fence, then first `{`/`[` via a real decoder),
validates with pydantic, retries once with a format reminder, then raises
`LLMError(INVALID_RESPONSE)`. Only `mock` is implemented; `registry.get_provider` raises
`NOT_AVAILABLE` for the others until phase 1.

## Conventions

- Python: 3.12+ syntax (PEP 695 generics, `StrEnum`), `from __future__ import annotations`, mypy strict,
  ruff (line length 100). Synchronous SQLAlchemy sessions (SQLite is local; avoids greenlet).
- Datetimes are timezone-aware UTC everywhere (`utcnow()`, `UTCDateTime` column type).
- Errors shown to users are French, understandable and secret-free; technical detail goes in `detail`.
- API error shape: `{"error": {"kind", "message", "detail"}}` for `LLMError`; FastAPI's `{"detail"}` otherwise.
- Frontend: TypeScript strict with `noUncheckedIndexedAccess`; imports via `@/`; no hard-coded UI text;
  icons from lucide-react only, no emojis; colors only through tokens (`bg-primary`, `text-muted`...).
- Accessibility: visible focus, labelled controls, `aria-live` for progress, skip link, keyboard-usable.
- Tests: every backend test runs in a temp `POSTULO_HOME`; async tests use `pytest.mark.anyio`.
- Commits: Conventional Commits, small, no AI attribution.

## Decisions (with reasons)

| Decision | Why |
|---|---|
| Native Windows dev, not WSL (deviates from SPEC 3) | Maintainer's choice; documented in docs/dev-windows.md with WSL as alternative. |
| React 19 instead of 18 | Current shadcn/ui targets React 19 + Tailwind v4 (no forwardRef). |
| TypeScript pinned to ~6.0 | typescript-eslint supports `<6.1`; TypeScript 7 (native Go port) is not supported yet. |
| `radix-ui` umbrella package, components written by hand in shadcn style | Same code shadcn generates, without an interactive CLI. |
| No `uvicorn[standard]` | httptools/watchfiles/websockets are compiled and unnecessary; reload uses polling. |
| Only `job`, `llm_usage`, `profile` tables in phase 0 | Other SPEC 4 tables arrive with their phase via new migrations. |
| SSE written by hand (`StreamingResponse`) | No extra dependency; replay-on-connect semantics are simple. |
| Ruff rule ASYNC109 disabled | SPEC 5.1 mandates a `timeout` argument on provider methods. |
| `TrustedHostMiddleware` (127.0.0.1, localhost) | Blocks DNS-rebinding attacks against the local server. |
| UI preferences (theme, language, sidebar) in localStorage | Per-browser conveniences; `settings.json` keeps the server-side settings. |
| `chunkSizeWarningLimit: 800` | Single bundle is fine on 127.0.0.1; code splitting is a phase 6 task. |
| `scripts/dev.py` instead of `dev.ps1` | PowerShell execution policies often block `.ps1` files. |
| PNG logo variants postponed to phase 6 | SVG logo and favicon are enough for now. |

## Open points / TODO

- `TODO(anthropic)`: before promoting the `claude_code_cli` provider publicly, ask Anthropic to confirm
  it is allowed (SPEC 5.3). It must stay off by default and labelled "personal use".
- Ctrl+K global search is a visual placeholder (disabled) until a later phase.
- `settings.json` is created on first save, not at first launch (defaults are used until then).
