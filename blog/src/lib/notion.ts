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
