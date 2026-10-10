"""Paths and defaults for the harness."""

from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = HARNESS_ROOT / "agents.toml"
BENCHMARKS_DIR = Path(__file__).resolve().parent / "benchmarks"
RESULTS_DIR = BENCHMARKS_DIR / "results"
DEFAULT_AGENT = "gemini-flash"
