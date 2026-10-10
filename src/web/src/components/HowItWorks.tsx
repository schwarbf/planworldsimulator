import { Section } from "./Section";

const STEPS = [
  {
    n: "01",
    title: "You describe it",
    body: "A paragraph is enough: the setting, what the agent has to achieve, and what it should not be told up front.",
  },
  {
    n: "02",
    title: "A coding agent builds it",
    body: "It writes a storyline, copies the base template, then fills in the simulator, the MCP tools and the world view. Tests run before the world is marked ready.",
  },
  {
    n: "03",
    title: "Agents plan inside it",
    body: "The harness only sees the world's MCP tools. It probes, forms hypotheses, acts, and gets scored against hidden dynamics.",
  },
];

export function HowItWorks() {
  return (
    <Section
      id="how"
      index="02"
      label="How it works"
      title={
        <>
          One paragraph in, a <em>self-contained</em> world out.
        </>
      }
    >
      <ol className="grid gap-x-10 gap-y-8 md:grid-cols-3">
        {STEPS.map((step) => (
          <li key={step.n} className="border-t border-ink pt-4">
            <p className="font-mono text-xs text-muted">{step.n}</p>
            <h3 className="mt-2 font-display text-2xl">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {step.body}
            </p>
          </li>
        ))}
      </ol>
      <figure className="mt-12">
        <img
          src="/showcase/fission-ops.png"
          alt="Fission Ops control room, a generated PlanBench world"
          className="w-full rounded-xl border border-line shadow-card"
          loading="lazy"
        />
        <figcaption className="mt-3 font-mono text-xs text-muted">
          Fig. 1 · Fission Ops, generated from a single paragraph. Branding and
          controls are shared by every world; the map and the rules are new each
          time.
        </figcaption>
      </figure>
    </Section>
  );
}
