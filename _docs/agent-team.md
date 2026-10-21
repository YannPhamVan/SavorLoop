# Agent Team

## Roles

| Role | Responsibilities | Permitted actions |
| --- | --- | --- |
| Project owner | Set priorities, resolve product questions, approve external actions, and judge the final demo. | Approve tracker publication, provider selection, production deployment, and any scope or data-store change. |
| Product Manager (PM) agent | Groom every issue before implementation using the four-section task template and make acceptance criteria checkable. | Read and rewrite issues, consider edge cases, and file linked follow-up issues for work moved out of scope. Must not write code. |
| Coding agent | Take one ready issue, inspect relevant code and docs, implement the accepted slice, test it, and report evidence. | Edit repository files and run local checks within the issue scope. No secret disclosure, external issue creation, production changes, or data edits outside validated application paths. |
| Reviewer agent / human reviewer | Independently examine the diff against acceptance criteria, test behavior, and identify regressions or missing evidence. | Read code, run tests, request changes. Do not silently expand scope or approve unverified claims. |
| On-call agent (planned) | Wake from a configured alert, inspect approved telemetry, diagnose a known recoverable incident, perform one allowlisted remediation, verify recovery, and record the result. | Read redacted health/telemetry signals and invoke a narrowly defined recovery tool. No arbitrary shell, SQL, inventory/notebook writes, credential access, prompt edits, or deployment configuration changes. |

## Collaboration protocol

The project owner authorizes scope and external actions. The coding agent links each change to a tracker issue, explains any deviation, runs acceptance checks, and records command results. A reviewer checks the actual diff and evidence before the issue is closed. The on-call agent is a separate operational identity and is not used as a general coding assistant.

The on-call agent is not implemented yet. Its permissions and remediation must be exercised in a test environment before any production alert is connected.