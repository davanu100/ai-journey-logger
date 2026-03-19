import json
from unittest.mock import MagicMock, patch

from lib.notion_push import build_properties, push_entry, retry_pending


def test_build_properties_minimal():
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "abc1234 feat: add login\ndef5678 fix: typo",
        "duration_minutes": 45,
    }
    props = build_properties(entry)
    assert props["session_id"]["title"][0]["text"]["content"] == "sess-001"
    assert props["date"]["date"]["start"] == "2026-03-19"
    assert props["project"]["rich_text"][0]["text"]["content"] == "my-app"
    assert props["commits"]["rich_text"][0]["text"]["content"] == entry["commits"]
    assert props["duration_minutes"]["number"] == 45


def test_build_properties_truncates_commits():
    long_commits = "x" * 2500
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": long_commits,
        "duration_minutes": None,
    }
    props = build_properties(entry)
    assert len(props["commits"]["rich_text"][0]["text"]["content"]) == 2000


def test_build_properties_null_duration():
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "",
        "duration_minutes": None,
    }
    props = build_properties(entry)
    assert props["duration_minutes"]["number"] is None


def test_push_entry_success(mock_notion_client, tmp_journey_dir):
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "",
        "duration_minutes": 10,
    }
    pending_file = tmp_journey_dir / "pending.jsonl"
    result = push_entry(mock_notion_client, "db-123", entry, pending_file)
    assert result is True
    mock_notion_client.pages.create.assert_called_once()
    assert not pending_file.exists()


def test_push_entry_failure_writes_pending(tmp_journey_dir):
    client = MagicMock()
    client.pages.create.side_effect = Exception("API error")
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "",
        "duration_minutes": 10,
    }
    pending_file = tmp_journey_dir / "pending.jsonl"
    result = push_entry(client, "db-123", entry, pending_file)
    assert result is False
    assert pending_file.exists()
    lines = pending_file.read_text().strip().split("\n")
    assert len(lines) == 1
    pending = json.loads(lines[0])
    assert pending["entry"]["session_id"] == "sess-001"


def test_retry_pending_success(mock_notion_client, tmp_journey_dir):
    pending_file = tmp_journey_dir / "pending.jsonl"
    pending_data = {
        "database_id": "db-123",
        "entry": {
            "session_id": "sess-old",
            "date": "2026-03-18",
            "project": "old-app",
            "commits": "",
            "duration_minutes": 5,
        },
    }
    pending_file.write_text(json.dumps(pending_data) + "\n")
    retry_pending(mock_notion_client, pending_file)
    assert not pending_file.exists()


def test_retry_pending_partial_failure(tmp_journey_dir):
    client = MagicMock()
    client.pages.create.side_effect = [
        {"id": "page-1"},
        Exception("API error"),
    ]
    pending_file = tmp_journey_dir / "pending.jsonl"
    entry1 = {"database_id": "db-123", "entry": {"session_id": "s1", "date": "2026-03-18", "project": "a", "commits": "", "duration_minutes": 1}}
    entry2 = {"database_id": "db-123", "entry": {"session_id": "s2", "date": "2026-03-18", "project": "b", "commits": "", "duration_minutes": 2}}
    pending_file.write_text(json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n")
    retry_pending(client, pending_file)
    lines = pending_file.read_text().strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0])["entry"]["session_id"] == "s2"


def test_retry_pending_noop_if_no_file(mock_notion_client, tmp_journey_dir):
    pending_file = tmp_journey_dir / "pending.jsonl"
    retry_pending(mock_notion_client, pending_file)
