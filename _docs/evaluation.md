# Evaluation evidence

## Scope and rubric caveat

This is an evidence register, not a score report. The 12 criterion names and point ranges below are the project's working checklist retained from the prior local planning document. The official evaluation wording and current scoring rules have **not** been independently verified. No points are claimed as earned, and no score should be inferred from this matrix.

Each row distinguishes repository artifacts from observed evidence and calls out important limits. A file, workflow, or configuration is not by itself proof of a live or successful result. Historical public-service evidence is labeled historical; no suspended service is represented as currently available.

## Criteria-to-evidence matrix

| # / working criterion (points) | Repository evidence | Observed evidence and limits |
| --- | --- | --- |
| 1. Problem and behavior (0–2) | [README](../README.md) explains the problem, expected behavior, prerequisites, local setup, demo, deployment state, and limitations. The [product specification](product-spec.md) defines the product behavior. | Fresh-checkout setup and test results are recorded below. A hosted demo is not currently available. |
| 2. Product specification and public tracker (0–2) | The [product specification](product-spec.md) and [GitHub Issues](https://github.com/YannPhamVan/SavorLoop/issues) are present; issues #1–#13 are closed and #14 is open as observed on 2026-11-05. | Issue/PR history is publicly inspectable. Issue #8 documents the tracker-workflow deliverable; [PR #16](https://github.com/YannPhamVan/SavorLoop/pull/16) is an issue-linked CI change. This does not establish evaluator acceptance or points. |
| 3. Agent team definition (0–2) | [Agent team](agent-team.md), role guides under [`team/`](team/), and [agent process](agent-process.md) define responsibilities and boundaries. | This repository contains the definitions; the current issue workflow provides a public task trail. No score is claimed. |
| 4. Context management (0–2) | [`AGENTS.md`](../AGENTS.md) links to the product, task, process, team, and evaluation documents and records architectural constraints. | This issue is being documented against the repository guidance and public issue tracker. A resolved link check and exact test run are recorded below; this does not establish official evaluator acceptance. |
| 5. Application (0–2) | The frontend, FastAPI backend, SQLAlchemy/SQLite persistence, and root [Compose configuration](../compose.yaml) are in the repository. | The recorded suite exercises backend and frontend behavior. The historical Render walkthrough is documented under criterion 8; the service is suspended and is not a current demo. |
| 6. Testing (0–2) | Tests are under `backend/tests` and `frontend`; [`scripts/verify.py`](../scripts/verify.py) runs the backend suite, frontend tests, and frontend production build. | The clean-checkout run below records each setup command and the full verification outcome. Passing tests do not prove every runtime/deployment scenario. |
| 7. Containerization (0–2) | [`compose.yaml`](../compose.yaml) starts the app and declares a named local SQLite volume. The README documents startup, stop/restart, backup, and restore commands. | The Issue #14 [local rehearsal](issue-14-rehearsal.md) directly observed the app journey and inventory/notebook persistence after stop/restart using a unique test volume and port-mapping override. This does not establish hosted persistence. |
| 8. Deployment (0–2) | [`render-free-demo.md`](render-free-demo.md) records the dated Render Free fact check, deployment configuration and limits. | The document records historical HTTP 200 responses from `/health` and `/ready` and a fabricated inventory walkthrough on 2026-11-05, then owner-directed suspension. The service is not currently offered, and its ephemeral SQLite data has no retention/recovery guarantee. No durable or production deployment is claimed. |
| 9. CI/CD (0–3) | [`ci.yml`](../.github/workflows/ci.yml) runs verification for pull requests; the Render record says Auto-Deploy was Off and deploys were manual. | [CI run 42063008631](https://github.com/YannPhamVan/SavorLoop/actions/runs/42063008631) completed successfully on 2026-11-05. [PR #16 CI run](https://github.com/YannPhamVan/SavorLoop/actions/runs/40706899477) is also recorded as successful. The workflow does not deploy; no automatic or CI-gated deployment is claimed. |
| 10. Observability (0–2) | [`observability/README.md`](../observability/README.md) describes the local Collector, Grafana, Prometheus, Loki, Tempo, dashboard, attribute allowlists, and host limitations. | The repository describes a local observability stack and automated signal/privacy checks. No hosted telemetry destination or hosted dashboard evidence is claimed; local configuration alone is not proof of a currently running UI. |
| 11. Alerting (0–1) | [`on-call-drill.md`](on-call-drill.md) and [`compose.issue12-drill.yaml`](../compose.issue12-drill.yaml) describe the test-only local alert route. | The documented issue-12 drill records an isolated synthetic readiness failure and alert. No external alert provider or hosted alert was configured or contacted. |
| 12. On-call agent (0–2) | The drill document describes the agent's three fixed tools, permissions, and isolated Docker/SQLite procedure. | The recorded drill reports one allowlisted pool reset, passing readiness verification, a recovered outcome, and unchanged fabricated inventory/notebook snapshots. This is local drill evidence, not hosted operations or evaluator scoring. |

## Clean-checkout setup and test record

Recorded for Issue #13 on 2026-11-05. The checkout was created from the local Git repository at commit `12de97848c364bdfa8acfe6a54c3c104132917cb` (`build(deps): bump pyasn1 from 0.6.4 to 0.6.5`), with tracked files checked out and no pre-existing `.vscode/`, `issue2-walkthrough.db`, or `node_modules/` copied into it. The environment reported Python 3.11.13, Node.js 22.13.1, and npm 10.9.2. Node 22.13.1 is below the frontend lockfile's declared Node 22.15 minimum, so the README now specifies Node.js 22.15 or newer. This validates the setup and application code at that commit; the Issue #13 changes are documentation-only.

Commands were run from the clean checkout root, in this order:

```powershell
uv sync --locked
npm --prefix frontend ci
uv run python scripts/verify.py
```

Observed result: `uv sync --locked` completed successfully; `npm --prefix frontend ci` completed successfully but emitted `EBADENGINE` warnings for OpenTelemetry packages requiring Node `>=22.15.0` under Node 22.13.1; `uv run python scripts/verify.py` completed successfully with 51 backend tests passed, frontend tests passed, and the frontend production build passed. Pytest reported one existing Starlette/httpx deprecation warning. The checks used no live provider credential and changed no deployment. This is a local clean-checkout result, not a claim about a newly deployed revision.

## Issue #14 rehearsal (2026-11-05)

The latest clean-worktree setup and test run, local inventory/notebook journey, Compose stop/restart persistence observation, criterion-by-criterion working-rubric status, issue-history review, exact commands, and evidence limitations are recorded in the dated [Issue #14 rehearsal checklist](issue-14-rehearsal.md). It was run from a clean worktree at baseline commit `76a14321222b7ae5f8ef1ecf6440d03e8bc50d29`; the test-only Compose override and pre-existing host-port conflict are disclosed there. This supplements the Issue #13 historical clean-checkout record above and does not replace or reinterpret it.

## Documentation link check

For Issue #13 on 2026-11-05, the local Markdown-link scan checked 33 relative links in `README.md` and this document, including the README's heading fragment; all 33 resolved. It skipped 13 external links, which were not checked; the result does not imply those destinations are reachable. The Issue #14 link check across the updated README, task backlog, evaluation matrix, and dated checklist is recorded in the checklist.

## Evidence sources and limits

- Repository code, tests, configuration, and documentation linked above are inspectable in this checkout.
- Public tracker history: [Issues](https://github.com/YannPhamVan/SavorLoop/issues), including [Issue #10](https://github.com/YannPhamVan/SavorLoop/issues/10), [Issue #11](https://github.com/YannPhamVan/SavorLoop/issues/11), [Issue #12](https://github.com/YannPhamVan/SavorLoop/issues/12), and this [Issue #13](https://github.com/YannPhamVan/SavorLoop/issues/13).
- Historical deployment and local drill outcomes are evidence recorded by their respective task documentation; they are not current external-service checks performed for Issue #13.
- No evaluation score, official-rubric confirmation, active public demo, durable hosted persistence, hosted telemetry UI, or external alerting capability is asserted here.
