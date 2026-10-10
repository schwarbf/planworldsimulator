import { SHOWCASE } from "../data/showcase";
import { Button, Card } from "./ui";

export function ShowcaseGallery({
  onUse,
}: {
  onUse: (prompt: string) => void;
}) {
  return (
    <section>
      <h2 className="font-display text-xl font-bold">Worlds people build</h2>
      <p className="mb-4 text-sm text-muted">
        Every world shares the PlanBench look and controls. Start from one of
        these.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SHOWCASE.map((world) => (
          <Card key={world.name} className="flex flex-col overflow-hidden">
            <img
              src={world.image}
              alt={`${world.name} world preview`}
              className="aspect-[8/5] w-full object-cover"
              loading="lazy"
            />
            <div className="flex flex-1 flex-col gap-2 p-4">
              <h3 className="font-display text-base font-bold">{world.name}</h3>
              <p className="flex-1 text-xs text-muted">{world.premise}</p>
              <Button
                variant="soft"
                className="py-2 text-xs"
                onClick={() => onUse(world.prompt)}
              >
                Use this prompt
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
