// [base] The server's state (dumped by tests/backend/test_contract.py) matches `mockState`
// and the world view and controls render it at every level.
import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { mockState, toControls, WorldView } from "./World";

const samples = import.meta.glob<{ default: Record<string, unknown> }>("./__samples__/*.json", { eager: true });
const files = Object.keys(samples).sort();
const load = (file: string) => samples[file].default as unknown as typeof mockState;

type Json = unknown;

/** Every key of `mock` must exist in `real` with the same primitive type (recursively). */
function missing(mock: Json, real: Json, path = "state"): string[] {
  if (mock === null || mock === undefined || real === null) return []; // optional or nullable in the state
  if (Array.isArray(mock)) {
    if (!Array.isArray(real)) return [`${path}: expected an array`];
    return mock.length && real.length ? missing(mock[0], real[0], `${path}[0]`) : [];
  }
  if (typeof mock === "object") {
    if (typeof real !== "object" || real === null) return [`${path}: expected an object`];
    return Object.entries(mock as Record<string, Json>).flatMap(([k, v]) =>
      k in (real as object) ? missing(v, (real as Record<string, Json>)[k], `${path}.${k}`) : [`${path}.${k}: missing`],
    );
  }
  return typeof mock === typeof real ? [] : [`${path}: expected ${typeof mock}, got ${typeof real}`];
}

test("the backend dumped state samples (run pixi run test first)", () => {
  expect(files.length).toBeGreaterThan(0);
});

test.each(files)("%s has the shape of mockState", (file) => {
  expect(missing(mockState, load(file))).toEqual([]);
});

test.each(files)("%s renders in the controls and the world view", (file) => {
  const real = load(file);
  const model = toControls(real, null);
  expect(model.brand.world).toBe(real.world.name);
  const { container } = render(<WorldView state={real} selectedId={null} onSelect={() => {}} />);
  expect(container.querySelector("svg")).not.toBeNull();
});
