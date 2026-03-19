# AI Journey Logger — Design Spec

## Goal

Build a system that automatically logs the user's daily AI-assisted development work across Claude Code sessions, stores it in Notion (private), and publishes curated entries to a personal blog (public).

## Architecture Overview

Three layers:

1. **Collection layer** — Claude Code hooks that capture session metadata automatically and prompt the user for manual inputs
2. **Storage layer** — Notion as the single source of truth (private by default)
3. **Presentation layer** — Astro static blog pulling from Notion as CMS (public, opt-in per entry)

```
Claude Code session finishing
  → Stop hook fires (Claude finished responding)
  → prompts user for: satisfaction, friction notes, learnings, publish flag
  → writes manual fields to state file
  → SessionEnd hook fires (session terminating)
  → auto-captures: project, commits, tools, skills, agents, model, duration
  → reads manual fields from state file
  → pushes complete entry to Notion via API
  → on failure: writes to local fallback file for retry
```

---

## Data Schema

Each session produces one Notion page with the following properties:

### Automated Fields

| Field | Type | Source |
|---|---|---|
| `session_id` | Text | Claude Code session ID from hook input `session_id` field |
| `date` | Date | System clock |
| `project` | Text | Git repo name from `cwd` in hook input (basename of working directory) |
| `model` | Select | Active model at session end (haiku/sonnet/opus) |
| `initial_prompt` | Text (truncated to 500 chars) | First user message in session transcript JSONL |
| `commits` | Text (multi-line) | `git log --oneline --no-decorate --since=<session_start>` (truncated to 2000 chars). Empty string if no commits. |
| `tools_used` | Multi-select | Distinct tool names invoked (Skill, Agent, Bash, Edit, etc.) |
| `skills_invoked` | Multi-select | Distinct skill names from Skill tool calls (for Notion-native querying) |
| `skill_counts` | Text | JSON `[{name, count}]` for detailed per-skill counts |
| `skills_created` | Text | New files in `~/.claude/skills/` (diff against session start snapshot) |
| `agents_dispatched` | Multi-select | Distinct agent types dispatched |
| `agent_counts` | Text | JSON `[{type, count}]` for detailed per-type counts |
| `message_count` | Number | Total user + assistant messages in transcript |
| `duration_minutes` | Number | Computed from session start timestamp in state file. Null if state file missing. |

### Manual Fields (prompted via Stop hook)

| Field | Type | Prompt |
|---|---|---|
| `model_fit` | Select: right / overkill / underpowered | "Was the model a good fit for this session?" |
| `category` | Select: debugging / feature / refactor / brainstorming / learning | "What best describes this session?" |
| `mode` | Select: guided / autonomous | "Were you actively guiding or did Claude run autonomously?" |
| `iterations_to_happy` | Number (1-5) | "How many attempts to get the result you wanted?" |
| `iteration_friction` | Text | "What caused the extra iterations? (bad prompt, misunderstanding, scope change)" |
| `learned_something` | Text | "Did Claude surface anything you didn't know?" |
| `satisfaction` | Number (1-5) | "Overall satisfaction with this session?" |
| `publish` | Checkbox | "Publish this to your blog?" |
| `blog_summary` | Text | Only if publish=true: "One-paragraph summary for the blog" |

---

## Collection Layer: Claude Code Hooks

### Hook Input Context

All hooks receive JSON on stdin with common fields:
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory"
}
```

### State File

Path: `~/.claude-journey/.session-state`

Written by SessionStart hook, read by Stop and SessionEnd hooks.

Format:
```json
{
  "session_id": "abc123",
  "start_time": "2026-03-19T10:30:00+05:30",
  "skills_snapshot": ["local-service-testing", "go-latency-metrics", "..."]
}
```

Updated by Stop hook to include manual fields:
```json
{
  "session_id": "abc123",
  "start_time": "...",
  "skills_snapshot": ["..."],
  "manual": {
    "model_fit": "right",
    "category": "debugging",
    "satisfaction": 4,
    "...": "..."
  }
}
```

### SessionStart Hook

Event: `SessionStart` (matcher: `startup`)

1. Snapshots `~/.claude/skills/` directory listing
2. Records session start timestamp (ISO 8601)
3. Records session_id from hook input
4. Writes state file to `~/.claude-journey/.session-state`

### Stop Hook (Manual Field Collection)

Event: `Stop`

Fires when Claude finishes responding. This hook CAN block and prompt the user.

1. Reads state file to check if manual fields already collected for this session
2. If not collected yet, outputs a JSON `decision: "block"` with a prompt asking the user for manual fields
3. Writes manual fields to state file
4. On subsequent Stop events in the same session, skips (already collected)

**Note:** The Stop hook fires on every agent completion. Check `session_id` matches and skip if manual fields are already present in state file.

### SessionEnd Hook (Automated Capture + Notion Push)

Event: `SessionEnd`

Non-blocking. Runs when session terminates.

1. Reads session transcript from `transcript_path` to extract:
   - First user message (initial_prompt, truncated to 500 chars)
   - Tool invocations (distinct names for multi-select + counts)
   - Skill invocations (distinct names for multi-select + counts)
   - Agent dispatches (distinct types for multi-select + counts)
   - Message count
2. Runs `git log --oneline --no-decorate --since=<start_time>` from `cwd` (truncated to 2000 chars)
3. Diffs `~/.claude/skills/` against snapshot in state file to detect new skills
4. Reads manual fields from state file (if present; null if user skipped)
5. Pushes complete entry to Notion via API
6. On Notion API failure: appends entry as JSON to `~/.claude-journey/pending.jsonl`
7. Cleans up state file

### Retry Mechanism

SessionStart hook checks `~/.claude-journey/pending.jsonl` on startup. If entries exist, attempts to push them to Notion before proceeding. Successfully pushed entries are removed from the file.

### Skill Hit Rate Tracking

`skills_invoked` is stored as a Notion Multi-select property (not JSON text), enabling native Notion filtering and grouping. The separate `skill_counts` text field preserves per-session invocation counts for detailed analysis.

Cumulative hit rate: queryable via Notion database filter on `skills_invoked` multi-select values.

---

## Storage Layer: Notion

### Database Structure

A single Notion database: **"AI Journey Log"**

- Each row = one Claude Code session (deduplicated by `session_id`)
- Properties match the data schema above
- Views:
  - **Timeline** — default, sorted by date
  - **By Project** — grouped by project field
  - **By Category** — grouped by category
  - **Published** — filtered to publish=true (feeds the blog)
  - **Skills** — filtered/grouped by skills_invoked multi-select for hit rate analysis

### Aggregated Insights (Notion formulas / rollups)

Queryable directly from Notion:
- Average satisfaction over last 7/30 days
- Average iterations_to_happy trending over time
- Skill invocation frequency (which skills pull their weight)
- Model usage distribution (% sonnet vs opus vs haiku)
- Time spent per category (debugging vs feature vs refactor)
- Session count per project

---

## Presentation Layer: Astro Blog

### Why Astro

- Static-first (fast, cheap to host)
- Well-tested Notion integration (@notionhq/client + notion-to-md)
- Deploys to Vercel/Netlify with zero config
- Lighter than Next.js for a read-only blog

### Site Structure

```
/                       → Home: latest entries, stats summary
/posts/:slug            → Individual session write-up
/stats                  → Aggregated insights (charts)
/skills                 → Skill directory with hit rates
```

### Content Pipeline

1. Astro build step queries Notion API for pages where `publish=true`
2. Converts Notion blocks to Markdown
3. Renders with Astro components (metadata sidebar, commit list, skill badges)
4. Deploys as static site

### Rebuild Trigger

- Phase 2: GitHub Actions cron job rebuilds site daily
- Phase 4: Notion webhook → Vercel build hook for instant publish

---

## Privacy Boundary

**Private (Notion only):**
- Full session transcript references
- Internal endpoints, configs, team details
- Raw initial prompts (may contain internal context — truncated, not sanitized; treat Notion as private)
- All fields by default

**Public (blog):**
- Only entries where `publish=true`
- Uses `blog_summary` (user-written) as the main content, not raw prompts
- Commits shown as messages only (no SHAs or internal repo URLs)
- Sanitized project names if needed

The user explicitly opts in per entry. Nothing is public by default.

---

## Tech Stack

| Component | Technology |
|---|---|
| Session hooks | Python scripts (single language for hooks + Notion client) |
| Notion API | Python `notion-client` |
| State/fallback files | JSON at `~/.claude-journey/` |
| Blog framework | Astro |
| Hosting | Vercel (free tier) |
| Styling | Tailwind CSS |
| Charts (stats page) | Recharts or Chart.js |
| Daily rebuild | GitHub Actions cron |

---

## Implementation Phases

### Phase 1a: Core Pipeline (trivially available fields)
- Set up `~/.claude-journey/` directory and state file convention
- Build SessionStart hook (state file creation)
- Build SessionEnd hook with Notion push for: session_id, date, project, commits, duration
- Set up Notion database with full schema
- Build fallback to `pending.jsonl` on Notion API failure
- Build retry mechanism in SessionStart hook
- Validate with 3-5 real sessions

### Phase 1b: Transcript-Dependent Fields
- Add transcript parsing to SessionEnd hook: initial_prompt, tools_used, skills_invoked, agents_dispatched, message_count
- Add skills diff (skills_created)
- Build Stop hook for manual field collection

### Phase 2: Blog
- Scaffold Astro site
- Integrate Notion as content source
- Build post template, home page, basic styling
- Deploy to Vercel
- Set up GitHub Actions daily rebuild cron

### Phase 3: Analytics
- Stats page with aggregated insights
- Skill hit rate dashboard
- Model usage distribution chart
- Satisfaction and iteration trends

### Phase 4: Polish
- Notion webhook for instant rebuild
- RSS feed
- Search
- Tags/categories filtering on the blog

---

## Known Limitations

1. **Multi-project sessions** — The `project` field reflects the working directory at session end. If the user switches projects mid-session, only the final project is captured. Acceptable for now; transcript parsing could detect multiple `cwd` values in a future iteration.
2. **Stop hook frequency** — The Stop hook fires on every agent completion, not just session end. The hook must check state file to avoid re-prompting for manual fields.
3. **Notion text limits** — Text properties have a 2000-character limit. `commits` and `initial_prompt` are truncated. `skill_counts` and `agent_counts` are unlikely to hit this limit but should be truncated defensively.

---

## Resolved Questions

1. **Transcript access** — CONFIRMED: Claude Code hooks receive `transcript_path` in the JSON input on stdin. The SessionEnd hook can read and parse the full JSONL transcript.
2. **Interactive prompts** — CONFIRMED: `SessionEnd` hooks are non-blocking and cannot prompt interactively. Solution: use the `Stop` hook (which CAN block) to collect manual fields, write to state file, then `SessionEnd` reads from state file.

## Open Questions

1. **Notion workspace** — Does the user have an existing Notion workspace, or create a new one?
2. **Domain** — Custom domain for the blog, or fine with `*.vercel.app`?
