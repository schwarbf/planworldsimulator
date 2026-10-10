"""episodes.jsonl → markdown table, one row per agent."""

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HEADER = (
    "| Agent | Episodes | Score | Baseline | Score − baseline | Tokens | Tool calls "
    "| Seconds | Stopped by |\n|---|---|---|---|---|---|---|---|---|"
)


def report(*run_dirs: Path) -> str:
    """One table over all given runs; also saved as report.md for a single run."""
    rows = [
        json.loads(line)
        for run_dir in run_dirs
        for line in (run_dir / "episodes.jsonl").open()
    ]
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_agent[row["agent"]].append(row)
    lines = [f"# {' + '.join(d.name for d in run_dirs)}", "", HEADER]
    for agent, eps in by_agent.items():
        score = mean(e["score"] for e in eps)
        baseline = mean(e["baseline"] for e in eps)
        tokens = mean(e["input_tokens"] + e["output_tokens"] for e in eps)
        calls = mean(e["tool_calls"] for e in eps)
        seconds = mean(e["seconds"] for e in eps)
        stops = Counter(e["stopped_by"] for e in eps)
        stopped = ", ".join(f"{k} {v}" for k, v in stops.items())
        cells = [
            agent,
            len(eps),
            f"{score:.3f}",
            f"{baseline:.3f}",
            f"{score - baseline:+.3f}",
            f"{tokens / 1e3:.0f}k",
            f"{calls:.0f}",
            f"{seconds:.0f}",
            stopped,
        ]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    text = "\n".join(lines) + "\n"
    if len(run_dirs) == 1:
        (run_dirs[0] / "report.md").write_text(text)
    return text
