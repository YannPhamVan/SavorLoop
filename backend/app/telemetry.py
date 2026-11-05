from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogRecordExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.util.types import Attributes

SERVICE_NAME = "savorloop-api"
SERVICE_VERSION = "0.1.0"
ENVIRONMENT = "development"
OPERATION = "inventory_update"


def _signal_endpoint(endpoint: str, signal: str) -> str:
    return f"{endpoint.rstrip('/')}/v1/{signal}"


def telemetry_resource(
    *,
    service_name: str = SERVICE_NAME,
    service_version: str | None = None,
    environment: str | None = None,
) -> Resource:
    deployed_version = (
        service_version
        or os.environ.get("SAVORLOOP_VERSION")
        or os.environ.get("RENDER_GIT_COMMIT")
        or SERVICE_VERSION
    )
    deployed_environment = (
        environment or os.environ.get("SAVORLOOP_ENVIRONMENT") or ENVIRONMENT
    )
    return Resource.create(
        {
            "service.name": service_name,
            "service.version": deployed_version,
            "deployment.environment.name": deployed_environment,
        }
    )


class Telemetry:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        resource: Resource | None = None,
        span_exporter: SpanExporter | None = None,
        log_exporter: LogRecordExporter | None = None,
        metric_reader: MetricReader | None = None,
    ) -> None:
        self.resource = resource or telemetry_resource()
        endpoint = endpoint or None
        self.span_exporter = span_exporter
        self.log_exporter = log_exporter
        self.metric_reader = metric_reader

        self.tracer_provider = TracerProvider(resource=self.resource)
        if span_exporter is not None:
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor

            self.tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
        elif endpoint:
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=_signal_endpoint(endpoint, "traces"))
                )
            )
        self.tracer = self.tracer_provider.get_tracer("savorloop.inventory")

        if metric_reader is not None:
            readers = [metric_reader]
        elif endpoint:
            readers = [
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=_signal_endpoint(endpoint, "metrics")),
                    export_interval_millis=int(os.environ.get("OTEL_METRIC_EXPORT_INTERVAL_MS", "5000")),
                )
            ]
        else:
            readers = []
        self.meter_provider = MeterProvider(resource=self.resource, metric_readers=readers)
        meter = self.meter_provider.get_meter("savorloop.inventory")
        self.requests = meter.create_counter(
            "savorloop.inventory_update.requests",
            unit="1",
            description="Natural-language inventory update requests",
        )
        self.errors = meter.create_counter(
            "savorloop.inventory_update.errors",
            unit="1",
            description="Failed natural-language inventory update requests",
        )
        self.ai_validation_failures = meter.create_counter(
            "savorloop.inventory_update.ai_validation_failures",
            unit="1",
            description="Inventory update plans rejected after the bounded AI correction",
        )
        self.duration = meter.create_histogram(
            "savorloop.inventory_update.duration",
            unit="s",
            description="Natural-language inventory update request duration",
            explicit_bucket_boundaries_advisory=[
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1,
                2.5,
                5,
                10,
                30,
                60,
            ],
        )

        self.logger_provider = LoggerProvider(resource=self.resource)
        if log_exporter is not None:
            self.logger_provider.add_log_record_processor(
                self._simple_log_processor(log_exporter)
            )
        elif endpoint:
            self.logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(
                    OTLPLogExporter(endpoint=_signal_endpoint(endpoint, "logs"))
                )
            )
        self.logger = self.logger_provider.get_logger("savorloop.inventory")

    @staticmethod
    def _simple_log_processor(exporter: LogRecordExporter) -> Any:
        from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

        return SimpleLogRecordProcessor(exporter)

    def record_inventory_update(
        self,
        *,
        status: str,
        duration_seconds: float,
        error_category: str | None = None,
    ) -> None:
        attributes: Attributes = {"operation": OPERATION, "status": status}
        self.requests.add(1, attributes)
        self.duration.record(duration_seconds, attributes)

        if status == "error":
            self.errors.add(1, attributes)
        if error_category == "ai_validation":
            self.ai_validation_failures.add(1, {"operation": OPERATION})

        span_context = trace.get_current_span().get_span_context()
        log_attributes: dict[str, Any] = {
            "operation.name": OPERATION,
            "status": status,
            "duration_ms": round(duration_seconds * 1000, 3),
            "trace_id": f"{span_context.trace_id:032x}",
        }
        if error_category:
            log_attributes["error.category"] = error_category
        self.logger.emit(
            body="inventory_update",
            attributes=log_attributes,
            severity_text="ERROR" if status == "error" else "INFO",
        )

    def shutdown(self) -> None:
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()
        self.logger_provider.shutdown()


def configured_telemetry() -> Telemetry:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    return Telemetry(endpoint=endpoint)
