import type { JourneyPost, TimelineEvent } from './notion';

function countCommits(post: JourneyPost): number {
  if (!post.commits) return 0;
  return post.commits.split('\n').filter(l => l.trim().length > 0).length;
}

function firstCommitMessage(post: JourneyPost): string {
  if (!post.commits) return '';
  const first = post.commits.split('\n').find(l => l.trim().length > 0);
  return first?.trim() || '';
}

export function generateOneLiner(post: JourneyPost): string {
  const parts: string[] = [];

  if (post.duration_minutes > 0) {
    parts.push(`${post.duration_minutes}-min`);
  }
  parts.push(post.model || 'unknown');
  parts.push('session on');
  parts.push(post.project);

  const commitCount = countCommits(post);
  const details: string[] = [];
  if (post.category) {
    details.push(post.category);
  }
  if (commitCount > 0) {
    details.push(`across ${commitCount} commit${commitCount === 1 ? '' : 's'}`);
  }
  if (post.skills_invoked.length > 0) {
    details.push(`using ${post.skills_invoked[0]}`);
  }

  if (details.length > 0) {
    parts.push('—');
    parts.push(details.join(' '));
  }

  return parts.join(' ');
}

export function generateNarrative(post: JourneyPost, timeline: TimelineEvent[]): string {
  if (timeline.length === 0) {
    return generateFallback(post);
  }

  const sentences: string[] = [];

  const durationPart = post.duration_minutes > 0 ? `${post.duration_minutes}-minute ` : '';
  const category = post.category || 'coding';
  sentences.push(`A ${durationPart}${category} session using ${post.model || 'unknown'}.`);

  const middleParts: string[] = [];
  let promptUsed = false;

  for (const evt of timeline) {
    if (middleParts.length >= 4) break;

    switch (evt.ty) {
      case 'p':
        if (!promptUsed && evt.tx) {
          middleParts.push(`Started by ${evt.tx.toLowerCase()}`);
          promptUsed = true;
        }
        break;
      case 's':
        if (evt.n) middleParts.push(`invoked ${evt.n}`);
        break;
      case 'a':
        if (evt.n) {
          const desc = evt.d ? ` to ${evt.d.toLowerCase()}` : '';
          middleParts.push(`dispatched a ${evt.n} agent${desc}`);
        }
        break;
      case 't': {
        const match = evt.n?.match(/×(\d+)/);
        if (match && parseInt(match[1]) >= 3) {
          middleParts.push(`used ${evt.n}`);
        }
        break;
      }
    }
  }

  if (middleParts.length > 0) {
    if (middleParts.length <= 2) {
      sentences.push(middleParts.join(', then ') + '.');
    } else {
      const first = middleParts.slice(0, 2).join(', then ');
      const second = middleParts.slice(2).join(' and ');
      sentences.push(`${first}.`);
      sentences.push(`Then ${second}.`);
    }
  }

  const commitCount = countCommits(post);
  if (commitCount > 0) {
    const msg = firstCommitMessage(post);
    const msgPart = msg ? ` ${msg}` : '';
    sentences.push(`Produced ${commitCount} commit${commitCount === 1 ? '' : 's'}${msgPart}.`);
  }

  return sentences.join(' ');
}

function generateFallback(post: JourneyPost): string {
  const parts: string[] = [];
  if (post.duration_minutes > 0) {
    parts.push(`${post.duration_minutes}-min`);
  }
  parts.push(`${post.model || 'unknown'} session`);

  const counts: string[] = [];
  if (post.tools_used.length > 0) counts.push(`${post.tools_used.length} tools`);
  if (post.skills_invoked.length > 0) counts.push(`${post.skills_invoked.length} skills`);
  if (post.agents_dispatched.length > 0) counts.push(`${post.agents_dispatched.length} agent${post.agents_dispatched.length === 1 ? '' : 's'}`);

  if (counts.length > 0) {
    parts.push('— used');
    parts.push(counts.join(', '));
  }

  return parts.join(' ') + '.';
}
