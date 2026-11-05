# SavorLoop

SavorLoop is a single-user cooking assistant that helps turn ingredients already at home into practical meals, prioritizes items that may expire soon, and learns from recipes the user has actually cooked.

## What it will do

- Track pantry staples as available or unavailable, and rotating ingredients with optional quantities, units, and expiry dates.
- Support conventional inventory editing and natural-language stock updates. AI may interpret a request, but deterministic backend code validates allowlisted changes and applies them atomically; rejected changes leave stored data unchanged.
- Generate complete recipes on demand from current stock, including quantities, steps, serving count, missing ingredients, substitutions, and a short explanation.
- Save a recipe only after the user confirms it was cooked, then retain ratings, comments, changes, substitutions, and attempt history.
- Use a small, explainable selection of highly rated cooking history to inform later suggestions.

The MVP has no accounts, shared inventory, initial taste questionnaire, recipe catalogue, or model training. Generated suggestions are not saved automatically.

## Stack and hosting boundary

React/TypeScript frontend, FastAPI backend, and SQLAlchemy over SQLite. Recipe suggestions use Google's Gemini API. SQLite is the initial database; data access stays behind SQLAlchemy. A Render Free service was used only for a disposable educational preview and is now suspended; it does not satisfy the product's durable-hosting requirement.

## Project status

The application includes a structured single-user inventory, server-side natural-language inventory updates, on-demand Gemini recipe suggestions, and a Cooking Notebook. Suggestions are validated and remain transient; a recipe enters the Notebook only after the user confirms it was cooked. Attempts preserve ratings and feedback, and only highly rated recipes and explicitly liked adjustments inform later suggestions. Authentication is not implemented. The Render Free educational preview was deployed and verified on 2026-11-05, then suspended by the owner; its SQLite data was ephemeral and may have been lost. See the [Render Free educational-preview facts and limitations](_docs/render-free-demo.md).

Task implementation and QA status are recorded in the [public GitHub Issues tracker](https://github.com/YannPhamVan/SavorLoop/issues). This application-status summary does not imply that an open issue has passed QA or that the project has earned an evaluation score.

## Prerequisites and one-command setup

For the one-command app startup, install Docker Engine or Docker Desktop with the Compose plugin. From the repository root, run:

```sh
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). This starts the frontend and backend with a local named SQLite volume. Recipe suggestions require a Gemini API key configured for the backend; this Compose configuration does not pass `GEMINI_API_KEY` to the backend, so inventory and notebook features work without that key. See the [Compose and backup instructions](#run-the-complete-app-with-docker-compose) before removing volumes.

For native development and the test suite, use Python 3.11 or newer with [uv](https://docs.astral.sh/uv/) and Node.js 22.15 or newer with npm. The frontend's locked OpenTelemetry packages declare a Node 22.15 minimum. Install the lockfile-pinned dependencies from the repository root:

```powershell
uv sync --locked
npm --prefix frontend ci
```

The optional [local observability stack](observability/README.md) instruments the browser and backend natural-language inventory update using OpenTelemetry and Grafana. It is separate from the application Compose project and is bound to localhost only.

The [issue 12 on-call drill](_docs/on-call-drill.md) is a separate, local-only Docker/SQLite test. It uses synthetic data and a test-only readiness failure; it is not connected to production or an external alert service.

### Run the complete app with Docker Compose

Prerequisite: Docker Engine or Docker Desktop with the Compose plugin. From the repository root, build and start the frontend and backend:

```sh
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) for the app. Compose waits for the backend's database-aware `/ready` check before starting the frontend. The frontend is served by Nginx and proxies `/api` requests to the backend. The backend is also available locally at `http://localhost:8000`; `/health` checks process liveness and `/ready` checks SQLite connectivity. Recipe suggestions require a backend Gemini key, which this local Compose setup intentionally does not read from `.env`; inventory and notebook features work without one.

SQLite is stored inside the backend container at `/data/savorloop.db` and backed by the named Docker volume `savorloop-sqlite-data`. The database is not stored in the container's writable layer. `docker compose stop` followed by `docker compose up -d` preserves data, as does `docker compose down` followed by `docker compose up -d`. **Do not use `docker compose down --volumes` unless you intend to delete the database.** This is a local volume only; it does not demonstrate or guarantee persistence in any hosted deployment.

Stop the app before making a file-level backup so SQLite has flushed its state. Run these commands from the repository root (the archive is written to the current directory):

```sh
docker compose stop
docker run --rm -v savorloop-sqlite-data:/data:ro -v "${PWD}:/backup" alpine:3.21 cp /data/savorloop.db /backup/savorloop.db
```

To restore `./savorloop.db` from the repository root, first stop the app, then replace the volume's database and restart:

```sh
docker compose stop
docker run --rm -v savorloop-sqlite-data:/data -v "${PWD}:/backup:ro" alpine:3.21 sh -c 'test -f /backup/savorloop.db && rm -f /data/savorloop.db* && cp /backup/savorloop.db /data/savorloop.db'
docker compose up -d
```

The backup/restore helper uses the official Alpine image and needs Docker image access. Keep backup files secure and outside the application volume. To remove the app containers and network while retaining the database, use `docker compose down`; remove the named database volume only when you explicitly want to discard its data.

Run these commands from the repository root:

```powershell
uv sync --locked
npm --prefix frontend ci
```

Run the complete keyless test and build check from the repository root:

```powershell
uv run python scripts/verify.py
```

This single command runs the backend unit/integration suite, frontend tests, and frontend production build. It returns a nonzero exit code if any check fails. The backend and frontend tests use isolated test data and stub providers, so no `.env` file or live AI credentials are needed. CI-compatible JUnit reports are written to `.test-results/backend.xml` and `.test-results/frontend.xml`; this generated directory is git-ignored.

### Continuous integration

The [CI workflow](.github/workflows/ci.yml) runs these checks automatically for every pull request, regardless of its target branch. To run the same verification locally, install from the lockfiles with `uv sync --locked` and `npm --prefix frontend ci`, then run `uv run python scripts/verify.py` from the repository root. No Gemini key, `.env` file, or other live provider credentials are needed.

### Render Free educational preview

There is no active hosted demo: the Render Free preview was suspended by the owner after its documented verification. The [Render Free fact check](_docs/render-free-demo.md) records the historical runtime observations, suspension, ephemeral SQLite data-loss behavior, and platform limits. The former service was a disposable educational preview, not durable product hosting or a production service. Do not treat its historical URL as a live demo.

For a keyless local inventory walkthrough, use the [demo-interpreter instructions](#gemini-recipe-suggestions) below to run the backend with `SAVORLOOP_INVENTORY_INTERPRETER=demo` and start the frontend. Then use a fabricated request such as `mark olive oil unavailable`. The demo interpreter is opt-in and limited; normal inventory controls work without an interpreter. For the app's complete local startup, use the Compose command above. Never use real or sensitive inventory data in demos.

The backend uses `DATABASE_URL` for its SQLAlchemy connection. Its local default is `sqlite:///./savorloop.db`, which creates `savorloop.db` in the process working directory. To use a different local SQLite file in PowerShell, set `$env:DATABASE_URL = "sqlite:///./local.db"` before starting the backend.

### Gemini recipe suggestions

Recipe suggestions use Google's official `google-genai` SDK and the configurable `GEMINI_MODEL` (default `gemini-3.8-flash`). Put the Gemini key in the gitignored `.env` file at the repository root; never commit or share its contents:

```dotenv
GEMINI_API_KEY=replace-with-your-Google-AI-Studio-key
GEMINI_MODEL=gemini-3.8-flash
```

Start the API from the repository root so `uv` loads those settings:

```powershell
uv run --env-file .env uvicorn backend.app.main:app --reload
```

Provider calls use structured JSON output, do not enable tools or grounding, and set `store=False`. Gemini free-tier quotas are limited and may change. Google may use content submitted through the free tier to improve its products; send only data appropriate for that service. The app sends available ingredient names, quantities, units, and expiry dates to generate a recipe. The real-API smoke test below uses fabricated inventory only.

The verification command above uses stub providers and never needs `.env` or a live API key. To run focused backend tests separately:

```powershell
uv run pytest backend/tests/test_recipe_suggestions.py
```

To separately verify real generation, run the synthetic-inventory smoke test once the key is configured. It does not read or write the application database and prints only the generated recipe from fabricated stock:

```powershell
uv run --env-file .env python -m backend.smoke_test_recipe
```

Natural-language updates return a safe unavailable response unless an interpreter is configured on the backend. For a keyless local UI walkthrough, explicitly opt into the limited demo interpreter before starting the API:

```powershell
$env:SAVORLOOP_INVENTORY_INTERPRETER = "demo"
uv run --env-file .env uvicorn backend.app.main:app --reload
```

The demo accepts requests such as `mark olive oil unavailable` and `use 50 g mushrooms`; deterministic inventory checks still apply. Without that setting, natural-language updates remain unavailable and the ordinary inventory controls continue to work. No provider credentials are used by the demo or exposed to the frontend. Automated tests inject a stub interpreter directly.

`GET /health` checks process liveness without touching the database. `GET /ready` executes a database connectivity check and returns HTTP 503 if it fails.

For a keyless Inventory screen walkthrough, run the backend from the repository root and leave it running:

```powershell
$env:SAVORLOOP_INVENTORY_INTERPRETER = "demo"
uv run uvicorn backend.app.main:app --reload
```

In a second terminal, start the frontend (if needed, install its dependencies from the repository root with `npm --prefix frontend ci`):

```powershell
npm --prefix frontend run dev
```

Open the local URL printed by Vite. The development server proxies `/api` requests to `http://127.0.0.1:8000` by default; set `$env:SAVORLOOP_API_TARGET` before `npm --prefix frontend run dev` to use another local API address. Inventory tables are created automatically in the configured SQLite database. Run the focused inventory API checks from the repository root with `uv run pytest backend/tests/test_inventory.py`.

## Project documents

- [Product specification](_docs/product-spec.md): current behavior and acceptance rules.
- [Task backlog](_docs/tasks.md): task definitions, acceptance criteria, evidence, dependencies, priorities, and estimates. [GitHub Issues](https://github.com/YannPhamVan/SavorLoop/issues) is the public execution tracker; each task links to its issue.
- [Evaluation evidence](_docs/evaluation.md): provisional criteria-to-evidence matrix, clean-checkout setup/test record, and explicit evidence gaps.
- [Render Free preview](_docs/render-free-demo.md): dated platform facts, historical runtime observations, ephemeral-data limits, and current suspended status.
- [Local observability](observability/README.md): local-only telemetry setup, dashboard, privacy boundaries, and hosted limitations.
- [On-call drill](_docs/on-call-drill.md): isolated local alert and remediation drill with its recorded result.
- [Agent team](_docs/agent-team.md): roles, permissions, and collaboration boundaries.
- [Agent process](_docs/agent-process.md): issue-driven implementation and evidence workflow.
- [Initial plan](_docs/plan.md): original brainstorming and decisions, with a dated status addendum.
- [Repository instructions](AGENTS.md): project context and coding boundaries for coding agents.

The [evaluation document](_docs/evaluation.md) treats the 12 criteria and point ranges as a working checklist only; the official evaluation wording has not been independently verified.
