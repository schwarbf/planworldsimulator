import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { Home } from "./Home";

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }),
  );
  window.scrollTo = vi.fn();
});
afterEach(() => vi.restoreAllMocks());

test("shows the hero, the showcase and an empty worlds list", async () => {
  render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );

  expect(
    screen.getByRole("heading", {
      level: 1,
      name: /describe a planning world/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByAltText(/fission ops control room/i)).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /three levels in every world/i }),
  ).toBeInTheDocument();
  expect(await screen.findByText(/no worlds yet/i)).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /existing worlds, ready to play/i }),
  ).toBeInTheDocument();
});

test("'Use this prompt' copies a showcase prompt into the generator", async () => {
  render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );

  const buttons = screen.getAllByRole("button", { name: /use this prompt/i });
  await userEvent.click(buttons[1]);

  expect(screen.getByLabelText("World name")).toHaveValue("Bike Factory");
  const box = screen.getByLabelText<HTMLTextAreaElement>(
    /describe your benchmark/i,
  );
  expect(box.value).toContain("bike factory");
});
