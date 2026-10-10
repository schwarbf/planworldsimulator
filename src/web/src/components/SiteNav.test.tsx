import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { SiteFooter } from "./SiteFooter";
import { SiteNav } from "./SiteNav";

const REPO = "https://github.com/schwarbf/planworldsimulator";

test("nav and footer link to the public GitHub repository", () => {
  render(
    <MemoryRouter>
      <SiteNav />
      <SiteFooter />
    </MemoryRouter>,
  );

  const nav = screen.getByRole("link", { name: /planbench on github/i });
  expect(nav).toHaveAttribute("href", REPO);
  expect(nav).toHaveAttribute("rel", expect.stringContaining("noopener"));
  expect(
    screen.getByRole("link", { name: /source on github/i }),
  ).toHaveAttribute("href", REPO);
});
