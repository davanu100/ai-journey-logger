import json
import sys
from pathlib import Path


def build_properties(entry: dict) -> dict:
    """Build Notion page properties from an entry dict (all fields)."""
    commits = entry.get("commits", "")
    if len(commits) > 2000:
        commits = commits[:2000]

    initial_prompt = entry.get("initial_prompt", "")
    if len(initial_prompt) > 500:
        initial_prompt = initial_prompt[:500]

    model_val = entry.get("model", "")

    props = {
        "session_id": {"title": [{"text": {"content": entry["session_id"]}}]},
        "date": {"date": {"start": entry["date"]}},
        "project": {"rich_text": [{"text": {"content": entry.get("project", "")}}]},
        "commits": {"rich_text": [{"text": {"content": commits}}]},
        "duration_minutes": {"number": entry.get("duration_minutes")},
        "model": {"select": {"name": model_val} if model_val else None},
        "initial_prompt": {"rich_text": [{"text": {"content": initial_prompt}}]},
        "tools_used": {"multi_select": [{"name": t} for t in entry.get("tools_used", [])]},
        "skills_invoked": {"multi_select": [{"name": s} for s in entry.get("skills_invoked", [])]},
        "skill_counts": {"rich_text": [{"text": {"content": json.dumps(entry.get("skill_counts", []))}}]},
        "skills_created": {"rich_text": [{"text": {"content": entry.get("skills_created", "")}}]},
        "agents_dispatched": {"multi_select": [{"name": a} for a in entry.get("agents_dispatched", [])]},
        "agent_counts": {"rich_text": [{"text": {"content": json.dumps(entry.get("agent_counts", []))}}]},
        "session_timeline": {"rich_text": [{"text": {"content": entry.get("timeline", "")}}]},
        "message_count": {"number": entry.get("message_count", 0)},
    }

    if "model_fit" in entry:
        props["model_fit"] = {"select": {"name": entry["model_fit"]}}
    if "category" in entry:
        props["category"] = {"select": {"name": entry["category"]}}
    if "mode" in entry:
        props["mode"] = {"select": {"name": entry["mode"]}}
    if "iterations_to_happy" in entry:
        props["iterations_to_happy"] = {"number": entry["iterations_to_happy"]}
    if "iteration_friction" in entry:
        props["iteration_friction"] = {"rich_text": [{"text": {"content": entry["iteration_friction"]}}]}
    if "learned_something" in entry:
        props["learned_something"] = {"rich_text": [{"text": {"content": entry["learned_something"]}}]}
    if "satisfaction" in entry:
        props["satisfaction"] = {"number": entry["satisfaction"]}
    if "publish" in entry:
        props["publish"] = {"checkbox": entry["publish"]}
    if "blog_summary" in entry:
        props["blog_summary"] = {"rich_text": [{"text": {"content": entry["blog_summary"]}}]}

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
