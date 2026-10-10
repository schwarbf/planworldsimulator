// Who is speaking, so the agent's spoken notes never talk over the narrator.
// Same in every world; do not edit per world.
export const voice = {
  /** Narrator intro or progress update is audible right now. */
  narratorSpeaking: false,
  /** Player muted the narrator: the agent stays quiet too. */
  muted: false,
};
