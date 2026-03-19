"""SessionStart hook — creates state file and retries pending Notion entries."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from notion_client import Client

from lib.config import get_config
from lib.state import write_state
from lib.notion_push import retry_pending

SKILLS_DIR = Path.home() / ".claude" / "skills"


def get_skills_snapshot() -> list[str]:
    """List current skill names (directories and .md files)."""
    if not SKILLS_DIR.exists():
        return []
    names = set()
    for entry in SKILLS_DIR.iterdir():
        if entry.is_dir():
            names.add(entry.name)
        elif entry.suffix == ".md":
            names.add(entry.stem)
    return sorted(names)


def run_session_start(hook_input: dict) -> None:
    config = get_config()
    config.journey_dir.mkdir(parents=True, exist_ok=True)

    # Retry pending entries if Notion is configured
    if config.notion_token and config.notion_database_id:
        client = Client(auth=config.notion_token)
        retry_pending(client, config.pending_file)

    # Create state file
    now = datetime.now(timezone.utc).astimezone().isoformat()
    write_state(
        path=config.state_file,
        session_id=hook_input["session_id"],
        start_time=now,
        skills_snapshot=get_skills_snapshot(),
    )


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        run_session_start(hook_input)
    except Exception as e:
        print(f"SessionStart hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
