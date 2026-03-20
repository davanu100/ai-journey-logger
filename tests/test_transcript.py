import json
from pathlib import Path

from lib.transcript import parse_transcript

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_minimal_transcript():
    result = parse_transcript(FIXTURES / "minimal_session.jsonl")
    assert result["initial_prompt"] == "What is Python?"
    assert result["model"] == "sonnet"
    assert result["message_count"] == 2
    assert result["tools_used"] == []
    assert result["skills_invoked"] == []
    assert result["skill_counts"] == []
    assert result["agents_dispatched"] == []
    assert result["agent_counts"] == []


def test_parse_rich_transcript():
    result = parse_transcript(FIXTURES / "rich_session.jsonl")
    assert result["initial_prompt"] == "Help me debug the authentication flow in our Go service. The login endpoint returns 500 when the Redis cache is cold."
    assert result["model"] == "opus"
    assert result["message_count"] == 6
    assert sorted(result["tools_used"]) == ["Agent", "Bash", "Edit", "Grep", "Read", "Skill"]
    assert sorted(result["skills_invoked"]) == ["superpowers:systematic-debugging", "superpowers:verification-before-completion"]
    assert result["skill_counts"] == [
        {"name": "superpowers:systematic-debugging", "count": 1},
        {"name": "superpowers:verification-before-completion", "count": 1},
    ]
    assert result["agents_dispatched"] == ["Explore"]
    assert result["agent_counts"] == [{"type": "Explore", "count": 2}]


def test_parse_initial_prompt_truncated():
    long_prompt = "x" * 1000
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": long_prompt}}),
        json.dumps({"type": "assistant", "message": {"model": "claude-haiku-4-5-20251001", "role": "assistant", "content": [{"type": "text", "text": "ok"}]}}),
    ]
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    assert len(result["initial_prompt"]) == 500
    assert result["model"] == "haiku"


def test_parse_nonexistent_file():
    result = parse_transcript(Path("/nonexistent/transcript.jsonl"))
    assert result["initial_prompt"] == ""
    assert result["model"] == ""
    assert result["message_count"] == 0
    assert result["tools_used"] == []


def test_parse_model_extraction():
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
        json.dumps({"type": "assistant", "message": {"model": "claude-sonnet-4-6", "role": "assistant", "content": [{"type": "text", "text": "hello"}]}}),
    ]
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    assert result["model"] == "sonnet"
