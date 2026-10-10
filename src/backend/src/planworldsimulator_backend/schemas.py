from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from planworldsimulator_backend.generator import LEVELS


class WorldCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    seed: int | None = Field(default=None, ge=0)


class WorldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    prompt: str
    seed: int
    levels: list[int] = list(LEVELS)
    status: str
    storyline: str | None
    path: str | None
    running: bool
    port: int | None
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step: str
    state: str
    message: str
    created_at: datetime
