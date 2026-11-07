import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Database, Globe, Download, RefreshCw } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { externalMetricLabels, filterActivity, loadExternal } from '../lib/external-data';
import type { ExternalResearch } from '../lib/external-data';
import { csvText, download, num } from '../lib/data';
import { GROUP_NAME, researchTooltipStyles } from '../lib/presentation';
import { Kpi, Notice, PageHeading, Panel } from './shared';
import { Button } from './ui/button';

export function ExternalEvidence() {
  const [data, setData] = useState<ExternalResearch | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    setData(null);
    loadExternal(controller.signal)
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : 'External evidence unavailable.');
      });
    return () => controller.abort();
  }, [attempt]);
  if (error)
    return (
      <Panel title="External evidence unavailable">
        <p role="alert">{error}</p>
        <p>
          No replacement observations were generated. This section has a separate release from the
          modeling experiment.
        </p>
        <Button onClick={() => setAttempt((v) => v + 1)}>Retry external evidence</Button>
        <Link to="/models">View existing model results</Link>
      </Panel>
    );
  if (!data) return <p role="status">Loading independent external evidence…</p>;
  return <ExternalEvidenceView data={data} />;
}

export function ExternalEvidenceView({ data }: { data: ExternalResearch }) {
  const [country, setCountry] = useState('all');
  const [year, setYear] = useState('all');
  const [area, setArea] = useState('all');
  const [siteQuery, setSiteQuery] = useState('');
  const [siteLimit, setSiteLimit] = useState(50);
  const [cableQuery, setCableQuery] = useState('');
  const [regionQuery, setRegionQuery] = useState('');
  const [regionCategory, setRegionCategory] = useState('all');
  const [month, setMonth] = useState('all');
  const [activityLimit, setActivityLimit] = useState(100);
  const [showChecks, setShowChecks] = useState(false);
  const [showLocations, setShowLocations] = useState(false);
  const [showDefinitions, setShowDefinitions] = useState(false);
  const [metric, setMetric] = useState<keyof typeof externalMetricLabels>('apparent_fishing_hours');
  const selected = useMemo(() => {
    const allowed = new Set(
      data.geographies
        .filter((g) => regionCategory === 'all' || g.region_category === regionCategory)
        .map((g) => g.id),
    );
    return filterActivity(data.activity, country, year, metric, area).filter(
      (r) => allowed.has(r.area_id) && (month === 'all' || r.period_start.slice(5, 7) === month),
    );
  }, [data, country, year, metric, area, regionCategory, month]);
  const countries = [
    ...new Set([
      ...data.infrastructure.map((r) => r.country),
      ...data.activity.map((r) => r.country),
      ...data.geographies.map((r) => r.country),
    ]),
  ].sort();
  const years = [...new Set(data.activity.map((r) => r.year))].sort();
  const sites = data.infrastructure.filter(
    (r) =>
      (country === 'all' || r.country === country) &&
      `${r.name} ${r.id}`.toLowerCase().includes(siteQuery.trim().toLowerCase()),
  );
  const countrySiteIds = new Set(
    data.infrastructure.filter((s) => country === 'all' || s.country === country).map((s) => s.id),
  );
  const countryCableIds = new Set(
    data.cable_landings.filter((e) => countrySiteIds.has(e.landing_id)).map((e) => e.cable_id),
  );
  const cables = data.cable_systems.filter(
    (r) =>
      `${r.name} ${r.id}`.toLowerCase().includes(cableQuery.trim().toLowerCase()) &&
      (country === 'all' || countryCableIds.has(r.id)),
  );
  const oneSided = data.cable_landings.filter(
    (r) => r.relationship_evidence !== 'both_directions',
  ).length;
  const chartRows = selected.map((r) => ({
    name: r.period_start.slice(0, 7),
    hours: r.value,
  }));
  const reset = () => {
    setCountry('all');
    setYear('all');
    setArea('all');
    setMetric('apparent_fishing_hours');
    setSiteQuery('');
    setCableQuery('');
    setSiteLimit(50);
    setRegionQuery('');
    setRegionCategory('all');
    setMonth('all');
    setActivityLimit(100);
  };
  return (
    <>
      <PageHeading
        eyebrow={`EXTERNAL EMPIRICAL EVIDENCE / ${GROUP_NAME}`}
        title="Infrastructure and maritime exposure"
        description="An independent source-backed study. No synthetic fault scores are assigned to real cables."
        action={
          <Button asChild variant="outline">
            <a href="/external-data/research.json" download="external-evidence.json">
              <Download size={16} />
              Download evidence snapshot
            </a>
          </Button>
        }
      />
      <Notice warning={!data.empirical_analysis_available}>
        {data.empirical_analysis_available
          ? 'Empirical observations are available within the documented source coverage. This is not external validation of the fault classifier.'
          : data.status === 'partial'
            ? 'Some empirical observations were acquired, but coverage/acquisition is incomplete. Only acquired records are shown. Missing areas and periods are not zero activity or evidence of model validity.'
            : 'Empirical acquisition is incomplete. The scraped resource metadata below are real, but they are not cable observations. Infrastructure and activity results remain unavailable until their acquisition succeeds.'}
      </Notice>
      <div className="external-kpis">
        <Kpi
          label="Scraped catalog resources"
          value={num(data.counts.catalog_resources)}
          note="Resource metadata, not cable records"
          icon={<Database size={18} />}
        />
        <Kpi
          label="Infrastructure records"
          value={data.counts.infrastructure ? num(data.counts.infrastructure) : 'Not acquired'}
          note="Only supplied, licensed real-source records"
          icon={<Globe size={18} />}
        />
        <Kpi
          label="Activity observations"
          value={data.counts.activity ? num(data.counts.activity) : 'Not acquired'}
          note="AIS-derived area/period/metric records"
          icon={<Database size={18} />}
        />
        <Kpi
          label="Release status"
          value={
            data.status === 'available'
              ? 'Available'
              : data.status === 'partial'
                ? 'Partial'
                : 'Awaiting data'
          }
          note={data.release_id}
          icon={<RefreshCw size={18} />}
        />
      </div>
      {data.cable_systems.length > 0 && (
        <Panel
          title="Historical cable inventory"
          subtitle="The archive maintainer describes a late-2022 vintage. Individual observation dates and current operating status are not established."
        >
          <p>
            {num(data.cable_systems.length)} distinct cable-system records,{' '}
            {num(data.infrastructure.length)} landing-point records and{' '}
            {num(data.cable_landings.length)} supplied relationships. These are separate record
            units, not fault counts.
          </p>
          <p>
            {oneSided} relationships appear in only one direction of the source records and remain
            flagged. {data.infrastructure.filter((r) => r.detail_record_available === false).length}{' '}
            point(s) use an exact source-country membership lookup because the individual detail
            file is absent.
          </p>
          <label htmlFor="external-cable-search">Find a historical cable</label>
          <input
            id="external-cable-search"
            className="form-control"
            value={cableQuery}
            onChange={(e) => setCableQuery(e.target.value)}
            placeholder="Cable name or source ID"
          />
          <p>
            {num(cables.length)} matching systems. Showing up to 50; the complete source-specific
            CSV is available below. Country selection also applies.
          </p>
          <div className="table-scroll">
            <table>
              <caption>Historical source-reported cable systems</caption>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Reported service date</th>
                  <th>Reported length</th>
                  <th>Landing links</th>
                </tr>
              </thead>
              <tbody>
                {cables.slice(0, 50).map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.rfs_reported || 'Not supplied'}</td>
                    <td>{c.length_reported || 'Not supplied'}</td>
                    <td>{c.landing_point_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Reported dates may have been planned at archive time. No status is updated by this
            project. Derived archive datasets retain CC BY-NC-SA 3.0 attribution, noncommercial and
            share-alike terms.
          </p>
          <a href="/external-data/historical_infrastructure.zip" download>
            Download historical datasets with original license and attribution
          </a>
        </Panel>
      )}
      {data.html_observations.length > 0 && (
        <Panel
          title="Cable records scraped from regulator HTML"
          subtitle="Independent Hong Kong context from OFCA. Entries are extracted from a dated prose list, not an HTML table, and are not joined to the historical inventory."
        >
          <p>
            {data.html_observations.length} named-system entries. Reference month:{' '}
            {data.html_observations[0].reference_period}. Source: Office of the Communications
            Authority, Hong Kong SAR Government. Noncommercial reuse with attribution.
          </p>
          <div className="table-scroll">
            <table>
              <caption>OFCA named cable systems extracted from HTML</caption>
              <thead>
                <tr>
                  <th>Source-reported name</th>
                  <th>Reference month</th>
                  <th>Source text quality</th>
                </tr>
              </thead>
              <tbody>
                {data.html_observations.map((r) => (
                  <tr key={r.observation_id}>
                    <td>{r.system_name_reported}</td>
                    <td>{r.reference_period}</td>
                    <td>{r.source_text_quality.replaceAll('_', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Original source spelling and encoding issues are retained and flagged. These are not
            cable faults, coordinates, or proof of operation outside the stated month.
          </p>
        </Panel>
      )}
      {data.infrastructure_summary.length > 0 && (
        <Panel
          title="Documented infrastructure distribution"
          subtitle="Counts are source records by country and record unit, not fault frequencies."
        >
          <div className="table-scroll">
            <table>
              <caption>Infrastructure records within the acquired source snapshot</caption>
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Record unit</th>
                  <th>Records</th>
                </tr>
              </thead>
              <tbody>
                {data.infrastructure_summary
                  .filter((r) => country === 'all' || r.country === country)
                  .map((r) => (
                    <tr key={`${r.country}:${r.record_kind}`}>
                      <td>{r.country}</td>
                      <td>{r.record_kind}</td>
                      <td>{r.records}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      <div className="external-source-grid">
        {data.sources.map((source) => (
          <Panel key={source.source_id} title={source.publisher} subtitle={source.source_name}>
            <p>
              <strong>Acquisition:</strong> {source.status.replaceAll('_', ' ')}
            </p>
            <p>
              <a href={source.source_url} target="_blank" rel="noreferrer">
                Source record
              </a>{' '}
              ·{' '}
              <a href={source.license_url} target="_blank" rel="noreferrer">
                {source.license}
              </a>
            </p>
            <dl className="external-definitions">
              <dt>Geographic scope</dt>
              <dd>{source.coverage}</dd>
              <dt>Period</dt>
              <dd>{source.period}</dd>
              <dt>Access recorded</dt>
              <dd>{source.access_date || 'No successful data acquisition recorded'}</dd>
              <dt>Metadata update</dt>
              <dd>{source.metadata_updated || 'Not established'}</dd>
              <dt>Version</dt>
              <dd>{source.version}</dd>
              <dt>Source format</dt>
              <dd>{source.original_format}</dd>
            </dl>
            <p>{source.limitations}</p>
          </Panel>
        ))}
      </div>
      <Panel
        title="Acquisition and coverage checks"
        subtitle="Completion describes actual acquisition, not the existence of code."
      >
        <p>
          {data.geographies.length} documented study regions.{' '}
          {data.events.filter((e) => e.stage === 'gfw_report' && e.status === 'acquired').length}{' '}
          reports returned observations;{' '}
          {
            data.events.filter(
              (e) => e.stage === 'gfw_report' && e.status === 'no_records_returned',
            ).length
          }{' '}
          reports returned no records;{' '}
          {data.events.filter((e) => e.stage === 'gfw_report' && e.status === 'blocked').length}{' '}
          report checks failed or remain blocked. An empty successful report is not an invented
          zero.
        </p>
        <details onToggle={(e) => setShowChecks(e.currentTarget.open)}>
          <summary>Inspect source and per-region acquisition checks</summary>
          {showChecks && (
            <div className="table-scroll">
              <table>
                <caption>Independent external workflow stages</caption>
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Area / dataset</th>
                    <th>Status</th>
                    <th>Rows</th>
                    <th>Evidence or required action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.events.map((e, i) => (
                    <tr key={i}>
                      <td>{e.stage.replaceAll('_', ' ')}</td>
                      <td>
                        {e.area_id || 'Source-level step'}
                        {e.dataset && <small> · {e.dataset}</small>}
                      </td>
                      <td>{e.status.replaceAll('_', ' ')}</td>
                      <td>{e.rows}</td>
                      <td>{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p>
            Requested activity window: {data.configuration.gfw.start_date} to{' '}
            {data.configuration.gfw.end_date} (exclusive end). A request window is not proof of
            complete coverage.
          </p>
        </details>
      </Panel>
      <Panel
        title="Explore empirical observations"
        subtitle="Infrastructure and AIS activity stay outside the synthetic classifier."
      >
        <div className="filter-bar">
          <label>
            Source territory / country label
            <select
              aria-label="External country"
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                setArea('all');
              }}
            >
              <option value="all">All available countries</option>
              {countries.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            Activity year
            <select
              aria-label="External year"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            >
              <option value="all">All available years</option>
              {years.map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </label>
          <label>
            Boundary category
            <select
              aria-label="External boundary category"
              value={regionCategory}
              onChange={(e) => {
                setRegionCategory(e.target.value);
                setArea('all');
              }}
            >
              <option value="all">All source regions</option>
              <option value="source_eez_region">Source EEZ regions</option>
              <option value="joint_or_overlapping">Joint / overlapping regimes</option>
            </select>
          </label>
          <label>
            Search region names
            <input
              aria-label="Search external regions"
              className="form-control"
              value={regionQuery}
              onChange={(e) => {setRegionQuery(e.target.value);setArea('all');}}
              placeholder="Region name or official ID"
            />
          </label>
          <label>
            Activity month
            <select
              aria-label="External month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            >
              <option value="all">All available months</option>
              {Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')).map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label>
            Exposure measurement
            <select
              aria-label="Exposure metric"
              value={metric}
              onChange={(e) => setMetric(e.target.value as keyof typeof externalMetricLabels)}
            >
              {Object.entries(externalMetricLabels).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Study area
            <select
              aria-label="External study area"
              value={area}
              onChange={(e) => setArea(e.target.value)}
            >
              <option value="all">All available areas</option>
              {data.geographies
                .filter(
                  (g) =>
                    (country === 'all' || g.country === country) &&
                    (regionCategory === 'all' || g.region_category === regionCategory) &&
                    `${g.name} ${g.id} ${g.iso3 || ''} ${g.territory_label || ''}`
                      .toLowerCase()
                      .includes(regionQuery.trim().toLowerCase()),
                )
                .map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
            </select>
          </label>
          <Button variant="ghost" onClick={reset}>
            Reset external filters
          </Button>
        </div>
        <p>
          Official EEZ regions provide broad geographic activity context. High seas are outside this
          study. Joint/overlapping regions remain separate, and totals across regions are not added.
          Source-territory labels are not a spatial cable-to-EEZ join.
        </p>
        {!data.activity.length ? (
          <p role="status">
            No empirical activity observations have been acquired. An empty table is not zero
            fishing or vessel activity.
          </p>
        ) : !selected.length ? (
          <p role="status">
            No acquired activity matches these filters. Change or reset the selection.
          </p>
        ) : (
          <>
            <Button
              variant="outline"
              onClick={() =>
                download(
                  csvText(selected, [
                    'area_id',
                    'country',
                    'period_start',
                    'period_end',
                    'metric',
                    'value',
                    'unit',
                    'dataset',
                    'coverage_status',
                  ]),
                  'selected-external-activity.csv',
                  'text/csv',
                )
              }
            >
              Download selected activity
            </Button>
            <p>
              {selected.length} matching observations. Hours refer to AIS-covered vessels.
              Overlapping areas are not summed into a global total.
            </p>
            {area === 'all' ? (
              <p role="status">
                Choose one study area to view its monthly chart. All-region observations remain
                available in the filtered table and CSV; no overlapping global total is calculated.
              </p>
            ) : (
              <div
                style={{ height: 320 }}
                aria-label={`${externalMetricLabels[metric]} by study area and period`}
              >
                <ResponsiveContainer>
                  <BarChart data={chartRows}>
                    <CartesianGrid stroke="#35475e" />
                    <XAxis dataKey="name" stroke="#b8c9db" />
                    <YAxis stroke="#b8c9db" />
                    <Tooltip {...researchTooltipStyles} />
                    <Bar dataKey="hours" fill="#69d9dc" name={externalMetricLabels[metric]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <p>
              Showing {Math.min(activityLimit, selected.length)} of {selected.length} matching
              records.
            </p>
            <div className="table-scroll">
              <table>
                <caption>
                  {externalMetricLabels[metric]} in vessel-hours, by documented study area and
                  period
                </caption>
                <thead>
                  <tr>
                    <th>Area</th>
                    <th>Country</th>
                    <th>Start</th>
                    <th>End exclusive</th>
                    <th>Vessel-hours</th>
                    <th>Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.slice(0, activityLimit).map((r) => (
                    <tr key={[r.area_id, r.period_start, r.dataset].join('|')}>
                      <td>{data.geographies.find((g) => g.id === r.area_id)?.name || r.area_id}</td>
                      <td>{r.country}</td>
                      <td>{r.period_start}</td>
                      <td>{r.period_end}</td>
                      <td>{num(r.value)}</td>
                      <td>{r.coverage_status.replaceAll('_', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selected.length > activityLimit && (
              <Button variant="outline" onClick={() => setActivityLimit((n) => n + 100)}>
                Show 100 more activity records
              </Button>
            )}
            <p>
              <a href="https://globalfishingwatch.org" target="_blank" rel="noreferrer">
                Powered by Global Fishing Watch.
              </a>{' '}
              AIS-derived estimates, not cable contact or fault probabilities.
            </p>
          </>
        )}
        {sites.length > 0 && (
          <div className="table-scroll">
            <table>
              <caption>
                Acquired infrastructure source records. Coordinates are source-supplied, not
                geocoded by the project.
              </caption>
              <thead>
                <tr>
                  <th>Source identity</th>
                  <th>Name</th>
                  <th>Country</th>
                  <th>Record unit</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Snapshot</th>
                </tr>
              </thead>
              <tbody>
                {sites.slice(0, siteLimit).map((s) => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td>{s.name}</td>
                    <td>{s.country}</td>
                    <td>{s.record_kind}</td>
                    <td>{s.latitude ?? 'Not supplied'}</td>
                    <td>{s.longitude ?? 'Not supplied'}</td>
                    <td>
                      {s.snapshot_date ?? 'Not established'}
                      {s.location_to_be_determined ? ' / location TBD in source' : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.infrastructure.length > 0 && (
          <div>
            <label htmlFor="external-site-search">Find a landing point</label>
            <input
              id="external-site-search"
              className="form-control"
              value={siteQuery}
              onChange={(e) => {
                setSiteQuery(e.target.value);
                setSiteLimit(50);
              }}
              placeholder="Location name or source ID"
            />
            <p>
              {num(sites.length)} matches. Showing {Math.min(siteLimit, sites.length)} source
              records.
            </p>
            {sites.length > siteLimit && (
              <Button variant="outline" onClick={() => setSiteLimit((n) => n + 50)}>
                Show 50 more landing points
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() =>
                download(
                  csvText(sites, [
                    'id',
                    'name',
                    'country',
                    'latitude',
                    'longitude',
                    'source_id',
                    'snapshot_date',
                    'coordinate_precision',
                    'location_to_be_determined',
                    'country_assignment',
                  ]),
                  'selected-historical-landing-points.csv',
                  'text/csv',
                )
              }
            >
              Download selected landing points
            </Button>
          </div>
        )}
        {sites.some((s) => s.latitude !== null) && (
          <Button variant="outline" onClick={() => setShowLocations((v) => !v)}>
            {showLocations ? 'Hide source locations' : 'Plot source-supplied locations'}
          </Button>
        )}
        {showLocations && sites.some((s) => s.latitude !== null) && (
          <figure className="external-location-plot">
            <svg
              viewBox="0 0 720 360"
              role="img"
              aria-label="Source-supplied infrastructure longitude and latitude overview"
            >
              <rect width="720" height="360" fill="#0b1220" />
              {[-60, 0, 60].map((lat) => (
                <g key={lat}>
                  <line x1="0" x2="720" y1={180 - lat * 2} y2={180 - lat * 2} stroke="#35475e" />
                  <text x="5" y={176 - lat * 2} fill="#b8c9db" fontSize="11">
                    {lat}° latitude
                  </text>
                </g>
              ))}
              {[-120, 0, 120].map((lon) => (
                <line
                  key={lon}
                  x1={(lon + 180) * 2}
                  x2={(lon + 180) * 2}
                  y1="0"
                  y2="360"
                  stroke="#35475e"
                />
              ))}
              {sites
                .filter((s) => s.latitude !== null && s.longitude !== null)
                .map((s) => (
                  <circle
                    key={s.id}
                    cx={(s.longitude! + 180) * 2}
                    cy={180 - s.latitude! * 2}
                    r="4"
                    fill={s.location_to_be_determined ? '#f1c66d' : '#69d9dc'}
                  >
                    <title>
                      {s.name}: {s.latitude}, {s.longitude}. Precision: {s.coordinate_precision}
                    </title>
                  </circle>
                ))}
            </svg>
            <figcaption>
              Longitude/latitude overview, not a physical cable-route map. Source coordinate
              precision applies; no missing locations are generated. Amber points are marked
              location TBD by the original source. Do not use these cartographic coordinates for
              narrow hazard buffers.
            </figcaption>
          </figure>
        )}
        {data.geographies.length > 0 && (
          <details onToggle={(e) => setShowDefinitions(e.currentTarget.open)}>
            <summary>Study-area definitions and buffer sensitivity</summary>
            {showDefinitions && (
              <div className="table-scroll">
                <table>
                  <caption>
                    Explicit geographies queried; overlapping areas must not be summed as an
                    independent total
                  </caption>
                  <thead>
                    <tr>
                      <th>Area</th>
                      <th>Country</th>
                      <th>Buffer km</th>
                      <th>Definition and limitations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.geographies.map((g) => (
                      <tr key={g.id}>
                        <td>{g.name}</td>
                        <td>{g.country}</td>
                        <td>{g.buffer_km ?? 'Official region'}</td>
                        <td>{g.definition}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </details>
        )}
      </Panel>
      <Panel
        title="What the HTML scraper actually collected"
        subtitle="One row per official catalog resource descriptor. These are metadata records, not observations about cable condition."
      >
        <div className="table-scroll">
          <table>
            <caption>
              Resource descriptors extracted from the official World Bank catalog HTML
            </caption>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Format</th>
                <th>Direct download listed</th>
                <th>Resource rights</th>
              </tr>
            </thead>
            <tbody>
              {data.catalog_resources.map((r) => (
                <tr key={r.resource_id}>
                  <td>
                    <a href={r.source_url} rel="noreferrer" target="_blank">
                      {r.name}
                    </a>
                  </td>
                  <td>{r.format}</td>
                  <td>{r.download_available ? 'Yes' : 'No'}</td>
                  <td>{r.resource_license}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          The catalog's license/update does not establish a third-party geocoded database's reuse
          rights or observation date.
        </p>
      </Panel>
      <Panel title="Variables, downloads and interpretation">
        <details>
          <summary>External variable dictionary</summary>
          <div className="table-scroll">
            <table>
              <caption>
                Supplementary empirical variables; none is an input to the synthetic classifier
              </caption>
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Group</th>
                  <th>Measurement</th>
                  <th>Unit</th>
                  <th>Definition</th>
                </tr>
              </thead>
              <tbody>
                {data.variables.map((v) => (
                  <tr key={v.variable}>
                    <td>{v.variable}</td>
                    <td>{v.indicator_group}</td>
                    <td>{v.measurement_kind}</td>
                    <td>{v.unit}</td>
                    <td>{v.definition}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        <ul>
          {data.limitations.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
        <p>
          Raw sources are retained locally with checksums. GFW personal access tokens are never sent
          to this browser.
        </p>
        <div className="external-downloads">
          {[
            'external_source_registry',
            'external_data_dictionary',
            'scraped_catalog_resources',
            'cleaned_world_bank_infrastructure',
            'cleaned_infrastructure',
            'historical_cable_systems',
            'historical_cable_landings',
            'scraped_ofca_systems',
            'cleaned_gfw_activity',
            'external_geographies',
            'external_empirical_summary',
          ].map((name) => (
            <a key={name} href={`/external-data/${name}.csv`} download>
              {name.replaceAll('_', ' ')} CSV
            </a>
          ))}
        </div>
      </Panel>
    </>
  );
}
