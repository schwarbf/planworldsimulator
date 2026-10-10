import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { api, type World, type WorldEvent } from "../api/client";
import { WorldDetail } from "./WorldDetail";

class Stream extends EventTarget {
  static all: Stream[] = [];
  closed = false;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) {
    super();
    Stream.all.push(this);
  }
  close() {
    this.closed = true;
  }
  emit(name: string, data: unknown) {
    this.dispatchEvent(new MessageEvent(name, { data: JSON.stringify(data) }));
  }
}
function world(overrides: Partial<World> = {}): World {
  return {
    id: "factory",
    title: "Factory",
    prompt: "A factory",
    seed: 42,
    levels: [1, 2, 3],
    status: "generating",
    generation_attempt: 1,
    storyline: null,
    path: null,
    duplicate_of: null,
    running: false,
    port: null,
    featured: false,
    play_count: 0,
    mine: true,
    has_thumbnail: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}
function event(
  id: number,
  step: string,
  state: WorldEvent["state"],
  attempt = 1,
): WorldEvent {
  return {
    id,
    step,
    state,
    attempt,
    message: `${step} ${state}`,
    elapsed_seconds: id,
    created_at: new Date().toISOString(),
  };
}
function mount() {
  render(
    <MemoryRouter initialEntries={["/worlds/factory"]}>
      <Routes>
        <Route path="/worlds/:id" element={<WorldDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  Stream.all = [];
  vi.stubGlobal("EventSource", Stream);
  vi.spyOn(api, "getWorld").mockResolvedValue(world());
  vi.spyOn(api, "listEvents").mockResolvedValue([]);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("restores actual branch progress and deduplicates replay", async () => {
  vi.mocked(api.listEvents).mockResolvedValue([event(1, "sim", "done")]);
  mount();
  await screen.findByText("sim done");
  expect(screen.getByText("Simulator")).toBeInTheDocument();
  expect(screen.getByText("World view")).toBeInTheDocument();
  act(() => Stream.all[0].emit("step", event(1, "sim", "done")));
  expect(screen.getAllByText("sim done")).toHaveLength(1);
  act(() => Stream.all[0].emit("step", event(2, "ui", "started")));
  expect(screen.getByText("ui started")).toBeInTheDocument();
});
test("loads storyline on design completion and play links on completion", async () => {
  mount();
  await waitFor(() => expect(Stream.all).toHaveLength(1));
  vi.mocked(api.getWorld).mockResolvedValue(
    world({ storyline: "Run the factory." }),
  );
  act(() => Stream.all[0].emit("step", event(1, "design", "done")));
  await screen.findByText("Run the factory.");
  vi.mocked(api.getWorld).mockResolvedValue(world({ status: "ready" }));
  act(() => Stream.all[0].emit("done", { status: "ready" }));
  await screen.findByText("Play this world");
  expect(Stream.all[0].closed).toBe(true);
});
test("retry starts a new stream and clears previous failure", async () => {
  vi.mocked(api.getWorld).mockResolvedValue(world({ status: "failed" }));
  vi.mocked(api.listEvents).mockResolvedValue([event(1, "error", "failed")]);
  vi.spyOn(api, "retryWorld").mockResolvedValue(
    world({ status: "queued", generation_attempt: 2 }),
  );
  mount();
  await screen.findByText("error failed");
  act(() => Stream.all[0].emit("done", { status: "failed" }));
  await waitFor(() => expect(Stream.all[0].closed).toBe(true));
  vi.mocked(api.listEvents).mockResolvedValue([event(2, "sim", "started", 2)]);
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(Stream.all.at(-1)?.url).toContain("attempt=2"));
  await screen.findByText("sim started");
  expect(screen.queryByText("error failed")).not.toBeInTheDocument();
});
test("shows reconnect and retry errors", async () => {
  vi.mocked(api.getWorld).mockResolvedValue(world({ status: "failed" }));
  vi.spyOn(api, "retryWorld").mockRejectedValue(new Error("Capacity reached"));
  mount();
  await waitFor(() => expect(Stream.all).toHaveLength(1));
  act(() => Stream.all[0].onerror?.());
  expect(screen.getByText(/Reconnecting/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("Capacity reached");
  expect(screen.getByText("Factory")).toBeInTheDocument();
});
