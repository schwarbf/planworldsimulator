"""Validated shared design; generated contracts are owned by the pipeline."""

import json
import math
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

IDENTIFIER = r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StateField(StrictModel):
    type: Literal["string", "number", "boolean", "object", "array"]
    nullable: bool = False
    properties: dict[str, "StateField"] = Field(default_factory=dict)
    items: "StateField | None" = None
    enum: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def structure(self):
        if (self.type == "array") != (self.items is not None):
            raise ValueError("Only arrays require items")
        if self.properties and self.type != "object":
            raise ValueError("Only objects have properties")
        if self.enum and self.type != "string":
            raise ValueError("Only strings have enum values")
        return self

    def check(self, value: Any, path="state") -> None:
        if value is None and self.nullable:
            return
        valid = {
            "string": isinstance(value, str),
            "number": isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value),
            "boolean": type(value) is bool,
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
        }
        if not valid[self.type]:
            raise ValueError(
                f"{path}: expected {self.type}{' or null' if self.nullable else ''}"
            )
        if self.enum and value not in self.enum:
            raise ValueError(f"{path}: expected one of {self.enum}")
        if self.type == "object":
            assert isinstance(value, dict)
            if set(value) != set(self.properties):
                raise ValueError(
                    f"{path}: fields differ "
                    f"(missing {set(self.properties) - set(value)}, "
                    f"extra {set(value) - set(self.properties)})"
                )
            for key, field in self.properties.items():
                field.check(value[key], f"{path}.{key}")
        elif self.type == "array":
            assert isinstance(value, list)
            assert self.items is not None
            for i, item in enumerate(value):
                self.items.check(item, f"{path}[{i}]")

    def typescript(self) -> str:
        if self.type == "object":
            text = (
                "{ "
                + "; ".join(
                    f"{json.dumps(k)}: {v.typescript()}"
                    for k, v in self.properties.items()
                )
                + " }"
            )
        elif self.type == "array":
            assert self.items is not None
            text = f"Array<{self.items.typescript()}>"
        elif self.enum:
            text = " | ".join(json.dumps(v) for v in self.enum)
        else:
            text = self.type
        return f"({text}) | null" if self.nullable else text


def scalar(kind, **kwargs):
    return StateField(type=kind, **kwargs)


def obj(**properties):
    return StateField(type="object", properties=properties)


BASE_STATE = {
    "world": obj(
        name=scalar("string"), seed=scalar("string"), difficulty=scalar("string")
    ),
    "week": scalar("number"),
    "weeks": scalar("number"),
    "story": StateField(
        type="object",
        nullable=True,
        properties={
            "tag": scalar("string"),
            "text": scalar("string"),
            "tone": scalar("string", enum=["amber", "mint", "coral"]),
        },
    ),
    "discoveries": obj(
        total=scalar("number"),
        found=scalar("array", items=scalar("string")),
        hidden=scalar("array", items=scalar("string", nullable=True)),
    ),
    "agent": obj(
        experiment=scalar("number"),
        experiments=scalar("number"),
        mode=scalar("string", enum=["you", "agent"]),
        scores=scalar("array", items=scalar("number")),
        baseline=scalar("number"),
        now=scalar("string"),
        code=scalar("string"),
    ),
    "active": scalar("string", nullable=True),
    "done": scalar("boolean"),
}


class Site(StrictModel):
    id: str = Field(pattern=IDENTIFIER)
    description: str = Field(min_length=1)
    tile: tuple[int, int]


class Argument(StrictModel):
    type: Literal["string", "number", "integer", "boolean"]
    limits: str = Field(min_length=1)


class Action(StrictModel):
    name: str = Field(pattern=IDENTIFIER)
    arguments: dict[str, Argument]
    description: str = Field(min_length=1)


class Level(StrictModel):
    sites: list[str] = Field(min_length=2, max_length=4)
    actions: list[str] = Field(min_length=1, max_length=5)
    rules: str = Field(min_length=1)


class Visual(StrictModel):
    palette: dict[str, str] = Field(min_length=4, max_length=5)
    grid_size: int = Field(ge=6, le=8)
    objects: list[str] = Field(min_length=8)
    animation: str = Field(min_length=1)


class WorldSpec(StrictModel):
    storyline: str = Field(min_length=1)
    weeks: int = Field(ge=12, le=16)
    sites: list[Site] = Field(min_length=2, max_length=4)
    actions: list[Action] = Field(min_length=1, max_length=5)
    levels: dict[Literal["easy", "medium", "hard"], Level]
    hidden_rules: list[str] = Field(min_length=3, max_length=3)
    demand: str = Field(min_length=1)
    scoring: str = Field(min_length=1)
    state_fields: dict[str, StateField] = Field(default_factory=dict)
    state_sample: dict
    visual: Visual

    @property
    def state(self) -> StateField:
        return StateField(type="object", properties=BASE_STATE | self.state_fields)

    @model_validator(mode="after")
    def consistent(self):
        if set(self.state_fields) & set(BASE_STATE):
            raise ValueError("state_fields must contain only additional world fields")
        self.state.check(self.state_sample)
        if self.state_sample["weeks"] != self.weeks:
            raise ValueError("state_sample.weeks must match weeks")
        sites = {s.id for s in self.sites}
        actions = {a.name for a in self.actions}
        if len(sites) != len(self.sites) or len(actions) != len(self.actions):
            raise ValueError("Site and action names must be unique")
        if set(self.levels) != {"easy", "medium", "hard"}:
            raise ValueError("Provide all three levels")
        previous_sites: set[str] = set()
        previous_actions: set[str] = set()
        for name in ("easy", "medium", "hard"):
            level = self.levels[name]
            if not set(level.sites) <= sites or not set(level.actions) <= actions:
                raise ValueError(f"{name}: unknown site or action")
            if not previous_sites <= set(level.sites) or not previous_actions <= set(
                level.actions
            ):
                raise ValueError("Levels must progressively enable sites and actions")
            previous_sites, previous_actions = set(level.sites), set(level.actions)
        if (
            previous_sites != sites
            or previous_actions != actions
            or len(self.levels["easy"].sites) != 2
        ):
            raise ValueError("Easy uses two sites; Hard enables all sites and actions")
        for site in self.sites:
            if any(c < 0 or c >= self.visual.grid_size for c in site.tile):
                raise ValueError("Site tile lies outside grid")
        if any(
            not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
            for color in self.visual.palette.values()
        ):
            raise ValueError("Palette values must be hex colours")
        return self

    def markdown(self) -> str:
        sections = {
            "Storyline": self.storyline,
            "Sites": "\n".join(
                f"- `{s.id}` — {s.description}, tile {s.tile}" for s in self.sites
            ),
            "Actions": json.dumps([a.model_dump() for a in self.actions], indent=2),
            "Hidden rules": "\n".join(self.hidden_rules),
            "Demand": self.demand,
            "Levels": json.dumps(
                {k: v.model_dump() for k, v in self.levels.items()}, indent=2
            ),
            "Scoring": f"Episode: {self.weeks} weeks.\n{self.scoring}",
            "UI state": "```json\n" + json.dumps(self.state_sample, indent=2) + "\n```",
            "Visual concept": json.dumps(self.visual.model_dump(), indent=2),
        }
        return "\n\n".join(f"## {k}\n{v}" for k, v in sections.items()) + "\n"

    def write_contract(self, world_dir: Path) -> None:
        (world_dir / "design.md").write_text(self.markdown())
        text = (
            "// Generated from design.json; edited only by the generation pipeline.\n"
        )
        text += f"export type State = {self.state.typescript()};\n"
        sample = json.dumps(self.state_sample, indent=2)
        text += f"export const mockState: State = {sample};\n"
        (world_dir / "ui/src/WorldState.ts").write_text(text)
