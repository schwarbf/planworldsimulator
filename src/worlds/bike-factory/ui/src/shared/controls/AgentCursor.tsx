import { useCallback, useEffect, useRef, useState } from "react";
import { voice } from "../voice";

/** One entry of the world's event log (`WS /api/events`). */
interface WorldEvent { seq: number; source: string; kind: string; name: string; args: Record<string, unknown> }

export interface AgentLook { label: string; color: string }

const MOVE_MS = 600;
const MIN_MOVE_MS = 180;
const PULSE_MS = 260;
const READ_MS = 900;
const RECONNECT_MS = 2000;
const POLL_MS = 800; // without a WebSocket (e.g. behind a plain HTTP proxy such as /play/<id>/)
const WS_SILENT_MS = 3000; // a working socket sends recent history at once

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Round robot face: the agent's badge on the cursor, banner and panel. */
export function RobotBadge({ color, size = 22 }: { color: string; size?: number }) {
  return (
    <svg className="robot" width={size} height={size} viewBox="0 0 22 22" aria-hidden>
      <circle cx="11" cy="11" r="10.5" fill={color} stroke="#fff" strokeWidth="1.5" />
      <line x1="11" y1="2.5" x2="11" y2="5.5" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="11" cy="2.6" r="1.3" fill="#fff" />
      <rect x="5" y="6.5" width="12" height="9.5" rx="3.2" fill="#fff" />
      <circle cx="8.6" cy="11" r="1.5" fill={color} />
      <circle cx="13.4" cy="11" r="1.5" fill={color} />
      <path d="M9 14h4" stroke={color} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

const NOTE_CHARS = 70;
const NOTE_GAP_MS = 6000; // pause after a spoken note ends; only the newest note is read, however often the agent writes
const NOTE_TICK_MS = 1000;
const NOTE_WATCH_MS = 150; // how fast a playing note yields to the narrator
const clip = (text: string, n: number) => (text.length > n ? `${text.slice(0, n - 1)}…` : text);

/** Visible name of a target: its `data-label` (dock verb or map object), else the raw id. */
function labelOf(selector: string, fallback: string): string {
  return document.querySelector(selector)?.getAttribute("data-label") ?? fallback;
}

/**
 * What the agent is doing, in words, from its MCP call alone (no model reasoning):
 * "Order 60 · Warehouse", "Checking Store B", "Next week". World-independent:
 * names come from `data-label` on the dock verbs and map objects.
 */
export function describe(e: WorldEvent): string {
  const strings = Object.values(e.args).filter((v): v is string => typeof v === "string");
  const site = strings.map((v) => labelOf(`[data-target="map:${CSS.escape(v)}"][data-label]`, "")).find(Boolean);
  if (e.kind === "action") {
    if (e.name === "cancel") return "Removing a queued action";
    const verb = labelOf(`[data-target="verb:${CSS.escape(e.name)}"]`, e.name.charAt(0).toUpperCase() + e.name.slice(1));
    const amount = Object.values(e.args).find((v) => typeof v === "number");
    return [verb + (amount != null ? ` ${amount}` : ""), site].filter(Boolean).join(" · ");
  }
  if (e.kind === "advance") {
    const steps = Number(e.args.steps ?? 1);
    return steps > 1 ? `Skipping ahead ${steps} weeks` : "Next week";
  }
  if (e.kind === "note") return "Writing down a hypothesis";
  if (e.name === "brief") return "Reading the brief";
  if (e.name === "score") return "Checking the score";
  return site ? `Checking ${site}` : "Checking the state";
}

/** Where the cursor points at for an element: its centre, in viewport pixels. */
function centre(el: Element): [number, number] {
  const r = el.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2];
}

/** First `[data-target="map:<value>"]` for any string argument (site, target, …). */
function mapTarget(args: Record<string, unknown>): { id: string; el: Element } | null {
  for (const v of Object.values(args)) {
    if (typeof v !== "string") continue;
    const el = document.querySelector(`[data-target="map:${CSS.escape(v)}"]`);
    if (el) return { id: v, el };
  }
  return null;
}

/**
 * Fake cursor that replays the agent's MCP calls (`source: "agent"` events)
 * one after another: move to the site on the map, move to the dock verb,
 * click pulse; `advance` goes to Play; reads show a "reading…" bubble.
 * World-independent: targets are found by `data-target` attributes.
 */
/**
 * Reads the agent's newest `note()` aloud in the agent's own voice (decision 0006).
 * Guarded so a busy agent cannot flood it: only the newest unread note, at most one
 * NOTE_GAP_MS after the last one ended, never over the narrator, not while muted.
 */
function useNoteVoice(enabled: boolean, active: boolean) {
  const [speaking, setSpeaking] = useState(false);
  const pending = useRef<string | null>(null);
  const busy = useRef(false);
  const last = useRef(0);
  const on = useRef(enabled && active);
  on.current = enabled && active;

  const speak = useCallback(async () => {
    const text = pending.current;
    if (!text || busy.current) return;
    if (!on.current || voice.muted) { pending.current = null; return; }
    if (voice.narratorSpeaking || Date.now() - last.current < NOTE_GAP_MS) return; // wait, keep the newest
    pending.current = null;
    busy.current = true;
    last.current = Date.now();
    try {
      const res = await fetch("api/narration", { // relative: the UI may live under /play/<id>/
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "note", text }),
      });
      const n = res.ok ? ((await res.json()) as { audio_url: string | null }) : null;
      if (n?.audio_url && on.current && !voice.muted && !voice.narratorSpeaking) {
        const clip = new Audio(new URL(n.audio_url.replace(/^\//, ""), window.location.href).href);
        setSpeaking(true);
        await new Promise<void>((done) => {
          // The narrator (intro or progress update) always wins: stop the agent at once.
          const watch = setInterval(() => {
            if (voice.narratorSpeaking || voice.muted || !on.current) {
              clip.pause();
              finish();
            }
          }, NOTE_WATCH_MS);
          const finish = () => { clearInterval(watch); done(); };
          clip.addEventListener("ended", finish);
          clip.play().catch(finish);
        });
      }
    } catch {
      // no server: stay quiet
    } finally {
      last.current = Date.now(); // the pause starts when the clip ends
      busy.current = false;
      setSpeaking(false);
    }
  }, []);

  useEffect(() => {
    const timer = setInterval(() => void speak(), NOTE_TICK_MS);
    return () => clearInterval(timer);
  }, [speak]);
  useEffect(() => {
    if (!enabled || !active) pending.current = null;
  }, [enabled, active]);

  const heard = useCallback((text: string) => { pending.current = text; }, []);
  return { speaking, heard };
}

export function AgentCursor({ look, active, onTarget, voiceNotes = false }: {
  look: AgentLook;
  active: boolean;
  onTarget?: (id: string) => void;
  /** Read the agent's notes aloud (toggle in the Agent panel). */
  voiceNotes?: boolean;
}) {
  const notes = useNoteVoice(voiceNotes, active);
  const heard = useRef(notes.heard);
  heard.current = notes.heard;
  const [pos, setPos] = useState<[number, number]>(() => [window.innerWidth / 2, window.innerHeight / 2]);
  const [moveMs, setMoveMs] = useState(MOVE_MS);
  const [doing, setDoing] = useState<string | null>(null); // tag above the cursor
  const [testing, setTesting] = useState<string | null>(null); // last note() hypothesis
  const [pulse, setPulse] = useState(0);
  const queue = useRef<WorldEvent[]>([]);
  const running = useRef(false);
  const onTargetRef = useRef(onTarget);
  onTargetRef.current = onTarget;

  // Taken over: drop what is still queued, so the cursor stops at once.
  useEffect(() => {
    if (!active) queue.current = [];
  }, [active]);

  useEffect(() => {
    let alive = true;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let lastSeq = Number.POSITIVE_INFINITY; // until we know where the log ends, skip the replay

    const move = async (el: Element | null) => {
      if (!el) return;
      const ms = Math.max(MIN_MOVE_MS, MOVE_MS / (1 + 0.35 * queue.current.length));
      setMoveMs(ms);
      setPos(centre(el));
      await sleep(ms);
    };
    const click = async () => {
      setPulse((n) => n + 1);
      await sleep(PULSE_MS);
    };

    const play = async (e: WorldEvent) => {
      setDoing(describe(e));
      if (e.kind === "note" && typeof e.args.text === "string") {
        setTesting(e.args.text);
        heard.current(e.args.text);
      }
      if (e.kind === "read" || e.kind === "note") {
        await sleep(queue.current.length > 2 ? READ_MS / 2 : READ_MS);
      } else if (e.kind === "advance") {
        await move(document.querySelector('[data-target="time:play"]'));
        await click();
      } else if (e.kind === "action") {
        const site = mapTarget(e.args);
        if (site) {
          onTargetRef.current?.(site.id);
          await move(site.el);
          await click();
        }
        await move(document.querySelector(`[data-target="verb:${CSS.escape(e.name)}"]`));
        await click();
      }
    };

    const drain = async () => {
      if (running.current) return;
      running.current = true;
      while (alive && queue.current.length) await play(queue.current.shift()!);
      running.current = false;
    };

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const url = new URL("api/events", window.location.href);
      url.protocol = `${proto}:`;
      ws = new WebSocket(url);
      // A proxy that cannot upgrade leaves the socket hanging: fall back to polling.
      const silent = setTimeout(() => ws?.close(), WS_SILENT_MS);
      ws.onmessage = (msg) => {
        clearTimeout(silent);
        const e = JSON.parse(String(msg.data)) as WorldEvent;
        if (e.seq <= lastSeq) return; // history sent on connect
        lastSeq = e.seq;
        if (e.source !== "agent") return;
        queue.current.push(e);
        void drain();
      };
      ws.onclose = () => { if (alive) timer = setTimeout(poll, RECONNECT_MS); };
    };

    const poll = async () => {
      try {
        const res = await fetch(`api/events?after=${lastSeq}`);
        if (res.ok) {
          const events = (await res.json()) as WorldEvent[];
          for (const e of events) {
            if (e.seq <= lastSeq) continue;
            lastSeq = e.seq;
            if (e.source === "agent") queue.current.push(e);
          }
          void drain();
        }
      } catch { /* Retry while the world server is unavailable. */ }
      if (alive) timer = setTimeout(poll, POLL_MS);
    };

    const start = async () => {
      try {
        const res = await fetch("api/events");
        const log = res.ok ? ((await res.json()) as WorldEvent[]) : [];
        lastSeq = log.reduce((m, e) => Math.max(m, e.seq), 0);
      } catch {
        lastSeq = 0;
      }
      if (alive) connect();
    };

    void start();
    return () => {
      alive = false;
      clearTimeout(timer);
      queue.current = [];
      ws?.close();
    };
  }, []);

  if (!active) return null;
  return (
    <div
      className="acursor"
      style={{ transform: `translate(${pos[0]}px, ${pos[1]}px)`, transitionDuration: `${moveMs}ms`, ["--agent" as string]: look.color }}
      aria-hidden
    >
      {pulse > 0 && <span key={pulse} className="acursor__pulse" />}
      <svg className="acursor__arrow" width="22" height="24" viewBox="0 0 22 24">
        <path d="M2 2l17 8.5-7.2 2.1L8.6 20z" fill="var(--agent)" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <span className="acursor__tag">
        <RobotBadge color={look.color} />
        <span className="acursor__name">{look.label}</span>
      </span>
      {doing && (
        <span className="acursor__think">
          <span className="acursor__doing"><i className="acursor__dots" />{doing}</span>
          {testing && (
            <span className={`acursor__why${notes.speaking ? " acursor__why--voice" : ""}`}>
              {notes.speaking && <SpeakingIcon />}Testing: {clip(testing, NOTE_CHARS)}
            </span>
          )}
        </span>
      )}
    </div>
  );
}

function SpeakingIcon() {
  return (
    <svg className="acursor__speaker" width="11" height="11" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-label="speaking">
      <path d="M2 5.2h2.2L7.4 2.5v9L4.2 8.8H2z" fill="currentColor" />
      <path d="M9.6 4.8a3 3 0 010 4.4M11.2 3.3a5.2 5.2 0 010 7.4" />
    </svg>
  );
}
