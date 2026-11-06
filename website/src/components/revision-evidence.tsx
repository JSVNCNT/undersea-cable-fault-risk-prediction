import { useState } from 'react';
import { z } from 'zod';
import source from '../revisionEvidence.json';
import type { Research } from '../lib/data';
import { Panel } from './shared';

const evidenceSchema = z.object({
  revision_date: z.string(), release_id: z.string(), model_sha256: z.string(), scope: z.string(),
  forward_checkable: z.number().int(), forward_disagreements: z.number().int(), numeric_parse_failures: z.number().int(),
  shared_validation_ids: z.number().int(), validation_ids: z.number().int(),
  reconciliation: z.array(z.object({ stage: z.string(), rows: z.number().int(), positives: z.number().int(), negatives: z.number().int() })),
  intervals: z.array(z.object({ measure: z.string(), estimate: z.number(), ci_low: z.number(), ci_high: z.number(), valid_repeats: z.number().int() })),
  files: z.array(z.object({ name: z.string(), href: z.string().startsWith('/revision-evidence/'), sha256: z.string().length(64) })),
});
export const revisionEvidence = evidenceSchema.parse(source);

export function RevisionEvidence({ research }: { research: Research }) {
  const [view, setView] = useState<'counts' | 'uncertainty'>('counts');
  const e = revisionEvidence;
  if (e.model_sha256 !== research.model_sha256 || e.release_id !== research.release_id) {
    return <Panel title="Supplementary revision evidence unavailable"><p>The revision evidence does not match this release. Original model results remain unchanged.</p></Panel>;
  }
  return (
    <Panel title="Revision evidence and study boundaries" subtitle={`Development-only supplementary checks dated ${e.revision_date}. Not new final-test results.`}>
      <p>This is an experiment using synthetic cable-year records. The contribution is a reproducible, leakage-aware workflow, not identification of real vulnerable cables.</p>
      <p>{e.forward_checkable.toLocaleString()} consecutive development pairs were checkable, with {e.forward_disagreements} forward-label disagreements and {e.numeric_parse_failures} numeric parsing failures. These checks establish internal consistency, not authenticity of the simulator.</p>
      <div className="segmented" role="group" aria-label="Supplementary evidence view">
        <button aria-pressed={view === 'counts'} onClick={() => setView('counts')}>Record reconciliation</button>
        <button aria-pressed={view === 'uncertainty'} onClick={() => setView('uncertainty')}>Validation uncertainty</button>
      </div>
      <div className="table-scroll">
        {view === 'counts' ? <table>
          <caption>Existing study populations. Terminal rows are last observations per identifier, not all observations from 2026.</caption>
          <thead><tr><th>Population</th><th>Rows</th><th>Positive labels</th><th>Negative labels</th></tr></thead>
          <tbody>{e.reconciliation.map(r => <tr key={r.stage}><td>{r.stage.replaceAll('_', ' ')}</td><td>{r.rows.toLocaleString()}</td><td>{r.positives.toLocaleString()}</td><td>{r.negatives.toLocaleString()}</td></tr>)}</tbody>
        </table> : <table>
          <caption>Paired whole-identifier bootstrap of fixed validation scores. 1,000 replicates, seed 42, percentile 95% intervals. No training or final inference.</caption>
          <thead><tr><th>Measure</th><th>Estimate</th><th>Lower</th><th>Upper</th></tr></thead>
          <tbody>{e.intervals.map(r => <tr key={r.measure}><td>{r.measure.replaceAll('_', ' ')}</td><td>{r.estimate.toFixed(4)}</td><td>{r.ci_low.toFixed(4)}</td><td>{r.ci_high.toFixed(4)}</td></tr>)}</tbody>
        </table>}
      </div>
      <p>The forest's small validation AP advantage is uncertain: the paired difference interval includes zero. This is not proof of equivalence or independent confirmation. {e.shared_validation_ids} of {e.validation_ids} validation identifiers also occur in training, so unseen-system performance is not established.</p>
      <details className="chart-data"><summary>Download supplementary evidence</summary><ul className="plain-list">{e.files.map(f => <li key={f.name}><a href={f.href} download>{f.name.replaceAll('_', ' ')}</a></li>)}</ul></details>
      <details className="chart-data"><summary>Evaluation history and remaining consultation</summary><p>The frozen forest was evaluated once on 2 November 2026 with project-owner authorization. That precedes the instructor memorandum dated 4 November. Instructor acceptance of that evaluation sequence must be confirmed separately. The existing final test is exposed, is not an untouched new test, and must not be used for model or threshold selection. Synthetic-data acceptance and evaluation authorization are different questions.</p></details>
    </Panel>
  );
}
