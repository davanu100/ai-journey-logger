"""Parse Claude Code JSONL transcript files."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def _extract_model_short(model_id: str) -> str:
    if not model_id:
        return ""
    for name in ("opus", "sonnet", "haiku"):
        if name in model_id:
            return name
    return model_id


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse ISO 8601 timestamp string, return None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _minutes_since(origin: datetime, ts: datetime) -> int:
    """Return whole minutes between origin and ts."""
    delta = ts - origin
    return int(delta.total_seconds() // 60)


def _deduplicate_tools(tool_names: list[str]) -> list[tuple[str, int]]:
    """Collapse consecutive same-tool names into (name, count) pairs."""
    if not tool_names:
        return []
    groups: list[tuple[str, int]] = []
    current = tool_names[0]
    count = 1
    for name in tool_names[1:]:
        if name == current:
            count += 1
        else:
            groups.append((current, count))
            current = name
            count = 1
    groups.append((current, count))
    return groups


def _build_timeline(events: list[dict]) -> str:
    """Cap events, enforce budget, and serialize to JSON string."""
    if not events:
        return ""

    # Cap at 40 events: first 15 + last 25
    if len(events) > 40:
        events = events[:15] + events[-25:]

    def serialize(evs: list[dict]) -> str:
        return json.dumps(evs, ensure_ascii=False, separators=(",", ":"))

    result = serialize(events)
    if len(result) <= 1900:
        return result

    # Step 1: drop 'd' fields from agent events
    stripped = [{k: v for k, v in e.items() if k != "d"} for e in events]
    result = serialize(stripped)
    if len(result) <= 1900:
        return result

    # Step 2: shorten 'tx' fields to 60 chars
    shortened = []
    for e in stripped:
        if "tx" in e:
            e = {**e, "tx": e["tx"][:60]}
        shortened.append(e)
    result = serialize(shortened)
    if len(result) <= 1900:
        return result

    # Step 3: reduce to 30 events (first 15 + last 15)
    reduced = shortened[:15] + shortened[-15:]
    result = serialize(reduced)
    if len(result) <= 1900:
        return result

    # Last resort: keep trimming until under budget
    while len(result) > 1900 and len(reduced) > 1:
        reduced = reduced[:-1]
        result = serialize(reduced)

    return result


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
    timeline_events: list[dict] = []
    first_user_ts: datetime | None = None

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type")
                entry_ts = _parse_timestamp(entry.get("timestamp", ""))

                if entry_type == "user":
                    message_count += 1
                    content = entry.get("message", {}).get("content", "")

                    if initial_prompt is None:
                        if isinstance(content, str):
                            initial_prompt = content[:500]

                    # Timeline: record prompt event
                    if isinstance(content, str) and content:
                        if first_user_ts is None and entry_ts is not None:
                            first_user_ts = entry_ts
                        t_min = 0
                        if first_user_ts is not None and entry_ts is not None:
                            t_min = _minutes_since(first_user_ts, entry_ts)
                        timeline_events.append({
                            "ty": "p",
                            "tx": content[:100],
                            "t": t_min,
                        })

                elif entry_type == "assistant":
                    message_count += 1
                    msg = entry.get("message", {})

                    if model is None:
                        model = _extract_model_short(msg.get("model", ""))

                    t_min = 0
                    if first_user_ts is not None and entry_ts is not None:
                        t_min = _minutes_since(first_user_ts, entry_ts)

                    # Collect tool_use blocks
                    regular_tools: list[str] = []
                    for block in msg.get("content", []):
                        if block.get("type") != "tool_use":
                            continue
                        name = block.get("name", "")
                        if name:
                            tool_names.add(name)

                        if name == "Skill":
                            # Flush accumulated regular tools first
                            for tool_name, count in _deduplicate_tools(regular_tools):
                                label = tool_name if count == 1 else f"{tool_name} \u00d7{count}"
                                timeline_events.append({"ty": "t", "n": label, "t": t_min})
                            regular_tools = []

                            skill = block.get("input", {}).get("skill", "")
                            if skill:
                                skill_counter[skill] += 1
                                timeline_events.append({"ty": "s", "n": skill, "t": t_min})

                        elif name == "Agent":
                            # Flush accumulated regular tools first
                            for tool_name, count in _deduplicate_tools(regular_tools):
                                label = tool_name if count == 1 else f"{tool_name} \u00d7{count}"
                                timeline_events.append({"ty": "t", "n": label, "t": t_min})
                            regular_tools = []

                            agent_type = block.get("input", {}).get("subagent_type", "general-purpose")
                            description = block.get("input", {}).get("description", "")
                            agent_counter[agent_type] += 1
                            event: dict = {"ty": "a", "n": agent_type, "t": t_min}
                            if description:
                                event["d"] = description
                            timeline_events.append(event)

                        else:
                            if name:
                                regular_tools.append(name)

                    # Flush remaining regular tools
                    for tool_name, count in _deduplicate_tools(regular_tools):
                        label = tool_name if count == 1 else f"{tool_name} \u00d7{count}"
                        timeline_events.append({"ty": "t", "n": label, "t": t_min})

    except OSError:
        return empty

    timeline_str = _build_timeline(timeline_events)

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
