"""Reap generation subprocess groups, including tools spawned by an agent."""

import asyncio
import contextlib
import os
import signal


def kill_group(process: asyncio.subprocess.Process) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)


async def reap(process: asyncio.subprocess.Process) -> None:
    kill_group(process)
    await process.wait()
