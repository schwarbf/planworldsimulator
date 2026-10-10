# Add a Gradium voice narrator

**Date:** 2026-10-10
**Status:** proposed

## Context

Gradium is a hackathon partner (voice AI). A new player needs a short
explanation of the world when it opens. Every world already has a public
`brief.md`.

## Decision

### Look and behaviour

- A shared control `Narrator.tsx` at the bottom right; same in every world.
- Compact, caption-first look (the "muted" draft): the intro text appears line by
  line, so it also works without sound.
- Audio plays automatically when the world opens; no click needed.
- If the browser blocks autoplay, captions keep running and a pulsing speaker
  shows that audio exists; audio starts on the first interaction.
- Controls: pause, mute, replay intro.
- Design draft: Figma page "Agent cursor – draft", frames "Narrator – parts",
  "World opens – intro", "Narrator commentary".

### Pipeline

1. Gemini turns `brief.md` into a spoken intro of about 60 words.
2. Gradium text-to-speech (REST) turns it into audio.
3. Text and audio are cached in the world folder; one call each per world.

### Server (base, every world)

- `POST /api/narration {kind}` returns `{text, sentences, audio_url}`.
- v1 supports `kind: "intro"` only.
- Keys (`GEMINI_API_KEY`, `GRADIUM_API_KEY`) stay on the server; the browser
  never sees them.

## Consequences

- Every world gets an intro for free, because every world has `brief.md`.
- Without keys the narrator shows `brief.md` as captions only.
- Future (not v1): `kind: "commentary"` sends the current state and score to
  Gemini ("how you are doing"), read aloud by Gradium, using its WebSocket for
  low latency.

## Alternatives considered

- **Start muted until the first click:** rejected; the intro should be heard
  right away.
- **Call Gradium from the browser:** rejected; it would expose the API key.

## Supersedes

None
