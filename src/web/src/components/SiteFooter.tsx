import { GITHUB_URL, GithubIcon } from "./GithubIcon";
import { Logo } from "./Logo";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="flex flex-col gap-8 px-5 py-10 sm:px-8 md:flex-row md:items-start md:justify-between lg:px-12">
        <div className="max-w-xs">
          <Logo />
          <p className="mt-3 text-sm text-muted">
            Planning benchmarks, generated from a paragraph of text.
          </p>
        </div>
        <ul className="flex flex-col gap-2 text-sm">
          <li>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 hover:underline"
            >
              <GithubIcon className="size-4" />
              Source on GitHub
            </a>
          </li>
          <li>
            <a
              href={`${GITHUB_URL}/tree/main/docs/design-decisions`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
            >
              Design decisions
            </a>
          </li>
        </ul>
      </div>
      <p className="border-t border-line px-5 py-4 font-mono text-xs text-muted sm:px-8 lg:px-12">
        © 2026 PlanWorldSimulator
      </p>
    </footer>
  );
}
