import { Client } from '@notionhq/client';
import type {
  PageObjectResponse,
  RichTextItemResponse,
} from '@notionhq/client/build/src/api-endpoints';

const notion = new Client({ auth: import.meta.env.NOTION_TOKEN });
const databaseId = import.meta.env.NOTION_DATABASE_ID;

// --- Types ---

export interface TimelineEvent {
  ty: 'p' | 't' | 's' | 'a';
  t: number;
  n?: string;
  tx?: string;
  d?: string;
}

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
  session_timeline: string;
}

export interface SkillStats {
  name: string;
  count: number;
  lastUsed: string;
  projects: string[];
  avgSatisfaction: number;
  sessions: string[];
  label: 'hot' | 'cold' | null;
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
    session_timeline: richText(p.session_timeline),
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
        sessions: s.sessions.slice(-10),
        label,
      };
    })
    .sort((a, b) => b.count - a.count);
}
