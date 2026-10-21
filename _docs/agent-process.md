# Agent Work Process

## Roles

- PM: grooms every task before anyone implements it and follows [`_docs/team/pm.md`](team/pm.md). The PM does not write code.
- Coding agent: implements only a groomed issue, one issue at a time, and reports verification evidence.

## Selecting work

1. Use the public SavorLoop GitHub Issues tracker as the task-status source once the owner authorizes and seeds it. Until then, use the numbered task in `tasks.md`; no public issue should be implied.
2. Select one task whose dependencies are complete. Work on one GitHub issue at a time.
3. Before implementation, the PM reads the issue as written and grooms it using [`_docs/task-template.md`](task-template.md), following the instructions in [`_docs/team/pm.md`](team/pm.md). Do not start implementation until Goal, Acceptance criteria, Out of scope, and Constraints are all filled in and the criteria are checkable.
4. The implementer reads the groomed acceptance criteria and linked documents before starting. Re-read the acceptance criteria before closing the issue and confirm each is met with evidence.
5. Inspect the current repository state and the closest relevant tests before editing. Raise a blocker when acceptance criteria conflict with existing behavior or require an unapproved external action.

## Implementing and validating

1. Keep the change to one task and preserve the product boundaries in `product-spec.md` and `AGENTS.md`.
2. Add focused tests for behavior and failure cases, especially invalid AI output and atomic database updates.
3. Run the task's focused check first, then the documented full test/build command when available.
4. Review the diff for secrets, unnecessary user content in telemetry, schema changes, and accidental scope growth.
5. Commit validated changes regularly, keeping each commit focused on the active issue.

## Recording and reviewing evidence

- Link the GitHub Issue in the branch/PR title or description when an authorized issue exists.
- In the issue or PR, record what changed, exact test/build commands and pass/fail result, and relevant workflow, deployment, dashboard, alert, or demo links.
- Do not mark work done based only on code/configuration presence. A live system criterion needs observable runtime evidence.
- A reviewer checks acceptance criteria and evidence. The owner approves deployments, external services, tracker publication, and unresolved product decisions.
- If work is blocked, leave the task open, state the blocker and evidence gathered, and do not create a duplicate issue or silently substitute a weaker criterion.

## Issue template

The PM rewrites each issue using the four-section template in [`_docs/task-template.md`](task-template.md). Preserve useful existing scope, dependencies, and constraints in those sections or in linked issues/documents; do not silently discard work. Add a completion comment with the implementation link and actual verification results. This provides visible evidence that agents used the tracker rather than merely having a task list in the repository.