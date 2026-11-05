# Issue 12 local on-call drill

This drill is restricted to a dedicated local Docker Compose project and its
named SQLite volume. It does not use Render, production services, credentials,
prompts, or real user data. The test-only fault and alert routes are unavailable
unless `SAVORLOOP_ON_CALL_TEST_MODE=1`; the drill Compose file is the only
checked-in configuration that enables them and publishes the API on loopback.

## Agent permissions

The on-call agent has exactly three fixed tools:

- `read_redacted_readiness` runs the fixed database readiness probe and returns
  only ready/unavailable plus a bounded error category.
- `reset_stale_connection_pool` calls SQLAlchemy `Engine.dispose()` without
  accepting arguments.
- `verify_readiness` repeats the fixed readiness probe after the remediation.

The agent has no shell or arbitrary SQL interface, inventory/notebook tools,
credentials, prompts, deployment configuration, or other remediation. The
test-only alert schema rejects extra fields. A failed verification produces an
`unresolved` outcome; the agent does not try a different fix or count a retry
as remediation.

## Run the isolated drill

From the repository root in PowerShell:

```powershell
docker compose -p savorloop-issue12 -f compose.issue12-drill.yaml up --build -d
uv run python backend\issue12_drill.py
docker compose -p savorloop-issue12 -f compose.issue12-drill.yaml down -v
```

The drill creates a fabricated pantry staple through the regular API before
injecting a readiness failure. The local monitor script observes the resulting
`503`, sends a fixed test alert to the disabled-by-default local receiver, and
checks the correlated agent events, post-reset readiness, and unchanged
inventory/notebook snapshots. Its output contains only synthetic identifiers
and redacted operation metadata. The final `down -v` removes only the
issue-12-specific container, network, and SQLite volume. The same structured
events are emitted to the backend container log and can be inspected with
`docker compose -p savorloop-issue12 -f compose.issue12-drill.yaml logs backend`.

Do not run the test-only endpoints on a hosted or production service. No hosted
alert provider or service was configured, contacted, or changed for this issue.

## Recorded result

The issue-12 Docker drill completed on 2026-11-05 with outcome `recovered`.
The isolated SQLite readiness probe returned `503`; test alert
`issue12-c1c244c4-9429-4ad2-82c7-827a2ba6dcc6` invoked incident
`ff7f0590-e92b-4ec4-a674-609f2ea3197d`. The redacted sequence was alert received
(2026-11-05T16:21:37.385795Z), agent invoked, diagnosis completed
(`database_unavailable`), exactly one
`reset_stale_connection_pool` invocation, readiness verified (`ready`), and
incident completed (`recovered`). The fabricated inventory snapshot was
unchanged and the notebook remained unchanged. The script removed its synthetic
ingredient after verification.

The selected fault is a deterministic synthetic stale-pool operation failure:
the test hook makes the existing pooled SQLite connection fail the fixed
`SELECT 1` readiness probe until that pool is disposed. A preliminary
closed-connection probe returned `503`, but an unremediated subsequent probe
returned `200` because SQLAlchemy automatically invalidated that connection.
That self-recovery was not counted as remediation or used as the drill result.
For the recorded drill, the agent's diagnostic still observed the selected
failure before its single explicit pool reset, and only the passing readiness
check after that reset counted as recovery.

Focused automated verification:

```powershell
uv run pytest backend\tests\test_on_call.py backend\tests\test_health.py -q
```
