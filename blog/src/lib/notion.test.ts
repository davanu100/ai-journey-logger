import { describe, it, expect } from 'vitest';
import { parseTimeline } from './notion';
import type { TimelineEvent } from './notion';

describe('parseTimeline', () => {
  it('parses valid compact JSON into TimelineEvent array', () => {
    const input = '[{"ty":"p","tx":"hello","t":0},{"ty":"t","n":"Read ×3","t":1}]';
    const result = parseTimeline(input);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ ty: 'p', tx: 'hello', t: 0 });
    expect(result[1]).toEqual({ ty: 't', n: 'Read ×3', t: 1 });
  });

  it('returns empty array for empty string', () => {
    expect(parseTimeline('')).toEqual([]);
  });

  it('returns empty array for malformed JSON', () => {
    expect(parseTimeline('not json')).toEqual([]);
    expect(parseTimeline('{}')).toEqual([]);
  });

  it('returns empty array for null/undefined', () => {
    expect(parseTimeline(null as any)).toEqual([]);
    expect(parseTimeline(undefined as any)).toEqual([]);
  });
});
