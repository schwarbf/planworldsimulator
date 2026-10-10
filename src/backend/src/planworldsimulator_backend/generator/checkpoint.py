"""Hash-verified retry artifacts, kept beside (never inside) published worlds."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from planworldsimulator_backend.generator import models, workspace
from planworldsimulator_backend.generator.base import GenerationRequest
from planworldsimulator_backend.generator.gates import GateResult


def hashes(root: Path, files) -> dict[str, str]:
    return {
        f: hashlib.sha256((root / f).read_bytes()).hexdigest()
        for f in files
        if (root / f).is_file()
    }


def fingerprint(request: GenerationRequest, template: Path, settings) -> str:
    # Include implementation/prompts so saved checks cannot survive changed semantics.
    generator = Path(__file__).parent
    payload = {
        "request": [request.world_id, request.title, request.prompt, request.seed],
        "model": [(m := models.resolve(request.model, settings)).opencode, m.variant],
        "template": hashes(template, [p.as_posix() for p in workspace._walk(template)]),
        "generator": hashes(
            generator,
            [
                p.relative_to(generator).as_posix()
                for p in generator.rglob("*")
                if p.suffix in (".py", ".md")
            ],
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class Checkpoint:
    def __init__(self, world_dir: Path, identity: str):
        self.root = world_dir
        self.path = world_dir.parent / ".generation" / f"{world_dir.name}.json"
        self.identity = identity
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            data = {}
        self.data = (
            data
            if data.get("identity") == identity
            else {"identity": identity, "stages": {}}
        )

    def valid(self, stage: str, files) -> bool:
        entry = self.data["stages"].get(stage)
        current = hashes(self.root, files)
        return bool(entry and len(current) == len(files) and current == entry["files"])

    def save(self, stage: str, files, results: list[GateResult] | None = None) -> None:
        self.data["stages"][stage] = {
            "files": hashes(self.root, files),
            "results": [asdict(r) for r in results or []],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2))
        temporary.replace(self.path)

    def results(self, stage: str) -> list[GateResult]:
        return [GateResult(**r) for r in self.data["stages"][stage]["results"]]
