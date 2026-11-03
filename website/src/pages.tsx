import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Activity,
  ArrowRight,
  Check,
  Copy,
  Database,
  Layers3,
  ListFilter,
  LoaderCircle,
  Network,
  Play,
  RefreshCw,
  ShieldCheck,
  Waves,
} from 'lucide-react';
import type { DataBundle, Feature, Filters, MetricKey, Observation, Research } from './lib/data';
import {
  annualSummary,
  csvText,
  download,
  emptyFilters,
  filterRows,
  metricKeys,
  metricLabels,
  modelNames,
  num,
  pct,
  splitNames,
} from './lib/data';
import { apiConfigured, checkHealth, predict } from './lib/api';
import type { Prediction } from './lib/api';
import { Button } from './components/ui/button';
import {
  ClassBalance,
  Empty,
  ExportButton,
  FiltersBar,
  Kpi,
  Matrix,
  Notice,
  PageHeading,
  Panel,
  SourceLink,
  SplitTimeline,
} from './components/shared';

const chartStyle = {
  backgroundColor: '#142238',
  border: '1px solid #35475e',
  color: '#eaf1fb',
  borderRadius: 10,
};
const grid = '#26354a';
const tick = { fill: '#aab8ca', fontSize: 11 };
type Props = DataBundle;

function CoverageChart({ rows }: { rows: Observation[] }) {
  const annual = annualSummary(rows);
  if (!rows.length) return <Empty />;
  return (
    <>
      <div
        className="chart-box"
        role="img"
        aria-label="Annual cable-year coverage and next-year positive labels. Exact counts are in the data table below."
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={annual} margin={{ top: 10, right: 12, bottom: 8, left: -22 }}>
            <defs>
              <linearGradient id="coverageGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#50c9d1" stopOpacity={0.42} />
                <stop offset="100%" stopColor="#50c9d1" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="year" tick={tick} tickLine={false} axisLine={false} />
            <YAxis tick={tick} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={chartStyle} labelFormatter={(v) => `Predictor year ${v}`} />
            <Area
              type="linear"
              dataKey="rows"
              name="Eligible cable-years"
              stroke="#6bddde"
              strokeWidth={2.5}
              fill="url(#coverageGradient)"
            />
            <Area
              type="linear"
              dataKey="positives"
              name="Next-year fault labels"
              stroke="#a6a1fb"
              strokeWidth={2}
              fill="transparent"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-legend">
        <span>
          <i className="dot cyan" />
          Eligible cable-years
        </span>
        <span>
          <i className="dot violet" />
          Next-year fault labels
        </span>
      </div>
      <details className="chart-data">
        <summary>View chart data</summary>
        <div className="table-scroll">
          <table>
            <caption>Counts by predictor year; labels refer to year t+1.</caption>
            <thead>
              <tr>
                <th>Year</th>
                <th>Eligible</th>
                <th>Positive</th>
                <th>Negative</th>
              </tr>
            </thead>
            <tbody>
              {annual.map((a) => (
                <tr key={a.year}>
                  <td>{a.year}</td>
                  <td>{a.rows}</td>
                  <td>{a.positives}</td>
                  <td>{a.negatives}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

export function Overview({ research, observations }: Props) {
  const [filters, setFilters] = useState<Filters>({ ...emptyFilters });
  const selected = useMemo(() => filterRows(observations, filters), [observations, filters]);
  const rf = research.models.find((m) => m.selected)!;
  const test = rf.final_test!;
  const positives = selected.reduce((s, r) => s + r.fault_next_year, 0);
  return (
    <>
      <PageHeading
        eyebrow="INTRODUCTION TO DATA SCIENCE / GROUP 5"
        title="Undersea cable analytics"
        description="Explore how infrastructure and operational indicators relate to next-year fault labels in our research dataset."
        action={
          <Button asChild>
            <Link to="/predict">
              Try the demonstrator
              <ArrowRight size={16} />
            </Link>
          </Button>
        }
      />
      <div className="research-banner">
        <div className="banner-symbol">
          <Waves size={27} />
        </div>
        <div>
          <span className="eyebrow">THE RESEARCH QUESTION</span>
          <h2>Can this year’s indicators help classify next year’s fault occurrence?</h2>
          <p>
            One cable-year at a time. A chronological study with an independently reserved final
            period.
          </p>
        </div>
        <span className="pill">Academic research</span>
      </div>
      <div className="row g-3 kpi-row">
        <div className="col-6 col-xl-3">
          <Kpi
            label="Eligible observations"
            value={num(research.counts.eligible)}
            note={`${num(research.counts.raw)} original cable-years`}
            icon={<Database size={18} />}
          />
        </div>
        <div className="col-6 col-xl-3">
          <Kpi
            label="Primary indicators"
            value={String(research.counts.predictors)}
            note="9 infrastructure · 4 operational"
            icon={<Layers3 size={18} />}
          />
        </div>
        <div className="col-6 col-xl-3">
          <Kpi
            label="Selected model"
            value="Random Forest"
            note="Selected using validation average precision"
            icon={<Network size={18} />}
          />
        </div>
        <div className="col-6 col-xl-3">
          <Kpi
            label="Final-test recall"
            value={pct(test.recall)}
            note={`${test.TP} of ${test.TP + test.FN} positive labels detected`}
            icon={<Activity size={18} />}
          />
        </div>
      </div>
      <div className="section-heading">
        <h2>Explore the research panel</h2>
        <span className="muted">Descriptive filters only</span>
      </div>
      <FiltersBar rows={observations} filters={filters} setFilters={setFilters} />
      <div className="row g-3">
        <div className="col-12 col-xl-8">
          <Panel
            title="Cable-year coverage"
            subtitle="Counts from the eligible panel, not a real-world incident time series."
            action={<span className="pill">2015–2025</span>}
          >
            <CoverageChart rows={selected} />
          </Panel>
        </div>
        <div className="col-12 col-xl-4">
          <Panel title="Selection at a glance" subtitle="Updates when you change the filters.">
            <div className="selection-total">
              <strong>{num(selected.length)}</strong>
              <span>matching cable-years</span>
            </div>
            <div className="stat-line">
              <span>Distinct panel IDs</span>
              <strong>{num(new Set(selected.map((r) => r.cable_id)).size)}</strong>
            </div>
            <div className="stat-line">
              <span>Next-year fault labels</span>
              <strong>{num(positives)}</strong>
            </div>
            <ClassBalance rows={selected} />
            <Link className="text-link" to="/dataset">
              Open dataset explorer
              <ArrowRight size={15} />
            </Link>
          </Panel>
        </div>
        <div className="col-12 col-xl-8">
          <Panel
            title="A chronological research design"
            subtitle="Earlier years teach the model; later years assess its performance."
          >
            <SplitTimeline research={research} />
            <p className="chart-note">
              Predictors are available at the end of year t. The label describes year t+1. Cable IDs
              can recur across partitions; this is not a test on entirely unseen cable systems.
            </p>
          </Panel>
        </div>
        <div className="col-12 col-xl-4">
          <Panel
            title="Final evaluation completed"
            subtitle="2 November 2026 · Frozen Random Forest"
          >
            <div className="stat-line">
              <span>Average precision</span>
              <strong>{test.pr_auc.toFixed(3)}</strong>
            </div>
            <div className="stat-line">
              <span>False alarms / missed positives</span>
              <strong>
                {test.FP} / {test.FN}
              </strong>
            </div>
            <Link className="text-link" to="/models">
              Read results in context
              <ArrowRight size={15} />
            </Link>
          </Panel>
        </div>
      </div>
      <Notice warning>
        <strong>Know the boundary.</strong> {research.origin} These results demonstrate a
        data-science method, not an operational cable-warning system. Real-world sector references
        are kept separate from the model panel.
      </Notice>
    </>
  );
}

export function Dataset({ research, observations }: Props) {
  const [filters, setFilters] = useState<Filters>({ ...emptyFilters });
  const [field, setField] = useState('lit_capacity_tbps');
  const [sort, setSort] = useState<{ key: keyof Observation; direction: number }>({
    key: 'year',
    direction: 1,
  });
  const [page, setPage] = useState(0);
  const [record, setRecord] = useState<Observation | null>(null);
  const [dictionarySearch, setDictionarySearch] = useState('');
  const filtered = useMemo(() => filterRows(observations, filters), [observations, filters]);
  const sorted = useMemo(
    () =>
      [...filtered].sort((a, b) => {
        const x = a[sort.key],
          y = b[sort.key];
        return (
          (typeof x === 'number' && typeof y === 'number'
            ? x - y
            : String(x).localeCompare(String(y))) * sort.direction
        );
      }),
    [filtered, sort],
  );
  const pageSize = 20,
    totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const current = Math.min(page, totalPages - 1);
  const changeFilters = (f: Filters) => {
    setFilters(f);
    setPage(0);
    setRecord(null);
  };
  const sortBy = (key: keyof Observation) => {
    setSort({ key, direction: sort.key === key ? -sort.direction : 1 });
    setPage(0);
  };
  const columns = [
    'cable_id',
    'year',
    'ocean_route',
    'operator_type',
    'chokepoint',
    'age_years',
    'fiber_pairs',
    'length_km',
    'n_landing_countries',
    'design_capacity_tbps',
    'lit_capacity_tbps',
    'utilization_pct',
    'protected_burial',
    'route_redundancy',
    'fault_this_year',
    'fault_next_year',
    'partition',
  ];
  const display: [keyof Observation, string][] = [
    ['cable_id', 'Panel ID'],
    ['year', 'Year'],
    ['ocean_route', 'Ocean route'],
    [field as keyof Observation, research.features.find((f) => f.name === field)?.label || field],
    ['fault_next_year', 'Next-year label'],
    ['partition', 'Partition'],
  ];
  return (
    <>
      <PageHeading
        eyebrow="DATA / EXPLORER"
        title="Understand every observation"
        description="Each row is one generated cable system in one predictor year. Each column describes that row, its research partition, or its next-year label."
        action={
          <ExportButton
            onClick={() =>
              download(
                csvText(sorted, columns),
                'undersea-filtered-cable-years.csv',
                'text/csv;charset=utf-8',
              )
            }
          />
        }
      />
      <Notice>
        Showing the <strong>{num(research.counts.eligible)} eligible supervised records</strong>,
        not the full raw file. The raw panel retains {research.counts.unlabeled} unlabelled rows and{' '}
        {research.counts.unresolved} temporally unresolved labels outside this view. ID and year are
        audit fields, not model predictors.
      </Notice>
      <FiltersBar rows={observations} filters={filters} setFilters={changeFilters} search />
      <div className="row g-3">
        <div className="col-12 col-lg-8">
          <Panel
            title="Class balance in your selection"
            subtitle={`${num(filtered.length)} matching records; filters do not re-evaluate any model.`}
          >
            <ClassBalance rows={filtered} />
          </Panel>
        </div>
        <div className="col-12 col-lg-4">
          <Panel title="How to read a row">
            <p>
              A row with predictor year <strong>2025</strong> and <code>fault_next_year = 1</code>{' '}
              has a positive label for <strong>2026</strong>. It does not record the location, date,
              or cause of a verified cable break.
            </p>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="Cable-year records"
            subtitle="Sort by a column heading. Select a record to inspect all its fields."
            action={
              <label className="compact-label">
                Indicator column
                <select value={field} onChange={(e) => setField(e.target.value)}>
                  {research.features.map((f) => (
                    <option value={f.name} key={f.name}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </label>
            }
          >
            <div className="table-scroll">
              <table>
                <caption className="sr-only">
                  Eligible records. The chosen indicator column can be changed above the table.
                </caption>
                <thead>
                  <tr>
                    {display.map(([key, label]) => (
                      <th
                        key={key}
                        aria-sort={
                          sort.key === key
                            ? sort.direction === 1
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button className="sort-button" onClick={() => sortBy(key)}>
                          {label}
                          <span aria-hidden="true">
                            {sort.key === key ? (sort.direction === 1 ? ' ↑' : ' ↓') : ' ↕'}
                          </span>
                        </button>
                      </th>
                    ))}
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.slice(current * pageSize, (current + 1) * pageSize).map((r) => (
                    <tr key={`${r.cable_id}-${r.year}`}>
                      {display.map(([key]) => (
                        <td key={key}>
                          {key === 'partition' ? (
                            <span className={`partition-label ${r.partition}`}>
                              {splitNames[r.partition]}
                            </span>
                          ) : key === 'fault_next_year' ? (
                            <span className={`target-label ${r.fault_next_year ? 'positive' : ''}`}>
                              {r.fault_next_year}
                            </span>
                          ) : (
                            String(r[key])
                          )}
                        </td>
                      ))}
                      <td>
                        <button
                          className="table-link"
                          onClick={() => setRecord(r)}
                          aria-label={`Inspect ${r.cable_id}, ${r.year}`}
                        >
                          Inspect
                          <ArrowRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!filtered.length && <Empty />}
            <div className="pagination">
              <span aria-live="polite">
                {filtered.length
                  ? `${current * pageSize + 1}–${Math.min((current + 1) * pageSize, filtered.length)} of ${num(filtered.length)}`
                  : '0 records'}
              </span>
              <div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={current === 0}
                  onClick={() => setPage(current - 1)}
                >
                  Previous
                </Button>
                <span>
                  Page {current + 1} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={current + 1 >= totalPages}
                  onClick={() => setPage(current + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </Panel>
        </div>
        {record && (
          <div className="col-12">
            <Panel
              title={`${record.cable_id} / ${record.year}`}
              subtitle="Selected source record. These are dataset values, not model explanations."
              action={
                <Button variant="ghost" size="sm" onClick={() => setRecord(null)}>
                  Close record
                </Button>
              }
            >
              <dl className="record-grid">
                {Object.entries(record).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </Panel>
          </div>
        )}
        <div className="col-12">
          <Panel
            title="Data dictionary"
            subtitle="Definitions, model roles, and safeguards for every original column."
            action={
              <label className="compact-label">
                Find a variable
                <input
                  type="search"
                  value={dictionarySearch}
                  placeholder="e.g. fault, capacity"
                  onChange={(e) => setDictionarySearch(e.target.value)}
                />
              </label>
            }
          >
            <div className="dictionary">
              {research.dictionary
                .filter((d) =>
                  `${d.variable} ${d.description}`
                    .toLowerCase()
                    .includes(dictionarySearch.toLowerCase()),
                )
                .map((d) => (
                  <details key={d.variable}>
                    <summary>
                      <code>{d.variable}</code>
                      <span className="pill">
                        {d.variable === 'fault_next_year'
                          ? 'Target'
                          : d.predictor_inclusion_status === 'primary predictor'
                            ? 'Primary input'
                            : 'Audit / excluded'}
                      </span>
                    </summary>
                    <p>{d.description}</p>
                    <dl>
                      <dt>Observed range</dt>
                      <dd>{d.valid_range}</dd>
                      <dt>Primary treatment</dt>
                      <dd>{d.planned_treatment}</dd>
                      {d.limitation_note && (
                        <>
                          <dt>Important note</dt>
                          <dd>{d.limitation_note}</dd>
                        </>
                      )}
                      {d.leakage_concern !== 'none identified' && (
                        <>
                          <dt>Leakage concern</dt>
                          <dd>{d.leakage_concern}</dd>
                        </>
                      )}
                    </dl>
                  </details>
                ))}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

const metricExplanations: Record<MetricKey, string> = {
  accuracy:
    'The share of all records classified correctly. A majority-class baseline can score highly when positive labels are uncommon.',
  precision:
    'Of records flagged as positive, how many actually have a positive label? Low precision means many false alarms.',
  recall:
    'Of all positive labels, how many did the model detect? Low recall means many missed positives.',
  f1: 'A balance of precision and recall, expressed as their harmonic mean.',
  pr_auc:
    'Average precision summarizes precision across recall levels. The CSV field is named pr_auc, but it stores sklearn average_precision_score, not trapezoidal PR area.',
  roc_auc:
    'How well scores rank positive labels above negative labels across thresholds. It is not the accuracy at one decision threshold.',
};

export function Models({ research }: Props) {
  const [partition, setPartition] = useState<'validation' | 'final_test'>('validation');
  const [metric, setMetric] = useState<MetricKey>('pr_auc');
  const chart = research.models
    .map((m) => ({
      name: modelNames[m.id],
      value: m[partition]?.[metric] ?? null,
      selected: m.selected,
    }))
    .filter((r) => r.value !== null);
  return (
    <>
      <PageHeading
        eyebrow="MODELS / SAVED EVIDENCE"
        title="Compare models, not just accuracy"
        description="Four candidates were compared on 2023–2024 validation data. Only the frozen, originally selected Random Forest received the one-time final evaluation."
      />
      <div className="controls-row">
        <div className="segmented" role="group" aria-label="Evaluation period">
          <button
            aria-pressed={partition === 'validation'}
            onClick={() => setPartition('validation')}
          >
            Validation · 891 rows
          </button>
          <button
            aria-pressed={partition === 'final_test'}
            onClick={() => setPartition('final_test')}
          >
            Final test · 464 rows
          </button>
        </div>
        <label className="compact-label">
          Chart metric
          <select value={metric} onChange={(e) => setMetric(e.target.value as MetricKey)}>
            {metricKeys.map((k) => (
              <option key={k} value={k}>
                {metricLabels[k]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="row g-3">
        <div className="col-12 col-xl-8">
          <Panel
            title={`${metricLabels[metric]} by model`}
            subtitle={`${partition === 'validation' ? '2023–2024 validation' : '2025 predictor-year final test'} · saved results, no live evaluation`}
          >
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chart}
                  layout="vertical"
                  margin={{ left: 0, right: 30, top: 10, bottom: 10 }}
                >
                  <CartesianGrid stroke={grid} horizontal={false} />
                  <XAxis
                    type="number"
                    domain={[0, 1]}
                    tick={tick}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={135}
                    tick={tick}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={chartStyle}
                    formatter={(v) => [Number(v).toFixed(4), metricLabels[metric]]}
                  />
                  <Bar dataKey="value" radius={[0, 5, 5, 0]} barSize={25}>
                    {chart.map((r) => (
                      <Cell key={r.name} fill={r.selected ? '#69d9dc' : '#637a9d'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-note">{metricExplanations[metric]}</p>
          </Panel>
        </div>
        <div className="col-12 col-xl-4">
          <Panel title="Why Random Forest?" subtitle="Selection used validation average precision.">
            <div className="model-symbol">
              <Network size={30} />
            </div>
            <p>
              It ranked first among the original four candidates on validation average precision,
              with F1 and recall as tie-breakers.
            </p>
            <p>
              The dummy baseline had higher accuracy, but detected{' '}
              <strong>zero positive labels</strong>. That is why accuracy alone was not the
              selection criterion.
            </p>
            <Notice>
              No hyperparameter search was recorded. Fixed settings were compared; do not describe
              this as exhaustive tuning.
            </Notice>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="Full metric comparison"
            subtitle="Scores are proportions on a 0–1 scale. Missing evaluations are not zero."
            action={
              <ExportButton
                onClick={() => {
                  const data = research.models.map((m) => ({
                    model: modelNames[m.id],
                    partition,
                    ...(m[partition] ||
                      Object.fromEntries(metricKeys.map((k) => [k, 'Not evaluated']))),
                  }));
                  download(
                    csvText(data, ['model', 'partition', ...metricKeys, 'TN', 'FP', 'FN', 'TP']),
                    `model-results-${partition}.csv`,
                    'text/csv;charset=utf-8',
                  );
                }}
              />
            }
          >
            <div className="table-scroll">
              <table>
                <caption className="sr-only">
                  {splitNames[partition]} scores for the original candidate models.
                </caption>
                <thead>
                  <tr>
                    <th>Model</th>
                    {metricKeys.map((k) => (
                      <th key={k}>{metricLabels[k]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {research.models.map((m) => (
                    <tr key={m.id} className={m.selected ? 'selected-row' : ''}>
                      <th>
                        {modelNames[m.id]}
                        {m.selected && <span className="selected-tag">Selected</span>}
                      </th>
                      {metricKeys.map((k) => (
                        <td key={k}>
                          {m[partition] ? (
                            m[partition]![k].toFixed(4)
                          ) : (
                            <span className="muted">Not evaluated</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="How each model works"
            subtitle="Plain-language explanations tied to the settings actually used."
          >
            <div className="explanation-grid">
              <article>
                <h3>Dummy baseline</h3>
                <p>
                  Learns class proportions and predicts the majority class. It sets a minimum
                  comparison point without using patterns in the indicators.
                </p>
                <code>strategy = prior</code>
              </article>
              <article>
                <h3>Logistic Regression</h3>
                <p>
                  Combines weighted inputs into a score through a logistic function. Numeric
                  features are standardized; categorical values are one-hot encoded.
                </p>
                <code>C = 1 · balanced classes</code>
              </article>
              <article>
                <h3>Decision Tree</h3>
                <p>
                  Asks a sequence of feature-based questions. Each leaf produces a class
                  distribution, making the model easier to describe but sensitive to the sample.
                </p>
                <code>depth ≤ 6 · leaf ≥ 10</code>
              </article>
              <article>
                <h3>Random Forest</h3>
                <p>
                  Averages class scores from 250 decision trees trained on bootstrap samples and
                  random feature subsets. The larger averaged class score determines the label.
                </p>
                <code>250 trees · depth ≤ 10 · leaf ≥ 3</code>
              </article>
            </div>
          </Panel>
        </div>
      </div>
      <Notice warning>
        Final-test results are already exposed. The website does not retrain, tune thresholds,
        select another model, or repeat the final evaluation. Demonstrator inputs are never added to
        the research dataset.
      </Notice>
    </>
  );
}

export function Interpretation({ research }: Props) {
  const [grouped, setGrouped] = useState(true);
  const [all, setAll] = useState(false);
  const [partition, setPartition] = useState<'validation' | 'final_test'>('final_test');
  const rf = research.models.find((m) => m.selected)!;
  const importance = grouped ? research.importance_grouped : research.importance_encoded;
  const chart = importance
    .slice(0, all ? importance.length : 10)
    .map((r) => ({
      ...r,
      label:
        research.features.find((f) => f.name === r.feature)?.label ||
        r.feature.replace('numeric__', '').replace('categorical__', ''),
    }));
  const result = rf[partition]!;
  return (
    <>
      <PageHeading
        eyebrow="INTERPRETATION / LIMITATIONS"
        title="Look inside the result"
        description="Read the model’s feature-use patterns alongside its false alarms and missed positive labels. Importance is not evidence of causation."
      />
      <div className="row g-3">
        <div className="col-12 col-xl-7">
          <Panel
            title="Random Forest feature importance"
            subtitle={
              grouped
                ? 'Encoded category importances summed back to the 13 original inputs.'
                : 'Impurity-based importance for the saved encoded input features.'
            }
            action={
              <label className="compact-label">
                Feature view
                <select
                  value={grouped ? 'grouped' : 'encoded'}
                  onChange={(e) => setGrouped(e.target.value === 'grouped')}
                >
                  <option value="grouped">Original inputs</option>
                  <option value="encoded">Encoded features</option>
                </select>
              </label>
            }
          >
            <div className="importance-chart" style={{ height: Math.max(310, chart.length * 32) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart} layout="vertical" margin={{ right: 16, left: 0 }}>
                  <CartesianGrid stroke={grid} horizontal={false} />
                  <XAxis type="number" tick={tick} tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={180}
                    tick={{ ...tick, fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={chartStyle}
                    formatter={(v) => [Number(v).toFixed(4), 'Importance']}
                  />
                  <Bar dataKey="importance" fill="#69d9dc" radius={[0, 4, 4, 0]} barSize={17} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
              {all ? 'Show top 10' : `Show all ${importance.length}`}
            </Button>
            <details className="chart-data">
              <summary>Read exact feature importance values</summary>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Importance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importance.map((r) => (
                      <tr key={r.feature}>
                        <td>{r.feature}</td>
                        <td>{r.importance.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <p className="chart-note">
              Impurity-based importance can favor continuous or high-cardinality features. It does
              not show direction, a causal effect, or a specific cable’s explanation.
            </p>
          </Panel>
        </div>
        <div className="col-12 col-xl-5">
          <Panel
            title="Where classification succeeds and fails"
            action={
              <label className="compact-label">
                Period
                <select
                  value={partition}
                  onChange={(e) => setPartition(e.target.value as typeof partition)}
                >
                  <option value="validation">Validation</option>
                  <option value="final_test">Final test</option>
                </select>
              </label>
            }
          >
            <Matrix metrics={result} label={splitNames[partition]} />
            <div className="error-summary">
              <div>
                <strong>{result.FP}</strong>
                <span>False alarms</span>
                <small>Flagged positive; label was 0</small>
              </div>
              <div>
                <strong>{result.FN}</strong>
                <span>Missed positives</span>
                <small>Predicted 0; label was 1</small>
              </div>
            </div>
            <Notice warning>
              On this period, the model detected {result.TP} of {result.TP + result.FN} positives.
              This is modest performance and does not justify operational deployment.
            </Notice>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="Training versus later periods"
            subtitle="Diagnostic scores from the already saved evaluation; no new scoring is performed."
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Partition</th>
                    <th>Rows</th>
                    <th>Average precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>ROC-AUC</th>
                  </tr>
                </thead>
                <tbody>
                  {research.partition_metrics.map((r) => (
                    <tr key={r.partition}>
                      <th>{splitNames[r.partition]}</th>
                      <td>{r.rows}</td>
                      <td>{r.pr_auc.toFixed(4)}</td>
                      <td>{r.recall.toFixed(4)}</td>
                      <td>{r.f1.toFixed(4)}</td>
                      <td>{r.roc_auc.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="chart-note">
              The gap is consistent with limited generalization, but these summaries cannot separate
              overfitting, changes over time, and cohort differences. Repeated panel IDs and
              computer-generated data further limit interpretation.
            </p>
          </Panel>
        </div>
      </div>
    </>
  );
}

export function Methodology({ research }: Props) {
  const steps = [
    [
      'Preserve the original panel',
      `${num(research.counts.raw)} rows and 21 original fields are retained. Duplicate row and cable-year checks found none. The literal chokepoint category “None” is preserved as a valid category.`,
    ],
    [
      'Audit target timing',
      `${research.counts.unlabeled} unlabelled rows are not assigned a target. Six populated labels without the required consecutive-year relationship are excluded from supervised modeling, leaving ${num(research.counts.eligible)} eligible rows.`,
    ],
    [
      'Define the prediction cutoff',
      'At the end of observation year t, the model uses nine infrastructure and four operational inputs to classify the label for t+1. Cable ID, year, fault cause, vulnerability index, constant design life, and duplicate redundancy flag are excluded from the primary predictors.',
    ],
    [
      'Split chronologically',
      'Training uses 2015–2022, validation uses 2023–2024, and the final test uses predictor year 2025 for target year 2026. No random row split is substituted.',
    ],
    [
      'Fit preprocessing on training only',
      'Numeric inputs use median imputation and categories use most-frequent imputation followed by one-hot encoding. There were no missing values in the 13 source predictors, so imputers are safeguards rather than actual replacements. Only Logistic Regression scales numeric inputs.',
    ],
    [
      'Compare four fixed candidates',
      'Dummy, Logistic Regression, Decision Tree, and Random Forest share the same primary inputs and chronological validation period. The original selection ranks validation average precision, then F1 and recall. No hyperparameter search was recorded.',
    ],
    [
      'Evaluate once, then publish',
      'The frozen original Random Forest was evaluated once on 2 November 2026. No refit, tuning, or threshold adjustment followed. This site reads those saved results and uses a separate inference-only service for manually supplied demonstrator inputs.',
    ],
  ];
  return (
    <>
      <PageHeading
        eyebrow="METHOD / REPRODUCIBILITY"
        title="From source data to saved results"
        description="A traceable workflow that preserves original records, keeps preprocessing inside the model pipeline, and separates model development from final evaluation."
      />
      <Panel
        title="Chronological partitions"
        subtitle="Counts refer to eligible supervised cable-years, not unique real cables."
      >
        <SplitTimeline research={research} />
      </Panel>
      <div className="method-timeline">
        {steps.map(([title, text], index) => (
          <article key={title}>
            <span className="step-number">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h2>{title}</h2>
              <p>{text}</p>
            </div>
          </article>
        ))}
      </div>
      <div className="row g-3">
        <div className="col-12 col-lg-6">
          <Panel title="What the prediction service actually does">
            <ol className="plain-list">
              <li>Validate the 13 submitted inputs and known categories.</li>
              <li>Make a one-row DataFrame in the saved feature order.</li>
              <li>Run the original saved preprocessing-plus-model pipeline.</li>
              <li>Return the larger-score class and the positive-class score.</li>
            </ol>
            <p className="chart-note">
              Ties map to class 0, following sklearn’s argmax rule. No manually chosen risk bands or
              recalibrated thresholds are introduced.
            </p>
          </Panel>
        </div>
        <div className="col-12 col-lg-6">
          <Panel title="Supplemental analyses stay supplemental">
            <p>
              The indicator-block experiment reused validation data. Infrastructure-only average
              precision was slightly higher than the combined model’s, but that was not a new,
              independent model-selection exercise.
            </p>
            <p>
              ITU, ICPC, and TeleGeography references explain the real-world motivation. They do not
              turn generated cable IDs into authenticated assets or validate the classifier.
            </p>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="Indicator framework"
            subtitle="Expand an input to understand what it measures and what it cannot establish."
          >
            <div className="dictionary">
              {research.features.map((f) => (
                <details key={f.name}>
                  <summary>
                    <span>{f.label}</span>
                    <span className="pill">{f.group}</span>
                  </summary>
                  <p>
                    {f.description}. Unit: {f.unit}.
                  </p>
                  <p>{f.qualification}</p>
                  <code>{f.name}</code>
                </details>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

const numberBounds: Record<string, { min: number; max: number }> = {
  age_years: { min: 0, max: 200 },
  fiber_pairs: { min: 1, max: 10000 },
  length_km: { min: 0.01, max: 100000 },
  n_landing_countries: { min: 1, max: 250 },
  design_capacity_tbps: { min: 0.01, max: 1000000 },
  lit_capacity_tbps: { min: 0, max: 1000000 },
  utilization_pct: { min: 0, max: 100 },
  protected_burial: { min: 0, max: 1 },
  route_redundancy: { min: 0, max: 100000 },
  fault_this_year: { min: 0, max: 1 },
};
function PredictorField({
  feature,
  value,
  onChange,
}: {
  feature: Feature;
  value: string;
  onChange: (value: string) => void;
}) {
  const range = numberBounds[feature.name];
  return (
    <div className="predictor-field">
      <label htmlFor={`predict-${feature.name}`}>
        {feature.label}
        <span className="unit">{feature.unit}</span>
      </label>
      {feature.kind === 'category' ? (
        <select
          id={`predict-${feature.name}`}
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={`hint-${feature.name}`}
        >
          <option value="">Select a category</option>
          {feature.categories.map((v) => (
            <option key={v} value={v}>
              {v === 'None' ? 'None (no named chokepoint)' : v}
            </option>
          ))}
        </select>
      ) : ['protected_burial', 'fault_this_year'].includes(feature.name) ? (
        <select
          id={`predict-${feature.name}`}
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={`hint-${feature.name}`}
        >
          <option value="">Select an option</option>
          <option value="0">0 · No</option>
          <option value="1">1 · Yes</option>
        </select>
      ) : (
        <input
          id={`predict-${feature.name}`}
          required
          type="number"
          step={feature.kind === 'integer' ? 1 : 'any'}
          min={range?.min}
          max={range?.max}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={`hint-${feature.name}`}
        />
      )}
      <small id={`hint-${feature.name}`}>
        {feature.kind === 'category'
          ? feature.description
          : `Training range: ${feature.train_min}–${feature.train_max} ${feature.unit}`}
      </small>
      <details className="field-help">
        <summary>What does this mean?</summary>
        <p>
          {feature.description}. {feature.qualification}
        </p>
      </details>
    </div>
  );
}

export function Demonstrator({ research }: Props) {
  const blank = () => Object.fromEntries(research.features.map((f) => [f.name, '']));
  const [values, setValues] = useState<Record<string, string>>(blank);
  const [health, setHealth] = useState<'checking' | 'ready' | 'unavailable'>('checking');
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState('');
  const [exampleLoaded, setExampleLoaded] = useState(false);
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    let active = true;
    setHealth('checking');
    checkHealth()
      .then(() => {
        if (active) setHealth('ready');
      })
      .catch(() => {
        if (active) setHealth('unavailable');
      });
    return () => {
      active = false;
    };
  }, [generation]);
  const change = (name: string, value: string) => {
    setValues((v) => ({ ...v, [name]: value }));
    setResult(null);
    setError('');
    setExampleLoaded(false);
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setResult(null);
    setError('');
    setPending(true);
    try {
      const payload: Record<string, string | number> = {};
      for (const f of research.features) {
        const value = values[f.name];
        if (value.trim() === '') throw new Error('Complete every predictor field.');
        payload[f.name] = f.kind === 'category' ? value : Number(value);
        if (f.kind !== 'category' && !Number.isFinite(payload[f.name]))
          throw new Error('Numeric fields must be finite.');
      }
      setResult(await predict(payload));
      setHealth('ready');
    } catch (e) {
      setError(
        e instanceof Error ? e.message : 'Prediction service unavailable. No result was produced.',
      );
    } finally {
      setPending(false);
    }
  };
  return (
    <>
      <PageHeading
        eyebrow="PREDICTION / ACADEMIC DEMONSTRATOR"
        title="Explore the frozen model"
        description="Enter end-of-year indicators to see the saved Random Forest’s next-year classification. This is not a live monitoring tool or a calibrated real-world forecast."
      />
      <div className={`service-banner ${health === 'ready' ? 'service-ready' : ''}`} role="status">
        <span className="service-dot" />
        <div>
          <strong>
            {health === 'checking'
              ? 'Checking Python service…'
              : health === 'ready'
                ? 'Frozen prediction service connected'
                : 'Prediction service unavailable'}
          </strong>
          <p>
            {health === 'ready'
              ? 'Model fingerprint and publication release match this website.'
              : apiConfigured
                ? 'The service may be starting, offline, or misconfigured. You can still inspect the form; no prediction will be fabricated.'
                : 'Set VITE_API_URL and start the Python service to enable actual inference.'}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={health === 'checking'}
          onClick={() => setGeneration((g) => g + 1)}
        >
          <RefreshCw size={14} />
          Recheck
        </Button>
      </div>
      <div className="row g-3">
        <div className="col-12 col-xl-8">
          <form onSubmit={submit}>
            <div className="form-toolbar">
              <h2>13 primary inputs</h2>
              <div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={pending}
                  onClick={() => {
                    setValues(
                      Object.fromEntries(
                        Object.entries(research.example).map(([k, v]) => [k, String(v)]),
                      ),
                    );
                    setResult(null);
                    setError('');
                    setExampleLoaded(true);
                  }}
                >
                  Load training example
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={pending}
                  onClick={() => {
                    setValues(blank());
                    setResult(null);
                    setError('');
                    setExampleLoaded(false);
                  }}
                >
                  Clear
                </Button>
              </div>
            </div>
            {exampleLoaded && (
              <p className="example-note">
                Loaded existing training record {research.example_source.cable_id},{' '}
                {research.example_source.year}. This is not a new observation or a final-test
                evaluation.
              </p>
            )}
            {(['infrastructure', 'operational'] as const).map((group) => (
              <fieldset className="panel predictor-group" key={group} disabled={pending}>
                <legend>
                  {group === 'infrastructure' ? <Layers3 size={18} /> : <Activity size={18} />}{' '}
                  {group === 'infrastructure'
                    ? 'Infrastructure indicators'
                    : 'Operational indicators'}
                  <span>{group === 'infrastructure' ? '9 inputs' : '4 inputs'}</span>
                </legend>
                <div className="row g-3">
                  {research.features
                    .filter((f) => f.group === group)
                    .map((feature) => (
                      <div className="col-12 col-sm-6" key={feature.name}>
                        <PredictorField
                          feature={feature}
                          value={values[feature.name]}
                          onChange={(v) => change(feature.name, v)}
                        />
                      </div>
                    ))}
                </div>
              </fieldset>
            ))}
            <div className="form-submit">
              <p>Scenarios are not stored and do not alter research data or the frozen model.</p>
              <Button type="submit" disabled={pending || health !== 'ready'}>
                {pending ? <LoaderCircle className="spin" size={16} /> : <Play size={16} />}{' '}
                {pending ? 'Running frozen pipeline…' : 'Run demonstration'}
              </Button>
            </div>
          </form>
        </div>
        <div className="col-12 col-xl-4">
          <div className="sticky-result">
            <Panel
              title="Demonstration result"
              subtitle="The result belongs only to your current inputs."
            >
              <div aria-live="polite" aria-atomic="true">
                {pending ? (
                  <div className="empty-state">
                    <LoaderCircle className="spin" size={30} />
                    <p>Running the original Python pipeline…</p>
                  </div>
                ) : result ? (
                  <div className="prediction-result">
                    <span className="eyebrow">PREDICTED CLASS</span>
                    <strong>{result.prediction}</strong>
                    <h3>
                      {result.prediction === 1
                        ? 'Positive next-year label'
                        : 'Negative next-year label'}
                    </h3>
                    <div className="score-line">
                      <span>Positive-class score</span>
                      <b>{pct(result.positive_class_score, 2)}</b>
                    </div>
                    <div className="score-track">
                      <div style={{ width: pct(result.positive_class_score, 4) }} />
                    </div>
                    <p>
                      The score is the forest’s averaged class score. It is not calibrated
                      confidence or the verified chance of a real cable failing.
                    </p>
                    {result.warnings.length > 0 && (
                      <Notice warning>
                        <ul>
                          {result.warnings.map((w) => (
                            <li key={w}>{w}</li>
                          ))}
                        </ul>
                      </Notice>
                    )}
                    <ExportButton
                      onClick={() =>
                        download(
                          JSON.stringify(
                            {
                              purpose: 'Academic scenario; not a research observation',
                              inputs: values,
                              ...result,
                            },
                            null,
                            2,
                          ),
                          'undersea-demonstration.json',
                        )
                      }
                    >
                      Download scenario
                    </ExportButton>
                  </div>
                ) : (
                  <Empty message="Complete the form and run the connected service to see an actual model result." />
                )}
                {error && (
                  <div className="notice notice-warning" role="alert">
                    {error}
                  </div>
                )}
              </div>
            </Panel>
            <Panel title="What happens behind the button">
              <ol className="plain-list">
                <li>Inputs are validated.</li>
                <li>Training-fitted imputation and encoding are applied.</li>
                <li>250 saved trees produce class scores.</li>
                <li>The higher-score class is returned.</li>
              </ol>
              <p className="chart-note">
                No retraining, new evaluation, SQL prediction, or JavaScript replacement model.
              </p>
            </Panel>
          </div>
        </div>
      </div>
    </>
  );
}

export function Summary({ research }: Props) {
  const test = research.models.find((m) => m.selected)!.final_test!;
  const [copied, setCopied] = useState('');
  const brief = `Our research studies whether nine infrastructure and four operational indicators can classify next-year fault labels in a publisher-declared computer-generated cable-year panel. We retained ${num(research.counts.eligible)} temporally eligible observations and used chronological training, validation, and final-test periods. Random Forest led the original candidate comparison by validation average precision. Its one-time final test on 464 rows detected ${test.TP} of ${test.TP + test.FN} positives, with ${test.FP} false alarms and ${test.FN} missed positives. Final average precision was ${test.pr_auc.toFixed(4)}. The results demonstrate a reproducible workflow, not operational reliability or causal effects.`;
  const answers = [
    [
      'Why research undersea cables?',
      'Submarine cables support international connectivity. Disruptions can interrupt communication and access to services, making resilience an important topic. This study uses available indicators to explore a classification workflow before any real-world deployment claim.',
    ],
    [
      'What is the practical contribution?',
      'A transparent way to prepare panel data, separate training from later evaluation, compare models against a baseline, and explain false alarms and missed positives. The website helps students and reviewers inspect that evidence.',
    ],
    [
      'Why these two indicator groups?',
      'Infrastructure describes the cable configuration and network setting. Operational indicators describe its supplied operating context at the end of the current year. Neither group contains full vessel activity, seabed exposure, maintenance records, or verified fault telemetry.',
    ],
    [
      'Why not call the score real-world risk?',
      'The observations are computer-generated and model scores are not calibrated against authenticated cable failures. A positive score is a classifier output within this academic setting.',
    ],
    [
      'Why not improve the model using the final test?',
      'Once the final results are visible, using them to tune or select a model would compromise the independent final assessment. Future changes need a new, independently held-out dataset.',
    ],
    [
      'What would a real deployment need?',
      'Authenticated cable records and fault histories, reliable observation dates, route geometry, exposure and maintenance data, operator review, independent validation, calibration, and a clear cost-based decision policy.',
    ],
  ];
  return (
    <>
      <PageHeading
        eyebrow="SUMMARY / DEFENSE NOTES"
        title="The research in plain language"
        description="Deterministic explanations grounded in the published data and saved metrics. No AI-generated claims or hidden live analysis."
        action={
          <Button
            variant="outline"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(brief);
                setCopied('Summary copied.');
              } catch {
                setCopied('Clipboard unavailable. Use Download brief instead.');
              }
            }}
          >
            {copied === 'Summary copied.' ? <Check size={16} /> : <Copy size={16} />}Copy short
            summary
          </Button>
        }
      />
      <p role="status" className="muted">
        {copied}
      </p>
      <Panel title="A short explanation for your defense">
        <p className="lead-paragraph">{brief}</p>
        <ExportButton onClick={() => download(brief, 'undersea-research-brief.txt', 'text/plain')}>
          Download brief
        </ExportButton>
      </Panel>
      <div className="row g-3">
        <div className="col-12 col-md-4">
          <Panel title="Research question">
            <p>
              Can current-year infrastructure and operational indicators help classify the next-year
              fault label?
            </p>
          </Panel>
        </div>
        <div className="col-12 col-md-4">
          <Panel title="Method">
            <p>
              Training-only preprocessing, chronological partitions, four fixed candidate
              classifiers, and a one-time final assessment.
            </p>
          </Panel>
        </div>
        <div className="col-12 col-md-4">
          <Panel title="Honest conclusion">
            <p>
              The selected model shows modest later-period discrimination, with substantial false
              alarms and missed positives.
            </p>
          </Panel>
        </div>
        <div className="col-12">
          <Panel title="Questions you may be asked">
            <div className="dictionary">
              {answers.map(([q, a]) => (
                <details key={q}>
                  <summary>{q}</summary>
                  <p>{a}</p>
                </details>
              ))}
            </div>
          </Panel>
        </div>
      </div>
      <Notice>
        <strong>Simple system explanation:</strong> React presents the research. Supabase can store
        the published release. Python runs the existing frozen model. Bootstrap adapts the layout to
        different screens. These tools do not change the scientific evidence.
      </Notice>
    </>
  );
}

export function About({ research }: Props) {
  const [tab, setTab] = useState<'context' | 'incidents'>('context');
  return (
    <>
      <PageHeading
        eyebrow="ABOUT / PURPOSE & SOURCES"
        title="Why this research exists"
        description="An Introduction to Data Science project by Group 5, exploring infrastructure and operational indicators through a reproducible, limited-scope classification study."
      />
      <div className="row g-3">
        <div className="col-12 col-lg-8">
          <Panel title="Connectivity deserves understandable evidence">
            <p className="lead-paragraph">
              Undersea cable disruptions matter because connectivity supports communication,
              learning, public services, and economic activity. Understanding what available
              indicators can—and cannot—tell us is a useful first step toward better resilience
              research.
            </p>
            <p>
              Our project asks a narrower question: can a repeatable data-science workflow classify
              next-year fault labels from this dataset? We expose the preparation rules, model
              comparison, and classification errors so readers can judge the evidence themselves.
            </p>
            <h3 className="research-title">{research.title}</h3>
            <SourceLink href={research.source_url}>
              Original Kaggle dataset and publisher
            </SourceLink>
          </Panel>
        </div>
        <div className="col-12 col-lg-4">
          <Panel title="Who can use this website?">
            <ul className="plain-list">
              <li>
                <strong>Students:</strong> learn a complete panel-data classification workflow.
              </li>
              <li>
                <strong>Reviewers:</strong> inspect saved results and limitations.
              </li>
              <li>
                <strong>Researchers:</strong> identify missing evidence for future empirical work.
              </li>
            </ul>
            <p className="chart-note">
              Not for dispatching repairs, ranking named real cables, or issuing public fault
              alerts.
            </p>
          </Panel>
        </div>
        <div className="col-12">
          <Panel
            title="Real-world motivation, kept separate"
            subtitle="Original source-backed context from the project. Scope, period, and qualifications are retained."
            action={
              <div className="segmented" role="group" aria-label="Reference dataset">
                <button aria-pressed={tab === 'context'} onClick={() => setTab('context')}>
                  Sector context
                </button>
                <button aria-pressed={tab === 'incidents'} onClick={() => setTab('incidents')}>
                  Historical incidents
                </button>
              </div>
            }
          >
            {tab === 'context' ? (
              <div className="reference-grid">
                {research.context.map((c) => (
                  <article className="reference-card" key={c.metric_id}>
                    <span className="eyebrow">
                      {c.source_organization} / {c.reference_period}
                    </span>
                    <h3>{c.metric}</h3>
                    <strong>
                      {c.unit === 'repairs_lower_bound'
                        ? '> '
                        : c.metric_id === 'annual_faults_estimate' ||
                            c.metric_id === 'new_cable_length_2024'
                          ? '≈ '
                          : ''}
                      {num(c.value)}
                      <small>
                        {c.unit === 'percent'
                          ? '%'
                          : c.unit === 'percent_per_year'
                            ? '% / year'
                            : c.unit === 'faults_per_year'
                              ? ' faults / year'
                              : c.unit === 'repairs_lower_bound'
                                ? ' repairs'
                                : ` ${c.unit}`}
                      </small>
                    </strong>
                    <p>
                      {c.scope}. {c.source_note}
                    </p>
                    <SourceLink href={c.source_url}>{c.source_title}</SourceLink>
                  </article>
                ))}
              </div>
            ) : (
              <div className="dictionary">
                {research.incidents.map((i) => (
                  <details key={i.incident_id}>
                    <summary>
                      <span>
                        {i.incident_date} · {i.location}
                      </span>
                      <span className="pill">Documented example</span>
                    </summary>
                    <p>
                      <strong>{i.vessel_or_description}.</strong> {i.cause_summary}.
                    </p>
                    <p>
                      Telecom cables damaged:{' '}
                      {i.telecom_cables_damaged ?? 'Not specified by source'}.
                      {i.other_assets_damaged && ` Other assets: ${i.other_assets_damaged}.`}
                    </p>
                    <SourceLink href={i.source_url}>
                      {i.source_organization} · {i.source_title}
                    </SourceLink>
                  </details>
                ))}
              </div>
            )}
            <Notice warning>
              These references are not joined to the generated CAB IDs. Historical percentages are
              not current global fault rates. Selected incidents are not a complete incident census.
              A typical design life does not certify an individual cable’s condition.
            </Notice>
          </Panel>
        </div>
        <div className="col-12 col-lg-6">
          <Panel title="What remains outside the study">
            <p>
              No authenticated asset crosswalk, route geometry, vessel tracking, fishing intensity,
              seabed condition, repair response time, or verified maintenance history is present in
              the primary inputs.
            </p>
            <p>
              The next research stage would need independently collected real observations and a new
              evaluation plan before making operational claims.
            </p>
          </Panel>
        </div>
        <div className="col-12 col-lg-6">
          <Panel title="Publication and provenance">
            <dl className="provenance">
              <dt>Research release</dt>
              <dd>
                <code>{research.release_id}</code>
              </dd>
              <dt>Final evaluation</dt>
              <dd>Completed once · 2 November 2026</dd>
              <dt>Model fingerprint</dt>
              <dd>
                <code>{research.model_sha256}</code>
              </dd>
            </dl>
            <details className="chart-data">
              <summary>Inspect source-file fingerprints</summary>
              <dl className="provenance">
                {Object.entries(research.source_sha256).map(([file, sha]) => (
                  <div key={file}>
                    <dt>{file}</dt>
                    <dd>
                      <code>{sha}</code>
                    </dd>
                  </div>
                ))}
              </dl>
            </details>
            <ExportButton
              onClick={() =>
                download(
                  JSON.stringify(
                    {
                      release: research.release_id,
                      model_sha256: research.model_sha256,
                      sources: research.source_sha256,
                    },
                    null,
                    2,
                  ),
                  'research-provenance.json',
                )
              }
            >
              Download provenance
            </ExportButton>
          </Panel>
        </div>
      </div>
    </>
  );
}
