import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DifficultyPicker } from "./DifficultyPicker";

test("selects a difficulty level", async () => {
  const onChange = vi.fn();
  render(<DifficultyPicker value={2} onChange={onChange} />);

  expect(screen.getByRole("radio", { name: /medium/i })).toBeChecked();
  await userEvent.click(screen.getByRole("radio", { name: /expert/i }));

  expect(onChange).toHaveBeenCalledWith(4);
});
