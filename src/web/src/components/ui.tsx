import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

import type { WorldStatus } from "../api/client";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx(
        "rounded-card border border-line bg-card shadow-card",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <p className="text-[10px] font-bold tracking-wide text-muted uppercase">
      {children}
    </p>
  );
}

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
}

export function Chip({ active, className, ...props }: ChipProps) {
  return (
    <button
      type="button"
      className={cx(
        "rounded-chip px-[11px] py-[7px] text-xs font-bold transition-colors",
        active ? "bg-ink text-white" : "bg-sand text-ink hover:bg-line",
        className,
      )}
      {...props}
    />
  );
}

type ButtonVariant = "primary" | "dark" | "soft";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-coral text-white hover:bg-coral-dark",
  dark: "bg-ink text-white hover:bg-ink/90",
  soft: "bg-sand text-ink hover:bg-line",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cx(
        "rounded-xl px-4 py-[11px] text-[13px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}

const STATUS_STYLE: Record<WorldStatus, string> = {
  queued: "bg-sand text-muted",
  generating: "bg-violet-soft text-violet",
  ready: "bg-good-soft text-good",
  failed: "bg-bad-soft text-bad",
};

export function StatusChip({ status }: { status: WorldStatus }) {
  return (
    <span
      className={cx(
        "rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize",
        STATUS_STYLE[status],
      )}
    >
      {status}
    </span>
  );
}
