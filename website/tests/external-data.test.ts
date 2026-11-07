import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { filterActivity, loadExternal, validateExternal } from '../src/lib/external-data';

const source = JSON.parse(readFileSync('public/external-data/research.json', 'utf8'));
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('independent empirical release', () => {
  it('validates the actual source-status export without inventing observations', () => {
    const result = validateExternal(source);
    expect(result.counts.catalog_resources).toBe(source.catalog_resources.length);
    expect(
      result.variables.every((v) => !v.used_in_synthetic_model && v.external_analysis_only),
    ).toBe(true);
  });
  it('rejects mismatched builds, fake availability, and wrong counts', () => {
    expect(() => validateExternal({ ...source, release_id: 'different' })).toThrow(/differs/);
    expect(() =>
      validateExternal({ ...source, counts: { ...source.counts, activity: 100 } }),
    ).toThrow(/counts/);
    expect(() =>
      validateExternal({
        ...source,
        activity: [],
        counts: { ...source.counts, activity: 0 },
        status: 'available',
        empirical_analysis_available: true,
      }),
    ).toThrow(/availability/);
  });
  it('rejects synthetic fault labels even if hidden in an otherwise unused field', () => {
    expect(() => validateExternal({ ...source, fault_next_year: 1 })).toThrow(/prohibited/);
  });
  it('loads the separate bundled snapshot with no GFW token or model request', async () => {
    vi.stubEnv('VITE_EXTERNAL_DATA_MODE', 'bundled');
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(source)));
    vi.stubGlobal('fetch', fetcher);
    const result = await loadExternal(new AbortController().signal);
    expect(result.release_id).toBe(source.release_id);
    expect(fetcher.mock.calls[0][0]).toBe('/external-data/research.json');
    expect(fetcher.mock.calls[0][1].headers).toBeUndefined();
  });
  it('does not silently substitute bundled data when an external Supabase release is missing', async () => {
    vi.stubEnv('VITE_EXTERNAL_DATA_MODE', 'supabase');
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_testfixture');
    const fetcher = vi.fn().mockResolvedValue(new Response('[]'));
    vi.stubGlobal('fetch', fetcher);
    await expect(loadExternal(new AbortController().signal)).rejects.toThrow(/not published/);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('rejects browser secret keys before any request', async () => {
    vi.stubEnv('VITE_EXTERNAL_DATA_MODE', 'supabase');
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'sb_secret_testfixture');
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    await expect(loadExternal(new AbortController().signal)).rejects.toThrow(/publishable/);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('filters the actual observation grain without changing measurement units or treating missing as zero', () => {
    // In-memory UI fixture only, not a production external observation.
    const row = {
      area_id: 'fixture-area',
      country: 'Fixture',
      year: 2024,
      metric: 'apparent_fishing_hours' as const,
      value: 0,
      period_start: '2024-01-01',
      period_end: '2024-02-01',
      unit: 'vessel-hours' as const,
      source_id: 'global_fishing_watch' as const,
      dataset: 'public-global-fishing-effort:v5.0' as const,
      coverage_status: 'reported_AIS_estimate' as const,
      raw_sha256: '0'.repeat(64),
    };
    expect(filterActivity([row], 'Fixture', '2024', 'apparent_fishing_hours')).toEqual([row]);
    expect(filterActivity([row], 'Other', '2024', 'apparent_fishing_hours')).toEqual([]);
    expect(filterActivity([], 'all', 'all', 'apparent_fishing_hours')).toEqual([]);
  });
});
