import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from hooks.session_start import run_session_start


def test_session_start_creates_state_file(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    with patch("hooks.session_start.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=tmp_journey_dir / "pending.jsonl",
            notion_token=None,
            notion_database_id=None,
        )
        with patch("hooks.session_start.get_skills_snapshot", return_value=["skill-a"]):
            run_session_start(sample_hook_input)

    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["session_id"] == "test-session-001"
    assert "start_time" in data
    assert data["skills_snapshot"] == ["skill-a"]


def test_session_start_creates_journey_dir(tmp_path, sample_hook_input):
    journey_dir = tmp_path / "new-journey-dir"
    state_file = journey_dir / ".session-state"
    with patch("hooks.session_start.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=journey_dir,
            state_file=state_file,
            pending_file=journey_dir / "pending.jsonl",
            notion_token=None,
            notion_database_id=None,
        )
        with patch("hooks.session_start.get_skills_snapshot", return_value=[]):
            run_session_start(sample_hook_input)

    assert journey_dir.exists()
    assert state_file.exists()


def test_session_start_retries_pending_if_notion_configured(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    pending_file = tmp_journey_dir / "pending.jsonl"
    pending_file.write_text(json.dumps({
        "database_id": "db-123",
        "entry": {"session_id": "old", "date": "2026-03-18", "project": "x", "commits": "", "duration_minutes": 1},
    }) + "\n")

    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-1"}

    with patch("hooks.session_start.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=pending_file,
            notion_token="ntn_test",
            notion_database_id="db-123",
        )
        with patch("hooks.session_start.get_skills_snapshot", return_value=[]):
            with patch("hooks.session_start.Client", return_value=mock_client):
                run_session_start(sample_hook_input)

    assert not pending_file.exists()


def test_session_start_skips_retry_if_no_token(tmp_journey_dir, sample_hook_input):
    state_file = tmp_journey_dir / ".session-state"
    pending_file = tmp_journey_dir / "pending.jsonl"
    pending_file.write_text('{"database_id":"db","entry":{"session_id":"x","date":"2026-03-18","project":"y","commits":"","duration_minutes":1}}\n')

    with patch("hooks.session_start.get_config") as mock_config:
        mock_config.return_value = MagicMock(
            journey_dir=tmp_journey_dir,
            state_file=state_file,
            pending_file=pending_file,
            notion_token=None,
            notion_database_id=None,
        )
        with patch("hooks.session_start.get_skills_snapshot", return_value=[]):
            run_session_start(sample_hook_input)

    assert pending_file.exists()
