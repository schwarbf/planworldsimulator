import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class World(Base):
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(Integer)
    # queued | generating | ready | failed | exists (the name was taken)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    generation_attempt: Mapped[int] = mapped_column(Integer, default=1)
    # generator.models id the world is generated with; NULL = the configured default
    generation_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storyline: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(32), nullable=True)
    running: Mapped[bool] = mapped_column(default=False)
    featured: Mapped[bool] = mapped_column(default=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_played_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # SHA-256 of the anonymous creator cookie; never exposed.
    creator_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class WorldEvent(Base):
    __tablename__ = "world_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id"), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    elapsed_seconds: Mapped[float] = mapped_column(default=0.0)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    step: Mapped[str] = mapped_column(String(32))
    # started | done | failed
    state: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text, default="")

    @property
    def kind(self) -> str | None:
        """For live-log lines (state "trace"): write, edit, read, run, text, ok, bad."""
        if self.state != "trace" or not self.metrics:
            return None
        return json.loads(self.metrics).get("trace")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
