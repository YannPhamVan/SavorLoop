# Agent Work Process

## Roles

- PM - grooms a task before anyone implements it, follows [`_docs/team/pm.md`](team/pm.md).
- Engineer - implements one groomed task, follows [`_docs/team/software-engineer.md`](team/software-engineer.md).
- QA - checks the result against the acceptance criteria, follows [`_docs/team/qa-engineer.md`](team/qa-engineer.md).

## Selecting work

1. Use the public SavorLoop GitHub Issues tracker as the task-status source once the owner authorizes and seeds it. Until then, use the numbered task in `tasks.md`; no public issue should be implied.
2. Select one task whose dependencies are complete. Work on one GitHub issue at a time.
3. Before implementation, the PM reads the issue as written and grooms it using [`_docs/task-template.md`](task-template.md), following the instructions in [`_docs/team/pm.md`](team/pm.md). Do not start implementation until Goal, Acceptance criteria, Out of scope, and Constraints are all filled in and the criteria are checkable.
4. The engineer reads the groomed acceptance criteria and linked documents before starting. Do not change acceptance criteria; if one is wrong, impossible, or conflicting, comment on the issue and wait for clarification.
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
- The engineer comments on the issue with a summary of the work and verification, and leaves the issue open. The reviewer checks acceptance criteria and evidence before an authorized person closes it.
- QA independently checks the running result against every issue acceptance criterion, runs and reports tests, and posts a PASS or FAIL verdict comment. QA does not modify code; a FAIL leaves the issue open for the engineer to address.
- Do not mark work done based only on code/configuration presence. A live system criterion needs observable runtime evidence.
- A reviewer checks acceptance criteria and evidence. The owner approves deployments, external services, tracker publication, and unresolved product decisions.
- If work is blocked, leave the task open, state the blocker and evidence gathered, and do not create a duplicate issue or silently substitute a weaker criterion.

## Issue template

The PM rewrites each issue using the four-section template in [`_docs/task-template.md`](task-template.md). Preserve useful existing scope, dependencies, and constraints in those sections or in linked issues/documents; do not silently discard work. Add a completion comment with the implementation link and actual verification results. This provides visible evidence that agents used the tracker rather than merely having a task list in the repository.