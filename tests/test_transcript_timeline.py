import json
import tempfile
from pathlib import Path

from lib.transcript import parse_transcript

FIXTURES = Path(__file__).parent / "fixtures"


def test_timeline_basic_extraction():
    """Timeline extracts correct events with types, names, and timestamps."""
    result = parse_transcript(FIXTURES / "timeline_session.jsonl")
    timeline = json.loads(result["timeline"])

    # Should have: 2 prompts, 1 tool group (Read ×3), 1 skill, 1 tool group (Edit ×3), 1 agent
    assert len(timeline) == 6

    # First event: user prompt at t=0 (relative to first user message)
    assert timeline[0]["ty"] == "p"
    assert "debug the auth" in timeline[0]["tx"]
    assert timeline[0]["t"] == 0

    # Second event: Read ×3 (deduplicated consecutive)
    assert timeline[1]["ty"] == "t"
    assert timeline[1]["n"] == "Read ×3"
    assert timeline[1]["t"] == 1  # ~1 min after start

    # Third: skill
    assert timeline[2]["ty"] == "s"
    assert timeline[2]["n"] == "superpowers:systematic-debugging"
    assert timeline[2]["t"] == 3

    # Fourth: second user prompt
    assert timeline[3]["ty"] == "p"
    assert "tests" in timeline[3]["tx"]
    assert timeline[3]["t"] == 4

    # Fifth: agent
    assert timeline[4]["ty"] == "a"
    assert timeline[4]["n"] == "Explore"
    assert timeline[4]["d"] == "Search auth test files"
    assert timeline[4]["t"] == 5

    # Sixth: Edit ×3
    assert timeline[5]["ty"] == "t"
    assert timeline[5]["n"] == "Edit ×3"
    assert timeline[5]["t"] == 12


def test_timeline_deduplication():
    """Consecutive same-tool uses collapse into one event with ×count."""
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}, "timestamp": "2026-03-20T10:00:00Z"}),
        json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [
            {"type": "tool_use", "name": "Read", "input": {}},
            {"type": "tool_use", "name": "Read", "input": {}},
            {"type": "tool_use", "name": "Grep", "input": {}},
            {"type": "tool_use", "name": "Grep", "input": {}},
            {"type": "tool_use", "name": "Grep", "input": {}},
        ]}, "timestamp": "2026-03-20T10:01:00Z"}),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    timeline = json.loads(result["timeline"])
    tool_events = [e for e in timeline if e["ty"] == "t"]
    assert len(tool_events) == 2
    assert tool_events[0]["n"] == "Read ×2"
    assert tool_events[1]["n"] == "Grep ×3"


def test_timeline_single_tool_no_count():
    """A single tool use shows just the name without ×1."""
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}, "timestamp": "2026-03-20T10:00:00Z"}),
        json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {}},
        ]}, "timestamp": "2026-03-20T10:01:00Z"}),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    timeline = json.loads(result["timeline"])
    tool_events = [e for e in timeline if e["ty"] == "t"]
    assert len(tool_events) == 1
    assert tool_events[0]["n"] == "Bash"


def test_timeline_cap_at_40():
    """More than 40 events keeps first 15 + last 25."""
    lines = []
    for i in range(60):
        ts = f"2026-03-20T10:{i:02d}:00Z"
        lines.append(json.dumps({
            "type": "user",
            "message": {"role": "user", "content": f"msg {i}"},
            "timestamp": ts,
        }))
        lines.append(json.dumps({
            "type": "assistant",
            "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "text", "text": "ok"}]},
            "timestamp": ts,
        }))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    timeline = json.loads(result["timeline"])
    assert len(timeline) == 40
    assert "msg 0" in timeline[0]["tx"]
    assert "msg 35" in timeline[15]["tx"]


def test_timeline_prompt_truncated_to_100_chars():
    """Prompt text is truncated to 100 characters."""
    long_prompt = "x" * 200
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": long_prompt}, "timestamp": "2026-03-20T10:00:00Z"}),
        json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "text", "text": "ok"}]}, "timestamp": "2026-03-20T10:00:10Z"}),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    timeline = json.loads(result["timeline"])
    assert len(timeline[0]["tx"]) == 100


def test_timeline_error_resilience():
    """Malformed lines are skipped; valid events still extracted."""
    lines = [
        json.dumps({"type": "user", "message": {"role": "user", "content": "hello"}, "timestamp": "2026-03-20T10:00:00Z"}),
        "THIS IS NOT JSON",
        json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "tool_use", "name": "Read", "input": {}}]}, "timestamp": "2026-03-20T10:01:00Z"}),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    timeline = json.loads(result["timeline"])
    assert len(timeline) == 2


def test_timeline_empty_transcript():
    """Empty file returns empty timeline string."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("")
        f.flush()
        result = parse_transcript(Path(f.name))
    assert result["timeline"] == ""


def test_timeline_nonexistent_file():
    """Nonexistent file returns empty timeline."""
    result = parse_transcript(Path("/nonexistent/transcript.jsonl"))
    assert result["timeline"] == ""


def test_timeline_budget_enforcement():
    """Large event list is truncated to fit under 1900 chars."""
    lines = []
    for i in range(40):
        ts = f"2026-03-20T10:{i:02d}:00Z"
        lines.append(json.dumps({
            "type": "user",
            "message": {"role": "user", "content": f"This is a long prompt message number {i} with extra padding " + "x" * 80},
            "timestamp": ts,
        }))
        lines.append(json.dumps({
            "type": "assistant",
            "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore", "description": f"Searching for files related to topic {i} with a long description " + "y" * 50}},
            ]},
            "timestamp": ts,
        }))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("\n".join(lines))
        f.flush()
        result = parse_transcript(Path(f.name))
    assert len(result["timeline"]) <= 1900
    assert len(result["timeline"]) > 0
    parsed = json.loads(result["timeline"])
    assert isinstance(parsed, list)
    assert len(parsed) > 0
