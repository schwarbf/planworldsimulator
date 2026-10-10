from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorldCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    seed: int | None = Field(default=None, ge=0)
    difficulty: int = Field(default=2, ge=1, le=4)


class WorldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    prompt: str
    seed: int
    difficulty: int
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
