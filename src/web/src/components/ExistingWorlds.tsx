import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { api, type World, type WorldPage } from "../api/client";
import { PlayLevels } from "./PlayLevels";
import { Section } from "./Section";
import { StatusChip } from "./ui";

const PAGE_SIZE = 12;
const POLL_MS = 3000;

function WorldCard({ world }: { world: World }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-line bg-card p-5">
      <div className="flex items-center gap-2">
        {world.featured && (
          <span className="rounded-full bg-violet-soft px-2.5 py-1 font-mono text-[11px] text-violet uppercase">
            Featured
          </span>
        )}
        {world.status !== "ready" && <StatusChip status={world.status} />}
        {world.mine && !world.featured && (
          <span className="font-mono text-[11px] text-muted uppercase">
            Yours
          </span>
        )}
      </div>
      <h3 className="font-display text-3xl leading-tight">
        <Link to={`/worlds/${world.id}`} className="hover:underline">
          {world.title}
        </Link>
      </h3>
      <p className="line-clamp-3 text-sm text-muted">
        {world.storyline ?? world.prompt}
      </p>
      <p className="font-mono text-xs text-muted">
        seed #{world.seed} · {world.levels.length} levels
        {world.play_count > 0 ? ` · played ${world.play_count}×` : ""}
      </p>
      <div className="mt-auto pt-2">
        {world.status === "ready" ? (
          <PlayLevels world={world} />
        ) : (
          <Link
            to={`/worlds/${world.id}`}
            className="text-sm font-semibold underline-offset-4 hover:underline"
          >
            {world.status === "failed" ? "Open to retry →" : "Watch progress →"}
          </Link>
        )}
      </div>
    </article>
  );
}

export function ExistingWorlds() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [page, setPage] = useState<WorldPage | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query.trim());
      setLimit(PAGE_SIZE);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const refresh = useCallback(async () => {
    try {
      setPage(await api.listWorlds({ q: search, limit }));
    } catch {
      setPage((current) => current ?? { items: [], total: 0 });
    }
  }, [search, limit]);

  useEffect(() => {
    const first = setTimeout(refresh, 0);
    const timer = setInterval(refresh, POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [refresh]);

  return (
    <Section
      id="worlds"
      index="05"
      label="Existing worlds"
      title={
        <>
          Existing worlds, <em>ready to play.</em>
        </>
      }
    >
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <p className="max-w-xl text-muted">
          Anyone can generate a world, and every finished world is public. Pick
          one and play it at any of its four difficulty levels.
        </p>
        <input
          type="search"
          aria-label="Search worlds"
          placeholder="Search worlds"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm outline-none focus:border-ink sm:w-64"
        />
      </div>

      {page === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : page.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line p-8 text-sm text-muted">
          {search
            ? `No worlds match “${search}”.`
            : "No worlds yet. Describe one at the top of the page and hit Generate."}
        </p>
      ) : (
        <>
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {page.items.map((world) => (
              <WorldCard key={world.id} world={world} />
            ))}
          </div>
          {page.items.length < page.total && (
            <div className="mt-8 flex items-center gap-4">
              <button
                type="button"
                onClick={() => setLimit((current) => current + PAGE_SIZE)}
                className="rounded-md border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-white"
              >
                Load more
              </button>
              <span className="font-mono text-xs text-muted">
                {page.items.length} of {page.total}
              </span>
            </div>
          )}
        </>
      )}
    </Section>
  );
}
