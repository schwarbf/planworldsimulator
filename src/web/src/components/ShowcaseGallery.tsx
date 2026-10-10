import { SHOWCASE } from "../data/showcase";
import { cx } from "./ui";
import { Section } from "./Section";

// Alternating column spans give an asymmetric two-row layout on wide screens.
const SPANS = [
  "lg:col-span-7",
  "lg:col-span-5",
  "lg:col-span-5",
  "lg:col-span-7",
];

export function ShowcaseGallery({
  onUse,
}: {
  onUse: (prompt: string) => void;
}) {
  return (
    <Section
      id="examples"
      index="04"
      label="Examples"
      title={<>Worlds to start from.</>}
    >
      <div className="grid gap-x-8 gap-y-12 lg:grid-cols-12">
        {SHOWCASE.map((world, i) => (
          <article key={world.name} className={cx("flex flex-col", SPANS[i])}>
            <img
              src={world.image}
              alt={`${world.name} world preview`}
              className="aspect-[8/5] w-full rounded-lg border border-line object-cover"
              loading="lazy"
            />
            <div className="mt-4 flex items-start justify-between gap-6">
              <div>
                <h3 className="font-display text-3xl">{world.name}</h3>
                <p className="mt-1 max-w-md text-sm text-muted">
                  {world.premise}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onUse(world.prompt)}
                className="shrink-0 pt-2 text-sm font-semibold underline-offset-4 hover:underline"
              >
                Use this prompt →
              </button>
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
