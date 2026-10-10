import { useState } from "react";
import { useNavigate } from "react-router";

import { GeneratorCard } from "../components/GeneratorCard";
import { ShowcaseGallery } from "../components/ShowcaseGallery";
import { WorldsList } from "../components/WorldsList";
import { SHOWCASE } from "../data/showcase";

export function Home() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState(SHOWCASE[0].prompt);

  function usePrompt(next: string) {
    setPrompt(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-14 px-4 pb-20">
      <section className="grid items-center gap-8 lg:grid-cols-[480px_1fr]">
        <div className="flex flex-col gap-5">
          <div>
            <h1 className="font-display text-4xl leading-tight font-bold text-balance sm:text-5xl">
              Describe a planning world. Get a playable benchmark.
            </h1>
            <p className="mt-3 text-muted">
              Write what the world is about in plain language. PlanBench
              generates the simulator, the agent interface and the interface to
              play it.
            </p>
          </div>
          <GeneratorCard
            prompt={prompt}
            onPromptChange={setPrompt}
            onCreated={(world) => navigate(`/worlds/${world.id}`)}
          />
        </div>
        <figure className="lg:-rotate-1">
          <img
            src="/showcase/fission-ops.png"
            alt="Fission Ops control room: a generated PlanBench world"
            className="w-full rounded-card border border-line shadow-card"
          />
          <figcaption className="mt-3 text-center text-xs text-muted">
            Fission Ops — generated from one paragraph of text.
          </figcaption>
        </figure>
      </section>

      <ShowcaseGallery onUse={usePrompt} />
      <WorldsList />
    </main>
  );
}
