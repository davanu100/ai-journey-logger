import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    notion_token: str | None
    notion_database_id: str | None
    journey_dir: Path

    @property
    def state_file(self) -> Path:
        return self.journey_dir / ".session-state"

    @property
    def pending_file(self) -> Path:
        return self.journey_dir / "pending.jsonl"


def get_config() -> Config:
    journey_dir_str = os.environ.get("CLAUDE_JOURNEY_DIR")
    journey_dir = Path(journey_dir_str) if journey_dir_str else Path.home() / ".claude-journey"

    return Config(
        notion_token=os.environ.get("NOTION_TOKEN"),
        notion_database_id=os.environ.get("NOTION_DATABASE_ID"),
        journey_dir=journey_dir,
    )
