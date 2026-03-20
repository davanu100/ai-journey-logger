import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from hooks.stop import run_stop


def test_stop_returns_block_when_no_manual_fields(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-20T10:00:00+05:30",
        "skills_snapshot": [],
    }))

    config = MagicMock(state_file=state_file)
    hook_input = {"session_id": "sess-001"}

    with patch("hooks.stop.get_config", return_value=config):
        result = run_stop(hook_input)

    assert result["decision"] == "block"
    assert "satisfaction" in result["reason"].lower() or "session" in result["reason"].lower()


def test_stop_returns_none_when_manual_fields_present(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-20T10:00:00+05:30",
        "skills_snapshot": [],
        "manual": {"satisfaction": 4},
    }))

    config = MagicMock(state_file=state_file)
    hook_input = {"session_id": "sess-001"}

    with patch("hooks.stop.get_config", return_value=config):
        result = run_stop(hook_input)

    assert result is None


def test_stop_returns_none_when_no_state_file(tmp_path):
    state_file = tmp_path / "nonexistent"
    config = MagicMock(state_file=state_file)
    hook_input = {"session_id": "sess-001"}

    with patch("hooks.stop.get_config", return_value=config):
        result = run_stop(hook_input)

    assert result is None


def test_stop_returns_none_when_session_id_mismatch(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    state_file = journey_dir / ".session-state"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-20T10:00:00+05:30",
        "skills_snapshot": [],
    }))

    config = MagicMock(state_file=state_file)
    hook_input = {"session_id": "different-session"}

    with patch("hooks.stop.get_config", return_value=config):
        result = run_stop(hook_input)

    assert result is None
