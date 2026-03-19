import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_journey_dir(tmp_path):
    """Provides a temporary ~/.claude-journey/ directory."""
    journey_dir = tmp_path / ".claude-journey"
    journey_dir.mkdir()
    return journey_dir


@pytest.fixture
def state_file(tmp_journey_dir):
    """Provides the path to a state file in the temp journey dir."""
    return tmp_journey_dir / ".session-state"


@pytest.fixture
def pending_file(tmp_journey_dir):
    """Provides the path to a pending.jsonl in the temp journey dir."""
    return tmp_journey_dir / "pending.jsonl"


@pytest.fixture
def sample_hook_input():
    """Sample JSON that Claude Code sends to hooks on stdin."""
    return {
        "session_id": "test-session-001",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/Users/testuser/projects/my-app",
    }


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing without API calls."""
    client = MagicMock()
    client.pages.create.return_value = {"id": "notion-page-id-123"}
    return client
