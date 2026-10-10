import type { ReactNode } from "react";

interface Props {
  id: string;
  index: string;
  label: string;
  title: ReactNode;
  children: ReactNode;
}

export function Section({ id, index, label, title, children }: Props) {
  return (
    <section
      id={id}
      className="scroll-mt-4 border-t border-line px-5 pt-10 sm:px-8 lg:px-12"
    >
      <p className="font-mono text-xs tracking-wide text-muted uppercase">
        {index} · {label}
      </p>
      <h2 className="mt-3 max-w-3xl font-display text-4xl leading-[1.05] sm:text-5xl">
        {title}
      </h2>
      <div className="mt-10">{children}</div>
    </section>
  );
}
