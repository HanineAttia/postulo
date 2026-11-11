# CLAUDE.md

Guide for Claude Code (and humans) working on Postulo. The source of truth for features is
[docs/SPEC.md](docs/SPEC.md); sources are in [docs/research.md](docs/research.md). Keep this file
up to date (commands, architecture, conventions, decisions).

## Status

- **Phase 0 (foundations): done.** Backend, frontend shell, demo mode, background jobs with SSE, CI.
- **Phase 1 (career library): done**, except the live Claude Code ping (acceptance criterion 3), which
  needs the maintainer's go-ahead because it uses her quota: `uv run pytest -m network -k claude`.
- **Phase 2 (application workshop): done** in demo mode (CV on one page, clickable links, no
  ligature, ATS 93, jury 74 then 84). Still to validate by the maintainer with her quota: a real
  offer pasted in the workshop with a real provider (ATS >= 85 expected; SPEC 7.7 references).
- **Phase 2 fix (SPEC 16.1 to 16.3)**: in progress (layout quality, offer metadata, import of
  two-column CVs, CV rules R-xx). See the plan in the commit history.
- Next: phase 3 (published offers: sources, pre-sorting, AI analysis, Offers and Organizations).

### SPEC 16 sections planned for later phases
Do them with their phase, not before (SPEC 16.4 to 16.9):
- **Phase 3**: 16.5 offer archive at discovery (full text, URL, dates, page saved as PDF if possible);
  16.6 in-app notifications for new relevant offers and background watch (`postulo watch` scheduled
  by the Windows Task Scheduler, SMTP digest sent to the user's own address); 16.7 offer given by link or text
  (JSON-LD), sort by date, relevance or both (relevance x freshness over 14 days), "published X
  days ago"; 16.9 application deadline extracted from the offer, calendar and reminder 3 days before.
- **Phase 4**: 16.8 public recruiting contacts with their source link, prepared LinkedIn search
  links, own LinkedIn connections import, lab team pages and HAL; never collect personal e-mails
  or LinkedIn profiles.
- **Phase 5**: 16.4 calendar view in Tracking (colour + label + icon per state), state changes at
  any time with history, interview events, announced response delay then "no answer (delay over)",
  mailbox classification that only proposes updates; 16.5 application record (all versions,
  e-mail, history, interview notes); 16.6 Windows toasts, Google Calendar template link and `.ics`
  export (no Google API); 16.9 reminder the day before an interview, weekly goal.
- **Phase 6**: 16.9 browser extension "Send to Postulo".

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
| Network tests (opt-in, use quota) | `uv run pytest -m network` (API test: set `POSTULO_TEST_ANTHROPIC_KEY`) |
| Frontend lint / types / tests | `pnpm -C frontend lint` · `pnpm -C frontend typecheck` · `pnpm -C frontend test` |
| End-to-end (build first) | `pnpm -C frontend build` then `pnpm -C frontend e2e` |
| E2E with installed Edge | set `PLAYWRIGHT_CHANNEL=msedge` before `pnpm -C frontend e2e` |
| HTML engine with Playwright (optional) | `uv sync --extra html` then `uv run playwright install chromium` |
| New DB migration | `uv run alembic -c backend/postulo/db/alembic.ini revision --autogenerate -m "..."` |

`pnpm -C frontend e2e` starts the real backend itself (`uv run postulo` on port 8790, throwaway
`POSTULO_HOME`), so `uv` must be on PATH. Test files share that backend and run on one worker, in
alphabetical order; reset state through the API (`e2e/helpers.ts`), never rely on another file.

## Architecture

Single process: FastAPI serves the API under `/api` and the compiled frontend (`frontend/dist`) under `/`.
Bound to `127.0.0.1` only. Node.js is only needed to develop, not to use the app.

```
backend/postulo/
  __init__.py        APP_NAME, __version__, USER_AGENT (rename the app here + logo)
  __main__.py        `postulo` CLI: free port from 8765, opens browser, detects a running instance
  app.py             create_app(): routers, LLMError handler, TrustedHost, dev-only CORS, SPA serving
  config.py          data dir (%APPDATA%/Postulo, ~/.local/share/postulo, POSTULO_HOME), settings.json
  errors.py          UserError (French message + detail), shown by jobs like LLMError
  db/models.py       SQLModel tables: job, llm_usage, profile, application (+ UTCDateTime type)
  data/              sample_profile.json ("Camille Exemple"), sample_offer.txt (fictional offer)
  assets/fonts/      Inter and Source Serif 4 TTF (OFL licences next to them)
  templates/typst/   common.typ, cv.typ, letter.typ (read data.json; style from data.layout)
  templates/html/    base/cv/letter .html.j2 for the HTML fallback engine
  db/session.py      engine cache, Alembic upgrade at startup, interrupted-job cleanup
  db/migrations/     Alembic (render_as_batch for SQLite)
  api/               one router per domain: health, settings, llm, jobs, profile, applications
  services/llm/      base.py (LLMProvider protocol, LLMError), json_utils.py (extract_json,
                     complete_json), usage.py (llm_usage logging), registry.py,
                     providers/{mock, mock_cv, claude_code_cli, anthropic_api}.py
  services/secrets.py  keyring get/set/delete (API key), ANTHROPIC_API_KEY env fallback
  services/prompts/  render(name, **ctx) (Jinja2, StrictUndefined), *.md templates (cv_extract,
                     application_draft, application_revision, jury), sanitize.py
  services/profile/  schema.py (pydantic, SPEC 6.1), references.py (F0/E0..., computed), store.py
                     (single row + version), lenient.py (drop invalid fields as warnings), merge.py
                     (merge_profiles + ImportDiff), preview.py, completeness.py, backup.py,
                     sample.py, cv_import.py (PDF/DOCX/TXT text, cv_import job)
  services/documents/ model.py (CvDocument, LetterDocument, Layout: render-ready), labels.py (dates,
                     headings FR/EN), selection.py (limits, section order, default selection),
                     draft.py (ApplicationDraft schema, prompts), honesty.py (guard SPEC 7.4),
                     assemble.py (build_cv/build_letter, typography, placeholders, file names),
                     render.py (Typst), compact.py (levels 0-4), html_engine.py (Edge/Chrome)
  services/quality/  ats_check.py (pypdfium2 text, pypdf links, score 60/40), jury.py (normalize)
  services/workshop/ pipeline.py (application job, render_documents, regenerate), storage.py
                     (application folder, ApplicationReport, EditableDocuments)
  services/jobs.py   JobManager: asyncio tasks persisted in `job`, fan-out queues for SSE
  services/demo.py   demo job (5 steps: draft, layout, ats_check, jury, revision) using MockProvider
  services/<domain>/ empty packages for later phases (profile, sources, matching, documents...)
frontend/src/
  app/               Providers, routes, navigation (SPEC 12.2 sidebar), layout (Sidebar, Header)
  pages/             DashboardPage, PlaceholderPage (empty state per future page), NotFoundPage
  features/jobs/     useJobEvents (EventSource hook), JobProgress (shared live steps), DemoJobCard
  features/llm/      useLLMStatus (header counter and provider badge)
  features/profile/  schema.ts (zod mirror of the pydantic schema), fields.tsx (spec-driven fields
                     bound to react-hook-form), sections.ts (form layout per section),
                     ItemSectionEditor (sortable cards), ProfileEditor (one form for all tabs),
                     ImportCvPanel, ImportPreviewPanel, BackupPanel, CompletenessCard, useProfile
  features/settings/ AIProviderForm (provider, model, key, connection test), DocumentSettingsForm,
                     useSettings
  features/workshop/ WorkshopPage (/workshop?id=), ApplicationForm, ApplicationResult (tabs:
                     documents, quality, e-mail, advice, edit), QualityPanel, EditPanel,
                     useApplications
  features/onboarding/ OnboardingPage (/welcome, 5 steps, shown until onboarding_completed)
  components/ui/     shadcn/ui-style components on `radix-ui` (button, card, badge, progress, tooltip,
                     skeleton, input, textarea, native-select, label, tabs, field, toaster)
  i18n/              fr.json (default), en.json, typed keys
  lib/               api.ts (typed client), theme.ts, preferences.ts (localStorage, never throws),
                     i18nKey.ts (useDynamicT for keys built at runtime)
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
`LLMError(INVALID_RESPONSE)`. `mock_cv.py` gives the mock a small rule-based `cv_extract` answer.

Prompts live in `services/prompts/<name>.md`. External text (CV, offer, page) always goes through
`sanitize_text` and inside tags (`<cv>...</cv>`) with `UNTRUSTED_NOTICE`.

- `claude_code_cli`: `claude -p "<instruction>" --output-format text --no-session-persistence
  --disallowedTools "mcp__*" --tools ""` (web: `--tools`/`--allowedTools "WebSearch,WebFetch"`), prompt
  on stdin, `cwd` = empty temp dir, timeout kills the process. Error kinds come from output patterns.
  Tests run a fake `claude` written in Python (`command_prefix`).
- `anthropic_api`: official SDK 2.x (built on `httpx2`; the key is sent as `Authorization: Bearer`),
  `client.beta.messages.create(..., betas=["server-side-fallback-2026-07-01"], fallbacks="default")`,
  `pause_turn` continuations, refusals handled. Tests inject `httpx2.MockTransport`.

### Application workshop (phase 2)
`POST /api/applications` starts an `application` job (steps draft, layout, ats_check, jury, revision).
One AI call returns an `ApplicationDraft`: references (E0, P1...) and rewritten bullets, title, summary,
section order, skills, interests, offer keywords, letter paragraphs, e-mail, tips, gaps. Contact details
are never sent to the AI. `honesty.apply_guard` works on a deep copy and returns a `Selection`: unknown
refs ignored, skills and interests outside the library removed (accents, case, parentheses ignored),
fallback selection by offer keywords, bullets or summary with a number absent from the source reverted,
keywords absent from the offer dropped. `assemble.build_cv` rebuilds facts from the library and sorts
newest first. `render_documents` compacts (levels 0-4 on copies), renders and runs the ATS check. The
jury reads the text extracted by pypdfium2; below the threshold, one revision starts from the
**original** draft (`merge_revision` keeps the parts the AI left out); the better version is kept and
both scores are reported. Everything is written to `<data>/applications/<id>/` (offer.txt, draft.json,
revised_draft.json, documents.json = editable full documents, data.json, report.json, PDFs); the row
is inserted at the end of the job. `PUT /api/applications/{id}/documents` re-renders edited documents
and re-runs the ATS check without AI. Demo answers: `providers/mock_application.py` (jury 74, then 8.4
on 10, normalized to 84).

### Career library and imports
The profile is one JSON document (table `profile`, single row, `version` bumped on each save).
`PUT /api/profile` replaces it whole and requires the version the client loaded (409 otherwise).
Imports (CV job result, backup upload) never write: they return an `ImportPreview` (incoming profile,
merge diff, replace diff, warnings); `POST /api/profile/apply` then merges or replaces against the
current version. Merge matches items by normalized keys (accents, case, punctuation ignored), fills
empty fields, unites lists, and never overwrites a filled field ("kept").

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
| DOCX read with stdlib `zipfile` + `xml.etree` | No lxml/python-docx (compiled, heavier); paragraphs, tables, hyperlinks are enough. |
| Profile saved whole, with optimistic `version` | One form across tabs; conflicts (two tabs, an import) are detected. |
| References F0/E0... computed, never stored | SPEC 6.1: recomputed for each generation from the list order. |
| Lenient validation for imports (`lenient.py`) | One odd date must not reject a whole CV; dropped fields are shown as warnings. |
| Default `anthropic_api` model: `claude-sonnet-5-5` | Maintainer's choice (cost and quality for students); configurable. |
| `fallbacks="default"` always sent | Harmless on models without fallback; retries policy declines server-side. |
| API key in keyring, env var fallback, no plaintext file | SPEC 2.3; the encrypted local fallback is still a TODO. |
| Ruff RUF001-003 disabled | French typography (en dash, apostrophe, no-break space) is intentional. |
| `Button` defaults to `type="button"` | Buttons inside the profile form must never submit it by accident. |
| Profile, settings and onboarding routes lazy-loaded | Keeps the main bundle under the 800 kB warning (zod, forms, dnd-kit). |
| Native `<select>` instead of Radix Select | Accessible by default and works with react-hook-form `register`. |
| Onboarding steps 4 and 5 shown as "coming soon" | Maintainer's choice; sources and organizations arrive in phase 3. |
| Playwright `workers: 1` | Test files share one backend and one data directory. |
| Typst through the `typst` package (typst-py 0.15, Typst 0.15.1), system fonts ignored | API checked in its own stubs; same output on every machine. |
| Inter (modern) and Source Serif 4 (classic), static TTF | OFL, complete French glyphs; Typst cannot read woff2. |
| One Typst template per document, style in `data.layout` | Two models without duplicating the layout logic. |
| Links and dates wrapped in `box` in Typst | A line break inside a URL made pdfium report U+FFFE. |
| HTML engine drives Edge/Chrome on the command line; Playwright only as an optional extra | Maintainer's choice: no 100 MB dependency, Edge ships with Windows. `--blink-settings` breaks printing. |
| One AI call for CV, letter, e-mail and tips | Saves the user's quota (SPEC 0, rule 8). |
| Numbers in rewritten bullets checked against the source item | Extends SPEC 7.4: a figure is never invented. |
| Jury on the ATS-extracted text, revision from the original draft | SPEC 7.6 and lesson 5. |
| Revision kept only if its jury score is not lower | Never replaces a better first version. |
| Application row inserted at the end of the job | A failed job leaves no half-empty application (its folder keeps the draft). |
| `application.offer_id` and `organization_id` without foreign keys | The `offer` and `organization` tables arrive in phase 3. |

## Open points / TODO

- `TODO(anthropic)`: before promoting the `claude_code_cli` provider publicly, ask Anthropic to confirm
  it is allowed (SPEC 5.3). It must stay off by default and labelled "personal use".
- Ctrl+K global search is a visual placeholder (disabled) until a later phase.
- `settings.json` is created on first save, not at first launch (defaults are used until then).
- `TODO(verify)`: Claude Code CLI error patterns (usage limit, not logged in) and the install URL in
  `providers/claude_code_cli.py`; confirm them against real outputs.
- PDF hyperlink annotations are not extracted yet (SPEC 2.1 suggests pypdf for links).
- Achievement coach (SPEC 6.2: reformulate weak bullets by asking for the missing figure) is not done;
  it needs the prompt work of phase 2.
- Encrypted local fallback for secrets when no keyring backend exists (SPEC 2.3).
- `TODO(verify)`: the HTML engine fails to print with headless Chrome/Edge on the Ubuntu CI runner
  (cause unknown, no stderr); it is verified on Windows with Edge. Its real-browser test only runs
  on Windows in CI. Do not add `--no-sandbox` to work around it.
- `TODO(latex)`: the optional LaTeX engine (SPEC 7.5) is not implemented; DOCX export is phase 6.
- Phase 2 acceptance with a real provider and a real pasted offer is still to be run by the
  maintainer (uses quota). Prompts `application_draft`, `application_revision` and `jury` are
  VERSION 1 and not tuned on real answers yet.
- Workshop opened from an offer (`offer_id`) and spontaneous applications: phases 3 and 4.
