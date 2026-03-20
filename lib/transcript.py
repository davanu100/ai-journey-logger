"""Parse Claude Code JSONL transcript files."""

import json
from collections import Counter
from pathlib import Path


def _extract_model_short(model_id: str) -> str:
    if not model_id:
        return ""
    for name in ("opus", "sonnet", "haiku"):
        if name in model_id:
            return name
    return model_id


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
    }

    if not path.exists():
        return empty

    initial_prompt = None
    model = None
    message_count = 0
    tool_names = set()
    skill_counter: Counter = Counter()
    agent_counter: Counter = Counter()

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                entry_type = entry.get("type")

                if entry_type == "user":
                    message_count += 1
                    if initial_prompt is None:
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, str):
                            initial_prompt = content[:500]

                elif entry_type == "assistant":
                    message_count += 1
                    msg = entry.get("message", {})

                    if model is None:
                        model = _extract_model_short(msg.get("model", ""))

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

                        elif name == "Agent":
                            agent_type = block.get("input", {}).get("subagent_type", "general-purpose")
                            agent_counter[agent_type] += 1

    except (json.JSONDecodeError, OSError):
        return empty

    return {
        "initial_prompt": initial_prompt or "",
        "model": model or "",
        "message_count": message_count,
        "tools_used": sorted(tool_names),
        "skills_invoked": sorted(skill_counter.keys()),
        "skill_counts": [{"name": k, "count": v} for k, v in sorted(skill_counter.items())],
        "agents_dispatched": sorted(agent_counter.keys()),
        "agent_counts": [{"type": k, "count": v} for k, v in sorted(agent_counter.items())],
    }
