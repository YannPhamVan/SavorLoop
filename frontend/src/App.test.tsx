import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import App from "./App";

const suggestion = {
  title: "Spinach rice bowl",
  ingredients: [{ name: "Spinach", quantity: 100, unit: "g" }],
  steps: ["Cook the rice.", "Wilt the spinach."],
  preparation_time_minutes: 20,
  substitutions: ["Use lime instead of lemon."],
  servings: 2,
  missing_ingredients: [],
  stock_explanation: "Uses the spinach in your inventory.",
};

interface AttemptPayload {
  attempt_date: string;
  rating: number;
  comments: string;
  changes: string[];
  substitutions: string[];
  liked_adjustments: string[];
}

const originalFetch = globalThis.fetch;
let fetchMock: Mock<typeof fetch>;

function jsonResponse(body: unknown): Response {
  return { ok: true, json: async () => body } as Response;
}

function callsTo(url: string, method = "GET") {
  return fetchMock.mock.calls.filter(
    ([input, init]) => String(input) === url && (init?.method ?? "GET") === method,
  );
}

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>();
  globalThis.fetch = fetchMock;
});

afterEach(() => {
  cleanup();
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("ephemeral demo notice", () => {
  it("warns that demo inventory data is temporary", async () => {
    fetchMock.mockImplementation(async (input) => {
      if (String(input) === "/api/inventory") return jsonResponse([]);
      throw new Error(`Unexpected fetch: ${String(input)}`);
    });

    render(<App ephemeralDemo />);

    expect(await screen.findByText(/Disposable educational demo:/)).toBeTruthy();
    expect(screen.getByText(/spins down, restarts, or redeploys/)).toBeTruthy();
    expect(screen.getByText(/Use fabricated data only/)).toBeTruthy();
  });
});

describe("natural-language inventory update", () => {
  it("shows a successful result and propagates browser trace context", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/inventory" && method === "GET") return jsonResponse([]);
      if (url === "/api/inventory/natural-language" && method === "POST") {
        return jsonResponse({ status: "updated", message: "Inventory updated.", updated_count: 1 });
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Describe the stock change"), {
      target: { value: "Mark fabricated basil unavailable" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update stock" }));

    expect(await screen.findByText("Inventory updated.")).toBeTruthy();
    const request = callsTo("/api/inventory/natural-language", "POST")[0][1];
    const headers = request?.headers as Record<string, string>;
    expect(headers.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });

  it("shows an AI-validation failure without reporting a successful update", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/inventory" && method === "GET") return jsonResponse([]);
      if (url === "/api/inventory/natural-language" && method === "POST") {
        return {
          ok: false,
          json: async () => ({
            detail: "I couldn't safely interpret that request. Restate it with an item name and a supported change.",
          }),
        } as Response;
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Describe the stock change"), {
      target: { value: "Use a fabricated item" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update stock" }));

    expect((await screen.findByRole("alert")).textContent).toContain("couldn't safely interpret");
    expect(screen.queryByText("Inventory updated.")).toBeNull();
    const headers = callsTo("/api/inventory/natural-language", "POST")[0][1]?.headers as Record<string, string>;
    expect(headers.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });
});

describe("Cooking Notebook UI", () => {
  it("keeps a suggestion out of the notebook until confirmation and submits only selected liked adjustments", async () => {
    let savedNotebook: Array<{
      id: number;
      recipe: typeof suggestion;
      attempts: Array<AttemptPayload & { id: number }>;
    }> = [];

    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/inventory" && method === "GET") return jsonResponse([]);
      if (url === "/api/suggestions" && method === "POST") return jsonResponse(suggestion);
      if (url === "/api/notebook" && method === "GET") return jsonResponse(savedNotebook);
      if (url === "/api/notebook" && method === "POST") {
        const payload = JSON.parse(String(init?.body)) as { recipe: typeof suggestion; attempt: AttemptPayload };
        savedNotebook = [{ id: 41, recipe: payload.recipe, attempts: [{ ...payload.attempt, id: 1 }] }];
        return jsonResponse(savedNotebook[0]);
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });

    render(<App />);
    await screen.findByText("A fresh start.");
    fireEvent.click(screen.getByRole("button", { name: "Suggestions" }));
    fireEvent.click(screen.getByRole("button", { name: /Suggest a recipe/ }));

    await screen.findByRole("heading", { name: "Spinach rice bowl" });
    expect(callsTo("/api/notebook", "POST")).toHaveLength(0);

    fireEvent.change(screen.getByLabelText("Comments"), { target: { value: "Bright and quick." } });
    fireEvent.change(screen.getByLabelText(/Changes you made/), { target: { value: "Sesame crunch" } });
    fireEvent.change(screen.getByLabelText(/Substitutions used/), { target: { value: "Use lime instead of lemon." } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Sesame crunch" }));

    fireEvent.click(screen.getByRole("button", { name: /Confirm cooked/ }));

    await screen.findByText("Bright and quick.");
    expect(callsTo("/api/notebook", "POST")).toHaveLength(1);
    const submitted = JSON.parse(String(callsTo("/api/notebook", "POST")[0][1]?.body)) as {
      recipe: typeof suggestion;
      attempt: AttemptPayload;
    };
    expect(submitted.attempt.changes).toEqual(["Sesame crunch"]);
    expect(submitted.attempt.substitutions).toEqual(["Use lime instead of lemon."]);
    expect(submitted.attempt.liked_adjustments).toEqual(["Sesame crunch"]);
    expect(screen.getByRole("heading", { name: /Attempt history/ })).toBeTruthy();
  });

  it("appends a second attempt while preserving the first attempt and its feedback", async () => {
    const firstAttempt: AttemptPayload & { id: number } = {
      id: 1,
      attempt_date: "2026-10-18",
      rating: 4,
      comments: "First attempt stayed crisp.",
      changes: ["Added sesame"],
      substitutions: ["Used lime"],
      liked_adjustments: ["Added sesame"],
    };
    let savedNotebook: Array<{
      id: number;
      recipe: typeof suggestion;
      attempts: Array<AttemptPayload & { id: number }>;
    }> = [{ id: 7, recipe: suggestion, attempts: [firstAttempt] }];

    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url === "/api/inventory" && method === "GET") return jsonResponse([]);
      if (url === "/api/notebook" && method === "GET") return jsonResponse(savedNotebook);
      if (url === "/api/notebook/7/attempts" && method === "POST") {
        const payload = JSON.parse(String(init?.body)) as AttemptPayload;
        savedNotebook = [{ ...savedNotebook[0], attempts: [...savedNotebook[0].attempts, { ...payload, id: 2 }] }];
        return jsonResponse(savedNotebook[0]);
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Notebook" }));
    await screen.findByText("First attempt stayed crisp.");
    fireEvent.click(screen.getByRole("button", { name: "Add attempt" }));
    fireEvent.change(screen.getByLabelText("Comments"), { target: { value: "Second attempt was softer." } });
    fireEvent.change(screen.getByLabelText(/Changes you made/), { target: { value: "Lower heat\nAdded lemon" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Lower heat" }));
    fireEvent.click(screen.getByRole("button", { name: "Save attempt" }));

    await screen.findByText("Second attempt was softer.");
    expect(screen.getByText("First attempt stayed crisp.")).toBeTruthy();
    expect(screen.getByText("Added sesame", { selector: ".liked-record" })).toBeTruthy();
    expect(screen.getByText("Attempt 1")).toBeTruthy();
    expect(screen.getByText("Attempt 2")).toBeTruthy();
    expect(callsTo("/api/notebook/7/attempts", "POST")).toHaveLength(1);
    const submitted = JSON.parse(String(callsTo("/api/notebook/7/attempts", "POST")[0][1]?.body)) as AttemptPayload;
    expect(submitted.liked_adjustments).toEqual(["Lower heat"]);
    await waitFor(() => expect(screen.queryByRole("button", { name: "Save attempt" })).toBeNull());
  });
});