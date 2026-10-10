import type { ControlsModel } from "../types";

/** Story event banner shown under the top bar. */
export function StoryToast({ story }: { story: NonNullable<ControlsModel["story"]> }) {
  return (
    <div className={`story story--${story.tone}`}>
      <span className="story__tag">{story.tag}</span>
      <span>{story.text}</span>
    </div>
  );
}
