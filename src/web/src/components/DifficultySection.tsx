import { Section } from "./Section";

const LEVELS = ["Easy", "Medium", "Hard", "Expert"];

const ROWS: [string, string[]][] = [
  ["Sites", ["3", "8", "12", "20"]],
  ["Hidden rules", ["1", "3", "5", "8"]],
  ["Shocks", ["none", "rare", "frequent", "chained"]],
  ["Demand", ["steady", "seasonal", "+ trend", "regime shifts"]],
  ["Lead times", ["fixed", "± 1 wk", "± 3 wk", "random + fails"]],
  ["Visibility", ["full map", "fog of war", "+ delayed data", "+ lost sales"]],
  ["Goal", ["profit", "+ service", "+ cash cap", "multi-objective"]],
];

export function DifficultyTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
        <caption className="sr-only">
          Difficulty levels and what changes at each
        </caption>
        <thead>
          <tr className="border-b border-ink">
            <th scope="col" className="py-3 pr-4 font-normal" />
            {LEVELS.map((level, i) => (
              <th
                key={level}
                scope="col"
                className="py-3 pr-4 font-mono text-xs font-medium uppercase"
              >
                L{i + 1} · {level}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([name, cells]) => (
            <tr key={name} className="border-b border-line">
              <th scope="row" className="py-3 pr-4 font-normal text-muted">
                {name}
              </th>
              {cells.map((cell) => (
                <td key={cell} className="py-3 pr-4">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DifficultySection() {
  return (
    <Section
      id="levels"
      index="03"
      label="Difficulty"
      title={
        <>
          Four levels in <em>every</em> world.
        </>
      }
    >
      <div className="grid gap-10 lg:grid-cols-[minmax(0,22rem)_1fr]">
        <p className="leading-relaxed text-muted">
          You never pick a difficulty when you generate a world. Each world
          ships with all four, and the level is chosen when it is played. The
          same story gets more sites, more hidden rules and less visibility as
          you go up, so results stay comparable across levels.
        </p>
        <DifficultyTable />
      </div>
    </Section>
  );
}
