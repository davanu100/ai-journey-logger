import { describe, it, expect } from 'vitest';
import { generateOneLiner, generateNarrative } from './narrative';
import type { JourneyPost, TimelineEvent } from './notion';

const basePost: JourneyPost = {
  session_id: 'sess-001',
  date: '2026-03-20',
  project: 'ai-journey-logger',
  model: 'opus',
  duration_minutes: 45,
  blog_summary: 'Debugged auth flow.',
  notes: '',
  category: 'debugging',
  tools_used: ['Read', 'Edit', 'Bash'],
  skills_invoked: ['systematic-debugging', 'verification-before-completion'],
  agents_dispatched: ['Explore'],
  commits: 'fix: auth token validation\nfix: redis cache warmup\nfeat: add retry logic',
  satisfaction: 4,
  message_count: 12,
  session_timeline: '',
};

describe('generateOneLiner', () => {
  it('generates a one-liner with duration, model, project, category, commits, top skill', () => {
    const result = generateOneLiner(basePost);
    expect(result).toContain('45-min');
    expect(result).toContain('opus');
    expect(result).toContain('ai-journey-logger');
    expect(result).toContain('3 commits');
  });

  it('handles missing skills gracefully', () => {
    const post = { ...basePost, skills_invoked: [] };
    const result = generateOneLiner(post);
    expect(result).toContain('45-min');
    expect(result).not.toContain('using');
  });

  it('handles missing commits', () => {
    const post = { ...basePost, commits: '' };
    const result = generateOneLiner(post);
    expect(result).not.toContain('commit');
  });
});

describe('generateNarrative', () => {
  const timeline: TimelineEvent[] = [
    { ty: 'p', tx: 'Help me debug the auth flow', t: 0 },
    { ty: 't', n: 'Read ×5', t: 1 },
    { ty: 's', n: 'systematic-debugging', t: 3 },
    { ty: 'a', n: 'Explore', d: 'Search auth code', t: 5 },
    { ty: 't', n: 'Edit ×3', t: 12 },
  ];

  it('generates opening sentence with duration, category, model', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toMatch(/^A 45-minute debugging session using opus\./);
  });

  it('includes first prompt text in middle sentence', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('debug the auth flow');
  });

  it('includes skill invocation', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('systematic-debugging');
  });

  it('includes agent dispatch', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('Explore');
  });

  it('includes commit count in closing sentence', () => {
    const result = generateNarrative(basePost, timeline);
    expect(result).toContain('3 commit');
  });

  it('falls back to aggregate summary when no timeline', () => {
    const result = generateNarrative(basePost, []);
    expect(result).toContain('45-min');
    expect(result).toContain('opus');
    expect(result).toContain('3 tools');
    expect(result).toContain('2 skills');
    expect(result).toContain('1 agent');
  });

  it('handles zero duration gracefully', () => {
    const post = { ...basePost, duration_minutes: 0 };
    const result = generateNarrative(post, timeline);
    expect(result).not.toContain('0-minute');
  });
});
