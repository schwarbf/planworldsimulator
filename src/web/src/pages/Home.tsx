import { useState } from "react";
import { useNavigate } from "react-router";

import { DifficultySection } from "../components/DifficultySection";
import { HowItWorks } from "../components/HowItWorks";
import { type Draft, PromptWindow } from "../components/PromptWindow";
import { ShowcaseGallery } from "../components/ShowcaseGallery";
import { WorldsList } from "../components/WorldsList";
import { SHOWCASE } from "../data/showcase";

export function Home() {
  const navigate = useNavigate();
  const [draft, setDraft] = useState<Draft>({
    name: SHOWCASE[0].name,
    prompt: SHOWCASE[0].prompt,
  });

  function usePrompt(next: Draft) {
    setDraft(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="flex flex-col gap-24">
      <PromptWindow
        draft={draft}
        onDraftChange={setDraft}
        onCreated={(world) => navigate(`/worlds/${world.id}`)}
      />
      <HowItWorks />
      <DifficultySection />
      <ShowcaseGallery onUse={usePrompt} />
      <WorldsList />
    </main>
  );
}
