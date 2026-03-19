import os
from unittest.mock import patch

from lib.config import get_config


def test_get_config_from_env(tmp_path):
    journey_dir = tmp_path / ".claude-journey"
    with patch.dict(os.environ, {
        "NOTION_TOKEN": "ntn_test_token",
        "NOTION_DATABASE_ID": "db-id-123",
        "CLAUDE_JOURNEY_DIR": str(journey_dir),
    }):
        config = get_config()
    assert config.notion_token == "ntn_test_token"
    assert config.notion_database_id == "db-id-123"
    assert config.journey_dir == journey_dir


def test_get_config_default_journey_dir():
    with patch.dict(os.environ, {
        "NOTION_TOKEN": "ntn_test",
        "NOTION_DATABASE_ID": "db-123",
    }, clear=False):
        os.environ.pop("CLAUDE_JOURNEY_DIR", None)
        config = get_config()
    from pathlib import Path
    assert config.journey_dir == Path.home() / ".claude-journey"


def test_get_config_missing_token():
    with patch.dict(os.environ, {}, clear=True):
        config = get_config()
    assert config.notion_token is None
    assert config.notion_database_id is None
