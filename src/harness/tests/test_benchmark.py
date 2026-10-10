import json

from planworldsimulator_harness.benchmarks.benchmark import load_suite
from planworldsimulator_harness.benchmarks.report import report


def test_smoke_suite_loads():
    suite = load_suite("smoke")
    assert suite.world == "bike-factory"
    assert suite.seeds == [1]
    assert suite.budget.tokens == 2_000_000


def test_report_has_one_row_per_agent(tmp_path):
    base = {"input_tokens": 900, "output_tokens": 100, "tool_calls": 5, "seconds": 3}
    rows = [
        {**base, "agent": "a", "score": 0.6, "baseline": 0.5, "stopped_by": "done"},
        {**base, "agent": "a", "score": 0.4, "baseline": 0.5, "stopped_by": "limit"},
        {**base, "agent": "b", "score": 0.9, "baseline": 0.5, "stopped_by": "done"},
    ]
    (tmp_path / "episodes.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )
    text = report(tmp_path)
    assert "| a | 2 | 0.500 | 0.500 | +0.000 | 1k | 5 | 3 | done 1, limit 1 |" in text
    assert "| b | 1 | 0.900 |" in text
    assert (tmp_path / "report.md").exists()
