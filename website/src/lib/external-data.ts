import { z } from 'zod';
import expectedRelease from '../externalRelease.json';

const https = z.string().url().startsWith('https://');
const isoDate = z
  .string()
  .refine(
    (v) =>
      /^\d{4}-\d{2}-\d{2}$/.test(v) &&
      Number.isFinite(Date.parse(v)) &&
      new Date(v).toISOString().slice(0, 10) === v,
    'Invalid ISO date',
  );
const sourceSchema = z.object({
  source_id: z.enum(['world_bank', 'global_fishing_watch', 'open_undersea_cable_map', 'ofca']),
  source_name: z.string(),
  publisher: z.string(),
  source_url: https,
  license: z.string().min(1),
  license_url: https,
  file_or_endpoint: z.string(),
  version: z.string(),
  original_format: z.string(),
  access_date: z.string().nullable(),
  metadata_updated: z.string().nullable(),
  coverage: z.string(),
  period: z.string(),
  purpose: z.string(),
  status: z.string(),
  limitations: z.string(),
});
const id = z
  .string()
  .min(1)
  .refine((v) => !/\bCAB\d{4,}\b/i.test(v), 'Synthetic identifiers cannot be empirical keys');
const siteSchema = z
  .object({
    id,
    name: z.string().min(1),
    country: z.string().min(1),
    latitude: z.number().finite().min(-90).max(90).nullable(),
    longitude: z.number().finite().min(-180).max(180).nullable(),
    record_kind: z.enum(['landing_point', 'cable_system', 'country']),
    source_id: z.enum(['world_bank', 'open_undersea_cable_map']),
    snapshot_date: isoDate.nullable(),
    coordinate_precision: z.string(),
    location_to_be_determined: z.boolean().nullable().optional(),
    detail_record_available: z.boolean().optional(),
    country_assignment: z.string().optional(),
  })
  .refine(
    (r) => (r.latitude === null) === (r.longitude === null),
    'Coordinates must be a complete pair',
  );
const activitySchema = z
  .object({
    area_id: id,
    country: z.string(),
    period_start: isoDate,
    period_end: isoDate,
    year: z.number().int().min(2012),
    metric: z.enum(['apparent_fishing_hours', 'vessel_presence_hours']),
    value: z.number().finite().nonnegative(),
    unit: z.literal('vessel-hours'),
    source_id: z.literal('global_fishing_watch'),
    dataset: z.enum(['public-global-fishing-effort:v5.0', 'public-global-presence:v5.0']),
    coverage_status: z.literal('reported_AIS_estimate'),
    raw_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  })
  .refine(
    (r) =>
      (r.metric === 'apparent_fishing_hours') ===
      (r.dataset === 'public-global-fishing-effort:v5.0'),
    'Metric and dataset mismatch',
  );
export const externalSchema = z.object({
  schema_version: z.literal(1),
  release_id: z.string(),
  manifest_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  created_at: z.string(),
  status: z.enum(['available', 'partial', 'blocked']),
  empirical_analysis_available: z.boolean(),
  scope: z.string(),
  counts: z.object({
    catalog_resources: z.number().int().nonnegative(),
    infrastructure: z.number().int().nonnegative(),
    activity: z.number().int().nonnegative(),
    geographies: z.number().int().nonnegative(),
    cable_systems: z.number().int().nonnegative().default(0),
    cable_landings: z.number().int().nonnegative().default(0),
    html_observations: z.number().int().nonnegative().default(0),
  }),
  sources: z.array(sourceSchema),
  catalog_resources: z.array(
    z.object({
      resource_id: z.string(),
      source_id: z.literal('world_bank'),
      name: z.string(),
      description: z.string(),
      source_url: https,
      format: z.string(),
      download_available: z.boolean(),
      resource_license: z.string(),
      record_kind: z.literal('catalog_resource_metadata'),
    }),
  ),
  infrastructure: z.array(siteSchema),
  cable_systems: z
    .array(
      z.object({
        id,
        name: z.string().min(1),
        source_id: z.literal('open_undersea_cable_map'),
        length_reported: z.string().nullable(),
        rfs_reported: z.string().nullable(),
        owners_reported: z.string().nullable(),
        suppliers_reported: z.string().nullable(),
        landing_point_count: z.number().int().positive(),
        status_interpretation: z.string(),
      }),
    )
    .default([]),
  cable_landings: z
    .array(
      z.object({
        cable_id: id,
        landing_id: id,
        source_id: z.literal('open_undersea_cable_map'),
        relationship_evidence: z.enum([
          'both_directions',
          'cable_record_only',
          'landing_record_only',
        ]),
      }),
    )
    .default([]),
  html_observations: z
    .array(
      z.object({
        observation_id: id,
        system_name_reported: z.string().min(1),
        country: z.literal('Hong Kong'),
        reference_period: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/),
        source_id: z.literal('ofca'),
        record_kind: z.literal('regulator_named_system'),
        extraction_method: z.literal('HTML prose list extraction'),
        html_sha256: z.string().regex(/^[a-f0-9]{64}$/),
        source_url: https,
        source_text_quality: z.enum([
          'source_contains_replacement_character',
          'source_contains_nonprinting_control',
          'no_replacement_character',
        ]),
        interpretation: z.string(),
      }),
    )
    .default([]),
  activity: z.array(activitySchema),
  geographies: z.array(
    z.object({
      id,
      name: z.string(),
      country: z.string(),
      definition: z.string(),
      buffer_km: z.number().positive().optional(),
      region_category: z.enum(['source_eez_region', 'joint_or_overlapping']).optional(),
      iso3: z.string().nullable().optional(),
      territory_label: z.string().nullable().optional(),
      sovereignty_iso_codes: z.array(z.string()).optional(),
      region_metadata_sha256: z
        .string()
        .regex(/^[a-f0-9]{64}$/)
        .optional(),
      region_metadata_url: https.optional(),
    }),
  ),
  infrastructure_summary: z.array(
    z.object({
      country: z.string(),
      record_kind: z.string(),
      records: z.number().int().positive(),
    }),
  ),
  variables: z.array(
    z.object({
      variable: z.string(),
      dataset: z.string(),
      definition: z.string(),
      unit: z.string(),
      indicator_group: z.enum(['infrastructure', 'exposure', 'provenance']),
      measurement_kind: z.string(),
      used_in_synthetic_model: z.literal(false),
      external_analysis_only: z.literal(true),
    }),
  ),
  events: z.array(
    z.object({
      stage: z.string(),
      status: z.string(),
      rows: z.number().int().nonnegative(),
      message: z.string(),
      area_id: z.string().optional(),
      dataset: z.string().optional(),
    }),
  ),
  limitations: z.array(z.string()),
  configuration: z.object({
    gfw: z.object({
      start_date: isoDate,
      end_date: isoDate,
      datasets: z.array(z.string()),
      period_rationale: z.string(),
      region_selection: z.string().optional(),
    }),
  }),
});
export type ExternalResearch = z.infer<typeof externalSchema>;
export type Activity = ExternalResearch['activity'][number];
export const externalMetricLabels = {
  apparent_fishing_hours: 'Apparent fishing hours',
  vessel_presence_hours: 'Vessel presence hours',
};

export function validateExternal(raw: unknown, expected = expectedRelease): ExternalResearch {
  if (
    raw &&
    typeof raw === 'object' &&
    /"(?:fault_next_year|fault_this_year|predicted_risk|model_probability)"\s*:/.test(
      JSON.stringify(raw),
    )
  )
    throw new Error('Fault labels and model scores are prohibited in empirical evidence.');
  const result = externalSchema.parse(raw);
  if (
    result.release_id !== expected.release_id ||
    result.manifest_sha256 !== expected.manifest_sha256
  )
    throw new Error('External release differs from this build. Export and rebuild together.');
  const sourceIds = new Set(result.sources.map((s) => s.source_id));
  if (
    sourceIds.size !== result.sources.length ||
    !sourceIds.has('world_bank') ||
    !sourceIds.has('global_fishing_watch')
  )
    throw new Error('Reviewed sources need distinct status records, including World Bank and GFW.');
  for (const key of [
    'catalog_resources',
    'infrastructure',
    'activity',
    'geographies',
    'cable_systems',
    'cable_landings',
    'html_observations',
  ] as const)
    if (result.counts[key] !== result[key].length)
      throw new Error('External record counts do not reconcile.');
  const siteIds = new Set(result.infrastructure.map((r) => r.id));
  const cableIds = new Set(result.cable_systems.map((r) => r.id));
  const connectionIds = new Set(result.cable_landings.map((r) => `${r.cable_id}|${r.landing_id}`));
  if (
    cableIds.size !== result.cable_systems.length ||
    connectionIds.size !== result.cable_landings.length ||
    new Set(result.html_observations.map((r) => r.observation_id)).size !==
      result.html_observations.length ||
    result.cable_landings.some((r) => !siteIds.has(r.landing_id) || !cableIds.has(r.cable_id))
  )
    throw new Error('Historical cable/landing or HTML observation keys do not reconcile.');
  if (
    [
      ...result.infrastructure,
      ...result.cable_systems,
      ...result.html_observations,
      ...result.activity,
    ].some((r) => !sourceIds.has(r.source_id))
  )
    throw new Error('Empirical observation source missing from registry.');
  if (
    new Set(result.infrastructure.map((s) => s.id)).size !== result.infrastructure.length ||
    new Set(result.geographies.map((s) => s.id)).size !== result.geographies.length
  )
    throw new Error('Duplicate empirical geography/infrastructure keys.');
  const areas = new Set(result.geographies.map((s) => s.id));
  const keys = new Set<string>();
  for (const row of result.activity) {
    const key = [row.area_id, row.period_start, row.period_end, row.metric, row.dataset].join('|');
    if (
      !areas.has(row.area_id) ||
      keys.has(key) ||
      row.period_end <= row.period_start ||
      row.year !== Number(row.period_start.slice(0, 4))
    )
      throw new Error('Invalid or duplicate empirical activity key/period.');
    keys.add(key);
  }
  if (
    (result.status === 'available') !== result.empirical_analysis_available ||
    (result.empirical_analysis_available &&
      (!result.infrastructure.length || !result.activity.length))
  )
    throw new Error(
      'Empirical availability cannot be claimed without acquired infrastructure and activity.',
    );
  if(result.empirical_analysis_available){
    const expected=new Set(result.geographies.flatMap(g=>result.configuration.gfw.datasets.map(d=>`${g.id}|${d}`)));
    const reports=result.events.filter(e=>e.stage==='gfw_report');
    const completed=new Set(reports.filter(e=>e.status==='acquired' || e.status==='no_records_returned').map(e=>`${e.area_id}|${e.dataset}`));
    if(reports.length!==expected.size || completed.size!==expected.size || [...completed].some(key=>!expected.has(key)))
      throw new Error('Empirical availability requires every requested region/metric check to reconcile.');
  }
  return result;
}

export async function loadExternal(signal: AbortSignal): Promise<ExternalResearch> {
  const mode = import.meta.env.VITE_EXTERNAL_DATA_MODE || 'bundled';
  let url = '/external-data/research.json';
  let headers: HeadersInit | undefined;
  if (mode === 'supabase') {
    const origin = import.meta.env.VITE_SUPABASE_URL?.replace(/\/$/, '');
    const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
    if (
      !origin ||
      !key?.startsWith('sb_publishable_') ||
      new URL(origin).origin !== origin ||
      !origin.startsWith('https://')
    )
      throw new Error(
        'External Supabase reads need a plain HTTPS origin and publishable key. Never use a secret key.',
      );
    url = `${origin}/rest/v1/external_releases?id=eq.${encodeURIComponent(expectedRelease.release_id)}&published=eq.true&select=payload`;
    headers = { apikey: key };
  } else if (mode !== 'bundled')
    throw new Error('VITE_EXTERNAL_DATA_MODE must be bundled or supabase.');
  const response = await fetch(url, {
    headers,
    signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
  });
  if (!response.ok)
    throw new Error(
      `External evidence request failed (${response.status}). Original model pages remain available.`,
    );
  let raw: unknown = await response.json();
  if (mode === 'supabase') {
    const releases = z.array(z.object({ payload: z.unknown() })).parse(raw);
    if (releases.length !== 1)
      throw new Error(
        'Expected external release is not published. No bundled data were silently substituted.',
      );
    raw = releases[0].payload;
  }
  return validateExternal(raw);
}

export function filterActivity(
  rows: Activity[],
  country: string,
  year: string,
  metric: string,
  area = 'all',
) {
  return rows.filter(
    (r) =>
      (country === 'all' || r.country === country) &&
      (year === 'all' || String(r.year) === year) &&
      r.metric === metric &&
      (area === 'all' || r.area_id === area),
  );
}
