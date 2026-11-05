# Render Free educational preview

## Purpose and decision

Checked against Render's official documentation on 2026-10-28 and rechecked on 2026-11-05. Render Free is selected only for a no-cost, disposable educational preview. This is a narrow exception to the product's durable-hosting requirement, not a hosting decision for production or for user data.

The Free web-service compute plan is $0. This does not mean total workspace usage or every resource is unconditionally free. No paid resource or add-on is in scope. Use Render's generated `onrender.com` address; a custom domain and application secrets are not needed for the inventory demonstration.

## Documented Free-service behavior and limits

- A Free web service spins down after 15 minutes without inbound traffic. A later request starts it again, typically in about one minute.
- Changes to the local filesystem, including SQLite data, are lost on spin-down, restart, and redeploy. Free web services cannot attach persistent disks.
- Render makes no data-retention guarantee for this ephemeral service. Render explicitly says Free instances are not for production applications.
- Each workspace receives 750 Free instance hours per calendar month. Time while a service is spun down does not consume those hours. When the allowance is exhausted, Free web services are suspended until the next month.
- Free web services and static sites consume included monthly outbound-bandwidth and build-pipeline usage. Render shows the workspace's included amounts in its billing dashboard; this fact check does not assume a universal allowance or calculate total workspace cost. Exceeding bandwidth can incur billing, or suspend Free services if no payment method is added. Exceeding build-pipeline usage can incur billing; if no payment method is added or the spend limit is reached, new builds are disabled for the rest of the month while existing deployed artifacts remain active.
- Render may restart a Free web service at any time and may suspend one generating an unusually high volume of outbound traffic.
- A Free web service is limited to one instance and cannot scale beyond it; it cannot attach a persistent disk.
- Render documents Free-service rollbacks to the two most recent previous deploys. This is a code/deploy rollback, not data recovery; it does not restore an ephemeral SQLite database. No rollback or data-recovery procedure has been tested or is claimed here.

## CI/CD and observed project status

The repository's [CI workflow](../.github/workflows/ci.yml) runs for pull requests only and performs dependency installation, tests, and a frontend build. It does not deploy. The merged [PR #16](https://github.com/YannPhamVan/SavorLoop/pull/16) has a [passing CI run](https://github.com/YannPhamVan/SavorLoop/actions/runs/40706899477). The planned Render service uses manual deploys; no auto-deploy or CI-gated deployment is configured. A Render service deployment is CD, but it does not change the PR-only GitHub Actions workflow. Verify the actual service's setting in the dashboard before reporting its deploy mode.

The owner authorized use of their existing Render account and provisioning/deployment of one Free web service on 2026-11-05. No account creation is needed. The planned service uses the generated `onrender.com` URL; no custom domain or application secret is needed for the inventory walkthrough. The [Render-specific Docker image](../render.Dockerfile) serves the frontend and API from one service and displays an ephemeral-data warning. No service is provisioned yet, so there is no public demo URL or observed runtime behavior to report. After deployment, use fabricated disposable data and verify `/health`, database-aware `/ready`, and one basic inventory add/view flow while the instance is active.

The durable local development path remains [Docker Compose with its named SQLite volume](../README.md); that local persistence does not establish hosted persistence. This preview makes no production-suitability, uptime, availability, performance, data-retention, recovery, rollback-test, or evaluation-score guarantee.

## Official sources

- [Render Free instances](https://render.com/docs/free)
- [Render deploys and ephemeral filesystem](https://render.com/docs/deploys#ephemeral-filesystem)
- [Render persistent disks](https://render.com/docs/disks)
- [Render rollbacks](https://render.com/docs/rollbacks)
