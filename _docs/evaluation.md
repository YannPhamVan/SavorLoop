# Evaluation Mapping and Roadmap

## Repository review

At the start of this review on 2026-10-21, the local repository tracked only `README.md` and `_docs/plan.md`; the README contained only the project title. There was no application code, test suite, `AGENTS.md`, Docker configuration, CI workflow, deployment evidence, or telemetry configuration. The public GitHub repository was accessible, but its Issues and Projects pages were empty; no GitHub Actions workflow was visible. The 23-task local backlog was untracked and had no acceptance criteria, evidence requirements, dependencies, estimates, or prioritization.

The revised backlog consolidates overlapping backend/UI/model tasks into independently testable vertical slices. It retains the agreed inventory, recipe, notebook, SQLite, and deterministic AI boundaries. It removes the proposed health-check-only incident retry as insufficient remediation, makes persistence and one-command Compose startup explicit, and adds public tracker usage, rubric evidence, agent permissions, and a genuine alert-triggered remediation workflow. No application functionality or external service is claimed complete.

## Evaluation matrix

"Current" describes the workspace after this documentation update, not a score prediction or a claim that local changes are already published. Task numbers refer to [`tasks.md`](tasks.md). Priority means priority for the proposed 13-point pass path unless marked stretch.

| # / criterion | Current | Tasks and acceptance criteria | Evidence required | Dependencies | Priority |
| --- | --- | --- | --- | --- | --- |
| 1. Problem description (0-2) | Partial: README now describes the problem and behavior; runnable setup, demo, and deployment details await implementation. | T13: README explains problem, functionality, expected behavior, local setup, demo, deployment, and limitations. | Public README and working demo/setup links; no unsupported claims. | Product slices; T13. | Mandatory |
| 2. Product specification and public task tracker (0-2) | Partial: product spec and issue-ready local tasks exist; public Issues are empty and agent usage is not evidenced. | T8, T13: publish the prepared tasks as Issues with acceptance criteria; record an agent-linked PR and completion evidence. Product behavior is documented in `product-spec.md`. | Public issue URLs, issue/PR links, agent activity and test/evidence comments. | Owner authorization; task criteria; T8. | Mandatory, external action pending |
| 3. Agent team specification (0-2) | `agent-team.md` added locally; public publication and issue-linked workflow evidence are pending. | `agent-team.md`: responsibilities, collaboration, permissions, and separate on-call role are explicit; T13 keeps it aligned with actual practice. | Public document plus a PR/issue trail following the process. | Documentation; T8 for public usage evidence. | Mandatory |
| 4. Context management (0-2) | `AGENTS.md` and modular documents added locally; changes are not yet published or exercised in a tracked task. | `AGENTS.md` summarizes architecture/boundaries and links to product, task, team, process, and evaluation documents. | Repository files and links resolve; an agent follows the instructions in a tracked task. | Documentation; T8 for usage evidence. | Mandatory |
| 5. Application (0-2) | Not implemented. | T1-T5, T7: frontend, FastAPI, SQLite, and the core single-user flow work end to end; one command starts the full app. | Clean-clone startup, UI/API/DB walkthrough, and retained data after app restart. | T1-T5; T7. | Mandatory |
| 6. Testing (0-2) | No tests. | T1, T2-T6: unit and integration tests cover core workflows and failure atomicity; one documented command runs them and passes. | Test command and passing CI run; include invalid-AI and no-persist-until-cooked cases. | T1-T5; T6; T9. | Mandatory |
| 7. Containerization (0-2) | No Docker files. | T7: Compose starts frontend/backend with SQLite persistence in one command; database survives container restart/redeployment procedure. | Clean `docker compose up --build`, health check, restart/data-retention demonstration, and backup/restore notes. | T1-T6; host storage caveat documented. | Useful, high value |
| 8. Deployment (0-2) | No deployment. | T10: select a host only after verifying persistent SQLite storage, deployment automation, and telemetry compatibility; publish app or a clear deployment demonstration. | Public URL/demo, health check, retained-data evidence, and rollback evidence. | T7; provider decision; owner authorization/secrets. | Stretch |
| 9. CI/CD (0-3) | No workflows. | T9: CI tests run for every PR (1-point target). T10 may add automatic deployment (2-point progression); separate automatic development and manual production deploy is stretch for 3. | PR workflow run; for higher scores, successful dev deployment and documented manual production approval/run. | T6; T7; T10 for deployment progression. | CI mandatory; deploy stretch |
| 10. Observability (0-2) | No telemetry. | T11: instrument one frontend-to-backend user journey with correlated structured logs, metrics, and distributed traces sharing a trace ID; collect/store/view via one UI. | UI screenshots/links showing same trace ID and correlated signals; privacy review and test event. | T3 or T4; T10 host/provider compatibility; T11. | Stretch |
| 11. Alerting on user impact (0-1) | No alert. | T12: a monitored user-impact failure triggers a configured alert in the test environment. | Alert rule, intentionally triggered test, delivered alert/event record. | T10-T11; safe test trigger. | Stretch |
| 12. On-call agent (0-2) | Not implemented; prior health-check retry proposal would not satisfy remediation. | T12: alert wakes the bounded agent; it reads approved signals, identifies a known failure, invokes one allowlisted fix, verifies recovery, and records result or unresolved status. | Correlated alert/agent/action/recovery event and intentional failure drill; no business-data mutation. | T10-T11; T12 tools, permissions, test environment. | Stretch |

## Score paths

- **Minimum passing target: 13/24, conditional, not guaranteed.** Aim for full evidence on criteria 1-6 (12 points) and CI on every PR for criterion 9 (1 point). Criterion 2's two points depend on publishing the tracker and demonstrating agent use; until the owner authorizes issue creation and the workflow is exercised, the total may fall below 10. Do not report points as earned before evaluator evidence exists.
- **Stretch path:** Add Docker (up to 2), public deployment (up to 2), full observability (2), alerting (1), and alert-triggered remediation (2); optionally progress CI/CD from 1 to 2 or 3. These additions could bring the score to 24 only if every criterion is accepted and evidenced.
- If the schedule slips, preserve the core workflow, tests, PR CI, and truthful documentation. Defer optional interface polish and do not substitute logs for observability, a health retry for remediation, or a local container for hosted persistence.

## Roadmap and estimates

Task estimates in `tasks.md` total about **18.5 hours**, with **1.5 hours of contingency** to stay within the approximately 20-hour budget. These are rough single-session estimates including implementation and focused verification; provider setup, review feedback, or deployment troubleshooting may exceed them.

| Phase | Tasks | Estimate | Outcome |
| --- | --- | ---: | --- |
| Foundation and product slices | T1-T5 | 7.25 h | Passing empty app; inventory, natural-language update, recipe suggestion, and cooking notebook journeys. |
| Verification and local release | T6-T7 | 2 h | Unit/integration checks and one-command Compose startup with persistent SQLite. |
| Evaluation workflow | T8-T9 | 1.25 h | Public Issues seeded and used, PR CI evidence. T8 requires owner authorization. |
| Stretch operations | T10-T12 | 5.5 h | Host decision/deployment, full telemetry, alert-triggered agent. Provider and tool compatibility are risks. |
| Docs and rehearsal | T13-T14 | 2.5 h | README/evidence, end-to-end rubric rehearsal, fix highest-priority defects. |
| **Planned total + contingency** |  | **18.5 h + 1.5 h** | **20 h** |

**Minimum passing path:** T1-T9, T13, and T14, with T10-T12 deferred; target 13 points only if criteria 1-6 and PR CI are actually demonstrated. **Stretch path:** complete T10-T12 and consider the extra CI/CD progression in T10. The public task tracker and agent usage are prerequisites to relying on criterion 2 for the pass target.

## Assumptions and owner decisions

- The 12 criteria and point values in the project request are treated as the evaluation source of truth; the official course page was not independently checked.
- The public GitHub repository is the intended tracker host. Its Issues tab is empty and Projects tab has no project. The backlog is import-ready, but publishing issues needs owner authorization; do not create a second tracker.
- Choose hosting only after checking current SQLite persistent-volume behavior, automated deployment, rollback, pricing/limits, and OTLP compatibility. A local Compose volume does not establish hosted persistence.
- Prefer one OTLP-compatible telemetry destination and one UI for logs, metrics, and traces. Provider selection and any account/secret creation need owner input.
- The on-call remediation candidate is resetting the SQLAlchemy connection pool after a deliberately induced stale-connection/readiness failure, then probing readiness. Validate that this is safe and actually fixes the injected failure before treating it as accepted; if not, choose another narrow, non-business-data remediation.
- Model provider, budget, hosting/telemetry providers, domain/serving validation rules, and production deployment authorization remain open. Do not add PostgreSQL, accounts, notifications, or broad agent permissions without approval.