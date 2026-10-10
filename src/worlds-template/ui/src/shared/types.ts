// Contract between a world (World.tsx) and the shared controls.
// World.tsx turns its raw state into a ControlsModel; App.tsx renders it.
import type { ReactNode } from "react";

export type Tone = "ink" | "coral" | "mint" | "amber" | "violet" | "muted";
export type IconName =
  | "probe" | "order" | "expand" | "auto" | "lock" | "bolt" | "battery" | "sell"
  | "pause" | "play" | "fast" | "spark" | "check" | "stats";

export interface Stat { label: string; value: string; tone?: Tone }
export interface ProgressBar { label: string; value: string; pct: number; tone: Tone; tick?: number }

export interface InspectorAction {
  id: string;
  label: string;
  sub: string;
  icon: IconName;
  variant: "soft" | "violet" | "locked";
}

export interface InspectorModel {
  title: string;
  level?: number;
  subtitle: string;
  icon?: ReactNode;
  note?: string;
  progress?: ProgressBar;
  stats: Stat[];
  primary?: { id: string; label: string; icon: IconName; amount: number; unit?: string; step: number };
  actions: InspectorAction[];
}

export interface Verb { id: string; label: string; icon: IconName; key: string; disabled?: boolean }

export interface ControlsModel {
  brand: { world: string; seed: string; difficulty: string };
  topBar: { value: string; chips: { text: string; tone: Tone }[]; timeLabel: string; timeProgress: number };
  story?: { tag: string; text: string; tone: "amber" | "mint" | "coral" };
  inspector?: InspectorModel;
  discoveries: { total: number; found: string[]; hidden: (string | null)[] };
  goal: { text: string; bars: ProgressBar[] };
  agent: { experiment: string; mode: "you" | "agent"; scores: number[]; baseline: number; slots: number; now: string; code: string };
  dock: { verbs: Verb[]; active?: string; unlocked: number; total: number };
}

/** Called by controls; App forwards it to the world server. */
export type OnAction = (id: string, args?: Record<string, unknown>) => void;
