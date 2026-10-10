import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import type { World, WorldPage } from "../api/client";
import { ExistingWorlds } from "./ExistingWorlds";

function world(overrides: Partial<World>): World {
  return {
    id: "w-1",
    title: "Bakery",
    prompt: "A bakery",
    seed: 7,
    levels: [1, 2, 3],
    status: "ready",
    storyline: "Plan the flour orders.",
    path: null,
    duplicate_of: null,
    running: false,
    port: null,
    featured: false,
    play_count: 0,
    mine: false,
    has_thumbnail: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function respondWith(page: (url: URL) => WorldPage) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = new URL(String(input), "http://localhost");
    return new Response(JSON.stringify(page(url)), { status: 200 });
  });
}

function renderWorlds() {
  render(
    <MemoryRouter>
      <ExistingWorlds />
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

test("every ready world can be played at each of its three levels", async () => {
  respondWith(() => ({
    items: [world({ id: "fission-ops", title: "Fission Ops", featured: true })],
    total: 1,
  }));
  renderWorlds();

  const group = await screen.findByRole("group", { name: "Play Fission Ops" });
  const links = within(group).getAllByRole("link");
  expect(links.map((l) => l.textContent)).toEqual(["Easy", "Medium", "Hard"]);
  expect(links[2]).toHaveAttribute("href", "/api/play/fission-ops/?level=3");
  expect(links[2]).toHaveAttribute("target", "_blank");
  expect(links[2]).toHaveAttribute("rel", expect.stringContaining("noopener"));
  expect(screen.getByText("Featured")).toBeInTheDocument();
});

test("worlds that are not ready can't be played, only followed", async () => {
  respondWith(() => ({
    items: [
      world({ id: "a", title: "Cooking", status: "generating" }),
      world({ id: "b", title: "Broken", status: "failed", mine: true }),
    ],
    total: 2,
  }));
  renderWorlds();

  expect(await screen.findByText("Watch progress →")).toBeInTheDocument();
  expect(screen.getByText("Open to retry →")).toBeInTheDocument();
  expect(
    screen.queryByRole("group", { name: /play/i }),
  ).not.toBeInTheDocument();
});

test("searching asks the API for matching worlds", async () => {
  const fetchMock = respondWith((url) => ({
    items:
      url.searchParams.get("q") === "bike"
        ? [world({ title: "Bike Factory" })]
        : [],
    total: url.searchParams.get("q") === "bike" ? 1 : 0,
  }));
  renderWorlds();
  await screen.findByText(/no worlds yet/i);

  await userEvent.type(screen.getByLabelText("Search worlds"), "bike");

  expect(await screen.findByText("Bike Factory")).toBeInTheDocument();
  const urls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(urls.some((u) => u.includes("q=bike"))).toBe(true);
});

test("an empty search result says so", async () => {
  respondWith(() => ({ items: [], total: 0 }));
  renderWorlds();
  await userEvent.type(await screen.findByLabelText("Search worlds"), "zzz");

  expect(await screen.findByText(/no worlds match/i)).toBeInTheDocument();
});

test("'Load more' fetches a larger page while more worlds exist", async () => {
  const fetchMock = respondWith((url) => {
    const limit = Number(url.searchParams.get("limit"));
    const all = Array.from({ length: 20 }, (_, i) =>
      world({ id: `w-${i}`, title: `World ${i}` }),
    );
    return { items: all.slice(0, limit), total: all.length };
  });
  renderWorlds();

  expect(await screen.findByText("12 of 20")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /load more/i }));

  await waitFor(() => expect(screen.getByText("World 19")).toBeInTheDocument());
  expect(
    screen.queryByRole("button", { name: /load more/i }),
  ).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.some(([u]) => String(u).includes("limit=24")),
  ).toBe(true);
});

test("a world with a thumbnail shows it on its card", async () => {
  respondWith(() => ({
    items: [world({ id: "pictured", title: "Pictured", has_thumbnail: true })],
    total: 1,
  }));
  renderWorlds();

  const image = await screen.findByAltText("Pictured world preview");
  expect(image).toHaveAttribute("src", "/api/worlds/pictured/thumbnail");
});
