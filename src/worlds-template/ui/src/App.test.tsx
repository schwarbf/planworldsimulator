// [base] Renders the world with its mock state (no server) and honours ?level=N.
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "./App";
import { mockState } from "./World";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset().mockRejectedValue(new Error("no server"));
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(console, "info").mockImplementation(() => {});
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

test("renders the world view and controls from the mock state", () => {
  const { container } = render(<App />);
  expect(container.querySelector("svg")).not.toBeNull();
  expect(screen.getAllByText(new RegExp(mockState.world.name)).length).toBeGreaterThan(0);
});

test("?level=2 resets the world to level 2, using a relative URL", () => {
  window.history.replaceState({}, "", "/?level=2");
  render(<App />);
  const call = fetchMock.mock.calls.find(([url]) => url === "api/reset");
  expect(call).toBeDefined();
  expect(JSON.parse(call![1].body)).toEqual({ level: 2 });
});

test("no ?level means no reset", () => {
  render(<App />);
  expect(fetchMock.mock.calls.some(([url]) => url === "api/reset")).toBe(false);
});
