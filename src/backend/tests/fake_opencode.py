#!/usr/bin/env python3
"""Stands in for `opencode run --format json`: writes design.md, changes nothing else.

Behaviour is chosen with the FAKE_OPENCODE environment variable:
  (unset)   a valid design on the design prompt, nothing on the others
  hang      never answers
  chatty    makes 5 tool calls, then stops
  tamper    also edits a [base] file
  silent    answers but writes nothing
"""

import json
import os
import sys
import time

DESIGN = """## Storyline
A tiny shop. Make money.

## Sites
- shop

## Actions
- invest(amount)

## Hidden rules
- none

## Demand
- seasonality

## Levels
easy medium hard

## Scoring
profit

## UI state
{}

## Visual concept
one house
"""


def emit(kind, **part):
    print(
        json.dumps(
            {"type": kind, "sessionID": "ses_fake", "timestamp": 0, "part": part}
        ),
        flush=True,
    )


def main():
    args = sys.argv[1:]
    cwd = args[args.index("--dir") + 1]
    prompt = args[-1]
    mode = os.environ.get("FAKE_OPENCODE", "")
    if mode == "hang":
        time.sleep(600)
    emit("step_start")
    if mode == "chatty":
        for i in range(5):
            emit(
                "tool_use",
                tool="read",
                state={"status": "completed", "input": {"filePath": f"{cwd}/x{i}"}},
            )
    if (
        mode != "silent"
        and "`design.md`" in prompt
        and "Write exactly one file" in prompt
    ):
        with open(f"{cwd}/design.md", "w") as f:
            f.write(DESIGN)
        emit(
            "tool_use",
            tool="write",
            state={"status": "completed", "input": {"filePath": f"{cwd}/design.md"}},
        )
    if mode == "tamper":
        with open(f"{cwd}/server/api.py", "a") as f:
            f.write("\n# tampered\n")
    emit("text", text="done")
    emit("step_finish", reason="stop", tokens={"total": 123})


main()
