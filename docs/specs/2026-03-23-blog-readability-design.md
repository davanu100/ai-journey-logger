# Blog Readability & Auto-Summary — Design Spec

## Goal

Make the AI Journey Log blog actually useful — auto-generate human-readable session narratives, add a visual timeline showing what happened in each session, and redesign the skills page to surface usage patterns and effectiveness signals.

## Problem

The current blog posts are data dumps: flat badge lists for tools/skills/agents, raw commit strings, and a metadata grid. You can't quickly understand what happened in a session without reading every field. The skills page is a bare list with no context.

---

## Part 1: Enhanced Transcript Parser — Event Log

### Changes to `lib/transcript.py`

Extend `parse_transcript()` to return a new `timeline` field — an ordered list of events extracted from the JSONL transcript.

**Event types:**

| Type | Key | Source | Fields |
|---|---|---|---|
| Prompt | `p` | All `user` messages (not just the first) | `tx` (text, truncated 100 chars) |
| Tool | `t` | `assistant` tool_use blocks | `n` (name, with ×count if consecutive) |
| Skill | `s` | `Skill` tool_use | `n` (skill name) |
| Agent | `a` | `Agent` tool_use | `n` (subagent_type), `d` (description) |

Each event gets a `t` field — minutes since session start, derived from JSONL entry timestamps.

**Deduplication:** Consecutive same-tool uses collapse into one event (e.g., `Read ×5`). Skills and agents are always individual events.

**Size limit:** Cap at 40 events. If more, keep first 15 + last 25 for a natural "start and finish" feel.

**Compact JSON format** (to fit Notion's 2000-char rich_text limit):

```json
[{"ty":"p","tx":"Help me debug auth","t":0},{"ty":"t","n":"Read ×5","t":1},{"ty":"s","n":"systematic-debugging","t":3},{"ty":"a","n":"Explore","d":"Search auth code","t":5},{"ty":"t","n":"Edit ×3","t":12}]
```

Short keys: `ty` (type), `tx` (text), `n` (name), `d` (description), `t` (minutes).

**Budget enforcement:** After building the event list and applying the 40-event cap, serialize to JSON. If the resulting string exceeds 1900 chars (leaving margin for Notion overhead), progressively truncate: (1) drop `d` fields from agents, (2) shorten `tx` fields to 60 chars, (3) reduce cap to 30 events. Re-serialize after each step until under 1900 chars.

**Error resilience:** Timeline extraction processes each JSONL line independently. A malformed line is skipped — it never causes the entire timeline to fail. If the final timeline is empty or extraction raises an unexpected error, `session_timeline` is set to an empty string (not omitted), and the session logs normally without timeline data.

### Changes to `hooks/session_end.py`

Add `session_timeline` to the entry dict before pushing to Notion. The timeline JSON string comes from the enhanced `parse_transcript()`.

### Changes to `lib/notion_push.py`

Add `session_timeline` to `build_properties()` as a rich_text field.

---

## Part 2: Notion Schema

**New property:** `session_timeline` (rich_text) — compact JSON event array.

Add to `setup_notion_db.py` for documentation and run one-time migration on the live database.

**Backward compatibility:** `build_properties()` in `notion_push.py` uses `.get()` with defaults, so pending entries serialized before this migration (lacking `session_timeline`) will retry safely — the field will simply be empty.

---

## Part 3: Build-Time Narrative Generator

### New file: `blog/src/lib/narrative.ts`

Two functions:

**`generateOneLiner(post: JourneyPost): string`**

For home page cards. Template-driven:
> "45-min opus session on ai-journey-logger — debugged auth across 3 commits using systematic-debugging"

Built from: `duration_minutes` + `model` + `project` + `category` + commit count + top skill (most invoked).

**`generateNarrative(post: JourneyPost, timeline: TimelineEvent[]): string`**

For post page. A 2-3 sentence paragraph:
> "A 45-minute debugging session using opus. Started by investigating auth token validation, then invoked systematic-debugging to isolate the issue. Dispatched an Explore agent to search the codebase, followed by targeted edits across 3 files. Produced 3 commits fixing the auth flow."

Built from timeline events + metadata. Deterministic template logic, not AI.

**Narrative construction rules:**

1. **Opening sentence:** Always `"A {duration}-minute {category} session using {model}."` If duration is missing, omit it.
2. **Middle sentences (1-2):** Walk timeline events in order. For each event type:
   - Prompt → `"Started by {tx}"` (first prompt only; subsequent prompts ignored in narrative)
   - Skill → `"invoked {name}"`
   - Agent → `"dispatched a {subagent_type} agent to {description}"`
   - Tool → `"used {name}"` (only include if tool count ≥ 3 for that tool, to avoid noise)
   - Combine consecutive events with "then" / "followed by". Max 2 middle sentences.
3. **Closing sentence:** `"Produced {N} commit(s) {first commit message}."` If no commits, omit.

Example output: `"A 45-minute debugging session using opus. Started by investigating auth token validation, then invoked systematic-debugging and dispatched an Explore agent to search the codebase. Produced 3 commits fixing the auth flow."`

**Fallback for older sessions** (no timeline data): simpler summary from aggregates:
> "45-min opus session — used 14 tools, invoked 12 skills, dispatched 4 agents."

### Timeline type

```typescript
interface TimelineEvent {
  ty: 'p' | 't' | 's' | 'a';  // prompt, tool, skill, agent
  t: number;                     // minutes since start
  n?: string;                    // name
  tx?: string;                   // text (for prompts)
  d?: string;                    // description (for agents)
}
```

---

## Part 4: Redesigned Post Page

### Layout (top to bottom)

1. **Header** — date · project
2. **Auto-narrative** — generated paragraph describing the session
3. **Manual blog_summary** — if present, shown in a subtle blockquote style below the narrative (author's take vs auto-generated facts)
4. **Timeline** — visual vertical timeline, the centerpiece
5. **Notes** — if present, with left accent border
6. **Session stats** — simplified: model, duration, messages, satisfaction dots

### Timeline Visual

```
 0 min  ● "Help me debug auth"
         │
 1 min  ● Read ×5, Grep ×2
         │
 3 min  ◆ systematic-debugging
         │
 5 min  ▲ Explore: "Search for auth code"
         │
12 min  ● Edit ×3
         │
35 min  ★ fix: auth token validation
         │
45 min  ○ Session ended
```

**Styling:**
- Vertical line connecting events (Tailwind border-left on a div)
- Color-coded dots: blue for tools, purple for skills, green for agents, yellow for commits, gray for start/end
- Timestamp left-aligned (monospace, muted), event name/description right of the line
- Agent descriptions shown in smaller muted text below the agent name

**Commit events:** Commits from the post's `commits` field are injected into the timeline **at render time in the Astro component** — they are NOT stored in the Notion `session_timeline` property. Since we don't have exact commit timestamps, they appear at the end of the timeline before the "Session ended" marker.

**Session ended marker:** The `Timeline.astro` component injects a synthetic "Session ended" event at render time, using `duration_minutes` from the post as its timestamp.

### Components

- Modify: `blog/src/pages/posts/[slug].astro` — new layout
- Create: `blog/src/components/Timeline.astro` — renders timeline events
- Create: `blog/src/components/TimelineEvent.astro` — single event node
- Modify: `blog/src/components/MetadataSidebar.astro` — simplified to just stats (remove tools/skills/agents badge lists). `SkillBadge.astro` is no longer used here but remains available for other components (e.g., skills page).

---

## Part 5: Redesigned Home Page Cards

### Changes to `PostCard.astro`

Replace the truncated `blog_summary` with the auto-generated one-liner from `narrative.ts`. If no structured data exists, fall back to `blog_summary` truncated.

The card shows:
- Date · project · category badge
- One-liner auto-summary
- Satisfaction dots
- Tool/skill/agent counts as small text (e.g., "8 tools · 3 skills · 2 agents") instead of full badge lists

---

## Part 6: Redesigned Skills Page

### Layout

```
┌─────────────────────────────────────────────┐
│  Skill Directory              12 skills     │
├─────────────────────────────────────────────┤
│                                             │
│  ◆ systematic-debugging              ↑ HOT │
│  Used 8× across 3 projects                 │
│  Avg satisfaction: 4.2 · Last: Mar 21      │
│  Projects: ai-journey-logger, pocket-pal   │
│  Sessions: sess-001, sess-005, sess-012    │
│                                             │
│  ◆ subagent-driven-development             │
│  Used 5× across 2 projects                 │
│  Avg satisfaction: 3.8 · Last: Mar 20      │
│  ...                                        │
└─────────────────────────────────────────────┘
```

### Data model changes

Enhance `getAllSkills()` in `blog/src/lib/notion.ts` to return additional fields:

```typescript
interface SkillStats {
  name: string;
  count: number;
  lastUsed: string;
  projects: string[];
  avgSatisfaction: number;    // NEW: mean of post.satisfaction across sessions using this skill (unweighted — one value per session, not per invocation)
  sessions: string[];         // NEW: session_ids that used this skill (capped at latest 10; display shows latest 5 with "+N more" indicator)
  label: 'hot' | 'cold' | null; // NEW: hot = 3+ uses in last 7 days, cold = no use in 14+ days (computed at build time — reflects deploy-time state, may go stale between builds; acceptable for a static site with daily rebuilds)
}
```

### Components

- Modify: `blog/src/pages/skills.astro` — new layout with skill profiles
- Create: `blog/src/components/SkillProfile.astro` — renders one skill card with all fields

---

## Part 7: Notion Client Updates

### Changes to `blog/src/lib/notion.ts`

- Add `session_timeline` to `JourneyPost` interface (string, raw JSON)
- Add `parseTimeline()` helper to decode compact JSON into `TimelineEvent[]` (returns empty array on parse failure — no throw)
- Update `pageToPost()` to extract `session_timeline` from Notion
- Enhance `getAllSkills()` to compute `avgSatisfaction`, `sessions`, and `label`
- Existing fields (`notes`, all current `JourneyPost` properties) are preserved — the update only adds `session_timeline`

---

## Test Plan

### Python (transcript parser)

- **Timeline extraction:** Unit test with a sample JSONL transcript. Assert correct event types, deduplication (consecutive Read calls → `Read ×5`), timestamp calculation, and 40-event cap with first-15/last-25 split.
- **Budget enforcement:** Unit test with a large event list that exceeds 1900 chars. Assert progressive truncation produces a string under 1900 chars.
- **Error resilience:** Unit test with malformed JSONL lines interspersed with valid ones. Assert malformed lines are skipped, valid events are extracted, and no exception is raised.
- **Empty transcript:** Assert empty input returns empty timeline string.

### TypeScript (narrative generator)

- **`generateOneLiner`:** Unit test with a mock `JourneyPost`. Assert output matches template pattern (duration, model, project, category, commit count, top skill).
- **`generateNarrative`:** Unit test with mock post + timeline events. Assert 2-3 sentence output following construction rules (opening/middle/closing).
- **`generateNarrative` fallback:** Unit test with no timeline data. Assert fallback summary uses aggregate counts.
- **`parseTimeline`:** Unit test with valid compact JSON string. Assert correct `TimelineEvent[]` output. Test with empty string → empty array. Test with malformed JSON → empty array (no throw).

### Astro components (visual)

- **Build validation:** `npm run build` succeeds with real Notion data. Spot-check generated HTML for timeline markup, narrative text, and skills page profiles.
- **Older sessions:** Verify posts without `session_timeline` render the fallback narrative and skip the timeline visual gracefully.

---

## What's Included

- Enhanced transcript parser with ordered event log
- `session_timeline` Notion property + migration
- Build-time narrative generator (one-liner + full paragraph)
- Redesigned post page with visual timeline
- Redesigned home page cards with auto-summaries
- Redesigned skills page with profiles, satisfaction, hot/cold labels
- Timeline and SkillProfile components
- Fallback for older sessions without timeline data

## What's NOT Included

- Charts/trend lines (Phase 3)
- AI-generated summaries via Claude API (future enhancement)
- Changes to Stop hook or manual field collection
- Visual timeline for the skills page (Phase 3 with charts)
