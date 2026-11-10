# Postulo

> Work in progress (phase 1: career library). Provisional name.

Postulo is a **free, open source, local-first** assistant for finding an internship, apprenticeship,
fixed-term or permanent job, or freelance mission in France, in any field: a single career library,
published offers and the hidden job market, tailored ATS-friendly resumes and cover letters,
interview preparation and application tracking.

Principles: nothing is invented, you send your applications yourself, your data stays on your computer,
no telemetry, no mandatory cost. The interface is in French first, with English available.

## Quick start (development)

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js LTS and pnpm (only to build the UI).

```
git clone https://github.com/HanineAttia/postulo.git
cd postulo
uv sync
pnpm -C frontend install
pnpm -C frontend build
uv run postulo
```

The server listens on `127.0.0.1` only and opens your browser. The first launch runs in **demo mode**
(simulated AI, no account needed).

A 5-step welcome wizard helps you choose the AI, import your CV and set your goal (skippable).

What works today (phase 1):
- **My career** page: full forms for every section, drag-and-drop ordering, completeness score with advice,
  JSON/YAML backup and restore, fictional sample profile.
- **CV import** (PDF, DOCX, TXT): text extraction, AI structuring, preview of the changes, then merge
  without duplicates or replace. Scanned PDFs are detected. Nothing is invented.
- **AI providers**: demo (default, simulated), Anthropic API with your own key (stored in the system
  keyring; default model Claude Sonnet 5.5), and Claude Code CLI (personal use only, off by default,
  runs in an empty temporary folder with no tools; check Anthropic's terms before enabling it).

Windows users: Smart App Control may block compiled Python libraries. See
[docs/dev-windows.md](docs/dev-windows.md) (in French).

Data lives in `%APPDATA%\Postulo` (Windows), `~/.local/share/postulo` (Linux, WSL, macOS), or `POSTULO_HOME`.

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Specification: [docs/SPEC.md](docs/SPEC.md) (French).

Independent project, not affiliated with Anthropic, France Travail or any platform mentioned.
License: [MIT](LICENSE).
