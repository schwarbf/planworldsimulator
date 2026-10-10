"""`harness play <url>`, `harness bench <suite>`, `harness report <run-dir>`,
`harness serve` (start agents from the world UI)."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from planworldsimulator_harness.agents import get_agent
from planworldsimulator_harness.benchmarks.benchmark import load_suite, run_suite
from planworldsimulator_harness.benchmarks.report import report
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.config import DEFAULT_AGENT
from planworldsimulator_harness.episode import run_episode
from planworldsimulator_harness.serve import (
    DEFAULT_PACE,
    DEFAULT_PORT,
    Runner,
    create_app,
)


def main() -> None:
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    parser = argparse.ArgumentParser(prog="harness")
    sub = parser.add_subparsers(dest="command", required=True)
    play = sub.add_parser("play", help="play one episode on a running world")
    play.add_argument("url", help="world server, e.g. http://127.0.0.1:8000")
    play.add_argument("--agent", default=DEFAULT_AGENT)
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--difficulty", default="medium")
    play.add_argument("--tokens", type=int, default=Budget.tokens)
    play.add_argument("--seconds", type=float, default=Budget.seconds)
    bench = sub.add_parser("bench", help="run a benchmark suite")
    bench.add_argument("suite", help="suite name (e.g. smoke) or path to a .toml")
    bench.add_argument("--agent", help="run only this agent of the suite")
    rep = sub.add_parser("report", help="markdown table for a finished run")
    rep.add_argument("run_dirs", type=Path, nargs="+", help="one or more run dirs")
    serve = sub.add_parser("serve", help="start/stop agents from the world UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument(
        "--pace", type=float, default=DEFAULT_PACE, help="seconds per tool call"
    )
    serve.add_argument("--tokens", type=int, default=Budget.tokens)
    serve.add_argument("--seconds", type=float, default=Budget.seconds)
    args = parser.parse_args()

    if args.command == "play":
        budget = Budget(args.tokens, args.seconds)
        agent = get_agent(args.agent)
        result = asyncio.run(
            run_episode(args.url, agent, args.seed, args.difficulty, budget)
        )
        print(json.dumps(result.to_dict(), indent=2))
    elif args.command == "bench":
        run_dir = asyncio.run(run_suite(load_suite(args.suite, args.agent)))
        print(f"\n{report(run_dir)}\nResults: {run_dir}")
    elif args.command == "serve":
        import uvicorn

        runner = Runner(Budget(args.tokens, args.seconds), pace=args.pace)
        uvicorn.run(create_app(runner), host=args.host, port=args.port)
    else:
        print(report(*args.run_dirs))


if __name__ == "__main__":
    main()
