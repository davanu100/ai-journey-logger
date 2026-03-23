"""One-time script to create the AI Journey Log database in Notion.

Usage:
    NOTION_TOKEN=ntn_xxx NOTION_PARENT_PAGE_ID=xxx python3 setup_notion_db.py

The NOTION_PARENT_PAGE_ID is the ID of the Notion page where the database will be created.
You can get it from the page URL: https://www.notion.so/Page-Title-<PAGE_ID>
"""

import os
import sys
from notion_client import Client


def main():
    token = os.environ.get("NOTION_TOKEN")
    parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")

    if not token or not parent_page_id:
        print("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID environment variables.")
        sys.exit(1)

    notion = Client(auth=token)

    properties = {
        "session_id": {"title": {}},
        "date": {"date": {}},
        "project": {"rich_text": {}},
        "model": {
            "select": {
                "options": [
                    {"name": "haiku", "color": "green"},
                    {"name": "sonnet", "color": "blue"},
                    {"name": "opus", "color": "purple"},
                ],
            },
        },
        "commits": {"rich_text": {}},
        "duration_minutes": {"number": {"format": "number"}},
        "initial_prompt": {"rich_text": {}},
        "tools_used": {"multi_select": {"options": []}},
        "skills_invoked": {"multi_select": {"options": []}},
        "skill_counts": {"rich_text": {}},
        "skills_created": {"rich_text": {}},
        "agents_dispatched": {"multi_select": {"options": []}},
        "agent_counts": {"rich_text": {}},
        "session_timeline": {"rich_text": {}},
        "message_count": {"number": {"format": "number"}},
        "model_fit": {
            "select": {
                "options": [
                    {"name": "right", "color": "green"},
                    {"name": "overkill", "color": "yellow"},
                    {"name": "underpowered", "color": "red"},
                ],
            },
        },
        "category": {
            "select": {
                "options": [
                    {"name": "debugging", "color": "red"},
                    {"name": "feature", "color": "blue"},
                    {"name": "refactor", "color": "yellow"},
                    {"name": "brainstorming", "color": "purple"},
                    {"name": "learning", "color": "green"},
                ],
            },
        },
        "mode": {
            "select": {
                "options": [
                    {"name": "guided", "color": "blue"},
                    {"name": "autonomous", "color": "orange"},
                ],
            },
        },
        "iterations_to_happy": {"number": {"format": "number"}},
        "iteration_friction": {"rich_text": {}},
        "learned_something": {"rich_text": {}},
        "satisfaction": {"number": {"format": "number"}},
        "publish": {"checkbox": {}},
        "blog_summary": {"rich_text": {}},
        "notes": {"rich_text": {}},
    }

    # Step 1: Create database with default title property
    response = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "AI Journey Log"}}],
        properties={},
    )

    db_id = response["id"]
    print(f"Database created: {db_id}")

    # Step 2: Rename default "Name" title to "session_id" and add all properties
    # (notion-client v3 / API 2022-06-28 doesn't support custom title in create)
    properties["Name"] = properties.pop("session_id")
    properties["Name"]["name"] = "session_id"

    notion.databases.update(database_id=db_id, properties=properties)

    print(f"Database schema configured successfully!")
    print(f"Database ID: {db_id}")
    print(f"")
    print(f"Add to your environment:")
    print(f"  export NOTION_DATABASE_ID={db_id}")


if __name__ == "__main__":
    main()
