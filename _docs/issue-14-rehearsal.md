# Issue #14 pass-path rehearsal

**Rehearsal date:** 2026-11-05
**Tracker:** [Issue #14](https://github.com/YannPhamVan/SavorLoop/issues/14), left open.
**Purpose:** Record observed checks and evidence gaps for the project's 12 working evaluation criteria. This is implementation/rehearsal evidence, not an independent QA verdict or an evaluation score. The official evaluation wording and scoring remain unverified.

## Repository and environment

The inspected worktree was `main` at `76a14321222b7ae5f8ef1ecf6440d03e8bc50d29` (`docs: complete README and evidence for #13`), tracking `origin/main` with no ahead/behind commits before this task. The pre-existing untracked `.vscode/`, `issue2-walkthrough.db`, and `node_modules/` in the primary worktree were not read, modified, or staged. The setup and runtime rehearsal used a separate detached Git worktree, `.issue14-clean`, which was clean before installing dependencies and had no `.venv`, `frontend\node_modules`, `savorloop.db`, `backend\savorloop.db`, or `.env`.

The environment reported uv 0.8.0, Python 3.12.8 on PATH (uv selected Python 3.11.13 for the project), Node.js 22.13.1, npm 10.9.2, Docker 29.9.2, and Docker Compose v5.6.1. Node 22.13.1 is below the documented/locked frontend minimum of 22.15, so npm emitted `EBADENGINE` warnings; installation and the test/build command nevertheless exited successfully. No Gemini credential, `.env`, telemetry destination, or external provider was used by the clean worktree tests or Compose app.

## Issue #14 acceptance-criteria results

1. **PASS — clean-checkout setup, backend tests, frontend tests, and production build.** A detached worktree at the inspected baseline was clean before setup. `uv sync --locked` and `npm --prefix frontend ci` exited 0. `uv run python scripts/verify.py` exited 0: 51 backend tests passed, frontend tests passed, and the production build passed. The two environment warnings (Node engine and one Starlette/httpx deprecation) are listed below.
2. **PASS — Compose journey and persistence, with a disclosed safety override.** Docker Compose was available. Before startup, the default app project had no containers, no container used the fixed `savorloop-sqlite-data` volume, and that volume did not exist. Host port 8000 was already listening on 127.0.0.1 (PID 11508), while 8080 was free. To avoid interfering with that pre-existing listener or any user volume, the clean worktree auto-loaded an untracked `compose.override.yaml` that published only `127.0.0.1:8080:80` and renamed the database volume to the initially absent `savorloop-issue14-rehearsal-data`. The command `docker compose up --build -d` exited 0; `http://localhost:8080/` returned HTTP 200; backend `/health` and `/ready` returned HTTP 200. The browser Inventory form created the synthetic rotating ingredient `Issue 14 rehearsal basil` (1 bunch). The Notebook UI initially showed its empty state; a synthetic cooked-recipe test record was posted to `/api/notebook` (HTTP 201, record ID 1, one attempt), then appeared in the refreshed Notebook UI. After `docker compose stop` and `docker compose up -d` (both exit 0, without removing volumes), reads confirmed the same one inventory record, notebook recipe, and attempt. The original `savorloop-sqlite-data` volume was not used. The exact stock Compose port mapping could not be exercised because the host's port 8000 was occupied; the local frontend URL, app journey, and SQLite restart persistence were observed with the disclosed override.
3. **PASS — working rubric checklist and direct evidence recorded.** The 12 criteria below each have a PASS, FAIL, or UNVERIFIED status and an evidence link or exact observed command/behavior. No stretch criterion is claimed. Failures, warnings, and evidence limits are explicit.
4. **PASS — status, evidence, and limitation alignment checked.** The public tracker listed Issues #1–#13 as closed and #14 as open on 2026-11-05. The README now links to the public tracker and separates app status from issue/QA status; the historical backlog now names the public tracker as the status source; and the evaluation matrix was corrected to reflect #1–#13 closed and #14 open. A relative-Markdown-link check for the four updated documents is recorded below. No deployment, external service, or tracker state was changed other than the requested Issue #14 report comment.

## Working evaluation-criteria checklist

The criterion labels and point ranges are the project's working checklist only; official wording and scoring were not verified. These statuses describe the available evidence, not points.

| # / working criterion | Status | Observed evidence and limit |
| --- | --- | --- |
| 1. Problem and behavior | **PASS** | The clean local app was opened at `http://localhost:8080/`. The browser added and displayed a rotating ingredient; a synthetic cooked recipe with an attempt was then displayed in the Notebook after an API-created confirmation record. The clean-checkout backend/frontend test suite also passed. This is local behavior, not a hosted demo or live-provider recipe call. |
| 2. Product specification and public tracker | **PASS** | The [product specification](product-spec.md) and public tracker were inspected. The [issue list](https://github.com/YannPhamVan/SavorLoop/issues) showed #1–#13 closed and #14 open; Issue #8 documents tracker use. This does not verify official evaluator acceptance or points. |
| 3. Agent team definition | **PASS** | [`agent-team.md`](agent-team.md), role guides, and [`agent-process.md`](agent-process.md) define roles and permissions; public implementation/QA history for Issues #1–#13 provides an observable task trail. This verifies the project-defined workflow, not evaluator judgment. |
| 4. Context management | **PASS** | [`AGENTS.md`](../AGENTS.md) links to the product, tasks, team, process, and evaluation context. The Issue #14 relative-link check below resolved every checked local target and heading fragment. External URLs were not network-checked by that scan. |
| 5. Application | **PASS** | The local React/FastAPI/SQLite app was reachable at `http://localhost:8080/`; the Inventory UI created a record and the Notebook UI displayed a cooked-recipe record and attempt. The native test/build command also passed. No live Gemini request was made. |
| 6. Testing | **PASS** | In the clean worktree, `uv sync --locked`, `npm --prefix frontend ci`, and `uv run python scripts/verify.py` exited 0; output reported 51 backend tests passed, frontend tests passed, and frontend production build passed. Node engine and Starlette/httpx warnings are disclosed below. |
| 7. Containerization | **PASS** | In the isolated clean worktree, `docker compose config --quiet` and `docker compose up --build -d` exited 0. The browser app and API/readiness checks returned HTTP 200. After `docker compose stop` and `docker compose up -d`, the synthetic inventory, notebook recipe, and attempt were still present. A test-only override avoided occupied host port 8000 and used a unique local volume; this does not establish hosted persistence. |
| 8. Deployment | **UNVERIFIED** | The Render Free demo is suspended. Historical runtime checks are documented in [`render-free-demo.md`](render-free-demo.md), but no current hosted endpoint was requested, awakened, or tested. No active demo, durable hosting, or current live-service behavior is claimed. |
| 9. CI/CD | **UNVERIFIED** | CI has direct successful evidence: `gh run view 42063008631 --repo YannPhamVan/SavorLoop --json databaseId,status,conclusion,event,headSha,createdAt,url,workflowName` returned `status=completed`, `conclusion=success`, `event=pull_request`, and the [run URL](https://github.com/YannPhamVan/SavorLoop/actions/runs/42063008631) on 2026-11-05. The same command for run `40706899477` returned success for the merged [PR #16](https://github.com/YannPhamVan/SavorLoop/pull/16). These runs verify CI only. The workflow does not deploy; no automatic or CI-gated CD/deployment is configured or claimed. |
| 10. Observability | **PASS (local only)** | Issue #11's [QA evidence](https://github.com/YannPhamVan/SavorLoop/issues/11#issuecomment-6662790699) reports direct local Grafana/Prometheus/Tempo/Loki API observations, correlated fabricated signals, and privacy checks. This is evidence for the local stack, not a hosted telemetry destination or current hosted dashboard. |
| 11. Alerting | **PASS (local drill only)** | Issue #12's [QA evidence](https://github.com/YannPhamVan/SavorLoop/issues/12#issuecomment-6663304791) records a synthetic readiness failure, test alert, correlated agent invocation, one approved pool reset, and recovered readiness. No hosted/external alert provider was used. |
| 12. On-call agent | **PASS (local drill only)** | The same Issue #12 [QA report](https://github.com/YannPhamVan/SavorLoop/issues/12#issuecomment-6663304791) records the diagnosis, sole allowlisted remediation, passing readiness verification, and unchanged fabricated inventory/notebook snapshots. This is not hosted operations. |

No stretch criterion is claimed in the evaluation matrix.

## Clean-checkout setup and test commands

The following ran from the fresh `.issue14-clean` worktree, at baseline `76a14321222b7ae5f8ef1ecf6440d03e8bc50d29`, with no project virtual environment, frontend dependencies, database, or `.env` present before setup:

```powershell
uv sync --locked
npm --prefix frontend ci
uv run python scripts/verify.py
```

Observed results:

- `uv sync --locked` — exit 0; installed 47 locked packages using Python 3.11.13.
- `npm --prefix frontend ci` — exit 0; 147 packages added and 148 audited, 0 vulnerabilities reported. npm emitted `EBADENGINE` warnings because OpenTelemetry packages require Node `>=22.15.0`, while the available Node was 22.13.1.
- `uv run python scripts/verify.py` — exit 0; **51 backend tests passed**, frontend tests passed, and TypeScript/frontend production build passed (Vite transformed 262 modules). Pytest emitted one existing Starlette/httpx deprecation warning. No live Gemini/API credential was supplied.

## Compose journey and persistence commands/results

Before creating the test stack, `docker --version` reported Docker 29.9.2 and `docker compose version` reported v5.6.1. `docker compose ps -a` showed no existing containers in the repository's default project; `docker ps -a --filter volume=savorloop-sqlite-data` returned no containers; inspecting `savorloop-sqlite-data` returned “no such volume.” Port 8000 was occupied by a pre-existing listener, so that listener was not stopped or modified. Port 8080 was free.

The clean checkout's untracked `compose.override.yaml` changed only test isolation: it published `127.0.0.1:8080:80` instead of binding host port 8000 and gave the rehearsal database the unique name `savorloop-issue14-rehearsal-data`. No telemetry endpoint or provider key was set. The exact commands and observed results were:

```powershell
docker compose config --quiet
docker compose up --build -d
# Browser: GET http://localhost:8080/ -> HTTP 200.
# Backend container: GET /health -> HTTP 200; GET /ready -> HTTP 200.
# Browser Inventory form: created “Issue 14 rehearsal basil”, quantity 1 bunch.
# POST http://localhost:8080/api/notebook -> HTTP 201, ID 1, one attempt.
# GET /api/notebook and refreshed Notebook UI displayed the synthetic recipe.
docker compose stop
docker compose up -d
# After restart: one inventory record, one notebook recipe, one attempt remained.
docker compose down
# Containers/network removed; rehearsal volume retained (no -v).
```

The app and database were started only in the isolated worktree with the named rehearsal volume. After the persistence check, `docker compose down` (without `-v`) removed only that project's containers and network; the new rehearsal volume was intentionally retained, and the original fixed `savorloop-sqlite-data` volume remained absent. The disposable clean worktree was then removed. The unrelated primary-worktree files were not touched. The synthetic fixture is not real user data. The local Compose observation says nothing about Render or hosted persistence.

## Issue #1–#13 tracker evidence reviewed

The public tracker was read before implementation; all of Issues #1–#13 were **CLOSED** as observed on 2026-11-05. Their histories contain implementation and QA evidence; this table links each reviewed task rather than treating local code/configuration as proof.

| Issue | Task and tracker evidence |
| --- | --- |
| [#1](https://github.com/YannPhamVan/SavorLoop/issues/1) | Bootstrap an empty app with a passing test — closed. |
| [#2](https://github.com/YannPhamVan/SavorLoop/issues/2) | Deliver the structured inventory journey — closed. |
| [#3](https://github.com/YannPhamVan/SavorLoop/issues/3) | Deliver safe natural-language inventory updates — closed. |
| [#4](https://github.com/YannPhamVan/SavorLoop/issues/4) | Deliver on-demand recipe suggestions — closed. |
| [#5](https://github.com/YannPhamVan/SavorLoop/issues/5) | Deliver the Cooking Notebook and explainable feedback loop — closed. |
| [#6](https://github.com/YannPhamVan/SavorLoop/issues/6) | Verify core workflows with one test command — closed. |
| [#7](https://github.com/YannPhamVan/SavorLoop/issues/7) | Run the complete app with persistent SQLite in one command — closed. |
| [#8](https://github.com/YannPhamVan/SavorLoop/issues/8) | Demonstrate agent use of the public GitHub Issues tracker — closed. |
| [#9](https://github.com/YannPhamVan/SavorLoop/issues/9) | Run tests automatically on every pull request — closed; CI evidence includes [PR #16](https://github.com/YannPhamVan/SavorLoop/pull/16). |
| [#10](https://github.com/YannPhamVan/SavorLoop/issues/10) | Deploy an ephemeral educational demo on Render Free — closed after historical verification and owner-directed suspension; not current service evidence. |
| [#11](https://github.com/YannPhamVan/SavorLoop/issues/11) | Instrument one private, correlated user journey — closed; direct local-stack QA evidence is linked above. |
| [#12](https://github.com/YannPhamVan/SavorLoop/issues/12) | Wake an on-call agent from an alert and verify remediation — closed; direct local-drill QA evidence is linked above. |
| [#13](https://github.com/YannPhamVan/SavorLoop/issues/13) | Complete the README and evaluation evidence — closed; its clean-checkout result is preserved as the earlier historical record in [`evaluation.md`](evaluation.md). |
| [#14](https://github.com/YannPhamVan/SavorLoop/issues/14) | Rehearse the rubric and close the highest-risk gaps — open; this checklist and the implementation report are its evidence. |

## Documentation link check

From the repository root, a PowerShell inline scan of `README.md`, `_docs/tasks.md`, `_docs/evaluation.md`, and this checklist extracted Markdown links with `\[[^\]]+\]\((?<target>[^)\s]+)(?:\s+"[^"]*")?\)`, skipped `http`, `https`, `mailto`, `tel`, and `ftp` URLs, resolved each relative target from its source file, and checked heading fragments against normalized Markdown headings. Result: **43 relative links and fragments checked, 55 external links skipped, 0 broken links**. External URLs were not checked for network reachability. This verifies local documentation links only, not the current availability or truth of external services.

## Remaining limitations and evidence gaps

- The working rubric remains unverified against official wording; no score or points are claimed.
- Node 22.13.1 is below the documented Node 22.15 minimum. `npm ci` and the build/tests passed in this environment, but the engine warnings remain.
- Pytest emitted one Starlette/httpx deprecation warning.
- The default Compose host mapping could not be tested unmodified because host port 8000 was already occupied. The safe override kept the app available at `http://localhost:8080` and exercised SQLite restart persistence without touching the pre-existing listener or default volume.
- The Render service is suspended; current hosted-demo and live-service behavior are **UNVERIFIED**.
- Successful GitHub Actions runs demonstrate CI only. Automatic deployment/CD is **UNVERIFIED** and is not claimed.
- Observability and alerting evidence is for prior local-stack and local-drill runs only; no hosted telemetry destination, hosted alert, or production on-call behavior is claimed.
- No live Gemini generation was performed. Provider-backed behavior is covered by repository tests/stubs, not this local Compose run.
