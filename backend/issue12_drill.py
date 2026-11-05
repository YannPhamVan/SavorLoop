import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = "http://127.0.0.1:18012"
SYNTHETIC_INGREDIENT = "Issue 12 Synthetic Basil"
ALLOWED_TOOLS = [
    "read_redacted_readiness",
    "reset_stale_connection_pool",
    "verify_readiness",
]


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict | None]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    outgoing = Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urlopen(outgoing, timeout=5) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except HTTPError as error:
        body = error.read()
        decoded = json.loads(body) if body else None
        return error.code, decoded
    except URLError as error:
        raise RuntimeError("The isolated local Docker drill API is unavailable") from error


def require_status(status: int, expected: int, operation: str) -> None:
    if status != expected:
        raise RuntimeError(f"{operation} returned HTTP {status}; expected {expected}")


def main() -> None:
    require_status(request("GET", "/ready")[0], 200, "Initial readiness")
    created_status, created = request(
        "POST",
        "/api/inventory",
        {
            "category": "pantry_staple",
            "name": SYNTHETIC_INGREDIENT,
            "available": True,
        },
    )
    require_status(created_status, 201, "Synthetic fixture creation")
    ingredient_id = created["id"]

    try:
        _, inventory_before = request("GET", "/api/inventory")
        _, notebook_before = request("GET", "/api/notebook")
        require_status(
            request("POST", "/internal/ops/test/arm-stale-readiness-failure")[0],
            200,
            "Controlled stale-pool fault injection",
        )
        require_status(request("GET", "/ready")[0], 503, "Controlled readiness failure")

        alert_id = f"issue12-{uuid4()}"
        alert_status, incident = request(
            "POST",
            "/internal/ops/test/alert",
            {
                "alert_id": alert_id,
                "alert_name": "stale_sqlalchemy_connection_pool",
                "status": "firing",
            },
        )
        require_status(alert_status, 200, "Test alert delivery")
        events = incident["events"]
        event_names = [event["event"] for event in events]
        remediation_calls = [
            event for event in events if event["event"] == "remediation.invoked"
        ]
        if incident["outcome"] != "recovered":
            raise RuntimeError("The agent did not verify recovery; the incident is unresolved")
        if event_names[0:2] != ["alert.received", "agent.invoked"]:
            raise RuntimeError("The alert did not produce observable agent invocation")
        if len(remediation_calls) != 1:
            raise RuntimeError("The agent did not invoke exactly one remediation")
        if remediation_calls[0]["tool"] != "reset_stale_connection_pool":
            raise RuntimeError("The agent invoked an unapproved remediation")
        if events[1]["tool_allowlist"] != ALLOWED_TOOLS:
            raise RuntimeError("The agent tool allowlist differs from the approved set")
        if any(event["alert_id"] != alert_id for event in events):
            raise RuntimeError("Alert and agent events are not correlated")
        if len({event["incident_id"] for event in events}) != 1:
            raise RuntimeError("Agent events do not share an incident correlation ID")

        require_status(request("GET", "/ready")[0], 200, "Post-agent readiness check")
        _, inventory_after = request("GET", "/api/inventory")
        _, notebook_after = request("GET", "/api/notebook")
        if inventory_after != inventory_before or notebook_after != notebook_before:
            raise RuntimeError("The incident response changed inventory or notebook data")

        print(
            json.dumps(
                {
                    "failure_status": 503,
                    "alert_id": alert_id,
                    "outcome": incident["outcome"],
                    "agent_event_sequence": event_names,
                    "events": events,
                    "remediation_count": len(remediation_calls),
                    "post_agent_readiness": "ready",
                    "synthetic_inventory_preserved": True,
                    "notebook_preserved": True,
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        request("DELETE", f"/api/inventory/{ingredient_id}")


if __name__ == "__main__":
    main()
