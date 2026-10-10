import { useEffect } from "react";
import { Chip } from "../primitives/Chip";
import { Icon } from "../primitives/Icon";
import type { ControlsModel, IconName, OnAction } from "../types";

const timeButtons: { id: string; icon: IconName; label: string }[] = [
  { id: "stats", icon: "stats", label: "Stats" },
  { id: "pause", icon: "pause", label: "Pause" },
  { id: "play", icon: "play", label: "Play" },
  { id: "fast", icon: "fast", label: "Fast forward" },
];

/** Verbs (with keyboard shortcuts), time controls and "New world". `data-target` lets the agent cursor find them. */
export function ActionDock({ dock, onAction, running = "play" }: { dock: ControlsModel["dock"]; onAction: OnAction; running?: string }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || (e.target as HTMLElement)?.closest?.("input, textarea")) return;
      const verb = dock.verbs.find((v) => !v.disabled && v.key.toLowerCase() === e.key.toLowerCase());
      if (verb) onAction(verb.id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dock.verbs, onAction]);

  return (
    <div className="dock">
      {dock.verbs.map((v) => (
        <button key={v.id} data-target={`verb:${v.id}`} data-label={v.label} className={`verb${dock.active === v.id ? " on" : ""}`} disabled={v.disabled} onClick={() => onAction(v.id)}>
          <Icon name={v.disabled ? "lock" : v.icon} size={14} />
          {v.label}
          <kbd>{v.key}</kbd>
        </button>
      ))}
      <Chip tone="muted">{dock.unlocked} / {dock.total} actions</Chip>
      <span className="dock__sep" />
      {timeButtons.map((b) => (
        <button key={b.id} data-target={`time:${b.id}`} className={`iconbtn${running === b.id ? " on" : ""}`} aria-label={b.label} title={b.label} onClick={() => onAction(b.id)}>
          <Icon name={b.icon} size={14} />
        </button>
      ))}
      <span className="dock__sep" />
      <button className="btn btn--coral" onClick={() => onAction("new_world")}>
        <Icon name="spark" size={14} />
        New world
      </button>
    </div>
  );
}
