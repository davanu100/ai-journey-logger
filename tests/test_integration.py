"""Integration test: full SessionStart → SessionEnd flow with mocked Notion."""

import json
from unittest.mock import MagicMock, patch

from hooks.session_start import run_session_start
from hooks.session_end import run_session_end


def test_full_session_lifecycle(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    pending_file = journey_dir / "pending.jsonl"

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
        "session_id": "integration-test-001",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/Users/testuser/projects/my-app",
    }

    # Phase 1: SessionStart
    with patch("hooks.session_start.get_config", return_value=config):
        with patch("hooks.session_start.get_skills_snapshot", return_value=["skill-a"]):
            with patch("hooks.session_start.Client", return_value=mock_client):
                run_session_start(hook_input)

    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["session_id"] == "integration-test-001"

    # Phase 2: SessionEnd
    with patch("hooks.session_end.get_config", return_value=config):
        with patch("hooks.session_end.Client", return_value=mock_client):
            with patch("hooks.session_end.gather_commits", return_value="abc feat: test"):
                run_session_end(hook_input)

    # Verify Notion was called
    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args[1]
    props = call_kwargs["properties"]
    assert props["session_id"]["title"][0]["text"]["content"] == "integration-test-001"
    assert props["project"]["rich_text"][0]["text"]["content"] == "my-app"
    assert props["commits"]["rich_text"][0]["text"]["content"] == "abc feat: test"

    # State file cleaned up
    assert not state_file.exists()


def test_full_lifecycle_with_notion_failure(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    pending_file = journey_dir / "pending.jsonl"

    failing_client = MagicMock()
    failing_client.pages.create.side_effect = Exception("Network error")

    config = MagicMock(
        journey_dir=journey_dir,
        state_file=state_file,
        pending_file=pending_file,
        notion_token="ntn_test",
        notion_database_id="db-123",
    )

    hook_input = {
        "session_id": "fail-test-001",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/tmp/some-project",
    }

    # SessionStart
    with patch("hooks.session_start.get_config", return_value=config):
        with patch("hooks.session_start.get_skills_snapshot", return_value=[]):
            with patch("hooks.session_start.Client", return_value=failing_client):
                run_session_start(hook_input)

    # SessionEnd with failing Notion
    with patch("hooks.session_end.get_config", return_value=config):
        with patch("hooks.session_end.Client", return_value=failing_client):
            with patch("hooks.session_end.gather_commits", return_value=""):
                run_session_end(hook_input)

    # Entry should be in pending.jsonl
    assert pending_file.exists()
    pending = json.loads(pending_file.read_text().strip())
    assert pending["entry"]["session_id"] == "fail-test-001"

    # Now simulate next session start with working Notion — should retry
    working_client = MagicMock()
    working_client.pages.create.return_value = {"id": "page-1"}

    with patch("hooks.session_start.get_config", return_value=config):
        with patch("hooks.session_start.get_skills_snapshot", return_value=[]):
            with patch("hooks.session_start.Client", return_value=working_client):
                run_session_start({"session_id": "next-session", "transcript_path": "/tmp/t.jsonl", "cwd": "/tmp"})

    # Pending should be cleared
    assert not pending_file.exists()
    working_client.pages.create.assert_called_once()
