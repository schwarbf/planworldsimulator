// Voice narrator (decision 0006): spoken intro with captions, bottom right.
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

/** `POST /api/narration` reply; without audio, `audio_url` is null and `audio_error` says why. */
interface Narration { text: string; sentences: string[]; audio_url: string | null; audio_error?: string | null }

const TICK_MS = 100;
const CHARS_PER_S = 15; // caption pace without audio (about 150 words per minute)
const COLLAPSE_MS = 2500;
const DOCK_GAP = 12;
const COMMENT_EVERY_WEEKS = 8; // progress update after this many weeks of play
const COMMENT_HOLD_MS = 5000; // keep the update visible after it was read // after the intro ends, shrink to the "Replay intro" pill
const BARS = Array.from({ length: 22 }, (_, k) => 0.25 + 0.75 * Math.abs(Math.sin(k * 1.7) * Math.cos(k * 0.45)));

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/**
 * Caption-first narrator. Captions run on their own clock, synced to the audio
 * while it plays, so the intro also works muted, without audio, or while the
 * browser blocks autoplay (then audio starts on the first click or key press).
 */
export function Narrator({ collapse = false, onOpen, week }: {
  /** Shrink to the small pill (e.g. while an agent plays), so the Agent panel has room. */
  collapse?: boolean;
  /** Current week; every COMMENT_EVERY_WEEKS weeks the narrator gives a progress update. */
  week?: number;
  /** Tells the layout whether the full card is shown. */
  onOpen?: (open: boolean) => void;
} = {}) {
  const [intro, setIntro] = useState<Narration | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [duration, setDuration] = useState<number | null>(null);
  const [open, setOpen] = useState(true);
  const [expanded, setExpanded] = useState(false); // hover shows the whole intro
  const audio = useRef<HTMLAudioElement | null>(null);
  const tRef = useRef(0);
  tRef.current = t;

  const chars = useMemo(() => intro?.sentences.map((s) => s.length) ?? [], [intro]);
  const totalChars = chars.reduce((a, b) => a + b, 0);
  const total = duration ?? Math.max(1, totalChars / CHARS_PER_S);
  const done = intro !== null && t >= total;

  // Load the intro once, then start it.
  useEffect(() => {
    let alive = true;
    fetch("api/narration", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "intro" }),
    })
      .then((r) => (r.ok ? (r.json() as Promise<Narration>) : null))
      .then((n) => { if (alive && n?.sentences?.length) setIntro(n); })
      .catch(() => {}); // no server: no narrator
    return () => { alive = false; };
  }, []);

  const startAudio = useCallback((from: number) => {
    const a = audio.current;
    if (!a) return;
    a.currentTime = from;
    a.play().then(() => setBlocked(false)).catch(() => setBlocked(true));
  }, []);

  useEffect(() => {
    if (!intro) return;
    if (intro.audio_url) {
      const a = new Audio(new URL(intro.audio_url.replace(/^\//, ""), window.location.href).href);
      a.preload = "auto";
      a.addEventListener("loadedmetadata", () => { if (Number.isFinite(a.duration)) setDuration(a.duration); });
      audio.current = a;
      startAudio(0);
    }
    setPlaying(true);
    return () => {
      audio.current?.pause();
      audio.current = null;
    };
  }, [intro, startAudio]);

  // Caption clock: follows the audio while it is audible, runs on its own otherwise.
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const a = audio.current;
      setT((prev) => (a && !a.paused ? a.currentTime : prev + TICK_MS / 1000));
    }, TICK_MS);
    return () => clearInterval(timer);
  }, [playing]);

  useEffect(() => {
    if (playing && done) setPlaying(false);
  }, [playing, done]);

  useEffect(() => {
    if (!done || playing) return;
    const timer = setTimeout(() => setOpen(false), COLLAPSE_MS);
    return () => clearTimeout(timer);
  }, [done, playing]);

  useEffect(() => {
    if (collapse) setOpen(false);
  }, [collapse]);

  // Progress updates (`kind: "commentary"`): every few weeks, or on "How am I doing?".
  const [comment, setComment] = useState<Narration | null>(null);
  const [asking, setAsking] = useState(false);
  const lastComment = useRef<number | null>(null);
  const busy = useRef({ asking: false, intro: false, muted: false });
  busy.current = { asking, intro: playing, muted };

  const askComment = useCallback(async () => {
    if (busy.current.asking || busy.current.intro) return;
    setAsking(true);
    try {
      const res = await fetch("api/narration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "commentary" }),
      });
      const n = res.ok ? ((await res.json()) as Narration) : null;
      if (n?.text) setComment(n);
    } catch {
      // no server: no update
    } finally {
      setAsking(false);
    }
  }, []);

  useEffect(() => {
    if (week == null) return;
    if (lastComment.current === null || week < lastComment.current) {
      lastComment.current = week; // first render or a new world: start counting here
      return;
    }
    if (week - lastComment.current >= COMMENT_EVERY_WEEKS) {
      lastComment.current = week;
      void askComment();
    }
  }, [week, askComment]);

  // Read the update aloud (unless muted), then hide it.
  useEffect(() => {
    if (!comment) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const hide = () => { timer = setTimeout(() => setComment(null), COMMENT_HOLD_MS); };
    let voice: HTMLAudioElement | null = null;
    if (comment.audio_url && !busy.current.muted) {
      voice = new Audio(new URL(comment.audio_url.replace(/^\//, ""), window.location.href).href);
      voice.addEventListener("ended", hide);
      voice.play().catch(hide);
    } else {
      timer = setTimeout(() => setComment(null), Math.max(COMMENT_HOLD_MS, (comment.text.length / CHARS_PER_S) * 1000));
    }
    return () => {
      clearTimeout(timer);
      voice?.pause();
    };
  }, [comment]);

  const shown = open && intro !== null;
  useEffect(() => onOpen?.(shown), [shown, onOpen]);

  // Autoplay blocked: start the audio, in sync with the captions, on the first interaction.
  useEffect(() => {
    if (!blocked || !playing) return;
    const unlock = () => startAudio(tRef.current);
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [blocked, playing, startAudio]);

  const replay = useCallback(() => {
    setT(0);
    setOpen(true);
    setPlaying(true);
    startAudio(0);
  }, [startAudio]);

  const togglePlay = useCallback(() => {
    if (playing) {
      audio.current?.pause();
      setPlaying(false);
    } else if (done) {
      replay();
    } else {
      setPlaying(true);
      startAudio(tRef.current);
    }
  }, [playing, done, replay, startAudio]);

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      if (audio.current) audio.current.muted = !m;
      return !m;
    });
  }, []);

  // Sit beside the dock when there is room, otherwise just above it.
  const root = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const el = root.current;
    const host = el?.parentElement;
    const dock = el?.closest(".app")?.querySelector(".app__dock");
    if (!el || !host || !dock) return;
    const place = () => {
      const overlap = dock.getBoundingClientRect().right + DOCK_GAP > el.getBoundingClientRect().left;
      host.classList.toggle("app__narrator--lifted", overlap);
    };
    place();
    const watch = new ResizeObserver(place);
    watch.observe(dock);
    watch.observe(el);
    window.addEventListener("resize", place);
    return () => {
      watch.disconnect();
      window.removeEventListener("resize", place);
    };
  }, [intro, open]);

  if (!intro) return null;

  if (!open) {
    return (
      <div ref={root} className="narrator narrator--idle">
        {comment ? (
          <div className="narrator__comment" role="status" aria-live="polite">
            <span className="narrator__name">Narrator</span>
            <span>{comment.text}</span>
          </div>
        ) : (
          <button className="narrator__replay" onClick={() => void askComment()} disabled={asking}>
            {asking ? "Looking at your game…" : "How am I doing?"}
          </button>
        )}
        <button className="narrator__logo narrator__logo--lg" onClick={replay} aria-label="Replay intro" title="Replay intro"><WaveIcon /></button>
      </div>
    );
  }

  // Sentence shown at time t: captions advance in proportion to sentence length.
  let idx = 0;
  for (let acc = 0; idx < chars.length - 1; idx++) {
    acc += chars[idx];
    if (t < (acc / totalChars) * total) break;
  }
  const progress = Math.min(1, t / total);
  const hasAudio = intro.audio_url !== null;
  const audible = hasAudio && playing && !muted && !blocked;
  const offline = `Voice off: ${intro.audio_error ?? "no Gradium connection"}`;
  const status = !hasAudio ? "No Gradium connection" : blocked ? "tap for sound" : muted ? "muted · captions stay on" : "powered by Gradium";

  return (
    <div ref={root} className="narrator card" role="region" aria-label="Narrator"
      onMouseEnter={() => setExpanded(true)} onMouseLeave={() => setExpanded(false)}>
      <div className="between">
        <span className="row">
          <span className="narrator__logo"><WaveIcon /></span>
          <span className="insp__head">
            <span className="narrator__name">Narrator · Gradium</span>
            <span className={`muted${hasAudio ? "" : " narrator__offline"}`} title={hasAudio ? undefined : offline}>{status}</span>
          </span>
        </span>
        {blocked ? (
          <button className="narrator__ctl narrator__ctl--pulse" onClick={() => startAudio(tRef.current)} aria-label="Play sound"><SpeakerIcon /></button>
        ) : (
          <span className={`narrator__chip${muted || !hasAudio ? " narrator__chip--muted" : ""}`}>{!hasAudio ? "text only" : muted ? "muted" : <><i /> intro</>}</span>
        )}
      </div>
      {expanded ? (
        <p className="narrator__caption narrator__caption--full">
          {intro.sentences.map((sentence, k) => (
            <span key={k} className={k === idx ? "narrator__now" : k < idx ? undefined : "narrator__next"}>{k > 0 && " "}{sentence}</span>
          ))}
        </p>
      ) : (
        <p className="narrator__caption" aria-live="polite">
          <span key={idx} className="narrator__now">{intro.sentences[idx]}</span>
          {idx < intro.sentences.length - 1 && <span className="narrator__next"> {intro.sentences[idx + 1]}</span>}
        </p>
      )}
      <div className="row">
        <button className="narrator__ctl narrator__ctl--ink" onClick={togglePlay} aria-label={playing ? "Pause" : "Play"}>
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        {hasAudio ? (
          <button className={`narrator__ctl${muted ? " narrator__ctl--coral" : ""}`} onClick={toggleMute} aria-label={muted ? "Unmute" : "Mute"}>
            <SpeakerIcon off={muted} />
          </button>
        ) : (
          <button className="narrator__ctl" disabled title={offline} aria-label={offline}><SpeakerIcon off /></button>
        )}
        <button className="narrator__ctl" onClick={replay} aria-label="Replay intro"><ReplayIcon /></button>
        {muted ? (
          <div className="narrator__dots" />
        ) : (
          <div className={`narrator__wave${audible ? " narrator__wave--live" : ""}${hasAudio ? "" : " narrator__wave--off"}`}
            title={hasAudio ? undefined : offline} aria-hidden>
            {BARS.map((h, k) => (
              <i key={k} className={k / BARS.length < progress ? "on" : undefined} style={{ height: `${Math.round(h * 100)}%`, animationDelay: `${(k % 7) * -0.13}s` }} />
            ))}
          </div>
        )}
        <span className="muted narrator__time">{fmt(Math.min(t, total))} / {fmt(total)}</span>
      </div>
    </div>
  );
}

function WaveIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      {[5, 10, 14, 8, 12, 6].map((h, k) => (
        <rect key={k} x={2 + k * 2.6} y={9 - h / 2} width="1.6" height={h} rx="0.8" fill="#fff" />
      ))}
    </svg>
  );
}

function PlayIcon() {
  return <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden><path d="M2 1l7 4-7 4z" fill="currentColor" /></svg>;
}

function PauseIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
      <rect x="2" y="1" width="2" height="8" rx="0.6" fill="currentColor" />
      <rect x="6" y="1" width="2" height="8" rx="0.6" fill="currentColor" />
    </svg>
  );
}

function SpeakerIcon({ off = false }: { off?: boolean }) {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M2 5.2h2.2L7.4 2.5v9L4.2 8.8H2z" fill="currentColor" />
      {off ? <path d="M9.6 5.2l3 3.6M12.6 5.2l-3 3.6" /> : <path d="M9.6 4.8a3 3 0 010 4.4M11.2 3.3a5.2 5.2 0 010 7.4" />}
    </svg>
  );
}

function ReplayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M2.5 7a4.5 4.5 0 104.5-4.5H4.5" />
      <path d="M5.5 1L4 2.5 5.5 4" />
    </svg>
  );
}
