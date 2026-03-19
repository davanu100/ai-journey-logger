import json
import sys
from pathlib import Path


def build_properties(entry: dict) -> dict:
    """Build Notion page properties from an entry dict."""
    commits = entry.get("commits", "")
    if len(commits) > 2000:
        commits = commits[:2000]

    props = {
        "session_id": {
            "title": [{"text": {"content": entry["session_id"]}}],
        },
        "date": {
            "date": {"start": entry["date"]},
        },
        "project": {
            "rich_text": [{"text": {"content": entry.get("project", "")}}],
        },
        "commits": {
            "rich_text": [{"text": {"content": commits}}],
        },
        "duration_minutes": {
            "number": entry.get("duration_minutes"),
        },
    }
    return props


def push_entry(
    notion_client,
    database_id: str,
    entry: dict,
    pending_file: Path,
) -> bool:
    """Push an entry to Notion. On failure, append to pending_file."""
    try:
        properties = build_properties(entry)
        notion_client.pages.create(
            parent={"database_id": database_id},
            properties=properties,
        )
        return True
    except Exception as e:
        print(f"Notion API failed: {e}", file=sys.stderr)
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_file, "a") as f:
            f.write(json.dumps({"database_id": database_id, "entry": entry}) + "\n")
        return False


def retry_pending(notion_client, pending_file: Path) -> None:
    """Retry pushing any entries in pending_file to Notion."""
    if not pending_file.exists():
        return

    lines = pending_file.read_text().strip().split("\n")
    failed = []

    for line in lines:
        if not line.strip():
            continue
        pending = json.loads(line)
        try:
            properties = build_properties(pending["entry"])
            notion_client.pages.create(
                parent={"database_id": pending["database_id"]},
                properties=properties,
            )
        except Exception:
            failed.append(line)

    if failed:
        pending_file.write_text("\n".join(failed) + "\n")
    else:
        pending_file.unlink(missing_ok=True)
