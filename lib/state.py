import json
from pathlib import Path


def write_state(
    path: Path,
    session_id: str,
    start_time: str,
    skills_snapshot: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "session_id": session_id,
        "start_time": start_time,
        "skills_snapshot": skills_snapshot,
    }
    path.write_text(json.dumps(data))


def read_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def update_state_manual_fields(path: Path, manual: dict) -> None:
    data = json.loads(path.read_text())
    if "manual" in data:
        return
    data["manual"] = manual
    path.write_text(json.dumps(data))
