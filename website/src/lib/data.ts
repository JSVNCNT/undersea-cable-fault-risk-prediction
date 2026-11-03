import { z } from 'zod';
import release from '../release.json';

export const metricKeys = ['accuracy', 'precision', 'recall', 'f1', 'pr_auc', 'roc_auc'] as const;
export type MetricKey = (typeof metricKeys)[number];
export const metricLabels: Record<MetricKey, string> = {
  accuracy: 'Accuracy',
  precision: 'Precision',
  recall: 'Recall',
  f1: 'F1 score',
  pr_auc: 'Average precision',
  roc_auc: 'ROC-AUC',
};
export const modelNames: Record<string, string> = {
  dummy_baseline: 'Dummy baseline',
  logistic_regression: 'Logistic Regression',
  decision_tree: 'Decision Tree',
  random_forest: 'Random Forest',
};
export const splitNames: Record<string, string> = {
  train: 'Training',
  validation: 'Validation',
  final_test: 'Final test',
};
const metricsSchema = z.object({
  accuracy: z.number().min(0).max(1),
  precision: z.number().min(0).max(1),
  recall: z.number().min(0).max(1),
  f1: z.number().min(0).max(1),
  pr_auc: z.number().min(0).max(1),
  roc_auc: z.number().min(0).max(1),
  TN: z.number().int().nonnegative(),
  FP: z.number().int().nonnegative(),
  FN: z.number().int().nonnegative(),
  TP: z.number().int().nonnegative(),
});
export const featureSchema = z.object({
  name: z.string(),
  label: z.string(),
  group: z.enum(['infrastructure', 'operational']),
  unit: z.string(),
  description: z.string(),
  qualification: z.string(),
  kind: z.enum(['category', 'integer', 'number']),
  categories: z.array(z.string()),
  train_min: z.number().nullable(),
  train_max: z.number().nullable(),
  missing_train: z.number(),
});
export const observationSchema = z.object({
  cable_id: z.string(),
  year: z.number().int(),
  partition: z.enum(['train', 'validation', 'final_test']),
  ocean_route: z.string(),
  operator_type: z.string(),
  chokepoint: z.string(),
  age_years: z.number(),
  fiber_pairs: z.number(),
  length_km: z.number(),
  n_landing_countries: z.number(),
  design_capacity_tbps: z.number(),
  lit_capacity_tbps: z.number(),
  utilization_pct: z.number(),
  protected_burial: z.number().int().min(0).max(1),
  route_redundancy: z.number(),
  fault_this_year: z.number().int().min(0).max(1),
  fault_next_year: z.number().int().min(0).max(1),
});
const importanceSchema = z.array(z.object({ feature: z.string(), importance: z.number() }));
const contextSchema = z.object({
  metric_id: z.string(),
  metric: z.string(),
  value: z.number(),
  unit: z.string(),
  scope: z.string(),
  reference_period: z.string(),
  source_organization: z.string(),
  source_title: z.string(),
  source_url: z.string().url(),
  source_note: z.string(),
});
const incidentSchema = z.object({
  incident_id: z.string(),
  incident_date: z.string(),
  location: z.string(),
  vessel_or_description: z.string(),
  cause_summary: z.string(),
  telecom_cables_damaged: z.number().nullable(),
  other_assets_damaged: z.string(),
  source_organization: z.string(),
  source_title: z.string(),
  source_url: z.string().url(),
});
export const researchSchema = z.object({
  schema_version: z.literal(1),
  release_id: z.string(),
  title: z.string(),
  completed_at: z.string(),
  model_sha256: z.string(),
  source_url: z.string().url(),
  origin: z.string(),
  counts: z.object({
    raw: z.number(),
    eligible: z.number(),
    cables_raw: z.number(),
    unlabeled: z.number(),
    unresolved: z.number(),
    predictors: z.number(),
    encoded: z.number(),
  }),
  features: z.array(featureSchema),
  dictionary: z.array(z.record(z.string(), z.string())),
  splits: z.array(
    z.object({
      partition: z.string(),
      min_year: z.number(),
      max_year: z.number(),
      rows: z.number(),
      unique_cables: z.number(),
      positives: z.number(),
      negatives: z.number(),
      prevalence: z.number(),
    }),
  ),
  models: z.array(
    z.object({
      id: z.string(),
      selected: z.boolean(),
      validation: metricsSchema,
      parameters: z.record(z.string(), z.unknown()),
      final_test: metricsSchema.nullable(),
    }),
  ),
  partition_metrics: z.array(metricsSchema.extend({ partition: z.string(), rows: z.number() })),
  importance_encoded: importanceSchema,
  importance_grouped: importanceSchema,
  context: z.array(contextSchema),
  incidents: z.array(incidentSchema),
  source_sha256: z.record(z.string(), z.string()),
  example: z.record(z.string(), z.union([z.string(), z.number()])),
  example_source: z.object({
    cable_id: z.string(),
    year: z.number(),
    partition: z.literal('train'),
  }),
});
export type Research = z.infer<typeof researchSchema>;
export type Observation = z.infer<typeof observationSchema>;
export type Feature = z.infer<typeof featureSchema>;
export type Metrics = z.infer<typeof metricsSchema>;
export type DataBundle = {
  research: Research;
  observations: Observation[];
  mode: 'bundled' | 'supabase';
};

async function json(url: string, signal: AbortSignal, headers?: HeadersInit) {
  const response = await fetch(url, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
    headers,
  });
  if (!response.ok) throw new Error(`Research data request failed (${response.status}).`);
  return response.json() as Promise<unknown>;
}

export function verifyBundle(research: Research, observations: Observation[]) {
  if (research.release_id !== release.release_id || research.model_sha256 !== release.model_sha256)
    throw new Error(
      'Published release does not match this website build. Re-export and rebuild together.',
    );
  if (
    observations.length !== research.counts.eligible ||
    new Set(observations.map((r) => `${r.cable_id}:${r.year}`)).size !== observations.length
  )
    throw new Error('Dataset is incomplete or has duplicate cable-year keys.');
  for (const split of research.splits) {
    const rows = observations.filter((r) => r.partition === split.partition);
    if (
      rows.length !== split.rows ||
      rows.reduce((sum, r) => sum + r.fault_next_year, 0) !== split.positives
    )
      throw new Error('Published dataset does not match the saved partition counts.');
  }
}

export async function loadData(signal: AbortSignal): Promise<DataBundle> {
  const mode = import.meta.env.VITE_DATA_MODE || 'bundled';
  if (!['bundled', 'supabase'].includes(mode))
    throw new Error('VITE_DATA_MODE must be bundled or supabase.');
  let rawResearch: unknown;
  let rawObservations: unknown;
  if (mode === 'supabase') {
    const url = import.meta.env.VITE_SUPABASE_URL?.replace(/\/$/, '');
    const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
    if (!url?.startsWith('https://') || !key)
      throw new Error('Supabase mode needs an HTTPS project URL and a publishable key.');
    if (!key.startsWith('sb_publishable_'))
      throw new Error(
        'Use a new sb_publishable_ key in the browser, never a secret or legacy service-role key.',
      );
    const headers = { apikey: key };
    const releases = z
      .array(z.object({ payload: z.unknown() }))
      .parse(
        await json(
          `${url}/rest/v1/dataset_versions?id=eq.${encodeURIComponent(release.release_id)}&published=eq.true&select=payload`,
          signal,
          headers,
        ),
      );
    if (releases.length !== 1)
      throw new Error('The expected research release is not published in Supabase.');
    rawResearch = releases[0].payload;
    const research = researchSchema.parse(rawResearch);
    const all: unknown[] = [];
    for (let offset = 0; offset < research.counts.eligible;) {
      const page = z
        .array(z.unknown())
        .parse(
          await json(
            `${url}/rest/v1/cable_year_observations?release_id=eq.${encodeURIComponent(release.release_id)}&select=*&order=cable_id.asc,year.asc&limit=1000&offset=${offset}`,
            signal,
            headers,
          ),
        );
      if (!page.length)
        throw new Error('Supabase import is incomplete. No bundled data was silently substituted.');
      all.push(...page);
      offset += page.length;
    }
    rawObservations = all;
  } else {
    [rawResearch, rawObservations] = await Promise.all([
      json('/data/research.json', signal),
      json('/data/observations.json', signal),
    ]);
  }
  const research = researchSchema.parse(rawResearch);
  const observations = z.array(observationSchema).parse(rawObservations);
  verifyBundle(research, observations);
  return { research, observations, mode: mode as DataBundle['mode'] };
}

export type Filters = { year: string; route: string; partition: string; query: string };
export const emptyFilters: Filters = { year: 'all', route: 'all', partition: 'all', query: '' };
export function filterRows(rows: Observation[], filters: Filters) {
  return rows.filter(
    (r) =>
      (filters.year === 'all' || String(r.year) === filters.year) &&
      (filters.route === 'all' || r.ocean_route === filters.route) &&
      (filters.partition === 'all' || r.partition === filters.partition) &&
      r.cable_id.toLowerCase().includes(filters.query.trim().toLowerCase()),
  );
}
export function annualSummary(rows: Observation[]) {
  const years = [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b);
  return years.map((year) => {
    const selected = rows.filter((r) => r.year === year);
    const positives = selected.reduce((s, r) => s + r.fault_next_year, 0);
    return {
      year,
      rows: selected.length,
      positives,
      negatives: selected.length - positives,
      rate: positives / selected.length,
    };
  });
}
export function pct(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}
export function num(value: number) {
  return value.toLocaleString('en-US', { maximumFractionDigits: 1 });
}
export function csvText(rows: Record<string, unknown>[], columns: string[]) {
  const cell = (value: unknown) => {
    let text = value == null ? '' : String(value);
    if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  return (
    '\uFEFF' +
    [
      columns.map(cell).join(','),
      ...rows.map((r) => columns.map((k) => cell(r[k])).join(',')),
    ].join('\r\n')
  );
}
export function download(content: string, filename: string, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
