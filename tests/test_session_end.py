import json
import os
import subprocess
from datetime import datetime as real_datetime, timezone as real_timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from hooks.session_end import run_session_end, gather_commits, compute_duration_minutes


def test_gather_commits_returns_log(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, capture_output=True)

    result = gather_commits(str(tmp_path), "2000-01-01T00:00:00Z")
    assert "initial commit" in result


def test_gather_commits_empty_for_non_git_dir(tmp_path):
    result = gather_commits(str(tmp_path), "2000-01-01T00:00:00Z")
    assert result == ""


def test_gather_commits_truncates_to_2000():
    long_output = "x" * 3000
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=long_output, returncode=0)
        result = gather_commits("/some/dir", "2000-01-01T00:00:00Z")
    assert len(result) == 2000


def test_compute_duration_minutes():
    assert compute_duration_minutes("2026-03-19T10:00:00+05:30", "2026-03-19T10:45:00+05:30") == 45


def test_compute_duration_minutes_rounds_up():
    assert compute_duration_minutes("2026-03-19T10:00:00+05:30", "2026-03-19T10:10:30+05:30") == 11


def test_session_end_pushes_to_notion(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    state_file.write_text(json.dumps({
        "session_id": "test-session-001",
        "start_time": "2026-03-19T10:00:00+05:30",
        "skills_snapshot": [],
    }))
    pending_file = tmp_journey_dir / "pending.jsonl"

    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-1"}

    fake_now = real_datetime(2026, 3, 19, 10, 45, 0, tzinfo=real_timezone.utc)

    with patch("hooks.session_end.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=pending_file,
            notion_token="ntn_test",
            notion_database_id="db-123",
        )
        with patch("hooks.session_end.Client", return_value=mock_client):
            with patch("hooks.session_end.gather_commits", return_value="abc feat: something"):
                with patch("hooks.session_end.datetime") as mock_dt:
                    mock_dt.now.return_value.astimezone.return_value = fake_now
                    mock_dt.fromisoformat = real_datetime.fromisoformat
                    run_session_end(sample_hook_input)

    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args[1]
    props = call_kwargs["properties"]
    assert props["session_id"]["title"][0]["text"]["content"] == "test-session-001"
    assert props["date"]["date"]["start"] == "2026-03-19"
    assert props["project"]["rich_text"][0]["text"]["content"] == "my-app"
    assert not state_file.exists()


def test_session_end_skips_if_no_state_file(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    with patch("hooks.session_end.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=tmp_journey_dir / "pending.jsonl",
            notion_token="ntn_test",
            notion_database_id="db-123",
        )
        run_session_end(sample_hook_input)


def test_session_end_skips_if_no_notion_token(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    state_file.write_text(json.dumps({
        "session_id": "test-session-001",
        "start_time": "2026-03-19T10:00:00+05:30",
        "skills_snapshot": [],
    }))
    with patch("hooks.session_end.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=tmp_journey_dir / "pending.jsonl",
            notion_token=None,
            notion_database_id=None,
        )
        with patch("hooks.session_end.datetime") as mock_dt:
            fake_now = real_datetime(2026, 3, 19, 11, 0, 0, tzinfo=real_timezone.utc)
            mock_dt.now.return_value.astimezone.return_value = fake_now
            mock_dt.fromisoformat = real_datetime.fromisoformat
            with patch("hooks.session_end.gather_commits", return_value=""):
                run_session_end(sample_hook_input)

    assert not state_file.exists()
