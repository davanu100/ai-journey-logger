"""Test SessionEnd hook with transcript parsing and full properties."""

import json
from datetime import datetime as real_datetime, timezone as real_timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from hooks.session_end import run_session_end

FIXTURES = Path(__file__).parent / "fixtures"


def test_session_end_with_transcript_parsing(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    pending_file = journey_dir / "pending.jsonl"

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "session_id": "sess-rich-test",
        "start_time": "2026-03-20T10:00:00+05:30",
        "skills_snapshot": ["existing-skill"],
    }))

    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-1"}

    config = MagicMock(
        journey_dir=journey_dir,
        state_file=state_file,
        pending_file=pending_file,
        notion_token="ntn_test",
        notion_database_id="db-123",
    )

    hook_input = {
        "session_id": "sess-rich-test",
        "transcript_path": str(FIXTURES / "rich_session.jsonl"),
        "cwd": "/Users/testuser/projects/my-app",
    }

    fake_now = real_datetime(2026, 3, 20, 10, 45, 0, tzinfo=real_timezone.utc)

    with patch("hooks.session_end.get_config", return_value=config):
        with patch("hooks.session_end.Client", return_value=mock_client):
            with patch("hooks.session_end.gather_commits", return_value="abc feat: fix auth"):
                with patch("hooks.session_end.datetime") as mock_dt:
                    mock_dt.now.return_value.astimezone.return_value = fake_now
                    mock_dt.fromisoformat = real_datetime.fromisoformat
                    with patch("hooks.session_end.get_skills_snapshot", return_value=["existing-skill"]):
                        run_session_end(hook_input)

    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args[1]
    props = call_kwargs["properties"]

    assert props["session_id"]["title"][0]["text"]["content"] == "sess-rich-test"
    assert props["project"]["rich_text"][0]["text"]["content"] == "my-app"
    assert props["model"]["select"]["name"] == "opus"
    assert "Help me debug" in props["initial_prompt"]["rich_text"][0]["text"]["content"]
    assert props["message_count"]["number"] == 6
    assert {"name": "Bash"} in props["tools_used"]["multi_select"]
    assert {"name": "Skill"} in props["tools_used"]["multi_select"]
    assert {"name": "superpowers:systematic-debugging"} in props["skills_invoked"]["multi_select"]
    assert {"name": "Explore"} in props["agents_dispatched"]["multi_select"]


def test_session_end_with_manual_fields(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    pending_file = journey_dir / "pending.jsonl"

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "session_id": "sess-manual-test",
        "start_time": "2026-03-20T10:00:00+05:30",
        "skills_snapshot": [],
        "manual": {
            "model_fit": "right",
            "category": "debugging",
            "mode": "guided",
            "iterations_to_happy": 2,
            "iteration_friction": "bad prompt",
            "learned_something": "new pattern",
            "satisfaction": 4,
            "publish": False,
            "blog_summary": "",
        },
    }))

    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-1"}

    config = MagicMock(
        journey_dir=journey_dir,
        state_file=state_file,
        pending_file=pending_file,
        notion_token="ntn_test",
        notion_database_id="db-123",
    )

    hook_input = {
        "session_id": "sess-manual-test",
        "transcript_path": str(FIXTURES / "minimal_session.jsonl"),
        "cwd": "/tmp/project",
    }

    fake_now = real_datetime(2026, 3, 20, 10, 30, 0, tzinfo=real_timezone.utc)

    with patch("hooks.session_end.get_config", return_value=config):
        with patch("hooks.session_end.Client", return_value=mock_client):
            with patch("hooks.session_end.gather_commits", return_value=""):
                with patch("hooks.session_end.datetime") as mock_dt:
                    mock_dt.now.return_value.astimezone.return_value = fake_now
                    mock_dt.fromisoformat = real_datetime.fromisoformat
                    with patch("hooks.session_end.get_skills_snapshot", return_value=[]):
                        run_session_end(hook_input)

    props = mock_client.pages.create.call_args[1]["properties"]
    assert props["model_fit"]["select"]["name"] == "right"
    assert props["category"]["select"]["name"] == "debugging"
    assert props["satisfaction"]["number"] == 4
    assert props["publish"]["checkbox"] is False
