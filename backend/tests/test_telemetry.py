from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import main
from backend.app.database import create_database_engine
from backend.app.models import Ingredient
from backend.app.telemetry import Telemetry, telemetry_resource

FABRICATED_TRACE_ID = "1234567890abcdef1234567890abcdef"
FABRICATED_SPAN_ID = "1234567890abcdef"
PRIVATE_MARKERS = (
    "PRIVATE_PROMPT_MARKER",
    "PRIVATE_INGREDIENT_MARKER",
    "PRIVATE_QUANTITY_MARKER",
    "PRIVATE_MODEL_OUTPUT_MARKER",
    "PRIVATE_DATABASE_MARKER",
    "PRIVATE_CREDENTIAL_MARKER",
)


class StubInventoryInterpreter:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)

    def interpret(self, text: str, correction: str | None = None) -> object:
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def instrumented_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, Telemetry]]:
    test_engine = create_database_engine(f"sqlite:///{tmp_path / 'telemetry.db'}")
    span_exporter = InMemorySpanExporter()
    log_exporter = InMemoryLogRecordExporter()
    metric_reader = InMemoryMetricReader()
    telemetry = Telemetry(
        resource=telemetry_resource(
            service_name="savorloop-api",
            service_version="test-build",
            environment="test",
        ),
        span_exporter=span_exporter,
        log_exporter=log_exporter,
        metric_reader=metric_reader,
    )
    telemetry.span_exporter = span_exporter
    telemetry.log_exporter = log_exporter
    telemetry.metric_reader = metric_reader
    previous_telemetry = main.app.state.telemetry
    monkeypatch.setattr(main, "engine", test_engine)
    main.app.state.telemetry = telemetry

    try:
        with TestClient(main.app) as client:
            yield client, telemetry
    finally:
        main.app.dependency_overrides.clear()
        main.app.state.telemetry = previous_telemetry
        telemetry.shutdown()
        test_engine.dispose()


def create_fabricated_ingredients(client: TestClient) -> None:
    response = client.post(
        "/api/inventory",
        json={
            "category": "pantry_staple",
            "name": f"{PRIVATE_MARKERS[1]}_{PRIVATE_MARKERS[4]}",
            "available": True,
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/api/inventory",
        json={
            "category": "rotating",
            "name": "Fabricated quantity test",
            "quantity": 250,
            "unit": PRIVATE_MARKERS[2],
        },
    )
    assert response.status_code == 201


def send_update(client: TestClient, text: str) -> object:
    return client.post(
        "/api/inventory/natural-language",
        json={"text": text},
        headers={
            "traceparent": f"00-{FABRICATED_TRACE_ID}-{FABRICATED_SPAN_ID}-01",
        },
    )


def get_metric_points(telemetry: Telemetry) -> dict[str, list[object]]:
    data = telemetry.metric_reader.get_metrics_data()
    assert data is not None
    points: dict[str, list[object]] = {}
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                points[metric.name] = list(metric.data.data_points)
    return points


def assert_no_private_markers(value: object, markers: tuple[str, ...]) -> None:
    serialized = repr(value)
    assert all(marker not in serialized for marker in markers)


def finished_spans(telemetry: Telemetry) -> list[object]:
    assert isinstance(telemetry.span_exporter, InMemorySpanExporter)
    return telemetry.span_exporter.get_finished_spans()


def finished_logs(telemetry: Telemetry) -> list[object]:
    assert isinstance(telemetry.log_exporter, InMemoryLogRecordExporter)
    return telemetry.log_exporter.get_finished_logs()


def test_successful_request_exports_correlated_private_spans_logs_and_metrics(
    instrumented_client: tuple[TestClient, Telemetry],
) -> None:
    client, telemetry = instrumented_client
    create_fabricated_ingredients(client)
    client.app.dependency_overrides[main.get_inventory_interpreter] = lambda: StubInventoryInterpreter(
        {
            "operations": [
                {
                    "action": "set_unavailable",
                    "ingredient": f"{PRIVATE_MARKERS[1]}_{PRIVATE_MARKERS[4]}",
                }
            ]
        }
    )

    response = send_update(
        client,
        f"{PRIVATE_MARKERS[0]} update {PRIVATE_MARKERS[1]} by 250 {PRIVATE_MARKERS[2]}",
    )

    assert response.status_code == 200
    with Session(main.engine) as session:
        ingredient = session.scalar(select(Ingredient))
        assert ingredient is not None
        assert ingredient.available is False

    telemetry.tracer_provider.force_flush()
    telemetry.logger_provider.force_flush()
    exported_spans = finished_spans(telemetry)
    span_names = {span.name for span in exported_spans}
    assert {
        "inventory.request",
        "inventory.update.provider",
        "inventory.update.validation",
        "inventory.update.database.write",
        "inventory.response",
    }.issubset(span_names)
    assert {span.context.trace_id for span in exported_spans} == {int(FABRICATED_TRACE_ID, 16)}
    assert all(
        span.resource.attributes["service.name"] == "savorloop-api"
        and span.resource.attributes["service.version"] == "test-build"
        and span.resource.attributes["deployment.environment.name"] == "test"
        for span in exported_spans
    )

    logs = finished_logs(telemetry)
    assert len(logs) == 1
    log = logs[0].log_record
    assert log.attributes["trace_id"] == FABRICATED_TRACE_ID
    assert log.attributes["operation.name"] == "inventory_update"
    assert log.attributes["status"] == "success"
    assert isinstance(log.attributes["duration_ms"], float)
    assert log.attributes["duration_ms"] >= 0
    assert "error.category" not in log.attributes
    assert_no_private_markers(
        (
            [
                (
                    span.name,
                    span.attributes,
                    span.resource.attributes,
                    [(event.name, event.attributes) for event in span.events],
                    span.status.description,
                )
                for span in exported_spans
            ],
            [(item.log_record.body, item.log_record.attributes, item.resource.attributes) for item in logs],
            get_metric_points(telemetry),
        ),
        PRIVATE_MARKERS,
    )

    points = get_metric_points(telemetry)
    assert points["savorloop.inventory_update.requests"][0].value == 1
    assert points["savorloop.inventory_update.duration"][0].count == 1
    assert "savorloop.inventory_update.errors" not in points
    assert all(
        set(point.attributes) <= {"operation", "status"}
        and "trace_id" not in point.attributes
        for metric_points in points.values()
        for point in metric_points
    )


def test_ai_validation_failure_has_no_write_span_or_database_change(
    instrumented_client: tuple[TestClient, Telemetry],
) -> None:
    client, telemetry = instrumented_client
    create_fabricated_ingredients(client)
    invalid_output = {
        "operations": [
            {
                "action": "consume",
                "ingredient": f"{PRIVATE_MARKERS[1]}_{PRIVATE_MARKERS[4]}",
                "amount": 500,
                "unit": PRIVATE_MARKERS[2],
            }
        ]
    }
    client.app.dependency_overrides[main.get_inventory_interpreter] = lambda: StubInventoryInterpreter(
        invalid_output,
        {
            **invalid_output,
            "private_model_output": PRIVATE_MARKERS[3],
            PRIVATE_MARKERS[5]: "fabricated",
        },
    )

    response = send_update(client, f"{PRIVATE_MARKERS[0]} {PRIVATE_MARKERS[4]} {PRIVATE_MARKERS[5]}")

    assert response.status_code == 422
    with Session(main.engine) as session:
        ingredient = session.scalar(select(Ingredient))
        assert ingredient is not None
        assert ingredient.available is True
        assert ingredient.name == f"{PRIVATE_MARKERS[1]}_{PRIVATE_MARKERS[4]}"

    telemetry.tracer_provider.force_flush()
    telemetry.logger_provider.force_flush()
    exported_spans = finished_spans(telemetry)
    span_names = {span.name for span in exported_spans}
    assert "inventory.update.provider" in span_names
    assert "inventory.update.validation" in span_names
    assert "inventory.response" in span_names
    assert "inventory.update.database.write" not in span_names
    assert {span.context.trace_id for span in exported_spans} == {int(FABRICATED_TRACE_ID, 16)}

    logs = finished_logs(telemetry)
    assert len(logs) == 1
    log = logs[0].log_record
    assert log.attributes["trace_id"] == FABRICATED_TRACE_ID
    assert log.attributes["operation.name"] == "inventory_update"
    assert log.attributes["status"] == "error"
    assert isinstance(log.attributes["duration_ms"], float)
    assert log.attributes["duration_ms"] >= 0
    assert log.attributes["error.category"] == "ai_validation"
    assert_no_private_markers(
        (
            [
                (
                    span.name,
                    span.attributes,
                    span.resource.attributes,
                    [(event.name, event.attributes) for event in span.events],
                    span.status.description,
                )
                for span in exported_spans
            ],
            [(item.log_record.body, item.log_record.attributes, item.resource.attributes) for item in logs],
            get_metric_points(telemetry),
        ),
        PRIVATE_MARKERS,
    )

    points = get_metric_points(telemetry)
    assert points["savorloop.inventory_update.requests"][0].value == 1
    assert points["savorloop.inventory_update.errors"][0].value == 1
    assert points["savorloop.inventory_update.ai_validation_failures"][0].value == 1
    assert all(
        set(point.attributes) <= {"operation", "status"}
        and "trace_id" not in point.attributes
        for metric_points in points.values()
        for point in metric_points
    )
