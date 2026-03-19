import json
from datetime import datetime, timezone

from lib.state import write_state, read_state, update_state_manual_fields


def test_write_state_creates_file(state_file):
    write_state(
        path=state_file,
        session_id="sess-001",
        start_time="2026-03-19T10:30:00+05:30",
        skills_snapshot=["skill-a", "skill-b"],
    )
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["session_id"] == "sess-001"
    assert data["start_time"] == "2026-03-19T10:30:00+05:30"
    assert data["skills_snapshot"] == ["skill-a", "skill-b"]
    assert "manual" not in data


def test_write_state_creates_parent_dir(tmp_path):
    state_file = tmp_path / "nested" / "dir" / ".session-state"
    write_state(
        path=state_file,
        session_id="sess-002",
        start_time="2026-03-19T11:00:00+05:30",
        skills_snapshot=[],
    )
    assert state_file.exists()


def test_read_state_returns_data(state_file):
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-19T10:30:00+05:30",
        "skills_snapshot": [],
    }))
    data = read_state(state_file)
    assert data["session_id"] == "sess-001"


def test_read_state_returns_none_if_missing(tmp_path):
    result = read_state(tmp_path / "nonexistent")
    assert result is None


def test_update_state_manual_fields(state_file):
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-19T10:30:00+05:30",
        "skills_snapshot": [],
    }))
    manual = {"satisfaction": 4, "category": "debugging"}
    update_state_manual_fields(state_file, manual)
    data = json.loads(state_file.read_text())
    assert data["manual"] == manual
    assert data["session_id"] == "sess-001"


def test_update_state_manual_fields_noop_if_already_present(state_file):
    state_file.write_text(json.dumps({
        "session_id": "sess-001",
        "start_time": "2026-03-19T10:30:00+05:30",
        "skills_snapshot": [],
        "manual": {"satisfaction": 3},
    }))
    update_state_manual_fields(state_file, {"satisfaction": 5})
    data = json.loads(state_file.read_text())
    assert data["manual"]["satisfaction"] == 3
