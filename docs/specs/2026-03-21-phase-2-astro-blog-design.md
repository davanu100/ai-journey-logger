# Phase 2: Astro Blog — Design Spec

## Goal

Build a static blog that publishes curated AI Journey Log entries from Notion, deployed on Vercel with daily automated rebuilds.

## Architecture

Static-first Astro site that queries Notion at build time. Only entries with `publish=true` are fetched. The blog lives in a `blog/` subdirectory of the existing `ai-journey-logger` repo.

**Content pipeline:** GitHub Actions cron → Vercel deploy hook → Astro build fetches Notion → static HTML on Vercel CDN.

---

## Site Structure

```
blog/
├── src/
│   ├── pages/
│   │   ├── index.astro            # Home: latest posts, reverse chronological
│   │   ├── posts/[slug].astro     # Individual post (slug = session_id)
│   │   ├── skills.astro           # Skill directory with usage counts
│   │   └── stats.astro            # "Coming soon" placeholder
│   ├── layouts/
│   │   └── Base.astro             # Shell: nav, footer, dark theme
│   ├── components/
│   │   ├── PostCard.astro         # Card for home page listing
│   │   ├── MetadataSidebar.astro  # Model, duration, tools badges
│   │   ├── SkillBadge.astro       # Styled skill tag
│   │   └── Nav.astro              # Top navigation
│   ├── lib/
│   │   └── notion.ts              # Notion client: fetch published entries
│   └── styles/
│       └── global.css             # Tailwind + dark theme tokens
├── astro.config.mjs
├── tailwind.config.mjs
├── package.json
├── .env.example                   # NOTION_TOKEN, NOTION_DATABASE_ID
└── .env                           # (gitignored)
```

### Routes

| Route | Description |
|---|---|
| `/` | Latest posts, 10 per page (static pagination: `/page/2`, `/page/3`), reverse chronological. Stats summary deferred to Phase 3. |
| `/posts/:session-id` | Single post with summary, notes, metadata, commits |
| `/skills` | All skills across published sessions with invocation counts |
| `/stats` | Stub — "Coming soon" placeholder |

---

## Data Model

### Notion → Blog Type

```typescript
interface JourneyPost {
  session_id: string       // used as slug
  date: string
  project: string
  model: string
  duration_minutes: number
  blog_summary: string     // main content
  notes?: string           // optional curated highlights (NEW property)
  category: string
  tools_used: string[]
  skills_invoked: string[]
  agents_dispatched: string[]
  commits: string          // commit messages only, no SHAs
  satisfaction: number
  message_count: number
}
```

### New Notion Property

Add `notes` (rich_text) to the AI Journey Log database — for optional per-post curated highlights written by the user in Notion.

### Privacy Enforcement (build time)

- Only `publish=true` entries are fetched from Notion
- `initial_prompt` is **never** included in the blog — `blog_summary` is the content
- Commits rendered as messages only — strip SHAs and repo URLs via regex
- Project names passed through as-is (user controls what they publish)
- Nothing is public by default

---

## Content Pipeline

1. `npm run build` triggers Astro static build
2. `src/lib/notion.ts` queries Notion API:
   - Filter: `publish` checkbox equals `true`
   - Sort: `date` descending
3. For each entry, extract properties into typed `JourneyPost` object
4. `[slug].astro` uses `getStaticPaths()` to generate one page per post
5. Output: static HTML in `dist/`, deployed to Vercel CDN

### Rich Text Handling

`blog_summary` and `notes` are Notion `rich_text` properties. They contain structured rich text objects (bold, italic, links, code). At build time, these are converted to plain text by concatenating `plain_text` fields from the rich text array. Rich formatting support (rendering bold, links, etc.) is deferred — Phase 2 treats these as plain text strings. This is acceptable because the user writes these summaries themselves and can keep them simple.

### Build-Time Error Handling

If the Notion API is unreachable during a Vercel build (triggered by cron or manual), the build fails and Vercel keeps the previous successful deployment live. This is the default Vercel behavior and is acceptable — the blog stays up with stale content until the next successful build. No custom error handling or caching needed.

### Notion Client (`src/lib/notion.ts`)

- Uses `@notionhq/client` (official JS SDK)
- `getPublishedPosts()` → `JourneyPost[]` — fetches all `publish=true` entries
- `getAllSkills()` → `{ name, count, lastUsed, projects }[]` — aggregates skills across published posts
- Handles Notion API pagination (100 results per page)
- Sanitizes commits: strips SHAs (regex: `/\b[0-9a-f]{7,40}\b/g`) and URLs
- Extracts `plain_text` from rich text arrays for `blog_summary` and `notes`

---

## Visual Design

### Theme: Developer-Minimal Dark

| Token | Value |
|---|---|
| Background | `#0a0a0a` (near-black) |
| Surface | `#141414` (cards, sidebar) |
| Border | `#262626` |
| Text primary | `#e5e5e5` (soft white) |
| Text secondary | `#a3a3a3` |
| Accent | `#3b82f6` (muted blue) |
| Monospace | `JetBrains Mono` or system monospace |
| Sans-serif | `Inter` or system sans |

### Post Page Layout

```
┌─────────────────────────────────────────────┐
│  Nav: Home | Skills | Stats                 │
├─────────────────────────────────────────────┤
│                                             │
│  March 20, 2026 · ai-journey-logger        │
│  ═══════════════════════════════════════    │
│                                             │
│  [blog_summary paragraph]                   │
│                                             │
│  [notes — if present, separate section      │
│   with subtle left border accent]           │
│                                             │
│  ┌─ Metadata ─────────────────────────┐     │
│  │ Model: opus    Duration: 45 min    │     │
│  │ Category: feature  Satisfaction: 4 │     │
│  │ Messages: 12                       │     │
│  └────────────────────────────────────┘     │
│                                             │
│  Tools: [Bash] [Edit] [Read] [Agent]        │
│  Skills: [systematic-debugging]             │
│  Agents: [Explore] [general-purpose]        │
│                                             │
│  Commits:                                   │
│  • feat: add transcript parser              │
│  • fix: handle empty sessions               │
│                                             │
├─────────────────────────────────────────────┤
│  Footer                                     │
└─────────────────────────────────────────────┘
```

### Home Page

Grid of `PostCard` components showing:
- Date
- Project name
- Category badge
- First line of blog_summary (truncated)
- Satisfaction (dot indicators: 1-5)

### Skills Page

Table/grid of all skills observed across published sessions:
- Skill name
- Times invoked (count)
- Last used date
- Projects used in

---

## Deployment

### Vercel Setup Checklist

> **Note for Anurag:** Follow these steps when setting up Vercel for the first time.

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "Add New Project" → import the `ai-journey-logger` repo
3. Set **Root Directory** to `blog/`
4. Framework Preset: **Astro**
5. Add environment variables:
   - `NOTION_TOKEN` = your Notion integration token
   - `NOTION_DATABASE_ID` = your database ID
6. Deploy — Vercel will build and publish
7. Copy the **Deploy Hook URL** from Project Settings → Git → Deploy Hooks
   - Create a hook named "daily-rebuild"
   - Save the URL — you'll need it for GitHub Actions

### GitHub Actions Daily Rebuild

```yaml
# .github/workflows/daily-rebuild.yml
name: Daily Blog Rebuild
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  workflow_dispatch: {}   # manual trigger

jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Vercel deploy
        run: curl -X POST "${{ secrets.VERCEL_DEPLOY_HOOK }}"
```

- `VERCEL_DEPLOY_HOOK` stored as a GitHub repository secret
- `workflow_dispatch` allows manual trigger from GitHub UI

### Manual Rebuild

```bash
curl -X POST "https://api.vercel.com/v1/integrations/deploy/your-hook-id"
```

---

## Schema Change

Add `notes` property to the existing Notion database. Update `setup_notion_db.py` to include it for documentation. One-time script to add it to the live database:

```python
notion.databases.update(
    database_id=DB_ID,
    properties={"notes": {"rich_text": {}}}
)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | Astro (static output) |
| Styling | Tailwind CSS |
| Fonts | Inter (sans), JetBrains Mono (mono) |
| Notion SDK | `@notionhq/client` (JS/TS) |
| Hosting | Vercel (free tier) |
| Rebuild trigger | GitHub Actions cron |
| Package manager | npm |

---

## What's Included (Phase 2)

- Astro project in `blog/` subdirectory
- Home page with paginated post listing
- Individual post pages (summary + notes + metadata + commits)
- Skills directory page with usage counts
- Stats stub page ("Coming soon")
- Dark developer-minimal theme with Tailwind
- `notion.ts` client fetching `publish=true` entries
- Commit message sanitization (strip SHAs/URLs)
- `notes` property added to Notion database
- GitHub Actions workflow for daily Vercel rebuild
- `.env.example` with required variables documented

## What's NOT Included

- Stats/charts (Phase 3)
- Notion webhooks for instant rebuild (Phase 4)
- RSS feed (Phase 4)
- Search or tag filtering (Phase 4)
- Custom domain setup (manual task, not automated)
- SSR / ISR
- Authentication
- Comments system
