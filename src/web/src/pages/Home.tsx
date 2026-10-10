import { useState } from "react";
import { useNavigate } from "react-router";

import { DifficultySection } from "../components/DifficultySection";
import { HowItWorks } from "../components/HowItWorks";
import { PromptWindow } from "../components/PromptWindow";
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
    <main className="flex flex-col gap-24">
      <PromptWindow
        prompt={prompt}
        onPromptChange={setPrompt}
        onCreated={(world) => navigate(`/worlds/${world.id}`)}
      />
      <HowItWorks />
      <DifficultySection />
      <ShowcaseGallery onUse={usePrompt} />
      <WorldsList />
    </main>
  );
}
