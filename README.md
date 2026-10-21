# SavorLoop

SavorLoop is a single-user cooking assistant that helps turn ingredients already at home into practical meals, prioritizes items that may expire soon, and learns from recipes the user has actually cooked.

## What it will do

- Track pantry staples as available or unavailable, and rotating ingredients with optional quantities, units, and expiry dates.
- Support conventional inventory editing and natural-language stock updates. AI may interpret a request, but deterministic backend code validates and applies every change.
- Generate complete recipes on demand from current stock, including quantities, steps, serving count, missing ingredients, substitutions, and a short explanation.
- Save a recipe only after the user confirms it was cooked, then retain ratings, comments, changes, substitutions, and attempt history.
- Use a small, explainable selection of highly rated cooking history to inform later suggestions.

The MVP has no accounts, shared inventory, initial taste questionnaire, recipe catalogue, or model training. Generated suggestions are not saved automatically.

## Planned stack

Lovable-generated React/TypeScript frontend, FastAPI backend, SQLAlchemy, SQLite, and a configurable LLM provider. SQLite is the initial database; data access stays behind SQLAlchemy. Hosting and telemetry providers remain undecided until their persistence, automation, and observability support are checked.

## Project status

The repository includes a structured single-user inventory with pantry staples and rotating ingredients. Natural-language inventory updates use a server-side interpreter boundary and deterministic validation; no production provider is configured. Suggestions, cooking history, authentication, and deployment are not implemented yet.

## Local setup

Prerequisites: Python 3.11 or newer with [uv](https://docs.astral.sh/uv/), and Node.js with npm.

Run these commands from the repository root:

```powershell
uv sync
uv run python -c "from backend.app.main import app"
uv run pytest
```

For the frontend, also from the repository root:

```powershell
Set-Location frontend
npm ci
npm run build
```

The backend uses `DATABASE_URL` for its SQLAlchemy connection. Its local default is `sqlite:///./savorloop.db`, which creates `savorloop.db` in the process working directory. To use a different local SQLite file in PowerShell, set `$env:DATABASE_URL = "sqlite:///./local.db"` before starting the backend. Start it from the repository root with `uv run uvicorn backend.app.main:app --reload`.

Natural-language updates return a safe unavailable response unless an interpreter is configured on the backend. For a keyless local UI walkthrough, explicitly opt into the limited demo interpreter before starting the API:

```powershell
$env:SAVORLOOP_INVENTORY_INTERPRETER = "demo"
uv run uvicorn backend.app.main:app --reload
```

The demo accepts requests such as `mark olive oil unavailable` and `use 50 g mushrooms`; deterministic inventory checks still apply. Without that setting, natural-language updates remain unavailable and the ordinary inventory controls continue to work. No provider credentials are used by the demo or exposed to the frontend. Automated tests inject a stub interpreter directly.

`GET /health` checks process liveness without touching the database. `GET /ready` executes a database connectivity check and returns HTTP 503 if it fails.

For the Inventory screen, run the backend from the repository root and leave it running:

```powershell
uv run uvicorn backend.app.main:app --reload
```

In a second terminal, start the frontend:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. The development server proxies `/api` requests to `http://127.0.0.1:8000` by default; set `$env:SAVORLOOP_API_TARGET` before `npm run dev` to use another local API address. Inventory tables are created automatically in the configured SQLite database. Run the focused inventory API checks from the repository root with `uv run pytest backend/tests/test_inventory.py`.

## Project documents

- [Product specification](_docs/product-spec.md): current behavior and acceptance rules.
- [Task backlog](_docs/tasks.md): task definitions, acceptance criteria, evidence, dependencies, priorities, and estimates. [GitHub Issues](https://github.com/YannPhamVan/SavorLoop/issues) is the public execution tracker; each task links to its issue.
- [Evaluation and roadmap](_docs/evaluation.md): rubric mapping, review findings, score paths, estimates, and open decisions.
- [Agent team](_docs/agent-team.md): roles, permissions, and collaboration boundaries.
- [Agent process](_docs/agent-process.md): issue-driven implementation and evidence workflow.
- [Initial plan](_docs/plan.md): original brainstorming and decisions, with a dated status addendum.
- [Repository instructions](AGENTS.md): project context and coding boundaries for coding agents.

The evaluation checklist records the 12 criteria supplied for the 2026 AI Dev Tools Zoomcamp. Their official wording has not been independently re-verified in this repository.