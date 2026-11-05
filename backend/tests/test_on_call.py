import json
import logging
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.database import create_database_engine
from backend.app.on_call import ON_CALL_TOOL_ALLOWLIST

SYNTHETIC_INGREDIENT = "Issue 12 Synthetic Basil"


@pytest.fixture
def client(monkeypatch) -> Iterator[TestClient]:
    database_path = Path(__file__).with_name(f"issue12-{uuid.uuid4()}.db")
    test_engine = create_database_engine(f"sqlite:///{database_path}")
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setenv("SAVORLOOP_ON_CALL_TEST_MODE", "1")
    main.app.state.on_call_fault_armed = False
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        test_engine.dispose()
        for path in (database_path, Path(f"{database_path}-shm"), Path(f"{database_path}-wal")):
            path.unlink(missing_ok=True)


def test_stale_pool_alert_invokes_one_reset_and_verifies_recovery(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="savorloop.on_call")
    created = client.post(
        "/api/inventory",
        json={
            "category": "pantry_staple",
            "name": SYNTHETIC_INGREDIENT,
            "available": True,
        },
    )
    assert created.status_code == 201
    inventory_before = client.get("/api/inventory").json()
    notebook_before = client.get("/api/notebook").json()

    armed = client.post("/internal/ops/test/arm-stale-readiness-failure")
    assert armed.status_code == 200
    failed_readiness = client.get("/ready")
    assert failed_readiness.status_code == 503

    response = client.post(
        "/internal/ops/test/alert",
        json={
            "alert_id": "issue12-synthetic-alert",
            "alert_name": "stale_sqlalchemy_connection_pool",
            "status": "firing",
        },
    )
    assert response.status_code == 200
    incident = response.json()
    events = incident["events"]

    assert incident["outcome"] == "recovered"
    assert [event["event"] for event in events] == [
        "alert.received",
        "agent.invoked",
        "diagnosis.completed",
        "remediation.invoked",
        "remediation.completed",
        "readiness.verified",
        "incident.completed",
    ]
    assert {event["alert_id"] for event in events} == {"issue12-synthetic-alert"}
    assert len({event["incident_id"] for event in events}) == 1
    assert events[2]["diagnosis"] == "stale_sqlalchemy_connection_pool"
    assert events[2]["error_category"] == "database_unavailable"
    assert events[1]["tool_allowlist"] == list(ON_CALL_TOOL_ALLOWLIST)
    assert [event["tool"] for event in events if event["event"] == "remediation.invoked"] == [
        "reset_stale_connection_pool"
    ]
    assert events[5]["readiness"] == "ready"
    assert client.get("/ready").status_code == 200
    assert client.get("/api/inventory").json() == inventory_before
    assert client.get("/api/notebook").json() == notebook_before
    assert SYNTHETIC_INGREDIENT not in caplog.text
    assert "synthetic stale pooled connection" not in caplog.text
    assert "issue12-synthetic-alert" in caplog.text
    assert "reset_stale_connection_pool" in caplog.text
    assert "database_unavailable" in caplog.text
    assert "recovered" in caplog.text
    assert SYNTHETIC_INGREDIENT not in json.dumps(incident)


def test_test_alert_does_not_remediate_when_readiness_is_already_available(
    client: TestClient,
) -> None:
    response = client.post(
        "/internal/ops/test/alert",
        json={
            "alert_id": "issue12-no-fault",
            "alert_name": "stale_sqlalchemy_connection_pool",
            "status": "firing",
        },
    )

    assert response.status_code == 200
    incident = response.json()
    assert incident["outcome"] == "unresolved"
    assert not any(event["event"] == "remediation.invoked" for event in incident["events"])
    assert incident["events"][-1]["outcome"] == "unresolved"


def test_test_alert_routes_are_disabled_outside_the_local_drill(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SAVORLOOP_ON_CALL_TEST_MODE")

    assert client.post("/internal/ops/test/arm-stale-readiness-failure").status_code == 404
    assert (
        client.post(
            "/internal/ops/test/alert",
            json={
                "alert_id": "issue12-disabled",
                "alert_name": "stale_sqlalchemy_connection_pool",
                "status": "firing",
            },
        ).status_code
        == 404
    )


def test_test_alert_payload_rejects_unallowlisted_fields(client: TestClient) -> None:
    response = client.post(
        "/internal/ops/test/alert",
        json={
            "alert_id": "issue12-extra-field",
            "alert_name": "stale_sqlalchemy_connection_pool",
            "status": "firing",
            "shell_command": "must not be accepted",
        },
    )

    assert response.status_code == 422
    assert not any(
        event["event"] == "remediation.invoked"
        for event in response.json().get("events", [])
    )
