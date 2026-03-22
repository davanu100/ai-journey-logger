# Blog Readability & Auto-Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auto-generated session narratives, a visual timeline, and redesigned skills page to the AI Journey Logger blog.

**Architecture:** Python transcript parser extracts timeline events from JSONL transcripts and stores them as compact JSON in Notion. At Astro build time, TypeScript functions generate human-readable narratives from timeline data. Redesigned Astro components render visual timelines and enriched skill profiles.

**Tech Stack:** Python 3 (transcript parsing), TypeScript/Astro (blog), Tailwind CSS v4, Notion API, Vitest (TS tests), pytest (Python tests)

**Spec:** `docs/specs/2026-03-23-blog-readability-design.md`

---

## File Structure

### Python (new/modified)

| File | Responsibility |
|------|---------------|
| `lib/transcript.py` | **Modify**: Add `timeline` field to `parse_transcript()` return value — ordered events with deduplication, 40-event cap, budget enforcement |
| `lib/notion_push.py` | **Modify**: Add `session_timeline` to `build_properties()` as rich_text |
| `hooks/session_end.py` | **Modify**: Wire `session_timeline` from transcript data into entry dict |
| `setup_notion_db.py` | **Modify**: Add `session_timeline` to schema definition |
| `tests/test_transcript_timeline.py` | **Create**: Timeline extraction tests |
| `tests/test_notion_push.py` | **Modify**: Add test for `session_timeline` in `build_properties()` |
| `tests/fixtures/timeline_session.jsonl` | **Create**: Test fixture with timestamps and varied event types |

### TypeScript/Astro (new/modified)

| File | Responsibility |
|------|---------------|
| `blog/src/lib/narrative.ts` | **Create**: `generateOneLiner()`, `generateNarrative()`, `TimelineEvent` type |
| `blog/src/lib/narrative.test.ts` | **Create**: Tests for narrative functions |
| `blog/src/lib/notion.ts` | **Modify**: Add `session_timeline` to `JourneyPost`, add `parseTimeline()`, enhance `getAllSkills()` with `avgSatisfaction`, `sessions`, `label` |
| `blog/src/lib/notion.test.ts` | **Create**: Tests for `parseTimeline()` |
| `blog/src/components/Timeline.astro` | **Create**: Visual vertical timeline component |
| `blog/src/components/TimelineEvent.astro` | **Create**: Single timeline event node |
| `blog/src/components/SkillProfile.astro` | **Create**: Skill card with satisfaction, sessions, hot/cold label |
| `blog/src/pages/posts/[slug].astro` | **Modify**: New layout with narrative + timeline |
| `blog/src/components/PostCard.astro` | **Modify**: Replace summary with one-liner, add counts |
| `blog/src/components/MetadataSidebar.astro` | **Modify**: Simplify to stats only (remove badge lists) |
| `blog/src/pages/skills.astro` | **Modify**: Use SkillProfile component |

---

## Task 1: Timeline Extraction in Transcript Parser

**Files:**
- Create: `tests/test_transcript_timeline.py`
- Create: `tests/fixtures/timeline_session.jsonl`
- Modify: `lib/transcript.py`

**Context:** The existing `parse_transcript()` in `lib/transcript.py:17-90` reads JSONL line by line, extracting tools, skills, agents. We need to add a `timeline` key to its return dict — a JSON string of ordered events. Each JSONL entry has a `timestamp` field (ISO 8601). The existing code catches `JSONDecodeError` and `OSError` at the top level (line 78); we need per-line resilience for timeline extraction.

- [ ] **Step 1: Create test fixture**

Create `tests/fixtures/timeline_session.jsonl` — a JSONL file with timestamps, multiple user messages, consecutive same-tool uses, a Skill, an Agent, and enough variety to test deduplication:

```jsonl
{"type": "progress", "data": {"type": "hook_progress"}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:00:00Z"}
{"type": "user", "message": {"role": "user", "content": "Help me debug the auth flow in our service"}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:00:30Z"}
{"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/src/auth.go"}}, {"type": "tool_use", "name": "Read", "input": {"file_path": "/src/config.go"}}, {"type": "tool_use", "name": "Read", "input": {"file_path": "/src/redis.go"}}]}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:01:00Z"}
{"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "superpowers:systematic-debugging"}}]}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:03:00Z"}
{"type": "user", "message": {"role": "user", "content": "Check the tests too"}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:04:00Z"}
{"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore", "description": "Search auth test files"}}]}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:05:00Z"}
{"type": "assistant", "message": {"model": "claude-opus-4-6", "role": "assistant", "content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "/src/auth.go", "old_string": "a", "new_string": "b"}}, {"type": "tool_use", "name": "Edit", "input": {"file_path": "/src/redis.go", "old_string": "c", "new_string": "d"}}, {"type": "tool_use", "name": "Edit", "input": {"file_path": "/src/config.go", "old_string": "e", "new_string": "f"}}]}, "sessionId": "sess-tl", "timestamp": "2026-03-20T10:12:00Z"}
```

- [ ] **Step 2: Write timeline extraction tests**

Create `tests/test_transcript_timeline.py`:

```python
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
    # Build 60 alternating user/assistant messages → 60 prompt events
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
    # First 15 should start with msg 0
    assert "msg 0" in timeline[0]["tx"]
    # Event at index 15 should be from the tail (last 25)
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
    assert len(timeline) == 2  # prompt + tool, malformed line skipped


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
    # Build 40 events with long prompt text and agent descriptions to exceed 1900 chars
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
    assert len(result["timeline"]) > 0  # not empty — truncated, not dropped
    # Should still be valid JSON
    parsed = json.loads(result["timeline"])
    assert isinstance(parsed, list)
    assert len(parsed) > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/test_transcript_timeline.py -v`
Expected: FAIL — `timeline` key not in parse_transcript result

- [ ] **Step 4: Implement timeline extraction**

Modify `lib/transcript.py`. The existing `parse_transcript()` function (lines 17-90) needs these changes:

1. Add imports at the top of the file:
```python
from datetime import datetime
```

2. Add `"timeline": ""` to the `empty` dict (line 18-27).

3. Inside the JSONL parsing loop, change the error handling from a top-level try/except to per-line. Add timeline tracking variables and event collection logic.

4. After the loop, add deduplication, capping, budget enforcement, and serialization.

Here is the complete updated `parse_transcript()`:

```python
def parse_transcript(path: Path) -> dict:
    empty = {
        "initial_prompt": "",
        "model": "",
        "message_count": 0,
        "tools_used": [],
        "skills_invoked": [],
        "skill_counts": [],
        "agents_dispatched": [],
        "agent_counts": [],
        "timeline": "",
    }

    if not path.exists():
        return empty

    initial_prompt = None
    model = None
    message_count = 0
    tool_names = set()
    skill_counter: Counter = Counter()
    agent_counter: Counter = Counter()

    # Timeline tracking
    raw_events = []       # list of (timestamp_str, event_dict)
    session_start_ts = None

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # per-line resilience
                entry_type = entry.get("type")
                ts = entry.get("timestamp", "")

                if entry_type == "user":
                    message_count += 1
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        if initial_prompt is None:
                            initial_prompt = content[:500]
                        # Timeline: prompt event
                        if ts:
                            raw_events.append((ts, {"ty": "p", "tx": content[:100]}))

                elif entry_type == "assistant":
                    message_count += 1
                    msg = entry.get("message", {})

                    if model is None:
                        model = _extract_model_short(msg.get("model", ""))

                    # Collect tool uses for this assistant message
                    msg_tools = []
                    for block in msg.get("content", []):
                        if block.get("type") != "tool_use":
                            continue
                        name = block.get("name", "")
                        if name:
                            tool_names.add(name)

                        if name == "Skill":
                            skill = block.get("input", {}).get("skill", "")
                            if skill:
                                skill_counter[skill] += 1
                                if ts:
                                    raw_events.append((ts, {"ty": "s", "n": skill}))

                        elif name == "Agent":
                            agent_type = block.get("input", {}).get("subagent_type", "general-purpose")
                            agent_counter[agent_type] += 1
                            desc = block.get("input", {}).get("description", "")
                            evt = {"ty": "a", "n": agent_type}
                            if desc:
                                evt["d"] = desc
                            if ts:
                                raw_events.append((ts, evt))

                        elif name not in ("Skill", "Agent") and name:
                            msg_tools.append(name)

                    # Deduplicate consecutive same-tool uses within this message
                    if msg_tools and ts:
                        groups = []
                        current_name = msg_tools[0]
                        current_count = 1
                        for t in msg_tools[1:]:
                            if t == current_name:
                                current_count += 1
                            else:
                                groups.append((current_name, current_count))
                                current_name = t
                                current_count = 1
                        groups.append((current_name, current_count))
                        for gname, gcount in groups:
                            label = f"{gname} ×{gcount}" if gcount > 1 else gname
                            raw_events.append((ts, {"ty": "t", "n": label}))

    except OSError:
        return empty

    # Build timeline JSON
    timeline_str = ""
    if raw_events:
        timeline_str = _build_timeline(raw_events)

    return {
        "initial_prompt": initial_prompt or "",
        "model": model or "",
        "message_count": message_count,
        "tools_used": sorted(tool_names),
        "skills_invoked": sorted(skill_counter.keys()),
        "skill_counts": [{"name": k, "count": v} for k, v in sorted(skill_counter.items())],
        "agents_dispatched": sorted(agent_counter.keys()),
        "agent_counts": [{"type": k, "count": v} for k, v in sorted(agent_counter.items())],
        "timeline": timeline_str,
    }
```

5. Add the `_build_timeline` helper function before `parse_transcript`:

```python
def _build_timeline(raw_events: list) -> str:
    """Build compact timeline JSON from raw events with capping and budget enforcement."""
    if not raw_events:
        return ""

    # Parse first event timestamp as session start
    try:
        start_ts = datetime.fromisoformat(raw_events[0][0].replace("Z", "+00:00"))
    except (ValueError, IndexError):
        return ""

    # Compute minutes since start for each event
    events = []
    for ts_str, evt in raw_events:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            minutes = max(0, int((ts - start_ts).total_seconds() / 60))
        except (ValueError, TypeError):
            minutes = 0
        evt["t"] = minutes
        events.append(evt)

    # Cap at 40 events: keep first 15 + last 25
    if len(events) > 40:
        events = events[:15] + events[-25:]

    # Budget enforcement: serialize and check < 1900 chars
    result = json.dumps(events, separators=(",", ":"))
    if len(result) <= 1900:
        return result

    # Step 1: drop 'd' fields from agents
    for evt in events:
        evt.pop("d", None)
    result = json.dumps(events, separators=(",", ":"))
    if len(result) <= 1900:
        return result

    # Step 2: shorten 'tx' to 60 chars
    for evt in events:
        if "tx" in evt and len(evt["tx"]) > 60:
            evt["tx"] = evt["tx"][:60]
    result = json.dumps(events, separators=(",", ":"))
    if len(result) <= 1900:
        return result

    # Step 3: reduce cap to 30 events
    if len(events) > 30:
        events = events[:10] + events[-20:]
    result = json.dumps(events, separators=(",", ":"))
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/test_transcript_timeline.py -v`
Expected: All PASS

- [ ] **Step 6: Run existing transcript tests to verify no regression**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/test_transcript.py -v`
Expected: All PASS (existing tests don't check for `timeline` key, so they pass; if any test does strict dict comparison, add `"timeline": ""` or the expected timeline value)

- [ ] **Step 7: Commit**

```bash
git add lib/transcript.py tests/test_transcript_timeline.py tests/fixtures/timeline_session.jsonl
git commit -m "feat: add timeline extraction to transcript parser"
```

---

## Task 2: Notion Push & Schema Updates

**Files:**
- Modify: `lib/notion_push.py:6-54`
- Modify: `hooks/session_end.py:84-92`
- Modify: `setup_notion_db.py`
- Modify: `tests/test_notion_push.py`

**Context:** `build_properties()` in `lib/notion_push.py:6-54` builds a dict of Notion properties from an entry dict. It uses `.get()` with defaults for all fields. `session_end.py:84-92` builds the entry dict and spreads `transcript_data` into it. Since `parse_transcript()` now returns a `timeline` key, and entry uses `**transcript_data`, the timeline will automatically be in the entry dict — but `build_properties()` needs to map it to a Notion rich_text property.

- [ ] **Step 1: Write test for session_timeline in build_properties**

Add to `tests/test_notion_push.py`:

```python
def test_build_properties_includes_session_timeline():
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "",
        "duration_minutes": 10,
        "timeline": '[{"ty":"p","tx":"hello","t":0}]',
    }
    props = build_properties(entry)
    assert "session_timeline" in props
    assert props["session_timeline"]["rich_text"][0]["text"]["content"] == '[{"ty":"p","tx":"hello","t":0}]'


def test_build_properties_empty_timeline():
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-19",
        "project": "my-app",
        "commits": "",
        "duration_minutes": 10,
    }
    props = build_properties(entry)
    assert props["session_timeline"]["rich_text"][0]["text"]["content"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/test_notion_push.py::test_build_properties_includes_session_timeline tests/test_notion_push.py::test_build_properties_empty_timeline -v`
Expected: FAIL — `session_timeline` not in props

- [ ] **Step 3: Add session_timeline to build_properties**

In `lib/notion_push.py`, add this line after line 32 (the `agent_counts` line) inside the `props` dict:

```python
        "session_timeline": {"rich_text": [{"text": {"content": entry.get("timeline", "")}}]},
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/test_notion_push.py -v`
Expected: All PASS

- [ ] **Step 5: Add session_timeline to Notion schema definition**

In `setup_notion_db.py`, find the properties dict (around line 25-83) and add `session_timeline` as a rich_text property alongside the other rich_text properties like `notes`:

```python
        "session_timeline": {"rich_text": {}},
```

- [ ] **Step 6: Run one-time migration to add property to live database**

Create and run a one-time script (do NOT commit this):

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -c "
import httpx
import os
resp = httpx.patch(
    f'https://api.notion.com/v1/databases/{os.environ[\"NOTION_DATABASE_ID\"]}',
    headers={
        'Authorization': f'Bearer {os.environ[\"NOTION_TOKEN\"]}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    },
    json={'properties': {'session_timeline': {'rich_text': {}}}},
)
print(resp.status_code, resp.json().get('id', resp.text[:200]))
"
```

Expected: `200` and the database ID

- [ ] **Step 7: Commit**

```bash
git add lib/notion_push.py setup_notion_db.py tests/test_notion_push.py
git commit -m "feat: add session_timeline to Notion properties and schema"
```

Note: `hooks/session_end.py` does NOT need modification — it already spreads `**transcript_data` into the entry dict (line 92), so the `timeline` key from `parse_transcript()` flows through automatically.

---

## Task 3: Notion Client TypeScript Updates

**Files:**
- Modify: `blog/src/lib/notion.ts`
- Create: `blog/src/lib/notion.test.ts`
- Modify: `blog/package.json` (add vitest)

**Context:** `blog/src/lib/notion.ts` defines `JourneyPost` (line 3-18), `SkillStats` (line 20-26), helper functions, and `getAllSkills()` (line 128-153). We need to add `session_timeline` to `JourneyPost`, add `parseTimeline()`, and enhance `SkillStats` with `avgSatisfaction`, `sessions`, and `label`.

- [ ] **Step 1: Install vitest**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npm install -D vitest
```

- [ ] **Step 2: Create parseTimeline tests**

Create `blog/src/lib/notion.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseTimeline } from './notion';
import type { TimelineEvent } from './notion';

describe('parseTimeline', () => {
  it('parses valid compact JSON into TimelineEvent array', () => {
    const input = '[{"ty":"p","tx":"hello","t":0},{"ty":"t","n":"Read ×3","t":1}]';
    const result = parseTimeline(input);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ ty: 'p', tx: 'hello', t: 0 });
    expect(result[1]).toEqual({ ty: 't', n: 'Read ×3', t: 1 });
  });

  it('returns empty array for empty string', () => {
    expect(parseTimeline('')).toEqual([]);
  });

  it('returns empty array for malformed JSON', () => {
    expect(parseTimeline('not json')).toEqual([]);
    expect(parseTimeline('{}')).toEqual([]);
  });

  it('returns empty array for null/undefined', () => {
    expect(parseTimeline(null as any)).toEqual([]);
    expect(parseTimeline(undefined as any)).toEqual([]);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx vitest run src/lib/notion.test.ts`
Expected: FAIL — `parseTimeline` not exported from notion.ts

- [ ] **Step 4: Update notion.ts**

Make these changes to `blog/src/lib/notion.ts`:

**4a.** Add `session_timeline` to `JourneyPost` interface (after line 18, before the closing `}`):
```typescript
  session_timeline: string;
```

**4b.** Add `parseTimeline` function (after `sanitizeCommits`, around line 76):
```typescript
export function parseTimeline(raw: string | null | undefined): TimelineEvent[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}
```

**4c.** Add `TimelineEvent` type at the top of the file (we define it here so notion.ts is self-contained; narrative.ts will import it):
```typescript
export interface TimelineEvent {
  ty: 'p' | 't' | 's' | 'a';
  t: number;
  n?: string;
  tx?: string;
  d?: string;
}
```

**4d.** Add `session_timeline` to `pageToPost()` (around line 115, inside the return object):
```typescript
    session_timeline: richText(p.session_timeline),
```

**4e.** Enhance `SkillStats` interface to add new fields:
```typescript
export interface SkillStats {
  name: string;
  count: number;
  lastUsed: string;
  projects: string[];
  avgSatisfaction: number;
  sessions: string[];
  label: 'hot' | 'cold' | null;
}
```

**4f.** Update `getAllSkills()` to compute new fields. Replace the existing function body (lines 128-153):
```typescript
export async function getAllSkills(): Promise<SkillStats[]> {
  const posts = await getPublishedPosts();
  const map = new Map<string, {
    count: number;
    lastUsed: string;
    projects: Set<string>;
    satisfactions: number[];
    sessions: string[];
    dates: string[];
  }>();

  for (const post of posts) {
    for (const skill of post.skills_invoked) {
      let entry = map.get(skill);
      if (!entry) {
        entry = { count: 0, lastUsed: '', projects: new Set(), satisfactions: [], sessions: [], dates: [] };
        map.set(skill, entry);
      }
      entry.count++;
      if (post.date > entry.lastUsed) entry.lastUsed = post.date;
      entry.projects.add(post.project);
      if (post.satisfaction > 0) entry.satisfactions.push(post.satisfaction);
      entry.sessions.push(post.session_id);
      entry.dates.push(post.date);
    }
  }

  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  return Array.from(map.entries())
    .map(([name, s]) => {
      const avgSatisfaction = s.satisfactions.length > 0
        ? Math.round((s.satisfactions.reduce((a, b) => a + b, 0) / s.satisfactions.length) * 10) / 10
        : 0;
      const recentDates = s.dates.filter(d => d >= sevenDaysAgo);
      const label: 'hot' | 'cold' | null =
        recentDates.length >= 3 ? 'hot' :
        s.lastUsed < fourteenDaysAgo ? 'cold' :
        null;
      return {
        name,
        count: s.count,
        lastUsed: s.lastUsed,
        projects: [...s.projects].sort(),
        avgSatisfaction,
        sessions: s.sessions.slice(-10),  // cap at latest 10
        label,
      };
    })
    .sort((a, b) => b.count - a.count);
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx vitest run src/lib/notion.test.ts`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add blog/src/lib/notion.ts blog/src/lib/notion.test.ts blog/package.json blog/package-lock.json
git commit -m "feat: add parseTimeline, session_timeline, and enhanced SkillStats to notion client"
```

---

## Task 4: Narrative Generator

**Files:**
- Create: `blog/src/lib/narrative.ts`
- Create: `blog/src/lib/narrative.test.ts`

**Context:** This module generates deterministic text summaries from structured post data and timeline events. It exports `generateOneLiner()` for home page cards and `generateNarrative()` for post pages. No external dependencies. Uses `TimelineEvent` type from `notion.ts`.

- [ ] **Step 1: Write narrative tests**

Create `blog/src/lib/narrative.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { generateOneLiner, generateNarrative } from './narrative';
import type { JourneyPost, TimelineEvent } from './notion';

const basePost: JourneyPost = {
  session_id: 'sess-001',
  date: '2026-03-20',
  project: 'ai-journey-logger',
  model: 'opus',
  duration_minutes: 45,
  blog_summary: 'Debugged auth flow.',
  notes: '',
  category: 'debugging',
  tools_used: ['Read', 'Edit', 'Bash'],
  skills_invoked: ['systematic-debugging', 'verification-before-completion'],
  agents_dispatched: ['Explore'],
  commits: 'fix: auth token validation\nfix: redis cache warmup\nfeat: add retry logic',
  satisfaction: 4,
  message_count: 12,
  session_timeline: '',
};

describe('generateOneLiner', () => {
  it('generates a one-liner with duration, model, project, category, commits, top skill', () => {
    const result = generateOneLiner(basePost);
    expect(result).toContain('45-min');
    expect(result).toContain('opus');
    expect(result).toContain('ai-journey-logger');
    expect(result).toContain('3 commits');
  });

  it('handles missing skills gracefully', () => {
    const post = { ...basePost, skills_invoked: [] };
    const result = generateOneLiner(post);
    expect(result).toContain('45-min');
    expect(result).not.toContain('using');
  });

  it('handles missing commits', () => {
    const post = { ...basePost, commits: '' };
    const result = generateOneLiner(post);
    expect(result).not.toContain('commit');
  });
});

describe('generateNarrative', () => {
  const timeline: TimelineEvent[] = [
    { ty: 'p', tx: 'Help me debug the auth flow', t: 0 },
    { ty: 't', n: 'Read ×5', t: 1 },
    { ty: 's', n: 'systematic-debugging', t: 3 },
    { ty: 'a', n: 'Explore', d: 'Search auth code', t: 5 },
    { ty: 't', n: 'Edit ×3', t: 12 },
  ];

  it('generates opening sentence with duration, category, model', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toMatch(/^A 45-minute debugging session using opus\./);
  });

  it('includes first prompt text in middle sentence', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('debug the auth flow');
  });

  it('includes skill invocation', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('systematic-debugging');
  });

  it('includes agent dispatch', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('Explore');
  });

  it('includes commit count in closing sentence', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('3 commit');
  });

  it('falls back to aggregate summary when no timeline', () => {
    const result = generateNarrative(basePost, []);
    expect(result).toContain('45-min');
    expect(result).toContain('opus');
    expect(result).toContain('3 tools');
    expect(result).toContain('2 skills');
    expect(result).toContain('1 agent');
  });

  it('handles zero duration gracefully', () => {
    const post = { ...basePost, duration_minutes: 0 };
    const result = generateNarrative(post, timeline);
    expect(result).not.toContain('0-minute');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx vitest run src/lib/narrative.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement narrative.ts**

Create `blog/src/lib/narrative.ts`:

```typescript
import type { JourneyPost, TimelineEvent } from './notion';

function countCommits(post: JourneyPost): number {
  if (!post.commits) return 0;
  return post.commits.split('\n').filter(l => l.trim().length > 0).length;
}

function firstCommitMessage(post: JourneyPost): string {
  if (!post.commits) return '';
  const first = post.commits.split('\n').find(l => l.trim().length > 0);
  return first?.trim() || '';
}

export function generateOneLiner(post: JourneyPost): string {
  const parts: string[] = [];

  // Duration + model
  if (post.duration_minutes > 0) {
    parts.push(`${post.duration_minutes}-min`);
  }
  parts.push(post.model || 'unknown');
  parts.push('session on');
  parts.push(post.project);

  // Category + commits
  const commitCount = countCommits(post);
  const details: string[] = [];
  if (post.category) {
    details.push(post.category);
  }
  if (commitCount > 0) {
    details.push(`across ${commitCount} commit${commitCount === 1 ? '' : 's'}`);
  }
  if (post.skills_invoked.length > 0) {
    details.push(`using ${post.skills_invoked[0]}`);
  }

  if (details.length > 0) {
    parts.push('—');
    parts.push(details.join(' '));
  }

  return parts.join(' ');
}

export function generateNarrative(post: JourneyPost, timeline: TimelineEvent[]): string {
  if (timeline.length === 0) {
    return generateFallback(post);
  }

  const sentences: string[] = [];

  // Opening sentence
  const durationPart = post.duration_minutes > 0 ? `${post.duration_minutes}-minute ` : '';
  const category = post.category || 'coding';
  sentences.push(`A ${durationPart}${category} session using ${post.model || 'unknown'}.`);

  // Middle sentences: walk timeline events
  const middleParts: string[] = [];
  let promptUsed = false;

  for (const evt of timeline) {
    if (middleParts.length >= 4) break;  // enough material for 2 sentences

    switch (evt.ty) {
      case 'p':
        if (!promptUsed && evt.tx) {
          middleParts.push(`Started by ${evt.tx.toLowerCase()}`);
          promptUsed = true;
        }
        break;
      case 's':
        if (evt.n) middleParts.push(`invoked ${evt.n}`);
        break;
      case 'a':
        if (evt.n) {
          const desc = evt.d ? ` to ${evt.d.toLowerCase()}` : '';
          middleParts.push(`dispatched a ${evt.n} agent${desc}`);
        }
        break;
      case 't': {
        // Only include tools with count >= 3
        const match = evt.n?.match(/×(\d+)/);
        if (match && parseInt(match[1]) >= 3) {
          middleParts.push(`used ${evt.n}`);
        }
        break;
      }
    }
  }

  if (middleParts.length > 0) {
    // Join with "then" / "followed by" — split into max 2 sentences
    if (middleParts.length <= 2) {
      sentences.push(middleParts.join(', then ') + '.');
    } else {
      const first = middleParts.slice(0, 2).join(', then ');
      const second = middleParts.slice(2).join(' and ');
      sentences.push(`${first}.`);
      sentences.push(`Then ${second}.`);
    }
  }

  // Closing sentence
  const commitCount = countCommits(post);
  if (commitCount > 0) {
    const msg = firstCommitMessage(post);
    const msgPart = msg ? ` ${msg}` : '';
    sentences.push(`Produced ${commitCount} commit${commitCount === 1 ? '' : 's'}${msgPart}.`);
  }

  return sentences.join(' ');
}

function generateFallback(post: JourneyPost): string {
  const parts: string[] = [];
  if (post.duration_minutes > 0) {
    parts.push(`${post.duration_minutes}-min`);
  }
  parts.push(`${post.model || 'unknown'} session`);

  const counts: string[] = [];
  if (post.tools_used.length > 0) counts.push(`${post.tools_used.length} tools`);
  if (post.skills_invoked.length > 0) counts.push(`${post.skills_invoked.length} skills`);
  if (post.agents_dispatched.length > 0) counts.push(`${post.agents_dispatched.length} agent${post.agents_dispatched.length === 1 ? '' : 's'}`);

  if (counts.length > 0) {
    parts.push('— used');
    parts.push(counts.join(', '));
  }

  return parts.join(' ') + '.';
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx vitest run src/lib/narrative.test.ts`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add blog/src/lib/narrative.ts blog/src/lib/narrative.test.ts
git commit -m "feat: add build-time narrative generator with one-liner and full narrative"
```

---

## Task 5: Timeline Components

**Files:**
- Create: `blog/src/components/TimelineEvent.astro`
- Create: `blog/src/components/Timeline.astro`

**Context:** These Astro components render the visual vertical timeline on post pages. `Timeline.astro` receives the parsed `TimelineEvent[]` array plus the post's `commits` and `duration_minutes`. It injects commit events and a "Session ended" marker at render time, then renders each event via `TimelineEvent.astro`.

- [ ] **Step 1: Create TimelineEvent.astro**

Create `blog/src/components/TimelineEvent.astro`:

```astro
---
interface Props {
  type: 'p' | 't' | 's' | 'a' | 'commit' | 'end';
  minutes: number;
  label: string;
  sublabel?: string;
}

const { type, minutes, label, sublabel } = Astro.props;

const dotColors: Record<string, string> = {
  p: 'bg-muted',
  t: 'bg-blue-500',
  s: 'bg-purple-500',
  a: 'bg-green-500',
  commit: 'bg-yellow-500',
  end: 'bg-muted/50',
};

const dotColor = dotColors[type] || 'bg-muted';
---

<div class="flex items-start gap-4 relative">
  <div class="w-14 text-right shrink-0">
    <span class="font-mono text-xs text-muted">{minutes} min</span>
  </div>
  <div class="flex flex-col items-center shrink-0">
    <div class={`w-3 h-3 rounded-full ${dotColor} ring-2 ring-bg z-10`}></div>
  </div>
  <div class="pb-6 min-w-0">
    <span class="text-sm text-text">{label}</span>
    {sublabel && (
      <span class="block text-xs text-muted mt-0.5">{sublabel}</span>
    )}
  </div>
</div>
```

- [ ] **Step 2: Create Timeline.astro**

Create `blog/src/components/Timeline.astro`:

```astro
---
import TimelineEvent from './TimelineEvent.astro';
import type { TimelineEvent as TEvent } from '../lib/notion';

interface Props {
  events: TEvent[];
  commits: string;
  durationMinutes: number;
}

const { events, commits, durationMinutes } = Astro.props;

// Build display events from timeline data
type DisplayEvent = {
  type: 'p' | 't' | 's' | 'a' | 'commit' | 'end';
  minutes: number;
  label: string;
  sublabel?: string;
};

const displayEvents: DisplayEvent[] = [];

for (const evt of events) {
  switch (evt.ty) {
    case 'p':
      displayEvents.push({
        type: 'p',
        minutes: evt.t,
        label: `"${evt.tx || '...'}"`,
      });
      break;
    case 't':
      displayEvents.push({
        type: 't',
        minutes: evt.t,
        label: evt.n || 'tool',
      });
      break;
    case 's':
      displayEvents.push({
        type: 's',
        minutes: evt.t,
        label: evt.n || 'skill',
      });
      break;
    case 'a':
      displayEvents.push({
        type: 'a',
        minutes: evt.t,
        label: evt.n || 'agent',
        sublabel: evt.d,
      });
      break;
  }
}

// Inject commit events before session end
const commitLines = commits
  .split('\n')
  .map(l => l.trim())
  .filter(l => l.length > 0);

const lastEventTime = displayEvents.length > 0
  ? displayEvents[displayEvents.length - 1].minutes
  : 0;
const commitTime = Math.max(lastEventTime + 1, durationMinutes - 2);

for (const line of commitLines) {
  displayEvents.push({
    type: 'commit',
    minutes: commitTime,
    label: line,
  });
}

// Inject session ended marker
displayEvents.push({
  type: 'end',
  minutes: durationMinutes,
  label: 'Session ended',
});
---

<div class="my-8">
  <h2 class="text-sm font-semibold text-muted uppercase tracking-wide mb-4">Timeline</h2>
  <div class="relative ml-[4.25rem] border-l border-border -translate-x-[0.4375rem]">
    <div class="-ml-[4.25rem] translate-x-[0.4375rem]">
      {displayEvents.map((evt) => (
        <TimelineEvent
          type={evt.type}
          minutes={evt.minutes}
          label={evt.label}
          sublabel={evt.sublabel}
        />
      ))}
    </div>
  </div>
</div>
```

- [ ] **Step 3: Verify build compiles**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx astro check`
Expected: No type errors related to Timeline components

- [ ] **Step 4: Commit**

```bash
git add blog/src/components/Timeline.astro blog/src/components/TimelineEvent.astro
git commit -m "feat: add Timeline and TimelineEvent components"
```

---

## Task 6: Redesigned Post Page

**Files:**
- Modify: `blog/src/pages/posts/[slug].astro`
- Modify: `blog/src/components/MetadataSidebar.astro`

**Context:** The current post page at `blog/src/pages/posts/[slug].astro` (lines 1-61) shows: header → blog_summary → notes → MetadataSidebar → commits → back link. The new layout per spec Part 4: header → auto-narrative → blog_summary (blockquote) → timeline → notes → simplified stats. `MetadataSidebar.astro` (lines 1-69) currently shows a grid of metadata + SkillBadge lists; we simplify it to just the stats grid.

- [ ] **Step 1: Rewrite the post page**

Replace the full content of `blog/src/pages/posts/[slug].astro`:

```astro
---
import Base from '../../layouts/Base.astro';
import MetadataSidebar from '../../components/MetadataSidebar.astro';
import Timeline from '../../components/Timeline.astro';
import { getPublishedPosts, parseTimeline } from '../../lib/notion';
import { generateNarrative } from '../../lib/narrative';
import type { JourneyPost } from '../../lib/notion';

export async function getStaticPaths() {
  const posts = await getPublishedPosts();
  return posts.map((post) => ({
    params: { slug: post.session_id },
    props: { post },
  }));
}

const { post } = Astro.props as { post: JourneyPost };
const timelineEvents = parseTimeline(post.session_timeline);
const narrative = generateNarrative(post, timelineEvents);

const commitLines = post.commits
  .split('\n')
  .map((line) => line.trim())
  .filter((line) => line.length > 0);
---

<Base title={`${post.project} — ${post.date}`}>
  <article>
    <header class="mb-6">
      <time class="text-muted text-sm">{post.date}</time>
      <span class="text-muted text-sm mx-2">·</span>
      <span class="font-mono text-sm text-muted">{post.project}</span>
      <hr class="border-border mt-4" />
    </header>

    <!-- Auto-narrative -->
    <div class="mb-6">
      <p class="text-text leading-relaxed">{narrative}</p>
    </div>

    <!-- Blog summary (author's take) -->
    {post.blog_summary && (
      <blockquote class="mb-6 pl-4 border-l-2 border-muted/30 text-muted leading-relaxed">
        {post.blog_summary}
      </blockquote>
    )}

    <!-- Visual timeline -->
    {timelineEvents.length > 0 && (
      <Timeline
        events={timelineEvents}
        commits={post.commits}
        durationMinutes={post.duration_minutes}
      />
    )}

    <!-- Notes -->
    {post.notes && (
      <div class="mb-8 pl-4 border-l-2 border-accent/40">
        <h2 class="text-sm font-semibold text-muted uppercase tracking-wide mb-2">Notes</h2>
        <p class="text-text leading-relaxed whitespace-pre-line">{post.notes}</p>
      </div>
    )}

    <!-- Session stats -->
    <MetadataSidebar post={post} />

    <!-- Commits (shown when no timeline — fallback for older sessions) -->
    {timelineEvents.length === 0 && commitLines.length > 0 && (
      <div class="mt-6">
        <h2 class="text-sm font-semibold text-muted uppercase tracking-wide mb-2">Commits</h2>
        <ul class="space-y-1">
          {commitLines.map((line) => (
            <li class="text-sm font-mono text-muted">• {line}</li>
          ))}
        </ul>
      </div>
    )}

    <div class="mt-10">
      <a href="/" class="text-accent hover:text-accent-hover text-sm">← Back to all posts</a>
    </div>
  </article>
</Base>
```

- [ ] **Step 2: Simplify MetadataSidebar**

Replace the full content of `blog/src/components/MetadataSidebar.astro`:

```astro
---
import type { JourneyPost } from '../lib/notion';

interface Props {
  post: JourneyPost;
}

const { post } = Astro.props;

const satisfactionDots = Array.from({ length: 5 }, (_, i) => i < post.satisfaction);
---

<div class="mt-8 p-4 bg-surface rounded border border-border">
  <h2 class="text-sm font-semibold text-muted uppercase tracking-wide mb-3">Session Stats</h2>
  <div class="grid grid-cols-2 gap-3 text-sm">
    <div>
      <span class="text-muted">Model</span>
      <span class="block font-mono text-text">{post.model}</span>
    </div>
    <div>
      <span class="text-muted">Duration</span>
      <span class="block font-mono text-text">{post.duration_minutes} min</span>
    </div>
    <div>
      <span class="text-muted">Messages</span>
      <span class="block font-mono text-text">{post.message_count}</span>
    </div>
    <div>
      <span class="text-muted">Category</span>
      <span class="block font-mono text-text">{post.category}</span>
    </div>
  </div>
  <div class="mt-3 flex items-center gap-1">
    <span class="text-muted text-sm mr-2">Satisfaction</span>
    {satisfactionDots.map((filled) => (
      <span class={`w-2 h-2 rounded-full ${filled ? 'bg-accent' : 'bg-border'}`}></span>
    ))}
  </div>
  <!-- Compact counts for tools/skills/agents -->
  <div class="mt-3 text-xs text-muted">
    {post.tools_used.length} tools · {post.skills_invoked.length} skills · {post.agents_dispatched.length} agents
  </div>
</div>
```

- [ ] **Step 3: Verify build compiles**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx astro check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add blog/src/pages/posts/[slug].astro blog/src/components/MetadataSidebar.astro
git commit -m "feat: redesign post page with auto-narrative and visual timeline"
```

---

## Task 7: Redesigned Home Page Cards

**Files:**
- Modify: `blog/src/components/PostCard.astro`

**Context:** Current `PostCard.astro` (lines 1-41) shows date, project, category badge, truncated blog_summary, and satisfaction dots. Per spec Part 5: replace summary with auto-generated one-liner, add tool/skill/agent counts.

- [ ] **Step 1: Rewrite PostCard.astro**

Replace the full content of `blog/src/components/PostCard.astro`:

```astro
---
import type { JourneyPost } from '../lib/notion';
import { generateOneLiner } from '../lib/narrative';

interface Props {
  post: JourneyPost;
}

const { post } = Astro.props;

const categoryColors: Record<string, string> = {
  debugging: 'bg-red-900/40 text-red-300 border-red-800',
  feature: 'bg-blue-900/40 text-blue-300 border-blue-800',
  refactor: 'bg-yellow-900/40 text-yellow-300 border-yellow-800',
  brainstorming: 'bg-purple-900/40 text-purple-300 border-purple-800',
  learning: 'bg-green-900/40 text-green-300 border-green-800',
};
const catStyle = categoryColors[post.category] || 'bg-surface text-muted border-border';

const satisfactionDots = Array.from({ length: 5 }, (_, i) => i < post.satisfaction);

const oneLiner = generateOneLiner(post);
---

<a href={`/posts/${post.session_id}`} class="block p-4 bg-surface rounded border border-border hover:border-accent/50 transition-colors">
  <div class="flex items-center gap-2 mb-2">
    <time class="text-xs text-muted">{post.date}</time>
    <span class="text-xs text-muted">·</span>
    <span class="font-mono text-xs text-muted">{post.project}</span>
    <span class={`text-xs px-1.5 py-0.5 rounded border ${catStyle}`}>{post.category}</span>
  </div>

  <p class="text-sm text-text leading-relaxed mb-2">{oneLiner}</p>

  <div class="flex items-center justify-between">
    <div class="flex items-center gap-1">
      {satisfactionDots.map((filled) => (
        <span class={`w-1.5 h-1.5 rounded-full ${filled ? 'bg-accent' : 'bg-border'}`}></span>
      ))}
    </div>
    <span class="text-xs text-muted">
      {post.tools_used.length} tools · {post.skills_invoked.length} skills · {post.agents_dispatched.length} agents
    </span>
  </div>
</a>
```

- [ ] **Step 2: Verify build compiles**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx astro check`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add blog/src/components/PostCard.astro
git commit -m "feat: redesign home page cards with auto-generated one-liners"
```

---

## Task 8: Redesigned Skills Page

**Files:**
- Create: `blog/src/components/SkillProfile.astro`
- Modify: `blog/src/pages/skills.astro`

**Context:** The current skills page at `blog/src/pages/skills.astro` (lines 1-35) renders a simple list with SkillBadge, count, last used, and projects. Per spec Part 6: replace with SkillProfile cards showing avgSatisfaction, sessions (latest 5 with +N more), and hot/cold labels. The enhanced `getAllSkills()` already returns the needed data from Task 3.

- [ ] **Step 1: Create SkillProfile.astro**

Create `blog/src/components/SkillProfile.astro`:

```astro
---
import type { SkillStats } from '../lib/notion';

interface Props {
  skill: SkillStats;
}

const { skill } = Astro.props;

const labelStyles: Record<string, string> = {
  hot: 'text-red-400 bg-red-900/30 border-red-800',
  cold: 'text-blue-400 bg-blue-900/30 border-blue-800',
};

const displaySessions = skill.sessions.slice(-5);
const extraCount = skill.sessions.length - displaySessions.length;

const satisfactionDots = Array.from({ length: 5 }, (_, i) =>
  i < Math.round(skill.avgSatisfaction)
);
---

<div class="p-4 bg-surface rounded border border-border">
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <span class="text-purple-400 font-mono text-sm font-semibold">{skill.name}</span>
    </div>
    {skill.label && (
      <span class={`text-xs px-1.5 py-0.5 rounded border ${labelStyles[skill.label]}`}>
        {skill.label === 'hot' ? '↑ HOT' : '↓ COLD'}
      </span>
    )}
  </div>

  <div class="text-sm text-muted mb-1">
    Used {skill.count}× across {skill.projects.length} project{skill.projects.length === 1 ? '' : 's'}
  </div>

  <div class="flex items-center gap-3 text-sm text-muted mb-2">
    <div class="flex items-center gap-1">
      <span>Avg:</span>
      {satisfactionDots.map((filled) => (
        <span class={`w-1.5 h-1.5 rounded-full ${filled ? 'bg-accent' : 'bg-border'}`}></span>
      ))}
    </div>
    <span>·</span>
    <span>Last: {skill.lastUsed}</span>
  </div>

  <div class="text-xs text-muted mb-1">
    <span class="text-muted/70">Projects:</span> {skill.projects.join(', ')}
  </div>

  <div class="text-xs text-muted">
    <span class="text-muted/70">Sessions:</span>
    {displaySessions.map((sid, i) => (
      <>
        <a href={`/posts/${sid}`} class="text-accent hover:text-accent-hover">{sid}</a>
        {i < displaySessions.length - 1 && ', '}
      </>
    ))}
    {extraCount > 0 && (
      <span class="text-muted/50"> +{extraCount} more</span>
    )}
  </div>
</div>
```

- [ ] **Step 2: Rewrite skills.astro**

Replace the full content of `blog/src/pages/skills.astro`:

```astro
---
import Base from '../layouts/Base.astro';
import SkillProfile from '../components/SkillProfile.astro';
import { getAllSkills } from '../lib/notion';

const skills = await getAllSkills();
---

<Base title="Skill Directory">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-xl font-semibold text-text">Skill Directory</h1>
    <span class="text-sm text-muted">{skills.length} skill{skills.length === 1 ? '' : 's'}</span>
  </div>

  {skills.length === 0 ? (
    <p class="text-muted">No skills recorded yet.</p>
  ) : (
    <div class="space-y-4">
      {skills.map((skill) => (
        <SkillProfile skill={skill} />
      ))}
    </div>
  )}
</Base>
```

- [ ] **Step 3: Verify build compiles**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx astro check`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add blog/src/components/SkillProfile.astro blog/src/pages/skills.astro
git commit -m "feat: redesign skills page with profiles, satisfaction, and hot/cold labels"
```

---

## Task 9: End-to-End Validation

**Files:** None (validation only)

**Context:** All pieces are in place. This task validates that everything works together: Python tests pass, TypeScript tests pass, and the Astro blog builds successfully with real Notion data.

- [ ] **Step 1: Run all Python tests**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger && .venv/bin/python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run all TypeScript tests**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npx vitest run`
Expected: All PASS

- [ ] **Step 3: Build the blog**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npm run build`
Expected: Build succeeds. Check output for generated pages count.

- [ ] **Step 4: Preview and spot-check**

Run: `cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog && npm run preview`

Check in browser:
- Home page: cards show one-liner summaries and tool/skill/agent counts
- Post page (any): auto-narrative at top, blog_summary in blockquote, timeline visual (for sessions that have timeline data), simplified stats at bottom
- Post page (older session without timeline): fallback narrative, no timeline section, commits shown as bullet list
- Skills page: skill profiles with counts, satisfaction dots, hot/cold labels, session links

- [ ] **Step 5: Commit any fixes from validation**

If fixes were needed:
```bash
git add -A
git commit -m "fix: address issues found during end-to-end validation"
```
