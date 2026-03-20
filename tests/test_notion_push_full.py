import json

from lib.notion_push import build_properties


def test_build_properties_all_fields():
    entry = {
        "session_id": "sess-001",
        "date": "2026-03-20",
        "project": "my-app",
        "commits": "abc1234 feat: login",
        "duration_minutes": 45,
        "model": "opus",
        "initial_prompt": "Help me debug auth",
        "tools_used": ["Bash", "Edit", "Read"],
        "skills_invoked": ["go-latency-metrics"],
        "skill_counts": [{"name": "go-latency-metrics", "count": 2}],
        "skills_created": "new-skill",
        "agents_dispatched": ["Explore"],
        "agent_counts": [{"type": "Explore", "count": 1}],
        "message_count": 12,
    }
    props = build_properties(entry)
    assert props["session_id"]["title"][0]["text"]["content"] == "sess-001"
    assert props["date"]["date"]["start"] == "2026-03-20"
    assert props["project"]["rich_text"][0]["text"]["content"] == "my-app"
    assert props["commits"]["rich_text"][0]["text"]["content"] == "abc1234 feat: login"
    assert props["duration_minutes"]["number"] == 45
    assert props["model"]["select"]["name"] == "opus"
    assert props["initial_prompt"]["rich_text"][0]["text"]["content"] == "Help me debug auth"
    assert props["tools_used"]["multi_select"] == [{"name": "Bash"}, {"name": "Edit"}, {"name": "Read"}]
    assert props["skills_invoked"]["multi_select"] == [{"name": "go-latency-metrics"}]
    assert props["skill_counts"]["rich_text"][0]["text"]["content"] == json.dumps([{"name": "go-latency-metrics", "count": 2}])
    assert props["skills_created"]["rich_text"][0]["text"]["content"] == "new-skill"
    assert props["agents_dispatched"]["multi_select"] == [{"name": "Explore"}]
    assert props["agent_counts"]["rich_text"][0]["text"]["content"] == json.dumps([{"type": "Explore", "count": 1}])
    assert props["message_count"]["number"] == 12


def test_build_properties_with_manual_fields():
    entry = {
        "session_id": "sess-002", "date": "2026-03-20", "project": "my-app",
        "commits": "", "duration_minutes": 10, "model": "sonnet",
        "initial_prompt": "Quick question", "tools_used": [], "skills_invoked": [],
        "skill_counts": [], "skills_created": "", "agents_dispatched": [],
        "agent_counts": [], "message_count": 2,
        "model_fit": "right", "category": "learning", "mode": "guided",
        "iterations_to_happy": 1, "iteration_friction": "",
        "learned_something": "New API pattern", "satisfaction": 5,
        "publish": False, "blog_summary": "",
    }
    props = build_properties(entry)
    assert props["model_fit"]["select"]["name"] == "right"
    assert props["category"]["select"]["name"] == "learning"
    assert props["satisfaction"]["number"] == 5
    assert props["publish"]["checkbox"] is False


def test_build_properties_empty_optional_fields():
    entry = {
        "session_id": "sess-003", "date": "2026-03-20", "project": "my-app",
        "commits": "", "duration_minutes": 5, "model": "", "initial_prompt": "",
        "tools_used": [], "skills_invoked": [], "skill_counts": [],
        "skills_created": "", "agents_dispatched": [], "agent_counts": [],
        "message_count": 0,
    }
    props = build_properties(entry)
    assert props["model"]["select"] is None
    assert props["tools_used"]["multi_select"] == []
    assert "model_fit" not in props
    assert "satisfaction" not in props


def test_build_properties_phase1a_only_entry():
    entry = {
        "session_id": "sess-old", "date": "2026-03-19",
        "project": "my-app", "commits": "abc fix", "duration_minutes": 10,
    }
    props = build_properties(entry)
    assert props["session_id"]["title"][0]["text"]["content"] == "sess-old"
    assert props["duration_minutes"]["number"] == 10
    assert props["model"]["select"] is None
    assert props["tools_used"]["multi_select"] == []
    assert props["message_count"]["number"] == 0
