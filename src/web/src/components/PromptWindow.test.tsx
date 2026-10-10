import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";

import type { World } from "../api/client";
import { type Draft, PromptWindow } from "./PromptWindow";

const world = { id: "bakery-1", title: "Bakery" } as World;

function Harness({ onCreated }: { onCreated: (w: World) => void }) {
  const [draft, setDraft] = useState<Draft>({ name: "", prompt: "" });
  return (
    <MemoryRouter>
      <PromptWindow
        draft={draft}
        onDraftChange={setDraft}
        onCreated={onCreated}
      />
    </MemoryRouter>
  );
}

afterEach(() => vi.restoreAllMocks());

const MODELS = [
  {
    id: "gemini-3.5-flash",
    label: "Gemini 3.5 Flash",
    note: "fast",
    default: true,
  },
  {
    id: "gemini-3.1-pro-preview",
    label: "Gemini 3.1 Pro",
    note: "slowest",
    default: false,
  },
];

/** Answers the model list on its own; every other request gets `create()`. */
function mockApi(create: () => Response) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) =>
      String(input).endsWith("/worlds/models")
        ? new Response(JSON.stringify(MODELS))
        : create(),
    );
}

test("disables Generate until both a name and a prompt are written", async () => {
  render(<Harness onCreated={vi.fn()} />);
  const button = screen.getByRole("button", { name: /generate world/i });
  expect(button).toBeDisabled();

  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  expect(button).toBeDisabled();

  await userEvent.type(screen.getByLabelText("World name"), "Bakery");
  expect(button).toBeEnabled();
});

test("has no difficulty control, and sends name, prompt and seed", async () => {
  const fetchMock = mockApi(
    () => new Response(JSON.stringify(world), { status: 201 }),
  );
  const onCreated = vi.fn();
  render(<Harness onCreated={onCreated} />);
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("World name"), "  Bakery  ");
  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  await userEvent.type(screen.getByLabelText("Seed"), "42");
  await userEvent.click(
    screen.getByRole("button", { name: /generate world/i }),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/worlds",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        name: "Bakery",
        prompt: "A bakery",
        seed: 42,
        model: "gemini-3.5-flash",
      }),
    }),
  );
  expect(onCreated).toHaveBeenCalledWith(world);
});

test("choosing a starting point fills the name and the prompt", async () => {
  render(<Harness onCreated={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Fission Ops" }));

  expect(screen.getByLabelText("World name")).toHaveValue("Fission Ops");
  const box = screen.getByLabelText<HTMLTextAreaElement>(
    /describe your benchmark/i,
  );
  expect(box.value).toContain("nuclear power plant");
});

test("shows the server's error when creating fails", async () => {
  mockApi(
    () =>
      new Response(JSON.stringify({ detail: "name too short" }), {
        status: 422,
      }),
  );
  render(<Harness onCreated={vi.fn()} />);
  await userEvent.type(screen.getByLabelText("World name"), "Bakery");
  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  await userEvent.click(
    screen.getByRole("button", { name: /generate world/i }),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent("name too short");
});

test("a taken name links to the world that has it", async () => {
  mockApi(
    () =>
      new Response(
        JSON.stringify({ detail: "A world called “Bakery” already exists." }),
        { status: 409, headers: { "X-Existing-World": "bakery-abc123" } },
      ),
  );
  render(<Harness onCreated={vi.fn()} />);
  await userEvent.type(screen.getByLabelText("World name"), "Bakery");
  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  await userEvent.click(
    screen.getByRole("button", { name: /generate world/i }),
  );

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("already exists");
  expect(screen.getByRole("link", { name: "Open it" })).toHaveAttribute(
    "href",
    "/worlds/bakery-abc123",
  );
});

test("the chosen generator model is sent with the world", async () => {
  const fetchMock = mockApi(
    () => new Response(JSON.stringify(world), { status: 201 }),
  );
  render(<Harness onCreated={vi.fn()} />);
  const picker = await screen.findByLabelText("Generator model");
  expect(picker).toHaveValue("gemini-3.5-flash");
  await userEvent.selectOptions(picker, "gemini-3.1-pro-preview");
  await userEvent.type(screen.getByLabelText("World name"), "Bakery");
  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  await userEvent.click(
    screen.getByRole("button", { name: /generate world/i }),
  );

  const body = JSON.parse(
    String(fetchMock.mock.calls.at(-1)?.[1]?.body ?? "{}"),
  ) as { model?: string };
  expect(body.model).toBe("gemini-3.1-pro-preview");
});
