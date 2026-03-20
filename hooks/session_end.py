"""SessionEnd hook — gathers automated fields and pushes entry to Notion."""

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from notion_client import Client

from lib.config import get_config
from lib.state import read_state
from lib.notion_push import push_entry
from lib.transcript import parse_transcript
from hooks.session_start import get_skills_snapshot


def gather_commits(cwd: str, since: str) -> str:
    """Run git log since session start, return truncated output."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", f"--since={since}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return ""
        output = result.stdout.strip()
        return output[:2000]
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def compute_duration_minutes(start_iso: str, end_iso: str) -> int:
    """Compute duration in minutes between two ISO timestamps, rounded up."""
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    delta = end - start
    return math.ceil(delta.total_seconds() / 60)


def run_session_end(hook_input: dict) -> None:
    config = get_config()
    state = read_state(config.state_file)

    if state is None:
        print("No state file found, skipping.", file=sys.stderr)
        return

    if state["session_id"] != hook_input.get("session_id"):
        print(f"Session ID mismatch: state={state['session_id']} hook={hook_input.get('session_id')}", file=sys.stderr)
        config.state_file.unlink(missing_ok=True)
        return

    now = datetime.now(timezone.utc).astimezone()
    now_iso = now.isoformat()
    duration = compute_duration_minutes(state["start_time"], now_iso)

    cwd = hook_input.get("cwd", ".")
    commits = gather_commits(cwd, state["start_time"])
    project = Path(cwd).name

    # Parse transcript
    transcript_path = hook_input.get("transcript_path", "")
    if transcript_path:
        transcript_data = parse_transcript(Path(transcript_path))
    else:
        transcript_data = {
            "initial_prompt": "", "model": "", "message_count": 0,
            "tools_used": [], "skills_invoked": [], "skill_counts": [],
            "agents_dispatched": [], "agent_counts": [],
        }

    # Detect new skills
    old_skills = set(state.get("skills_snapshot", []))
    current_skills = set(get_skills_snapshot())
    new_skills = sorted(current_skills - old_skills)
    skills_created = ", ".join(new_skills) if new_skills else ""

    # Build entry
    entry = {
        "session_id": state["session_id"],
        "date": now.strftime("%Y-%m-%d"),
        "project": project,
        "commits": commits,
        "duration_minutes": duration,
        "skills_created": skills_created,
        **transcript_data,
    }

    # Merge manual fields if present
    manual = state.get("manual", {})
    if manual:
        entry.update(manual)

    # Push to Notion if configured
    if config.notion_token and config.notion_database_id:
        client = Client(auth=config.notion_token)
        push_entry(client, config.notion_database_id, entry, config.pending_file)
    else:
        print("Notion not configured, skipping push.", file=sys.stderr)

    config.state_file.unlink(missing_ok=True)


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        run_session_end(hook_input)
    except Exception as e:
        print(f"SessionEnd hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
