import { describe, expect, it } from "vitest";
import { resourceFromAttributes } from "@opentelemetry/resources";
import {
  InMemorySpanExporter,
  SimpleSpanProcessor,
  TracerProvider,
} from "@opentelemetry/sdk-trace";
import { createInventoryUpdateSender } from "./telemetry";

describe("browser inventory update telemetry", () => {
  it("exports a safe browser span and propagates its context to the request", async () => {
    const exporter = new InMemorySpanExporter();
    const provider = new TracerProvider({
      resource: resourceFromAttributes({
        "service.name": "savorloop-browser",
        "service.version": "fabricated-build",
        "deployment.environment.name": "test",
      }),
      spanProcessors: [new SimpleSpanProcessor({ exporter })],
    });
    const sent: RequestInit[] = [];
    const sender = createInventoryUpdateSender(provider.getTracer("savorloop.test"));

    await sender("PRIVATE_PROMPT_MARKER", async (_input, init) => {
      sent.push(init ?? {});
      return { ok: true, status: 200 } as Response;
    });

    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    expect(spans[0].name).toBe("inventory.update.browser_request");
    expect(spans[0].attributes).toEqual({
      "operation.name": "inventory_update",
      "http.response.status_code": 200,
    });
    expect(spans[0].resource.attributes).toMatchObject({
      "service.name": "savorloop-browser",
      "service.version": "fabricated-build",
      "deployment.environment.name": "test",
    });

    const headers = sent[0].headers as Record<string, string>;
    const match = headers.traceparent.match(/^00-([0-9a-f]{32})-([0-9a-f]{16})-01$/);
    expect(match).not.toBeNull();
    expect(match?.[1]).toBe(spans[0].spanContext().traceId);
    expect(match?.[2]).toBe(spans[0].spanContext().spanId);
    expect(
      JSON.stringify(
        spans.map((span) => ({
          name: span.name,
          attributes: span.attributes,
          resource: span.resource.attributes,
        })),
      ),
    ).not.toContain("PRIVATE_PROMPT_MARKER");

    await provider.shutdown();
  });
});
