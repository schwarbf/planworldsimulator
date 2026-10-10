"""A scripted OpenAI-compatible model for running the real `opencode` binary offline.

The prompt says what to do: a line `WRITE <absolute path>` makes the model call
OpenCode's `write` tool for that file; once the tool answered, it replies "done".
Anything else (e.g. OpenCode's title request) gets a short text answer.
"""

import json
import re
import socket
import threading
import time
from collections.abc import Iterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

CONTENT = '{"ok": true}'


def _chunk(delta: dict, finish: str | None = None) -> str:
    body = {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "scripted",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(body)}\n\n"


def _text(text: str) -> Iterator[str]:
    yield _chunk({"role": "assistant", "content": text})
    yield _chunk({}, "stop")
    yield "data: [DONE]\n\n"


def _write(path: str) -> Iterator[str]:
    args = json.dumps({"filePath": path, "content": CONTENT})
    call = {
        "index": 0,
        "id": "call_1",
        "type": "function",
        "function": {"name": "write", "arguments": args},
    }
    yield _chunk({"role": "assistant", "tool_calls": [call]})
    yield _chunk({}, "tool_calls")
    yield "data: [DONE]\n\n"


def _flatten(content: object) -> str:
    if isinstance(content, list):
        return " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
    return str(content or "")


def create_app() -> FastAPI:
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def complete(request: Request) -> StreamingResponse:
        messages = (await request.json()).get("messages", [])
        answered = any(m.get("role") == "tool" for m in messages)
        users = [
            _flatten(m.get("content")) for m in messages if m.get("role") == "user"
        ]
        target = re.search(r"WRITE ([^\s\"'<>]+)", users[-1]) if users else None
        events = _text("done") if answered or not target else _write(target.group(1))
        return StreamingResponse(events, media_type="text/event-stream")

    return app


class FakeModel:
    """Runs the fake model on a free local port, in a background thread."""

    def __init__(self) -> None:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        config = uvicorn.Config(
            create_app(), host="127.0.0.1", port=self.port, log_level="warning"
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def __enter__(self) -> "FakeModel":
        self.thread.start()
        while not self.server.started:
            time.sleep(0.05)
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
