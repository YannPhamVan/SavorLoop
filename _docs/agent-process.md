# Agent Work Process

## Selecting work

1. Use the public SavorLoop GitHub Issues tracker as the task-status source once the owner authorizes and seeds it. Until then, use the numbered task in `tasks.md`; no public issue should be implied.
2. Select a task whose dependencies are complete. Read its goal, description, acceptance criteria, evidence, priority, and estimate.
3. Inspect the current repository state and the closest relevant tests before editing. Raise a blocker when acceptance criteria conflict with existing behavior or require an unapproved external action.

## Implementing and validating

1. Keep the change to one task and preserve the product boundaries in `product-spec.md` and `AGENTS.md`.
2. Add focused tests for behavior and failure cases, especially invalid AI output and atomic database updates.
3. Run the task's focused check first, then the documented full test/build command when available.
4. Review the diff for secrets, unnecessary user content in telemetry, schema changes, and accidental scope growth.

## Recording and reviewing evidence

- Link the GitHub Issue in the branch/PR title or description when an authorized issue exists.
- In the issue or PR, record what changed, exact test/build commands and pass/fail result, and relevant workflow, deployment, dashboard, alert, or demo links.
- Do not mark work done based only on code/configuration presence. A live system criterion needs observable runtime evidence.
- A reviewer checks acceptance criteria and evidence. The owner approves deployments, external services, tracker publication, and unresolved product decisions.
- If work is blocked, leave the task open, state the blocker and evidence gathered, and do not create a duplicate issue or silently substitute a weaker criterion.

## Issue template

Use each backlog entry as the issue body. Preserve its Goal, Description, Priority, Estimate, Dependencies, Acceptance criteria, and Evidence fields. Add a completion comment with the implementation link and actual verification results. This provides visible evidence that agents used the tracker rather than merely having a task list in the repository.