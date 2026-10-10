import { render, screen } from "@testing-library/react";

import { DifficultyTable } from "./DifficultySection";

test("lists all four difficulty levels as column headers", () => {
  render(<DifficultyTable />);

  for (const name of ["L1 · Easy", "L2 · Medium", "L3 · Hard", "L4 · Expert"]) {
    expect(screen.getByRole("columnheader", { name })).toBeInTheDocument();
  }
  expect(
    screen.getByRole("rowheader", { name: "Hidden rules" }),
  ).toBeInTheDocument();
});
