import {
  context,
  propagation,
  SpanKind,
  SpanStatusCode,
  trace,
  type Tracer,
} from "@opentelemetry/api";
import { W3CTraceContextPropagator } from "@opentelemetry/core";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { BatchSpanProcessor, TracerProvider } from "@opentelemetry/sdk-trace";

const traceEndpoint = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;
const provider = new TracerProvider({
  resource: resourceFromAttributes({
    "service.name": "savorloop-browser",
    "service.version": import.meta.env.VITE_SAVORLOOP_VERSION || "local",
    "deployment.environment.name": import.meta.env.VITE_SAVORLOOP_ENVIRONMENT || "development",
  }),
  spanProcessors: traceEndpoint
    ? [
        new BatchSpanProcessor({
          exporter: new OTLPTraceExporter({ url: traceEndpoint }),
        }),
      ]
    : [],
});

trace.setGlobalTracerProvider(provider);
propagation.setGlobalPropagator(new W3CTraceContextPropagator());

export function createInventoryUpdateSender(tracer: Tracer) {
  return async (text: string, fetcher: typeof fetch = fetch): Promise<Response> => {
    const span = tracer.startSpan(
      "inventory.update.browser_request",
      { kind: SpanKind.CLIENT, attributes: { "operation.name": "inventory_update" } },
    );
    const requestContext = trace.setSpan(context.active(), span);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    propagation.inject(requestContext, headers);

    try {
      const response = await fetcher("/api/inventory/natural-language", {
        method: "POST",
        headers,
        body: JSON.stringify({ text }),
      });
      span.setAttribute("http.response.status_code", response.status);
      if (!response.ok) span.setStatus({ code: SpanStatusCode.ERROR });
      return response;
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR });
      throw error;
    } finally {
      span.end();
    }
  };
}

export const fetchInventoryUpdate = createInventoryUpdateSender(
  trace.getTracer("savorloop.inventory"),
);
