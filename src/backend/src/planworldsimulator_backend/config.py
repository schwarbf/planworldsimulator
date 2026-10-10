from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANWORLDSIMULATOR_")

    database_url: str = "sqlite+aiosqlite:///./data/planworldsimulator.db"
    worlds_dir: Path = Path("src/worlds")
    template_dir: Path = Path("src/worlds-template")
    # Pause between fake generation steps, so progress is visible in the UI.
    step_delay_seconds: float = 1.0
    host: str = "0.0.0.0"
    port: int = 8000
