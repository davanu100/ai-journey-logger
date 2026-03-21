# Phase 2: Astro Blog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static Astro blog that publishes curated AI Journey Log entries from Notion, deployed on Vercel with daily automated rebuilds.

**Architecture:** Static Astro site in `blog/` subdirectory. Queries Notion at build time for `publish=true` entries. Dark developer-minimal theme with Tailwind v4. GitHub Actions cron triggers Vercel deploy hook daily.

**Tech Stack:** Astro v5, Tailwind CSS v4 (via `@tailwindcss/vite`), `@notionhq/client`, TypeScript, Vercel

**Note:** The spec lists `tailwind.config.mjs` in the file structure, but Tailwind v4 uses CSS-based configuration via `@theme` directives in `global.css` instead of a JS config file. This is intentional — no `tailwind.config.mjs` is needed.

**Spec:** `docs/specs/2026-03-21-phase-2-astro-blog-design.md`

---

## File Structure

```
blog/
├── src/
│   ├── pages/
│   │   ├── index.astro              # Home: paginated post listing
│   │   ├── page/[page].astro        # Pagination pages (/page/2, /page/3)
│   │   ├── posts/[slug].astro       # Individual post page
│   │   ├── skills.astro             # Skills directory
│   │   └── stats.astro              # "Coming soon" stub
│   ├── layouts/
│   │   └── Base.astro               # Shell: html, head, nav, footer, dark theme
│   ├── components/
│   │   ├── Nav.astro                # Top navigation
│   │   ├── PostCard.astro           # Card for home page listing
│   │   ├── MetadataSidebar.astro    # Model, duration, tools badges on post page
│   │   └── SkillBadge.astro         # Styled skill/tool tag
│   ├── lib/
│   │   └── notion.ts                # Notion client: fetch, transform, paginate
│   └── styles/
│       └── global.css               # Tailwind import + dark theme tokens
├── astro.config.mjs
├── package.json
├── tsconfig.json
├── .env.example
└── .env                             # (gitignored)
.github/
└── workflows/
    └── daily-rebuild.yml            # GitHub Actions cron → Vercel deploy hook
setup_notion_db.py                   # Updated: add `notes` property
```

---

## Task 1: Scaffold Astro Project + Tailwind

**Files:**
- Create: `blog/package.json`
- Create: `blog/astro.config.mjs`
- Create: `blog/tsconfig.json`
- Create: `blog/src/styles/global.css`
- Create: `blog/src/layouts/Base.astro`
- Create: `blog/src/pages/index.astro` (placeholder)
- Create: `blog/.env.example`

- [ ] **Step 1: Create the Astro project**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
mkdir -p blog
cd blog
npm create astro@latest . -- --template minimal --typescript strict --no-git --no-install
```

Accept defaults. The `--no-git` flag prevents a nested `.git`.

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm install
npm install @notionhq/client
npm install tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Astro with Tailwind**

Replace `blog/astro.config.mjs`:

```js
// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  vite: {
    plugins: [tailwindcss()],
  },
});
```

- [ ] **Step 4: Create dark theme CSS**

Create `blog/src/styles/global.css`:

```css
@import "tailwindcss";

@theme {
  --color-bg: #0a0a0a;
  --color-surface: #141414;
  --color-border: #262626;
  --color-text: #e5e5e5;
  --color-muted: #a3a3a3;
  --color-accent: #3b82f6;
  --color-accent-hover: #60a5fa;

  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}
```

- [ ] **Step 5: Create Base layout**

Create `blog/src/layouts/Base.astro`:

```astro
---
import '../styles/global.css';

interface Props {
  title: string;
  description?: string;
}

const { title, description = 'AI Journey Log — a developer blog about working with Claude Code' } = Astro.props;
---

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content={description} />
    <title>{title} | AI Journey Log</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-bg text-text min-h-screen font-sans">
    <nav class="border-b border-border px-6 py-4 flex items-center gap-6">
      <a href="/" class="text-accent font-semibold hover:text-accent-hover">Home</a>
      <a href="/skills" class="text-muted hover:text-text">Skills</a>
      <a href="/stats" class="text-muted hover:text-text">Stats</a>
    </nav>
    <main class="max-w-3xl mx-auto px-6 py-10">
      <slot />
    </main>
    <footer class="border-t border-border px-6 py-6 text-center text-muted text-sm">
      AI Journey Log — built with Astro & Claude Code
    </footer>
  </body>
</html>
```

- [ ] **Step 6: Create placeholder index page**

Replace `blog/src/pages/index.astro`:

```astro
---
import Base from '../layouts/Base.astro';
---

<Base title="Home">
  <h1 class="text-2xl font-semibold mb-4">AI Journey Log</h1>
  <p class="text-muted">Posts will appear here once connected to Notion.</p>
</Base>
```

- [ ] **Step 7: Create .env.example**

Create `blog/.env.example`:

```
NOTION_TOKEN=ntn_your_token_here
NOTION_DATABASE_ID=your_database_id_here
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run dev
```

Expected: Astro dev server starts, navigating to `http://localhost:4321` shows the dark-themed placeholder page with nav.

Kill the server after verifying (Ctrl+C).

- [ ] **Step 9: Verify build works**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run build
```

Expected: Build succeeds, outputs static files to `blog/dist/`.

- [ ] **Step 10: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
echo "node_modules/" > blog/.gitignore
echo "dist/" >> blog/.gitignore
echo ".env" >> blog/.gitignore
git add blog/
git commit -m "feat: scaffold Astro project with Tailwind dark theme"
```

---

## Task 2: Notion Client Library

**Files:**
- Create: `blog/src/lib/notion.ts`

This is the core data layer. It fetches published entries from Notion, transforms them into typed `JourneyPost` objects, handles pagination, and sanitizes data for public display.

- [ ] **Step 1: Create the Notion client module**

Create `blog/src/lib/notion.ts`:

```ts
import { Client } from '@notionhq/client';
import type {
  PageObjectResponse,
  RichTextItemResponse,
} from '@notionhq/client/build/src/api-endpoints';

const notion = new Client({ auth: import.meta.env.NOTION_TOKEN });
const databaseId = import.meta.env.NOTION_DATABASE_ID;

// --- Types ---

export interface JourneyPost {
  session_id: string;
  date: string;
  project: string;
  model: string;
  duration_minutes: number;
  blog_summary: string;
  notes: string;
  category: string;
  tools_used: string[];
  skills_invoked: string[];
  agents_dispatched: string[];
  commits: string;
  satisfaction: number;
  message_count: number;
}

export interface SkillStats {
  name: string;
  count: number;
  lastUsed: string;
  projects: string[];
}

// --- Helpers ---

function richText(prop: { rich_text?: RichTextItemResponse[] } | undefined): string {
  if (!prop || !('rich_text' in prop)) return '';
  return prop.rich_text?.map((rt) => rt.plain_text).join('') ?? '';
}

function titleText(prop: { title?: RichTextItemResponse[] } | undefined): string {
  if (!prop || !('title' in prop)) return '';
  return prop.title?.map((t) => t.plain_text).join('') ?? '';
}

function selectName(prop: { select?: { name: string } | null } | undefined): string {
  if (!prop || !('select' in prop)) return '';
  return prop.select?.name ?? '';
}

function multiSelectNames(prop: { multi_select?: { name: string }[] } | undefined): string[] {
  if (!prop || !('multi_select' in prop)) return [];
  return prop.multi_select?.map((o) => o.name) ?? [];
}

function numberVal(prop: { number?: number | null } | undefined): number {
  if (!prop || !('number' in prop)) return 0;
  return prop.number ?? 0;
}

function dateVal(prop: { date?: { start: string } | null } | undefined): string {
  if (!prop || !('date' in prop)) return '';
  return prop.date?.start ?? '';
}

/** Strip git SHAs (7-40 hex chars) and URLs from commit text */
function sanitizeCommits(raw: string): string {
  return raw
    .replace(/\b[0-9a-f]{7,40}\b/g, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

// --- API ---

/** Fetch all pages from the database, handling pagination */
async function queryAll(filter: object, sorts: object[]): Promise<PageObjectResponse[]> {
  const pages: PageObjectResponse[] = [];
  let cursor: string | undefined = undefined;

  do {
    const response = await notion.databases.query({
      database_id: databaseId,
      filter: filter as any,
      sorts: sorts as any,
      start_cursor: cursor,
      page_size: 100,
    });

    pages.push(...(response.results as PageObjectResponse[]));
    cursor = response.has_more ? (response.next_cursor ?? undefined) : undefined;
  } while (cursor);

  return pages;
}

function pageToPost(page: PageObjectResponse): JourneyPost {
  const p = page.properties as any;
  return {
    session_id: titleText(p.session_id),
    date: dateVal(p.date),
    project: richText(p.project),
    model: selectName(p.model),
    duration_minutes: numberVal(p.duration_minutes),
    blog_summary: richText(p.blog_summary),
    notes: richText(p.notes),
    category: selectName(p.category),
    tools_used: multiSelectNames(p.tools_used),
    skills_invoked: multiSelectNames(p.skills_invoked),
    agents_dispatched: multiSelectNames(p.agents_dispatched),
    commits: sanitizeCommits(richText(p.commits)),
    satisfaction: numberVal(p.satisfaction),
    message_count: numberVal(p.message_count),
  };
}

export async function getPublishedPosts(): Promise<JourneyPost[]> {
  const pages = await queryAll(
    { property: 'publish', checkbox: { equals: true } },
    [{ property: 'date', direction: 'descending' }],
  );
  return pages.map(pageToPost);
}

export async function getAllSkills(): Promise<SkillStats[]> {
  const posts = await getPublishedPosts();
  const map = new Map<string, { count: number; lastUsed: string; projects: Set<string> }>();

  for (const post of posts) {
    for (const skill of post.skills_invoked) {
      const existing = map.get(skill);
      if (existing) {
        existing.count++;
        if (post.date > existing.lastUsed) existing.lastUsed = post.date;
        existing.projects.add(post.project);
      } else {
        map.set(skill, { count: 1, lastUsed: post.date, projects: new Set([post.project]) });
      }
    }
  }

  return Array.from(map.entries())
    .map(([name, data]) => ({
      name,
      count: data.count,
      lastUsed: data.lastUsed,
      projects: Array.from(data.projects).sort(),
    }))
    .sort((a, b) => b.count - a.count);
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npx astro check
```

Expected: No type errors in `notion.ts`. (Warnings about unused exports are fine.)

- [ ] **Step 3: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add blog/src/lib/notion.ts
git commit -m "feat: add Notion client library with typed post fetching"
```

---

## Task 3: Reusable Components

**Files:**
- Create: `blog/src/components/Nav.astro`
- Create: `blog/src/components/PostCard.astro`
- Create: `blog/src/components/MetadataSidebar.astro`
- Create: `blog/src/components/SkillBadge.astro`
- Modify: `blog/src/layouts/Base.astro` (extract nav to component)

- [ ] **Step 1: Create Nav component**

Create `blog/src/components/Nav.astro`:

```astro
---
const currentPath = Astro.url.pathname;

function isActive(path: string): boolean {
  if (path === '/') return currentPath === '/';
  return currentPath.startsWith(path);
}
---

<nav class="border-b border-border px-6 py-4 flex items-center gap-6">
  <a href="/" class:list={['font-semibold', isActive('/') ? 'text-accent' : 'text-muted hover:text-text']}>
    Home
  </a>
  <a href="/skills" class:list={[isActive('/skills') ? 'text-accent' : 'text-muted hover:text-text']}>
    Skills
  </a>
  <a href="/stats" class:list={[isActive('/stats') ? 'text-accent' : 'text-muted hover:text-text']}>
    Stats
  </a>
</nav>
```

- [ ] **Step 2: Create SkillBadge component**

Create `blog/src/components/SkillBadge.astro`:

```astro
---
interface Props {
  name: string;
  variant?: 'tool' | 'skill' | 'agent';
}

const { name, variant = 'skill' } = Astro.props;

const colors = {
  tool: 'bg-blue-900/40 text-blue-300 border-blue-800',
  skill: 'bg-purple-900/40 text-purple-300 border-purple-800',
  agent: 'bg-green-900/40 text-green-300 border-green-800',
};
---

<span class:list={['inline-block px-2 py-0.5 rounded text-xs font-mono border', colors[variant]]}>
  {name}
</span>
```

- [ ] **Step 3: Create PostCard component**

Create `blog/src/components/PostCard.astro`:

```astro
---
import type { JourneyPost } from '../lib/notion';

interface Props {
  post: JourneyPost;
}

const { post } = Astro.props;

const categoryColors: Record<string, string> = {
  debugging: 'text-red-400',
  feature: 'text-blue-400',
  refactor: 'text-yellow-400',
  brainstorming: 'text-purple-400',
  learning: 'text-green-400',
};

const dots = Array.from({ length: 5 }, (_, i) => i < post.satisfaction);
const summaryPreview = post.blog_summary.length > 120
  ? post.blog_summary.slice(0, 120) + '…'
  : post.blog_summary;
---

<a href={`/posts/${post.session_id}`} class="block p-4 rounded-lg bg-surface border border-border hover:border-accent/40 transition-colors">
  <div class="flex items-center gap-3 mb-2 text-sm">
    <time class="text-muted">{post.date}</time>
    <span class="font-mono text-muted">{post.project}</span>
    {post.category && (
      <span class:list={['text-xs uppercase tracking-wide', categoryColors[post.category] ?? 'text-muted']}>
        {post.category}
      </span>
    )}
  </div>
  <p class="text-text text-sm leading-relaxed mb-2">{summaryPreview}</p>
  <div class="flex items-center gap-1">
    {dots.map((filled) => (
      <span class:list={['w-1.5 h-1.5 rounded-full', filled ? 'bg-accent' : 'bg-border']} />
    ))}
  </div>
</a>
```

- [ ] **Step 4: Create MetadataSidebar component**

Create `blog/src/components/MetadataSidebar.astro`:

```astro
---
import SkillBadge from './SkillBadge.astro';
import type { JourneyPost } from '../lib/notion';

interface Props {
  post: JourneyPost;
}

const { post } = Astro.props;

const dots = Array.from({ length: 5 }, (_, i) => i < post.satisfaction);
---

<div class="bg-surface border border-border rounded-lg p-4 space-y-4">
  <div class="grid grid-cols-2 gap-3 text-sm">
    <div>
      <span class="text-muted">Model</span>
      <p class="font-mono">{post.model || '—'}</p>
    </div>
    <div>
      <span class="text-muted">Duration</span>
      <p>{post.duration_minutes} min</p>
    </div>
    <div>
      <span class="text-muted">Category</span>
      <p>{post.category || '—'}</p>
    </div>
    <div>
      <span class="text-muted">Messages</span>
      <p>{post.message_count}</p>
    </div>
  </div>

  <div>
    <span class="text-muted text-sm">Satisfaction</span>
    <div class="flex items-center gap-1 mt-1">
      {dots.map((filled) => (
        <span class:list={['w-2 h-2 rounded-full', filled ? 'bg-accent' : 'bg-border']} />
      ))}
    </div>
  </div>

  {post.tools_used.length > 0 && (
    <div>
      <span class="text-muted text-sm">Tools</span>
      <div class="flex flex-wrap gap-1 mt-1">
        {post.tools_used.map((t) => <SkillBadge name={t} variant="tool" />)}
      </div>
    </div>
  )}

  {post.skills_invoked.length > 0 && (
    <div>
      <span class="text-muted text-sm">Skills</span>
      <div class="flex flex-wrap gap-1 mt-1">
        {post.skills_invoked.map((s) => <SkillBadge name={s} variant="skill" />)}
      </div>
    </div>
  )}

  {post.agents_dispatched.length > 0 && (
    <div>
      <span class="text-muted text-sm">Agents</span>
      <div class="flex flex-wrap gap-1 mt-1">
        {post.agents_dispatched.map((a) => <SkillBadge name={a} variant="agent" />)}
      </div>
    </div>
  )}
</div>
```

- [ ] **Step 5: Update Base layout to use Nav component**

Replace the inline `<nav>` in `blog/src/layouts/Base.astro` with:

```astro
---
import '../styles/global.css';
import Nav from '../components/Nav.astro';

interface Props {
  title: string;
  description?: string;
}

const { title, description = 'AI Journey Log — a developer blog about working with Claude Code' } = Astro.props;
---

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content={description} />
    <title>{title} | AI Journey Log</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-bg text-text min-h-screen font-sans">
    <Nav />
    <main class="max-w-3xl mx-auto px-6 py-10">
      <slot />
    </main>
    <footer class="border-t border-border px-6 py-6 text-center text-muted text-sm">
      AI Journey Log — built with Astro & Claude Code
    </footer>
  </body>
</html>
```

- [ ] **Step 6: Verify build**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add blog/src/components/ blog/src/layouts/Base.astro
git commit -m "feat: add Nav, PostCard, MetadataSidebar, SkillBadge components"
```

---

## Task 4: Home Page with Pagination

**Files:**
- Modify: `blog/src/pages/index.astro`
- Create: `blog/src/pages/page/[page].astro`

- [ ] **Step 1: Create paginated home page**

Replace `blog/src/pages/index.astro`:

```astro
---
import Base from '../layouts/Base.astro';
import PostCard from '../components/PostCard.astro';
import { getPublishedPosts } from '../lib/notion';

const posts = await getPublishedPosts();
const firstPage = posts.slice(0, 10);
const hasMore = posts.length > 10;
---

<Base title="Home">
  <h1 class="text-2xl font-semibold mb-6">AI Journey Log</h1>

  {firstPage.length === 0 ? (
    <p class="text-muted">No published posts yet. Mark an entry as publish=true in Notion.</p>
  ) : (
    <div class="space-y-4">
      {firstPage.map((post) => <PostCard post={post} />)}
    </div>
  )}

  {hasMore && (
    <div class="mt-8 text-center">
      <a href="/page/2" class="text-accent hover:text-accent-hover">Older posts →</a>
    </div>
  )}
</Base>
```

- [ ] **Step 2: Create pagination page**

Create `blog/src/pages/page/[page].astro`:

```astro
---
import Base from '../../layouts/Base.astro';
import PostCard from '../../components/PostCard.astro';
import { getPublishedPosts } from '../../lib/notion';

export async function getStaticPaths() {
  const posts = await getPublishedPosts();
  const pageSize = 10;
  const totalPages = Math.ceil(posts.length / pageSize);

  // Page 1 is handled by index.astro, start from page 2
  return Array.from({ length: Math.max(0, totalPages - 1) }, (_, i) => {
    const pageNum = i + 2;
    const start = (pageNum - 1) * pageSize;
    return {
      params: { page: String(pageNum) },
      props: {
        posts: posts.slice(start, start + pageSize),
        currentPage: pageNum,
        totalPages,
      },
    };
  });
}

const { posts, currentPage, totalPages } = Astro.props;
const prevPage = currentPage === 2 ? '/' : `/page/${currentPage - 1}`;
const nextPage = currentPage < totalPages ? `/page/${currentPage + 1}` : null;
---

<Base title={`Page ${currentPage}`}>
  <h1 class="text-2xl font-semibold mb-6">AI Journey Log — Page {currentPage}</h1>

  <div class="space-y-4">
    {posts.map((post) => <PostCard post={post} />)}
  </div>

  <nav class="mt-8 flex justify-between">
    <a href={prevPage} class="text-accent hover:text-accent-hover">← Newer</a>
    {nextPage && <a href={nextPage} class="text-accent hover:text-accent-hover">Older →</a>}
  </nav>
</Base>
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run build
```

Expected: Build succeeds. If no `publish=true` entries exist in Notion, the home page shows the "No published posts" message and no pagination pages are generated.

- [ ] **Step 4: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add blog/src/pages/
git commit -m "feat: add home page with pagination"
```

---

## Task 5: Individual Post Page

**Files:**
- Create: `blog/src/pages/posts/[slug].astro`

- [ ] **Step 1: Create the post page**

Create `blog/src/pages/posts/[slug].astro`:

```astro
---
import Base from '../../layouts/Base.astro';
import MetadataSidebar from '../../components/MetadataSidebar.astro';
import { getPublishedPosts } from '../../lib/notion';
import type { JourneyPost } from '../../lib/notion';

export async function getStaticPaths() {
  const posts = await getPublishedPosts();
  return posts.map((post) => ({
    params: { slug: post.session_id },
    props: { post },
  }));
}

const { post } = Astro.props as { post: JourneyPost };

const commitLines = post.commits
  .split('\n')
  .map((line) => line.trim())
  .filter((line) => line.length > 0);
---

<Base title={`${post.project} — ${post.date}`}>
  <article>
    <header class="mb-8">
      <time class="text-muted text-sm">{post.date}</time>
      <span class="text-muted text-sm mx-2">·</span>
      <span class="font-mono text-sm text-muted">{post.project}</span>
      <hr class="border-border mt-4" />
    </header>

    <div class="mb-8">
      <p class="text-text leading-relaxed whitespace-pre-line">{post.blog_summary}</p>
    </div>

    {post.notes && (
      <div class="mb-8 pl-4 border-l-2 border-accent/40">
        <h2 class="text-sm font-semibold text-muted uppercase tracking-wide mb-2">Notes</h2>
        <p class="text-text leading-relaxed whitespace-pre-line">{post.notes}</p>
      </div>
    )}

    <MetadataSidebar post={post} />

    {commitLines.length > 0 && (
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

- [ ] **Step 2: Verify build**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run build
```

Expected: Build succeeds. If there are `publish=true` entries, individual post pages are generated in `dist/posts/`.

- [ ] **Step 3: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add blog/src/pages/posts/
git commit -m "feat: add individual post page with metadata sidebar"
```

---

## Task 6: Skills Directory Page

**Files:**
- Create: `blog/src/pages/skills.astro`

- [ ] **Step 1: Create the skills page**

Create `blog/src/pages/skills.astro`:

```astro
---
import Base from '../layouts/Base.astro';
import SkillBadge from '../components/SkillBadge.astro';
import { getAllSkills } from '../lib/notion';

const skills = await getAllSkills();
---

<Base title="Skills">
  <h1 class="text-2xl font-semibold mb-6">Skill Directory</h1>

  {skills.length === 0 ? (
    <p class="text-muted">No skills tracked yet.</p>
  ) : (
    <div class="space-y-3">
      {skills.map((skill) => (
        <div class="p-4 bg-surface border border-border rounded-lg flex items-center justify-between">
          <div>
            <SkillBadge name={skill.name} variant="skill" />
            <span class="text-muted text-xs ml-3">
              Last used: {skill.lastUsed}
            </span>
          </div>
          <div class="text-right">
            <span class="text-text font-mono">{skill.count}×</span>
            <span class="text-muted text-xs block">
              {skill.projects.join(', ')}
            </span>
          </div>
        </div>
      ))}
    </div>
  )}
</Base>
```

- [ ] **Step 2: Create stats stub page**

Create `blog/src/pages/stats.astro`:

```astro
---
import Base from '../layouts/Base.astro';
---

<Base title="Stats">
  <h1 class="text-2xl font-semibold mb-6">Stats</h1>
  <p class="text-muted">Coming soon — aggregated insights, charts, and trends.</p>
</Base>
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
npm run build
```

Expected: Build succeeds. `dist/skills/index.html` and `dist/stats/index.html` exist.

- [ ] **Step 4: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add blog/src/pages/skills.astro blog/src/pages/stats.astro
git commit -m "feat: add skills directory and stats stub pages"
```

---

## Task 7: Add `notes` Property to Notion Database

**Files:**
- Modify: `setup_notion_db.py`

- [ ] **Step 1: Add `notes` to the database schema in `setup_notion_db.py`**

Add `"notes": {"rich_text": {}}` to the `properties` dict in `setup_notion_db.py`, right after `"blog_summary"`.

- [ ] **Step 2: Run one-time migration to add `notes` to the live database**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
.venv/bin/python3 -c "
import os
from notion_client import Client
client = Client(auth=os.environ['NOTION_TOKEN'])
client.databases.update(
    database_id=os.environ['NOTION_DATABASE_ID'],
    properties={'notes': {'rich_text': {}}}
)
print('notes property added successfully')
"
```

Note: Ensure `NOTION_TOKEN` and `NOTION_DATABASE_ID` are set in your environment (they're already configured in your shell via the hooks setup).

Expected: "notes property added successfully"

- [ ] **Step 3: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add setup_notion_db.py
git commit -m "feat: add notes property to Notion database schema"
```

---

## Task 8: GitHub Actions Daily Rebuild

**Files:**
- Create: `.github/workflows/daily-rebuild.yml`

- [ ] **Step 1: Create the workflow file**

```bash
mkdir -p /Users/anuragthakur/ai-projects/ai-journey-logger/.github/workflows
```

Create `.github/workflows/daily-rebuild.yml`:

```yaml
name: Daily Blog Rebuild

on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  workflow_dispatch: {}   # manual trigger from GitHub UI

jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Vercel deploy
        run: curl -X POST "${{ secrets.VERCEL_DEPLOY_HOOK }}"
```

- [ ] **Step 2: Commit**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger
git add .github/workflows/daily-rebuild.yml
git commit -m "ci: add GitHub Actions daily rebuild workflow"
```

- [ ] **Step 3: Note for user**

After deploying to Vercel:
1. Go to Vercel → Project Settings → Git → Deploy Hooks
2. Create a hook named "daily-rebuild"
3. Copy the URL
4. Go to GitHub → repo Settings → Secrets → Actions
5. Add secret `VERCEL_DEPLOY_HOOK` with the URL value

---

## Task 9: End-to-End Validation

- [ ] **Step 1: Mark a Notion entry as publish=true**

In the AI Journey Log database in Notion, find an existing entry and check the `publish` checkbox. Add a `blog_summary` value like "Testing the blog pipeline." Optionally add `notes`.

- [ ] **Step 2: Build and preview locally**

```bash
cd /Users/anuragthakur/ai-projects/ai-journey-logger/blog
echo "NOTION_TOKEN=$NOTION_TOKEN" > .env
echo "NOTION_DATABASE_ID=$NOTION_DATABASE_ID" >> .env
npm run build && npx astro preview
```

Note: This writes your environment variables into `.env` (which is gitignored). Ensure `NOTION_TOKEN` and `NOTION_DATABASE_ID` are set in your shell.

Expected: Preview server starts. Navigate to `http://localhost:4321`:
- Home page shows the published post card
- Click through to the post page — blog_summary, metadata sidebar, commits rendered
- Skills page shows any skills from that session
- Stats page shows "Coming soon"

- [ ] **Step 3: Verify dark theme**

Check that:
- Background is near-black
- Text is soft white
- Nav links have accent colors
- Cards have surface background with border
- Badges are color-coded (blue for tools, purple for skills, green for agents)

- [ ] **Step 4: Deploy to Vercel**

Follow the Vercel Setup Checklist in the spec:
1. Sign in at vercel.com with GitHub
2. Import `ai-journey-logger` repo
3. Set root directory to `blog/`
4. Framework preset: Astro
5. Add `NOTION_TOKEN` and `NOTION_DATABASE_ID` env vars
6. Deploy

Verify the live site shows the published post.
