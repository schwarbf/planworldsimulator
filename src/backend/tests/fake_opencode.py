#!/usr/bin/env python3
"""Stands in for `opencode run --format json`: writes design.json, changes nothing else.

Behaviour is chosen with the FAKE_OPENCODE environment variable:
  (unset)   a valid design on the design prompt, nothing on the others
  hang      never answers
  chatty    makes 5 tool calls, then stops
  tamper    also edits a [base] file
  silent    answers but writes nothing
  badjson   first writes broken JSON, then a valid design once asked to fix it
"""

import json
import os
import sys
import time


def _num():
    return {"type": "number"}


SPEC = {
    "storyline": "A tiny shop. Make money.",
    "weeks": 12,
    "sites": [
        {"id": "shop", "description": "the shop", "tile": [1, 1]},
        {"id": "outlet", "description": "a second outlet", "tile": [3, 3]},
    ],
    "actions": [
        {
            "name": "invest",
            "arguments": {"amount": {"type": "integer", "limits": "1 to 10"}},
            "description": "add capacity",
        }
    ],
    "levels": {
        name: {"sites": ["shop", "outlet"], "actions": ["invest"], "rules": name}
        for name in ("easy", "medium", "hard")
    },
    "hidden_rules": ["rule one", "rule two", "rule three"],
    "demand": "seasonality",
    "scoring": "profit",
    "state_fields": {
        "cash": _num(),
        "capacity": _num(),
        "demand": _num(),
        "profit": _num(),
        "target": _num(),
    },
    "state_sample": {
        "world": {"name": "Shop", "seed": "1", "difficulty": "Easy"},
        "week": 1,
        "weeks": 12,
        "story": None,
        "discoveries": {"total": 0, "found": [], "hidden": []},
        "agent": {
            "experiment": 1,
            "experiments": 20,
            "mode": "you",
            "scores": [0],
            "baseline": 0.5,
            "now": "x",
            "code": "x",
        },
        "active": None,
        "done": False,
        "cash": 1000,
        "capacity": 10,
        "demand": 30,
        "profit": 0,
        "target": 100,
    },
    "visual": {
        "palette": {"a": "#112233", "b": "#223344", "c": "#334455", "d": "#445566"},
        "grid_size": 6,
        "objects": ["Tree"] * 8,
        "animation": "clouds",
    },
}


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
    is_design = "game designer" in prompt or "does not pass validation" in prompt
    if mode != "silent" and is_design:
        with open(f"{cwd}/design.json", "w") as f:
            if mode == "badjson" and "does not pass validation" not in prompt:
                f.write(json.dumps(SPEC) + "}")
            else:
                json.dump(SPEC, f)
        emit(
            "tool_use",
            tool="write",
            state={"status": "completed", "input": {"filePath": f"{cwd}/design.json"}},
        )
    if mode == "tamper":
        with open(f"{cwd}/server/api.py", "a") as f:
            f.write("\n# tampered\n")
    emit("text", text="done")
    emit("step_finish", reason="stop", tokens={"total": 123})


main()
