# SavorLoop Agent Instructions

## Project context

SavorLoop is a single-user cooking assistant. The planned stack is a Lovable-generated React/TypeScript frontend, FastAPI backend, SQLAlchemy, SQLite, and a configurable LLM provider. The repository is currently documentation-only; do not assume application code, commands, deployments, or external tracker issues already exist.

## Read before changing behavior

- [Product specification](_docs/product-spec.md) is the current source of truth for product behavior.
- [Task backlog](_docs/tasks.md) defines deliverables, acceptance criteria, dependencies, priority, estimates, and evidence.
- [Agent team](_docs/agent-team.md) defines roles and permissions.
- [Agent process](_docs/agent-process.md) defines task selection, implementation, review, and evidence practices.
- [PM role](_docs/team/pm.md) defines task grooming responsibilities and boundaries.
- [Task template](_docs/task-template.md) is the required four-section issue template.
- [Evaluation and roadmap](_docs/evaluation.md) maps the supplied rubric and records assumptions.
- [Initial plan](_docs/plan.md) preserves the original brainstorming; the dated addendum records later decisions.

## Architectural boundaries

- AI may interpret user text or generate a recipe; it never receives direct database mutation capability.
- Validate structured model output, then apply allowlisted changes through deterministic backend operations.
- Invalid operations must be atomic: no partial database changes.
- Do not persist a generated suggestion until the user confirms it was cooked.
- Keep single-user scope; do not add authentication, multi-user support, notifications, or unrelated analytics.
- Keep persistence behind SQLAlchemy. SQLite is the initial database; do not migrate to PostgreSQL without a demonstrated need and approval.
- Telemetry may include safe operation metadata, status, durations, and error categories, but not credentials, raw secrets, or unnecessary user content.
- Operational agents have only explicit diagnostic and remediation tools. They must not edit inventory, notebook data, credentials, prompts, or deployment configuration.

## Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file

## Rules

- Select a ready backlog task and read its acceptance criteria before implementation.
- Keep changes within that task; record dependencies or blockers instead of silently expanding scope.
- Add or update focused tests for changed behavior and run the documented checks.
- Dependencies are added in `pyproject.toml`. Do not add one without asking.
- Never claim a task, test, alert, deployment, tracker update, or rollback succeeded without observable evidence.
- Link changes to their GitHub Issue when the public tracker is authorized and available; otherwise record the local task ID and evidence in the pull request or task notes.
- Do not publish issues, deploy, or change external services without the repository owner's authorization.