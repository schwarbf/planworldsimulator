import { useState } from "react";
import { Bar } from "../primitives/Bar";
import { Card } from "../primitives/Card";
import { Chip } from "../primitives/Chip";
import { Icon } from "../primitives/Icon";
import type { InspectorModel, OnAction, Tone } from "../types";

const toneColor: Partial<Record<Tone, string>> = {
  coral: "var(--coral)", mint: "var(--mint)", amber: "#c47f00", violet: "var(--violet)", muted: "var(--muted)",
};

/**
 * Selected object. App renders it with `key={title}` so the stepper amount
 * resets when the selection changes.
 */
export function Inspector({ model, onAction }: { model: InspectorModel; onAction: OnAction }) {
  const { primary } = model;
  const [amount, setAmount] = useState(primary?.amount ?? 0);

  return (
    <Card className="inspector">
      <div className="row">
        <div className="insp__icon">{model.icon}</div>
        <div className="insp__head">
          <div className="row">
            <span className="title">{model.title}</span>
            {model.level != null && <Chip tone="ink">LV {model.level}</Chip>}
          </div>
          <div className="muted">{model.subtitle}</div>
        </div>
      </div>

      {model.note && <div className="insp__note">{model.note}</div>}

      {model.progress && (
        <div className="insp__progress">
          <div className="between">
            <span className="caps">{model.progress.label}</span>
            <span className="stat__value">{model.progress.value}</span>
          </div>
          <Bar pct={model.progress.pct} tone={model.progress.tone} tick={model.progress.tick} height={10} />
        </div>
      )}

      {model.stats.length > 0 && (
        <div className="stats">
          {model.stats.map((s) => (
            <div key={s.label} className="stat">
              <span className="caps">{s.label}</span>
              <span className="stat__value" style={s.tone ? { color: toneColor[s.tone] } : undefined}>{s.value}</span>
            </div>
          ))}
        </div>
      )}

      {primary && (
        <div className="row">
          <div className="stepper">
            <button aria-label="less" onClick={() => setAmount((a) => Math.max(0, a - primary.step))}>−</button>
            <span>{amount}{primary.unit ?? ""}</span>
            <button aria-label="more" onClick={() => setAmount((a) => a + primary.step)}>+</button>
          </div>
          <button className="btn btn--ink" onClick={() => onAction(primary.id, { amount })}>
            <Icon name={primary.icon} size={14} />
            {primary.label} {amount}
          </button>
        </div>
      )}

      {model.actions.map((a) => (
        <button
          key={a.id}
          className={`action action--${a.variant}`}
          disabled={a.variant === "locked"}
          onClick={() => onAction(a.id)}
        >
          <Icon name={a.variant === "locked" ? "lock" : a.icon} size={16} />
          <span className="insp__col">
            <span className="action__label">{a.label}</span>
            <span className="action__sub">{a.sub}</span>
          </span>
        </button>
      ))}
    </Card>
  );
}
