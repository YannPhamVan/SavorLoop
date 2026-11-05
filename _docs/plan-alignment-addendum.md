# Plan Alignment Addendum

Date: 2026-10-21

The initial brainstorming in [`plan.md`](plan.md) is preserved. This addendum records decisions and repository status that supersede its earlier open questions.

## Decisions since the initial plan

- Selected stack: Lovable-generated React/TypeScript frontend, FastAPI backend, SQLAlchemy, SQLite initially, and a configurable LLM provider with schema-validated outputs.
- The user supplied 12 evaluation criteria and point values in the backlog-alignment request; [`evaluation.md`](evaluation.md) treats those supplied criteria as the working source of truth. Their wording has not been independently checked against the course site.
- The product specification, modular agent documents, revised backlog, rubric matrix, and roadmap are maintained in their linked documents rather than duplicating detailed acceptance criteria here.
- The repository is documentation-only. The public GitHub repository has no issues or projects at the time checked. No public tracker or application implementation is claimed.

## Decisions still open

- LLM provider and spending limit.
- Hosting platform, only after verifying persistent SQLite storage, deployment automation/rollback, and telemetry compatibility.
- One OTLP-compatible telemetry destination and associated account/secrets.
- Exact ingredient unit policy and recipe plausibility checks.
- Production deployment authorization and the safe, demonstrable on-call remediation.

See [`product-spec.md`](product-spec.md), [`tasks.md`](tasks.md), and [`evaluation.md`](evaluation.md) for the current scope and action plan.

## Update — 2026-11-05

- The owner selected Render Free for a no-cost, disposable educational preview. This does not replace the requirement that product hosting preserve SQLite data and is not production authorization.
- The [Render Free fact check](render-free-demo.md) records current official limits, ephemeral data loss, and the authorization boundary. On 2026-11-05, the owner authorized deployment using their existing account; no new account, custom domain, paid resource, or application secret was created or configured.
- The [Render Free preview](https://savorloop-free-demo.onrender.com) was deployed and verified for fabricated disposable data, then suspended at the owner's request on 2026-11-05. Runtime evidence and suspension limits are recorded in `render-free-demo.md`.
- The repository has PR-only CI, verified by merged [PR #16](https://github.com/YannPhamVan/SavorLoop/pull/16) and its [passing workflow run](https://github.com/YannPhamVan/SavorLoop/actions/runs/40706899477). The Render service was CD with Auto-Deploy Off, so the deployment was manual; the service is currently suspended.