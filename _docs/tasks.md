# SavorLoop Backlog

The backlog is prepared to seed the existing public GitHub Issues tracker. Issues and a GitHub Project are not yet present; publishing issues requires owner authorization. Each item below is intended as a one-session deliverable. Copy the full item into an issue so its acceptance criteria and evidence stay with the work.

## Shared context

SavorLoop is a single-user cooking assistant with Inventory, Suggestions, and Cooking Notebook areas. The planned stack is Lovable-generated React/TypeScript, FastAPI, SQLAlchemy, SQLite, and a configurable schema-validated LLM provider. AI may interpret text or generate recipes, but deterministic backend code validates and applies all data changes. Do not add accounts, notifications, PostgreSQL migration, or unrelated analytics. `product-spec.md` is the current behavior source of truth; `AGENTS.md` and `agent-process.md` define agent boundaries and workflow.

## 1. Bootstrap an empty app with a passing test
Goal: Create a minimal project foundation that builds and has a passing smoke test.
Description: Set up an empty React/TypeScript frontend and FastAPI backend for SavorLoop, with SQLAlchemy/SQLite wiring and no cooking features. Add environment-based settings, `/health` and database-aware `/ready` endpoints, and one backend smoke test so a new contributor can verify the project before feature work begins.
Priority: Mandatory for pass path
Estimate: 0.75 h
Dependencies: None
Acceptance criteria:
- Frontend production build succeeds from a clean dependency install.
- FastAPI app imports and a smoke test passes without an external LLM credential.
- `/health` reports process health and `/ready` reports database connectivity; both have focused tests.
- No secrets or real user data are committed.
Evidence: Exact install, test, and build commands with passing output in the issue/PR.

## 2. Deliver the structured inventory journey
Goal: Let the user view and edit pantry staples and rotating ingredients.
Description: Implement the SQLAlchemy model, validated FastAPI CRUD endpoints, and React Inventory screen for one user's ingredients. Pantry staples use available/unavailable status; rotating ingredients support quantity, unit, and optional expiry date, with clear loading, empty, and error states.
Priority: Mandatory for pass path
Estimate: 1.5 h
Dependencies: T1
Acceptance criteria:
- UI and API create, list, edit, and delete both ingredient categories.
- Category-specific fields and invalid quantity/date values are validated.
- Unit/integration tests cover success and invalid requests; invalid requests leave stored data unchanged.
Evidence: Passing focused API tests and a short UI/API/SQLite walkthrough.

## 3. Deliver safe natural-language inventory updates
Goal: Interpret a stock-change request and apply it only through deterministic validated code.
Description: Add a backend LLM adapter and a natural-language update flow for requests such as consuming mushrooms or marking oil unavailable, then connect it to the inventory interface. The model returns an allowlisted operation only; the backend validates identity, units, and quantities and commits atomically, with no more than one correction retry.
Priority: Mandatory for pass path
Estimate: 1.5 h
Dependencies: T2
Acceptance criteria:
- Provider credentials stay server-side and tests use a stub provider.
- Valid operations update inventory; unknown items, incompatible units, negative amounts, over-consumption, and repeated invalid model output do not change the database.
- The UI reports success or a safe actionable failure and refreshes only after confirmed success.
Evidence: Passing tests for valid, invalid, retry, and no-partial-write cases; one redacted UI walkthrough.

## 4. Deliver on-demand recipe suggestions
Goal: Generate complete recipes from current stock and explain why they fit.
Description: Add deterministic recipe context selection and a Suggestions screen backed by the configured LLM adapter. Use available stock, prioritize suitable ingredients with nearer optional expiry dates, and include a small selection of highly rated notebook history when available; do not save generated suggestions.
Priority: Mandatory for pass path
Estimate: 2 h
Dependencies: T2, T3
Acceptance criteria:
- Validated results include quantities, steps, preparation time, servings, missing ingredients, substitutions, and a brief stock/urgency explanation.
- User can request a serving count and receive quantities scaled to it; missing ingredients are limited to two.
- Invalid output is retried at most once, clearly reported on repeated failure, and never persisted.
- Stubbed-provider tests cover dated/undated stock, response validation, serving changes, and no persistence.
Evidence: Passing focused tests and a redacted request/response walkthrough.

## 5. Deliver the Cooking Notebook and explainable feedback loop
Goal: Save only cooked recipes and preserve feedback across attempts.
Description: Add notebook persistence/API and a React screen for confirming a recipe was cooked, recording an attempt, and reviewing its history. Keep one recipe record with dated ratings, comments, changes, and substitutions; use only a small deterministic selection of highly rated recipes and user-approved adjustments for later suggestions.
Priority: Mandatory for pass path
Estimate: 1.5 h
Dependencies: T4
Acceptance criteria:
- A generated suggestion creates no record until the user confirms it was cooked.
- A recipe stores multiple attempts without overwriting prior feedback.
- Only highly rated recipes and explicitly liked adjustments enter suggestion context; no training or opaque preference inference is added.
- API/UI tests cover create, history preservation, and feedback selection.
Evidence: Passing tests and a walkthrough from suggestion through two notebook attempts.

## 6. Verify core workflows with one test command
Goal: Provide passing unit and integration tests for the complete core user journey.
Description: Add a root-level command that runs backend unit/integration tests and the frontend production build. Cover inventory editing, natural-language updates, recipe generation with a stub LLM, and cooking/notebook persistence, including failure atomicity and safe error handling.
Priority: Mandatory for pass path
Estimate: 1.25 h
Dependencies: T1-T5
Acceptance criteria:
- One documented command runs the full test/build suite from a clean checkout.
- Both unit and integration tests exist and pass without live AI credentials.
- Tests assert invalid operations do not mutate data and suggestions are not saved before cooking confirmation.
Evidence: Full command output and passing CI-compatible test report.

## 7. Run the complete app with persistent SQLite in one command
Goal: Start the frontend, backend, and application database locally with Docker Compose.
Description: Containerize the React build and FastAPI service and define a one-command Compose workflow for the complete app. Store the SQLite database on a named persistent volume, document backup/restore, and ensure container rebuilds or restarts do not silently erase data.
Priority: Mandatory for intended app path; useful for score
Estimate: 0.75 h
Dependencies: T1-T6
Acceptance criteria:
- `docker compose up --build` starts a usable app and health/readiness checks pass.
- A test ingredient remains after stopping and restarting the containers.
- Database path, volume behavior, backup, and restore are documented; no claim is made that a local volume proves hosted persistence.
Evidence: Clean-build output and restart/data-retention demonstration.

## 8. Seed and use the public GitHub Issues tracker
Goal: Make task status public and demonstrate that coding agents work from the tracker.
Description: After the repository owner authorizes publication, create one GitHub Issue per backlog task in the existing public SavorLoop repository; do not create a second tracker. Have an agent complete one authorized issue and link its issue, branch/PR, test output, and evidence so tracker usage is observable.
Priority: Mandatory for the intended pass score
Estimate: 0.75 h
Dependencies: Owner authorization; backlog acceptance criteria
Acceptance criteria:
- Public issues preserve task goals, acceptance criteria, dependencies, priority, and evidence fields.
- A completed issue links to the implementation and an agent-authored verification record.
- No task is marked complete solely because code/configuration exists.
Evidence: Public issue and PR links plus the actual test/workflow evidence. Do not claim completion until these links are verified.

## 9. Run tests automatically on every pull request
Goal: Establish verifiable CI for the core application.
Description: Configure GitHub Actions to install dependencies and run the same backend tests and frontend build used locally for every pull request. This task is CI only; it must not be described as continuous deployment.
Priority: Mandatory for intended pass score
Estimate: 0.5 h
Dependencies: T6
Acceptance criteria:
- Pull-request workflow runs automatically and blocks success when tests/build fail.
- A real passing PR run is available as evidence.
- Workflow instructions or README point to the local equivalent command.
Evidence: Workflow file and passing PR run URL.

## 10. Qualify a host and deploy with a rollback path
Goal: Make SavorLoop publicly accessible without losing SQLite data.
Description: Compare candidate hosts before selection against current persistent-volume guarantees, redeploy behavior, GitHub Actions automation, rollback, cost/limits, and OTLP compatibility. With owner approval, deploy the Compose-compatible app, verify retained data and health checks, and document how to roll back; add automatic deployment only if supported and authorized.
Priority: Useful score improvement
Estimate: 1.5 h
Dependencies: T7, T9; owner approval and deployment secrets
Acceptance criteria:
- The provider decision cites current documentation/evidence for persistent SQLite storage and telemetry/deploy support.
- Public URL or clear deployment demonstration works and data survives the documented redeploy/restart test.
- A rollback procedure is tested or clearly demonstrated; no deployment is claimed before verification.
- CI-only, auto-deploy, and dev-auto/prod-manual are accurately distinguished for the rubric.
Evidence: Provider decision note, public URL/demo, health check, persistence proof, and rollback record.

## 11. Instrument one private, correlated user journey
Goal: Collect and inspect structured logs, metrics, and distributed traces with a shared trace ID.
Description: Instrument the natural-language inventory update from browser request through backend validation, AI-provider call, database operation, and final response. Use one OTLP-compatible collection/storage/UI destination selected for the chosen host; export safe metadata only and never raw prompts, ingredient content, credentials, or secrets.
Priority: Optional stretch
Estimate: 1.5 h
Dependencies: T3, T10 provider compatibility decision; telemetry account/secrets approved
Acceptance criteria:
- Frontend and backend spans propagate a trace ID; structured logs include that ID and metrics cover requests, errors, and AI validation failures.
- Signals are collected, stored, and visible together in a UI, not merely emitted locally.
- An intentional test request is inspectable end to end and privacy tests/review show no prohibited content is exported.
- Only one overlapping monitoring stack is introduced.
Evidence: UI links/screenshots showing the same trace ID across spans/logs and associated metrics, plus privacy review.

## 12. Wake an on-call agent from an alert and verify remediation
Goal: Demonstrate a narrow agent that fixes a known recoverable incident triggered by an alert.
Description: Configure a test alert to invoke the on-call agent, which reads approved redacted signals, identifies a deliberately induced recoverable failure, runs one explicitly allowlisted remediation, verifies recovery, and records the result. Start by validating whether resetting a stale SQLAlchemy connection pool fixes the selected readiness failure; if not, choose and document another proven remediation rather than counting a health retry as a fix.
Priority: Optional stretch
Estimate: 2.5 h
Dependencies: T10-T11; owner-approved test environment and remediation
Acceptance criteria:
- A test failure produces an alert that demonstrably wakes/invokes the agent.
- The agent identifies the known failure from approved diagnostics, applies only the authorized tool, and verifies recovery or reports an unresolved incident.
- Tool permissions exclude arbitrary shell/SQL, inventory/notebook writes, credentials, prompts, and deployment configuration.
- An intentional failure drill records alert, diagnosis, action, verification, and outcome without exposing user data.
Evidence: Correlated alert and agent event records, recovery check, permission list, and test-drill procedure/results.

## 13. Complete the README and evaluation evidence
Goal: Make the repository understandable and substantiate every claimed evaluation result.
Description: Update the README with the problem, expected behavior, prerequisites, one-command setup, demo, deployment, and limitations. Link modular project documentation and map rubric claims only to real test runs, issue/PR history, public deployment, telemetry UI, alerts, or incident-drill evidence.
Priority: Mandatory for pass path
Estimate: 0.75 h
Dependencies: T1-T9; include T10-T12 only if completed
Acceptance criteria:
- New contributor can follow setup and test instructions from a clean checkout.
- README and evaluation matrix contain no invented status, URL, test, score, or deployment claim.
- Known gaps and unverified official-criteria wording are explicit.
Evidence: Documentation link check and clean-checkout setup/test record.

## 14. Rehearse the rubric and close the highest-risk gaps
Goal: Use the remaining project time to verify the pass path rather than add unplanned features.
Description: Run the core journey and each claimed evaluation check from a clean environment, review the public issue/PR evidence, and compare actual behavior against `evaluation.md`. Fix only the highest-priority defects or missing proof; defer polish and report any criterion that remains unverified.
Priority: Mandatory for pass path
Estimate: 1.75 h
Dependencies: T1-T9, T13; include stretch tasks only if they are claimed
Acceptance criteria:
- Core tests, build, one-command local start, and persistence checks pass from a clean state.
- Each claimed rubric point has direct evidence; gaps and failed checks are listed without qualification by related code alone.
- Final README, task tracker, and evaluation matrix agree on project status.
Evidence: Dated rehearsal checklist with exact commands, links, results, and remaining limitations.
