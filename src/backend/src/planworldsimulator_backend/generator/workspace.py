"""The world folder: copy the template, name what the agent may write."""

import hashlib
import shutil
from pathlib import Path

# Files the generator writes ([gen], decision 0003), by the owning agent track.
DESIGN_FILES = ("design.json",)
CONTRACT_FILES = frozenset({"design.md", "ui/src/WorldState.ts"})
SIM_FILES = (
    "brief.md",
    "secret.md",
    "sim/env.py",
    "sim/rules.py",
    "sim/demand_config.py",
    "server/mcp.py",
    "tests/backend/test_rules.py",
)
UI_FILES = ("ui/src/World.tsx",)
GEN_FILES = frozenset(DESIGN_FILES + SIM_FILES + UI_FILES) | CONTRACT_FILES

# Never copied or checksummed: build output, caches and what the generator adds.
SKIP_DIRS = {
    "node_modules",
    ".pixi",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "__samples__",
    ".vite-cache",
    "reference",
    ".opencode",
}
SKIP_SUFFIXES = (".tsbuildinfo", ".pyc")
EXTRA_FILES = {"world.json", "thumbnail.png", "opencode.json"}


def _skipped(rel: Path) -> bool:
    return (
        any(part in SKIP_DIRS for part in rel.parts)
        or rel.name.endswith(SKIP_SUFFIXES)
        or rel.as_posix() in EXTRA_FILES
    )


def _walk(root: Path):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_file() and not _skipped(rel):
            yield rel


def copy_template(
    template_dir: Path,
    world_dir: Path,
    reference_dir: Path | None,
    node_modules: Path | None = None,
) -> None:
    """Copy the template (and a read-only reference world) into the world folder.

    The shared `ui/node_modules` is linked in, so no install is needed.
    """
    world_dir.mkdir(parents=True, exist_ok=True)
    for rel in _walk(template_dir):
        target = world_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_dir / rel, target)
    if reference_dir is not None and reference_dir.is_dir():
        reference = world_dir / "reference"
        for rel in _walk(reference_dir):
            target = reference / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(reference_dir / rel, target)
    link_node_modules(template_dir, world_dir, node_modules)


def link_node_modules(
    template_dir: Path, world_dir: Path, node_modules: Path | None = None
) -> None:
    shared = node_modules or template_dir / "ui" / "node_modules"
    link = world_dir / "ui" / "node_modules"
    if shared.is_dir() and not link.exists():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(shared.resolve(), target_is_directory=True)


def remove_reference(world_dir: Path) -> None:
    shutil.rmtree(world_dir / "reference", ignore_errors=True)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_files(template_dir: Path) -> list[str]:
    """Template files the agent must not change: everything that is not a [gen] file."""
    return [
        rel.as_posix() for rel in _walk(template_dir) if rel.as_posix() not in GEN_FILES
    ]


def changed_base_files(template_dir: Path, world_dir: Path) -> list[str]:
    """[base] files that differ from the template or are gone."""
    changed = []
    for rel in base_files(template_dir):
        mine = world_dir / rel
        if not mine.is_file() or _sha(mine) != _sha(template_dir / rel):
            changed.append(rel)
    return changed


def stray_files(template_dir: Path, world_dir: Path) -> list[str]:
    """Files in the world that neither the template nor the generator account for."""
    known = {rel.as_posix() for rel in _walk(template_dir)} | GEN_FILES
    return [
        rel.as_posix()
        for rel in _walk(world_dir)
        if rel.as_posix() not in known
        and not rel.as_posix().startswith("tests/backend/test_gen_")
    ]


def agent_config(world_dir: Path, writable: tuple[str, ...]) -> dict:
    """OpenCode permissions for one agent track.

    Edit patterns are matched against the absolute path without its leading slash.
    """
    root = str(world_dir.resolve()).lstrip("/")
    edit = {"*": "deny"} | {f"{root}/{rel}": "allow" for rel in writable}
    return {
        "$schema": "https://opencode.ai/config.json",
        "share": "disabled",
        "autoupdate": False,
        "permission": {
            "external_directory": "deny",
            "edit": edit,
            "bash": "deny",
            "webfetch": "deny",
            "task": "deny",
            "skill": "deny",
        },
    }
