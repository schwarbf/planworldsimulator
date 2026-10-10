"""Prompt templates (generator/prompts/*.md) filled with the world's own files."""

import ast
import re
from pathlib import Path
from string import Template

PROMPTS = Path(__file__).parent / "prompts"


def render(name: str, **values: str) -> str:
    return Template((PROMPTS / f"{name}.md").read_text()).safe_substitute(values)


def read(world_dir: Path, rel: str) -> str:
    return (world_dir / rel).read_text()


def fenced(world_dir: Path, rel: str) -> str:
    lang = {".py": "python", ".tsx": "tsx", ".md": "markdown"}.get(Path(rel).suffix, "")
    return f"### {rel}\n```{lang}\n{read(world_dir, rel).rstrip()}\n```"


def demand_api(world_dir: Path) -> str:
    """Signatures and docstrings of the public names in sim/demand.py."""
    tree = ast.parse(read(world_dir, "sim/demand.py"))
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            out.append(f"def {node.name}({ast.unparse(node.args)}){returns}:")
            doc = ast.get_docstring(node)
            out.append(f'    """{doc}"""' if doc else "    ...")
        elif isinstance(node, ast.ClassDef):
            out.append(f"class {node.name}:")
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    out.append(f"    {ast.unparse(item)}")
                elif isinstance(item, ast.FunctionDef) and not item.name.startswith(
                    "_"
                ):
                    returns = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                    out.append(
                        f"    def {item.name}({ast.unparse(item.args)}){returns}: ..."
                    )
    return "```python\n" + "\n".join(out) + "\n```"


def section(markdown: str, heading: str) -> str:
    """The text under `## heading` (until the next `## `), or an empty string."""
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", markdown, re.S | re.M
    )
    return match.group(1).strip() if match else ""


REQUIRED_DESIGN_SECTIONS = (
    "Storyline",
    "Sites",
    "Actions",
    "Hidden rules",
    "Demand",
    "Levels",
    "Scoring",
    "UI state",
    "Visual concept",
)


def missing_sections(markdown: str) -> list[str]:
    return [h for h in REQUIRED_DESIGN_SECTIONS if not section(markdown, h)]
