import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  annualSummary,
  csvText,
  emptyFilters,
  filterRows,
  observationSchema,
  researchSchema,
  verifyBundle,
} from '../src/lib/data';
const research = researchSchema.parse(
  JSON.parse(readFileSync(new URL('../public/data/research.json', import.meta.url), 'utf8')),
);
const observations = observationSchema
  .array()
  .parse(
    JSON.parse(readFileSync(new URL('../public/data/observations.json', import.meta.url), 'utf8')),
  );

describe('published research snapshot', () => {
  it('reconciles all exported rows and partitions', () => {
    expect(() => verifyBundle(research, observations)).not.toThrow();
    expect(observations).toHaveLength(4315);
    expect(annualSummary(observations).reduce((s, r) => s + r.rows, 0)).toBe(4315);
  });
  it('keeps source categories and final scores truthful', () => {
    expect(observations.some((r) => r.chokepoint === 'None')).toBe(true);
    expect(research.models.filter((m) => m.final_test !== null)).toHaveLength(1);
    expect(research.models.find((m) => m.id === 'random_forest')?.final_test?.TP).toBe(29);
  });
  it('never confuses unavailable final evaluations with zero', () => {
    expect(research.models.find((m) => m.id === 'dummy_baseline')?.final_test).toBeNull();
  });
  it('filters year, route, partition and ID together', () => {
    const example = observations[0];
    const result = filterRows(observations, {
      year: String(example.year),
      route: example.ocean_route,
      partition: example.partition,
      query: example.cable_id,
    });
    expect(result).toEqual([example]);
    expect(filterRows(observations, { ...emptyFilters, query: 'no-match' })).toEqual([]);
  });
  it('does not mutate records or fixed benchmark metrics', () => {
    const before = JSON.stringify(research.models);
    filterRows(observations, { ...emptyFilters, year: '2025' }).sort(
      (a, b) => a.age_years - b.age_years,
    );
    expect(JSON.stringify(research.models)).toBe(before);
  });
  it('detects incomplete or mixed-release imports', () => {
    expect(() => verifyBundle(research, observations.slice(1))).toThrow();
    expect(() => verifyBundle({ ...research, release_id: 'other' }, observations)).toThrow();
  });
  it('exports literal values and escapes formula injection and quotes', () => {
    const output = csvText(
      [{ category: 'None', text: 'a,"b"', formula: '=1+1' }],
      ['category', 'text', 'formula'],
    );
    expect(output).toContain('"None"');
    expect(output).toContain('"a,""b"""');
    expect(output).toContain('"\'=1+1"');
  });
  it('maps original importance back to 13 inputs', () => {
    expect(research.importance_grouped).toHaveLength(13);
    expect(research.importance_grouped.reduce((s, r) => s + r.importance, 0)).toBeCloseTo(1, 12);
  });
});
