// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readFileSync } from 'node:fs';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import {
  About,
  Dataset,
  Demonstrator,
  Interpretation,
  Methodology,
  Models,
  Overview,
  Summary,
} from '../src/pages';
import { researchSchema, observationSchema } from '../src/lib/data';
import * as data from '../src/lib/data';
import { checkHealth, predict } from '../src/lib/api';
import { Tooltip } from 'recharts';
import { GROUP_NAME, researchTooltipStyles } from '../src/lib/presentation';

vi.mock('../src/lib/api', () => ({ apiConfigured: true, checkHealth: vi.fn(), predict: vi.fn() }));
// DOM tests validate controls and state; they deliberately do not claim chart rendering QA.
vi.mock('recharts', () => {
  const Wrapper = ({ children }: { children?: ReactNode }) => <div>{children}</div>;
  const Chart = ({ children }: { children?: ReactNode }) => <svg>{children}</svg>;
  const Empty = () => null;
  return {
    ResponsiveContainer: Wrapper,
    AreaChart: Chart,
    BarChart: Chart,
    Area: Empty,
    Bar: Empty,
    Cell: Empty,
    CartesianGrid: Empty,
    Tooltip: vi.fn(Empty),
    XAxis: Empty,
    YAxis: Empty,
  };
});
const research = researchSchema.parse(
  JSON.parse(readFileSync('public/data/research.json', 'utf8')),
);
const observations = observationSchema
  .array()
  .parse(JSON.parse(readFileSync('public/data/observations.json', 'utf8')));
const bundle = { research, observations, mode: 'bundled' as const };
function show(element: ReactNode) {
  return render(<MemoryRouter>{element}</MemoryRouter>);
}

beforeEach(() => {
  vi.mocked(checkHealth).mockReset();
  vi.mocked(predict).mockReset();
  vi.mocked(checkHealth).mockResolvedValue();
  vi.mocked(Tooltip).mockClear();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('research page components', () => {
  it('shows explicit provenance and switches supplementary revision evidence', async () => {
    const user = userEvent.setup();
    show(<Methodology {...bundle} />);
    expect(screen.getByText(/experiment using synthetic cable-year records/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Record reconciliation' }).getAttribute('aria-pressed')).toBe('true');
    await user.click(screen.getByRole('button', { name: 'Validation uncertainty' }));
    expect(screen.getByText('AP random forest minus logistic regression')).toBeTruthy();
    expect(screen.getByText('-0.0358')).toBeTruthy();
    expect(screen.getByText(/424 of 460 validation identifiers/)).toBeTruthy();
  });
  for (const [name, Page] of Object.entries({
    Overview,
    Dataset,
    Models,
    Interpretation,
    Methodology,
    Demonstrator,
    Summary,
    About,
  })) {
    it(`renders ${name} with a single main heading`, async () => {
      const view = show(<Page {...bundle} />);
      expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
      if (['Overview', 'Methodology', 'Summary', 'About'].includes(name)) {
        expect(view.container.textContent).toMatch(/\bsynthetic\b/i);
      }
      if (name === 'Demonstrator') await screen.findByText('Frozen prediction service connected');
    });
  }
  it('uses a compact source note instead of the large overview warning banner', () => {
    show(<Overview {...bundle} />);
    expect(screen.queryByText('Know the boundary.')).toBeNull();
    expect(screen.getByText('Computer-generated research dataset.')).toBeTruthy();
    const sourceLink = screen.getByRole('link', { name: 'Data source and study limitations' });
    expect(sourceLink.getAttribute('href')).toBe('/about');
    expect(sourceLink.closest('.notice-warning')).toBeNull();
  });
  it('uses readable tooltip colors on all three chart pages', () => {
    for (const Page of [Overview, Models, Interpretation]) {
      vi.mocked(Tooltip).mockClear();
      const view = show(<Page {...bundle} />);
      expect(vi.mocked(Tooltip).mock.calls.length).toBeGreaterThan(0);
      for (const [props] of vi.mocked(Tooltip).mock.calls) {
        expect(props.labelStyle).toEqual(researchTooltipStyles.labelStyle);
        expect(props.itemStyle).toEqual(researchTooltipStyles.itemStyle);
        expect(props.contentStyle).toEqual(researchTooltipStyles.contentStyle);
      }
      view.unmount();
    }
  });
  it('shows the group name on the overview and about pages', () => {
    const overview = show(<Overview {...bundle} />);
    expect(screen.getByText(`INTRODUCTION TO DATA SCIENCE / ${GROUP_NAME}`)).toBeTruthy();
    overview.unmount();
    show(<About {...bundle} />);
    expect(
      screen.getByText(new RegExp(`project by ${GROUP_NAME.replace('.', '\\.')}`)),
    ).toBeTruthy();
  });
  it('filters, inspects and exports only matching source records', async () => {
    const user = userEvent.setup();
    const exported = vi.spyOn(data, 'download').mockImplementation(() => {});
    show(<Dataset {...bundle} />);
    await user.selectOptions(screen.getByLabelText('Predictor year'), '2025');
    await user.type(screen.getByLabelText('Cable ID'), 'CAB0001');
    expect(screen.getByText('1–1 of 1')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Inspect CAB0001, 2025' }));
    expect(screen.getByRole('heading', { name: 'CAB0001 / 2025' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Download CSV' }));
    expect(exported).toHaveBeenCalledTimes(1);
    const text = exported.mock.calls[0][0];
    expect(text.split('\r\n')).toHaveLength(2);
    expect(text).toContain('"2025"');
    expect(text).toContain('"None"');
    await user.click(screen.getByRole('button', { name: 'Reset filters' }));
    expect(screen.getByText('1–20 of 4,315')).toBeTruthy();
  });
  it('shows an explicit empty selection and can recover', async () => {
    const user = userEvent.setup();
    show(<Dataset {...bundle} />);
    await user.type(screen.getByLabelText('Cable ID'), 'not-a-record');
    expect(screen.getByText('0 records')).toBeTruthy();
    expect(
      screen.getByText('No observations match these filters. Try clearing a filter.'),
    ).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Reset filters' }));
    expect(screen.getByText('1–20 of 4,315')).toBeTruthy();
  });
  it('keeps unperformed final model evaluations unavailable', async () => {
    const user = userEvent.setup();
    show(<Models {...bundle} />);
    await user.click(screen.getByRole('button', { name: 'Final test · 464 rows' }));
    expect(screen.getAllByText('Not evaluated')).toHaveLength(18);
    const rows = screen.getAllByRole('row');
    const forest = rows.find((r) => r.textContent?.includes('Random Forest'))!;
    expect(within(forest).getByText('0.2877')).toBeTruthy();
    await user.selectOptions(screen.getByLabelText('Chart metric'), 'recall');
    expect(screen.getByRole('heading', { name: 'Recall by model' })).toBeTruthy();
  });
  it('never invokes inference when health is unavailable', async () => {
    vi.mocked(checkHealth).mockRejectedValue(new Error('offline'));
    const user = userEvent.setup();
    show(<Demonstrator {...bundle} />);
    await screen.findByText('Prediction service unavailable');
    await user.click(screen.getByRole('button', { name: 'Load training example' }));
    expect(
      (screen.getByRole('button', { name: 'Run demonstration' }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(predict).not.toHaveBeenCalled();
  });
  it('submits the exact training example and clears stale output on edits', async () => {
    const user = userEvent.setup();
    vi.mocked(predict).mockResolvedValue({
      prediction: 0,
      positive_class_score: 0.25,
      model: 'random_forest',
      model_sha256: research.model_sha256,
      release_id: research.release_id,
      decision_rule: 'Saved argmax rule',
      warnings: [],
      limitation: 'Test fixture, not a published model result.',
    });
    show(<Demonstrator {...bundle} />);
    await screen.findByText('Frozen prediction service connected');
    await user.click(screen.getByRole('button', { name: 'Load training example' }));
    await user.click(screen.getByRole('button', { name: 'Run demonstration' }));
    await screen.findByText('25.00%');
    expect(predict).toHaveBeenCalledWith(research.example);
    await user.clear(screen.getByLabelText('Cable age', { exact: false }));
    expect(screen.queryByText('25.00%')).toBeNull();
  });
  it('reports an API error without manufacturing a replacement result', async () => {
    const user = userEvent.setup();
    vi.mocked(predict).mockRejectedValue(
      new Error('Prediction service unavailable. No result was produced.'),
    );
    show(<Demonstrator {...bundle} />);
    await screen.findByText('Frozen prediction service connected');
    await user.click(screen.getByRole('button', { name: 'Load training example' }));
    await user.click(screen.getByRole('button', { name: 'Run demonstration' }));
    expect(await screen.findByRole('alert')).toHaveProperty(
      'textContent',
      'Prediction service unavailable. No result was produced.',
    );
    expect(screen.queryByText('PREDICTED CLASS')).toBeNull();
  });
  it('switches to historical references without implying cable-ID joins', async () => {
    const user = userEvent.setup();
    show(<About {...bundle} />);
    await user.click(screen.getByRole('button', { name: 'Historical incidents' }));
    expect(screen.getByText('2002 · U.S. East Coast (Philadelphia to New York)')).toBeTruthy();
    expect(screen.getByText(/not joined to the generated CAB IDs/)).toBeTruthy();
  });
});
