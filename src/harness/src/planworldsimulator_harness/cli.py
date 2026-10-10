"""`harness play <url>`: play one episode on a running world and print the result."""

import argparse
import asyncio
import json
import os

from planworldsimulator_harness.agents import get_agent
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.config import DEFAULT_AGENT
from planworldsimulator_harness.episode import run_episode


def main() -> None:
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    parser = argparse.ArgumentParser(prog="harness")
    sub = parser.add_subparsers(dest="command", required=True)
    play = sub.add_parser("play", help="play one episode on a running world")
    play.add_argument("url", help="world server, e.g. http://127.0.0.1:8000")
    play.add_argument("--agent", default=DEFAULT_AGENT)
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--difficulty", default="medium")
    play.add_argument("--tool-calls", type=int, default=Budget.tool_calls)
    play.add_argument("--tokens", type=int, default=Budget.tokens)
    play.add_argument("--seconds", type=float, default=Budget.seconds)
    args = parser.parse_args()

    budget = Budget(args.tool_calls, args.tokens, args.seconds)
    result = asyncio.run(
        run_episode(args.url, get_agent(args.agent), args.seed, args.difficulty, budget)
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
