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