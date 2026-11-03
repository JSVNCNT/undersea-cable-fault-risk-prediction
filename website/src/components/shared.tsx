import type { ReactNode } from 'react';
import { Info, RotateCcw, Download, ArrowUpRight } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { emptyFilters, num, pct } from '../lib/data';
import type { Filters, Metrics, Observation, Research } from '../lib/data';

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  children,
  action,
  className = '',
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
export function Notice({ children, warning = false }: { children: ReactNode; warning?: boolean }) {
  return (
    <div className={`notice ${warning ? 'notice-warning' : ''}`}>
      <Info size={18} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
export function Kpi({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string;
  note: string;
  icon: ReactNode;
}) {
  return (
    <Card className="kpi">
      <div className="kpi-top">
        <span>{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </Card>
  );
}
export function FiltersBar({
  rows,
  filters,
  setFilters,
  search = false,
}: {
  rows: Observation[];
  filters: Filters;
  setFilters: (f: Filters) => void;
  search?: boolean;
}) {
  return (
    <div className="filter-bar">
      <label>
        Predictor year
        <select
          value={filters.year}
          onChange={(e) => setFilters({ ...filters, year: e.target.value })}
        >
          <option value="all">All years</option>
          {[...new Set(rows.map((r) => r.year))]
            .sort((a, b) => a - b)
            .map((y) => (
              <option key={y}>{y}</option>
            ))}
        </select>
      </label>
      <label>
        Ocean route
        <select
          value={filters.route}
          onChange={(e) => setFilters({ ...filters, route: e.target.value })}
        >
          <option value="all">All routes</option>
          {[...new Set(rows.map((r) => r.ocean_route))].sort().map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <label>
        Partition
        <select
          value={filters.partition}
          onChange={(e) => setFilters({ ...filters, partition: e.target.value })}
        >
          <option value="all">All partitions</option>
          <option value="train">Training</option>
          <option value="validation">Validation</option>
          <option value="final_test">Final test</option>
        </select>
      </label>
      {search && (
        <label className="search-field">
          Cable ID
          <input
            type="search"
            placeholder="Search CAB…"
            value={filters.query}
            onChange={(e) => setFilters({ ...filters, query: e.target.value })}
          />
        </label>
      )}
      <Button variant="ghost" onClick={() => setFilters({ ...emptyFilters })}>
        <RotateCcw size={15} />
        Reset filters
      </Button>
    </div>
  );
}
export function SplitTimeline({ research }: { research: Research }) {
  return (
    <div className="split-timeline">
      {research.splits.map((s) => (
        <div
          key={s.partition}
          className={`split-segment ${s.partition}`}
          style={{ flexGrow: s.rows }}
        >
          <span>
            {s.partition === 'train'
              ? 'Training'
              : s.partition === 'validation'
                ? 'Validation'
                : 'Final test'}
          </span>
          <strong>{num(s.rows)}</strong>
          <small>
            {s.min_year}
            {s.min_year !== s.max_year ? `–${s.max_year}` : ''}
          </small>
        </div>
      ))}
    </div>
  );
}
export function Matrix({ metrics, label }: { metrics: Metrics; label: string }) {
  return (
    <div>
      <div className="matrix" aria-label={`${label} confusion matrix`}>
        <span />
        <span>Predicted 0</span>
        <span>Predicted 1</span>
        <span>Actual 0</span>
        <div className="matrix-cell correct">
          <strong>{num(metrics.TN)}</strong>
          <small>True negatives</small>
        </div>
        <div className="matrix-cell error">
          <strong>{num(metrics.FP)}</strong>
          <small>False positives</small>
        </div>
        <span>Actual 1</span>
        <div className="matrix-cell error">
          <strong>{num(metrics.FN)}</strong>
          <small>False negatives</small>
        </div>
        <div className="matrix-cell correct">
          <strong>{num(metrics.TP)}</strong>
          <small>True positives</small>
        </div>
      </div>
      <p className="chart-note">
        {label}. Class 1 = a next-year fault label; class 0 = no next-year fault label.
      </p>
    </div>
  );
}
export function SourceLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a className="source-link" href={href} target="_blank" rel="noreferrer">
      {children}
      <ArrowUpRight size={14} aria-label="opens in a new tab" />
    </a>
  );
}
export function Empty({
  message = 'No observations match these filters. Try clearing a filter.',
}: {
  message?: string;
}) {
  return (
    <div className="empty-state">
      <Info size={28} />
      <p>{message}</p>
    </div>
  );
}
export function ExportButton({
  onClick,
  children = 'Download CSV',
}: {
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <Button variant="outline" onClick={onClick}>
      <Download size={16} />
      {children}
    </Button>
  );
}
export function ClassBalance({ rows }: { rows: Observation[] }) {
  const positives = rows.reduce((s, r) => s + r.fault_next_year, 0);
  return (
    <div className="balance">
      <div className="balance-track">
        <div style={{ width: `${rows.length ? (positives / rows.length) * 100 : 0}%` }} />
      </div>
      <div className="balance-labels">
        <span>
          <i className="dot cyan" />
          Fault label: <strong>{num(positives)}</strong>
        </span>
        <span>
          <i className="dot slate" />
          No fault: <strong>{num(rows.length - positives)}</strong>
        </span>
      </div>
      <p className="chart-note">
        {rows.length ? pct(positives / rows.length) : 'No data'} positive-class prevalence across
        the selected cable-years. This is not a real-world fault frequency.
      </p>
    </div>
  );
}
