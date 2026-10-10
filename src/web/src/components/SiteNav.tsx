import { Link } from "react-router";

import { GITHUB_URL, GithubIcon } from "./GithubIcon";
import { Logo } from "./Logo";

const LINKS = [
  { href: "/#how", label: "How it works" },
  { href: "/#levels", label: "Difficulty" },
  { href: "/#examples", label: "Examples" },
  { href: "/#worlds", label: "Your worlds" },
];

export function SiteNav() {
  return (
    <header className="border-b border-line">
      <nav
        aria-label="Main"
        className="flex h-16 items-center gap-8 px-5 sm:px-8 lg:px-12"
      >
        <Link to="/" aria-label="PlanBench home">
          <Logo />
        </Link>
        <ul className="ml-auto hidden items-center gap-7 text-sm md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a href={link.href} className="text-muted hover:text-ink">
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="PlanBench on GitHub"
          className="ml-auto flex items-center gap-2 rounded-md border border-line px-3 py-1.5 text-sm hover:border-ink md:ml-0"
        >
          <GithubIcon className="size-4" />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </nav>
    </header>
  );
}
