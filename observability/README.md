# Local observability stack

This is one Compose project, separate from the application Compose file, with pinned versions of the OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana. The application exports only the natural-language inventory-update journey. The Collector applies an attribute allowlist before exporting signals. Traces and logs retain fixed operation/status metadata and the trace ID; metric dimensions are restricted to `operation` and `status`, and never include trace IDs, request text, ingredient data, prompts, model output, database values, or credentials.

The backend resource identifies `service.name`, `service.version`, and `deployment.environment.name`. The browser uses its own `service.name` and the matching build version/environment. Configure `SAVORLOOP_VERSION` and `SAVORLOOP_ENVIRONMENT` for local deployments; on Render the backend falls back to `RENDER_GIT_COMMIT` when configured. Version/environment resource attributes remain in traces and logs but are not converted into Prometheus labels.

## Start locally

From the repository root, copy the example and set a non-default Grafana password in the untracked local file. Do not commit or post that file or its values:

```powershell
Copy-Item observability\.env.example observability\.env
notepad observability\.env
docker compose --env-file observability\.env -f observability\compose.yaml --project-directory observability up -d
```

Set `GRAFANA_ADMIN_PASSWORD` in `observability\.env`; the default username is `admin`. The `.env` file is git-ignored. Grafana is available at `http://localhost:3000`, Prometheus at `http://localhost:9090`, and the Collector's OTLP/HTTP receiver at `http://127.0.0.1:4318`. Only Grafana and Prometheus have host-published ports, and they bind to loopback; Loki and Tempo are private to the Compose network.

To run the application Compose project with telemetry enabled, build the browser endpoint into the frontend and point the backend container at the host-published Collector. The demo interpreter is deterministic and is only for fabricated local requests:

```powershell
$env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://host.docker.internal:4318"
$env:VITE_OTEL_EXPORTER_OTLP_ENDPOINT = "http://127.0.0.1:4318/v1/traces"
$env:SAVORLOOP_ENVIRONMENT = "local"
$env:SAVORLOOP_VERSION = "local"
$env:SAVORLOOP_INVENTORY_INTERPRETER = "demo"
docker compose up --build -d
```

Add a fabricated pantry staple in the app, then submit a supported update such as `mark Demo basil unavailable`. Submit an unsupported fabricated request to exercise the deterministic validation error. Do not use real or sensitive inventory data. Allow the Collector batch processors and Prometheus scrape interval to run before inspecting the `SavorLoop natural-language inventory updates` Grafana dashboard. Use Grafana Explore with the Tempo and Loki datasources to inspect traces and correlated logs; the `trace_id` is a log field, not a metric label. Stop both Compose projects with `docker compose down` from the repository root and the observability directory respectively.

The Grafana dashboard includes request count, error count, AI-validation-failure count, request-duration quantiles, and request outcomes. Trace spans cover the browser request, backend request, provider boundary, structured-plan validation, deterministic database write, and response. A rejected plan does not enter the database-write span. The backend logs one structured operation record per inventory update; the frontend never exports request/response payloads.

## Privacy and host limits

Automated backend tests inspect fabricated success and AI-validation-failure signals, verify shared W3C trace context, confirm there is no database-write span or mutation on validation failure, and reject request, ingredient, quantity, model-output, database, and credential marker strings from span attributes, span events, logs, and metric attributes. The application does not record exception events in these spans, and the Collector fails closed if its allowlists cannot be applied and removes span-event attributes as defense in depth. The frontend test verifies the browser span's trace context is the context propagated to the backend request.

No hosted Render Blueprint is supplied or deployed. Render documents Free services as public web services; Free web services can send private-network requests but cannot receive them. A public Collector receiver needs authentication, but browser-exported OTLP cannot safely carry a backend secret, and CORS is not authentication. There is no approved secure browser-to-Collector relay in the existing application architecture. Exposing an unauthenticated receiver or silently adding a public proxy would violate the privacy boundary, so this implementation does not provision or resume the suspended Render service. A secure hosted path needs an owner-approved design for browser-span forwarding or private ingress that remains within the Free-only budget; paid private services are not used.

Render Free services also spin down, have ephemeral filesystems, and can lose telemetry on restart; that temporary loss is accepted by the owner but no hosted retention or runtime evidence is claimed here. The local Compose stack has named volumes for convenience only. These are not a hosted persistence guarantee.

Render evidence sources checked on 2026-11-05:

- [Render Free services](https://render.com/docs/free)
- [Render private networking](https://render.com/docs/private-network)
- [Render private services](https://render.com/docs/private-services)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
