"""Runs one OpenCode prompt as a subprocess and turns its JSON lines into events."""

import asyncio
import contextlib
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from planworldsimulator_backend.generator.processes import kill_group, reap

log = logging.getLogger(__name__)

# Without these the agent loads the user's global skills and wanders outside the folder.
AGENT_ENV = {
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE": "1",
    "OPENCODE_DISABLE_AUTOUPDATE": "1",
}


@dataclass(frozen=True)
class AgentEvent:
    kind: str  # tool | text | step_finish | error
    tool: str = ""
    path: str = ""  # file the tool touched, relative to the world folder
    status: str = ""  # tool: completed | error
    text: str = ""
    tokens: int = 0


@dataclass
class AgentResult:
    session_id: str | None = None
    ok: bool = False
    timed_out: bool = False
    too_many_calls: bool = False
    text: str = ""
    tokens: int = 0
    tool_calls: int = 0
    seconds: float = 0.0
    error: str = ""

    @property
    def summary(self) -> str:
        if self.timed_out:
            return "timed out"
        if self.too_many_calls:
            return "too many tool calls"
        return self.error or ("done" if self.ok else "failed")


@dataclass(frozen=True)
class AgentConfig:
    binary: str
    model: str
    variant: str
    gemini_api_key: str
    # Extra OpenCode config (permissions) as JSON, passed as OPENCODE_CONFIG_CONTENT.
    config: dict | None = None

    def env(self) -> dict[str, str]:
        env = {**os.environ, **AGENT_ENV}
        env["GOOGLE_GENERATIVE_AI_API_KEY"] = self.gemini_api_key
        if self.config is not None:
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps(self.config)
        return env


def parse_event(line: str, cwd: Path) -> tuple[str | None, AgentEvent | None]:
    """One stdout line → (session id, event). Non-JSON lines are ignored."""
    try:
        raw = json.loads(line)
    except ValueError:
        return None, None
    if not isinstance(raw, dict):
        return None, None
    session = raw.get("sessionID")
    part = raw.get("part") or {}
    kind = raw.get("type")
    if kind == "tool_use":
        state = part.get("state") or {}
        args = state.get("input") or {}
        path = str(args.get("filePath") or args.get("path") or "")
        with contextlib.suppress(ValueError):
            path = str(Path(path).resolve().relative_to(cwd.resolve()))
        return session, AgentEvent(
            "tool",
            tool=str(part.get("tool", "")),
            path=path,
            status=str(state.get("status", "")),
            text=str(state.get("error") or ""),
        )
    if kind == "text":
        return session, AgentEvent("text", text=str(part.get("text", "")))
    if kind == "step_finish":
        tokens = int((part.get("tokens") or {}).get("total") or 0)
        return session, AgentEvent(
            "step_finish", text=str(part.get("reason", "")), tokens=tokens
        )
    if kind == "error":
        return session, AgentEvent(
            "error", text=json.dumps(raw.get("error", raw))[:500]
        )
    return session, None


async def run_agent(
    prompt: str,
    *,
    cwd: Path,
    config: AgentConfig,
    timeout: float,
    max_tool_calls: int = 60,
    session_id: str | None = None,
    files: tuple[Path, ...] = (),
    on_event: Callable[[AgentEvent], None] | None = None,
) -> AgentResult:
    """Send `prompt` to OpenCode in `cwd` and wait for it to finish (or the timeout)."""
    command = [
        config.binary,
        "run",
        "--format",
        "json",
        "--model",
        config.model,
        "--dir",
        str(cwd),
    ]
    if config.variant:
        command += ["--variant", config.variant]
    if session_id:
        command += ["--session", session_id]
    if files:
        # `--file` takes a list, so it goes last (it would swallow the prompt).
        command = [command[0], command[1], prompt, *command[2:]]
        for file in files:
            command += ["--file", str(file)]
    else:
        command.append(prompt)

    result = AgentResult(session_id=session_id)
    started = time.monotonic()
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            start_new_session=True,
            cwd=cwd,
            env=config.env(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1 << 24,
        )
    except OSError as exc:
        result.error = f"cannot start {config.binary}: {exc}"
        return result

    stop_reason = ""
    texts: list[str] = []

    async def read_stdout() -> None:
        nonlocal stop_reason
        assert process.stdout is not None
        async for raw in process.stdout:
            session, event = parse_event(raw.decode(errors="replace"), cwd)
            if session and result.session_id is None:
                result.session_id = session
            if event is None:
                continue
            if event.kind == "tool":
                result.tool_calls += int(event.status in ("completed", "error"))
                if result.tool_calls > max_tool_calls:
                    result.too_many_calls = True
                    kill_group(process)
            elif event.kind == "text":
                texts.append(event.text)
            elif event.kind == "step_finish":
                result.tokens += event.tokens
                stop_reason = event.text
            elif event.kind == "error":
                result.error = event.text
            if on_event is not None:
                on_event(event)

    reader = asyncio.create_task(read_stdout())
    stderr = asyncio.create_task(process.stderr.read()) if process.stderr else None
    try:
        async with asyncio.timeout(timeout):
            await reader
            await process.wait()
    except TimeoutError:
        result.timed_out = True
    finally:
        await reap(process)
        reader.cancel()
        if stderr is not None and not stderr.done():
            stderr.cancel()
        await asyncio.gather(
            reader, *([stderr] if stderr else []), return_exceptions=True
        )
        result.seconds = time.monotonic() - started
        result.text = "".join(texts)

    if stderr is not None and not stderr.cancelled() and not result.error:
        result.error = (
            stderr.result().decode(errors="replace")[-300:]
            if process.returncode
            else ""
        )

    result.ok = (
        process.returncode == 0
        and stop_reason == "stop"
        and not result.timed_out
        and not result.too_many_calls
    )
    if not result.ok and not result.error and process.returncode:
        result.error = f"opencode exited with {process.returncode}"
    log.info(
        "agent finished ok=%s calls=%d tokens=%d in %.0fs",
        result.ok,
        result.tool_calls,
        result.tokens,
        result.seconds,
    )
    return result
