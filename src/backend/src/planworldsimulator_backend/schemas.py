from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from planworldsimulator_backend.generator import LEVELS


class WorldCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    prompt: str = Field(min_length=3, max_length=4000)
    seed: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("name must be at least 2 characters")
        return value


class WorldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    prompt: str
    seed: int
    levels: list[int] = list(LEVELS)
    status: str
    generation_attempt: int
    storyline: str | None
    path: str | None
    duplicate_of: str | None = None
    running: bool
    port: int | None
    featured: bool
    play_count: int
    mine: bool = False
    created_at: datetime
    updated_at: datetime


class WorldPage(BaseModel):
    items: list[WorldOut]
    total: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt: int
    elapsed_seconds: float
    step: str
    state: str
    message: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value
