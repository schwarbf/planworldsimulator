import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import type { World } from "../api/client";
import { GeneratorCard } from "./GeneratorCard";

const world = { id: "w-1", title: "Test world" } as World;

function Harness({ onCreated }: { onCreated: (w: World) => void }) {
  const [prompt, setPrompt] = useState("");
  return (
    <GeneratorCard
      prompt={prompt}
      onPromptChange={setPrompt}
      onCreated={onCreated}
    />
  );
}

afterEach(() => vi.restoreAllMocks());

test("disables Generate until a prompt is written", async () => {
  render(<Harness onCreated={vi.fn()} />);
  const button = screen.getByRole("button", { name: /generate world/i });
  expect(button).toBeDisabled();

  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  expect(button).toBeEnabled();
});

test("submits prompt, difficulty and seed to the API", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(JSON.stringify(world), { status: 201 }));
  const onCreated = vi.fn();
  render(<Harness onCreated={onCreated} />);

  await userEvent.type(
    screen.getByLabelText(/describe your benchmark/i),
    "A bakery",
  );
  await userEvent.click(screen.getByRole("radio", { name: /hard/i }));
  await userEvent.type(screen.getByLabelText("Seed"), "42");
  await userEvent.click(
    screen.getByRole("button", { name: /generate world/i }),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/worlds",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ prompt: "A bakery", difficulty: 3, seed: 42 }),
    }),
  );
  expect(onCreated).toHaveBeenCalledWith(world);
});

test("picking a theme fills the prompt", async () => {
  render(<Harness onCreated={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Fission Ops" }));

  const box = screen.getByLabelText<HTMLTextAreaElement>(
    /describe your benchmark/i,
  );
  expect(box.value).toContain("nuclear power plant");
});
