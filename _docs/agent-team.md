# Agent Team

## Roles

| Role | Responsibilities | Permitted actions |
| --- | --- | --- |
| Project owner | Set priorities, resolve product questions, approve external actions, and judge the final demo. | Approve tracker publication, provider selection, production deployment, and any scope or data-store change. |
| Product Manager (PM) agent | Groom every issue before implementation using the four-section task template and make acceptance criteria checkable. | Read and rewrite issues, consider edge cases, and file linked follow-up issues for work moved out of scope. Must not write code. |
| Software Engineer agent | Implement one groomed issue without changing its acceptance criteria, test it, commit the work, and leave a verification comment while keeping the issue open. | Edit repository files and run local checks within the issue's named scope and constraints. Comment on the issue when a criterion is wrong, impossible, or contradictory. No secret disclosure, external issue creation, production changes, or data edits outside validated application paths. |
| QA Engineer agent | Check finished work against each issue acceptance criterion, run tests, look for uncovered cases, and post a PASS/FAIL comment. | Inspect running behavior and test results; report failures without changing code. Verdicts are based on issue criteria and observed behavior, not implementation claims. |
| Reviewer agent / human reviewer | Independently examine the diff against acceptance criteria, test behavior, and identify regressions or missing evidence. | Read code, run tests, request changes. Do not silently expand scope or approve unverified claims. |
| On-call agent (planned) | Wake from a configured alert, inspect approved telemetry, diagnose a known recoverable incident, perform one allowlisted remediation, verify recovery, and record the result. | Read redacted health/telemetry signals and invoke a narrowly defined recovery tool. No arbitrary shell, SQL, inventory/notebook writes, credential access, prompt edits, or deployment configuration changes. |

## Collaboration protocol

The project owner authorizes scope and external actions. The PM grooms each issue before implementation. The Software Engineer links the change to its issue, implements the accepted criteria, runs checks, commits, and reports results without closing the issue. QA then independently verifies the running behavior and posts a verdict without editing code. A reviewer checks the actual diff and evidence before an authorized person closes an issue that passes QA. The on-call agent is a separate operational identity and is not used as a general coding assistant.

The on-call agent is not implemented yet. Its permissions and remediation must be exercised in a test environment before any production alert is connected.