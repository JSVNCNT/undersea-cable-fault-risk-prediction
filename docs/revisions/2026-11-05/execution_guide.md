# Revision execution and verification

Run commands from the repository root using the model-compatible environment.
The frozen environment is recorded in `requirements-research-frozen.txt`.
The original final experiment and public research release must not be overwritten.

## Inspect existing revision evidence

Read `outputs/revisions/2026-11-05/revision_summary.json`, the CSV reports, and
`docs/revisions/2026-11-05/compliance_matrix.csv`. This requires no model loading.

## Reproduce supplementary reports in a new directory

```powershell
.\.venv\Scripts\python.exe -B scripts/review_research.py --output-root outputs/revisions/my-new-review
```

The default action only audits records and saved outputs. For validation-only
permutation and paired cluster-bootstrap checks add `--model-diagnostics`.
This verifies the frozen model/runtime before loading it and never fits a
classifier, changes the threshold, or runs final-test inference. The output
directory must not already exist. Original evidence is hash-checked before/after.

## Verify development reproduction

```powershell
.\.venv\Scripts\python.exe -B scripts/check_reproduction.py
```

This creates a fresh retained working copy under ignored `tmp/reproduction_checks`.
Only temporary copies of fixed development candidates are fitted. Comparison
uses original validation/CV/split results with numerical tolerances. It uses the
existing compatible environment, not a newly installed or independent environment.
The original frozen model is not refitted or replaced; no final inference occurs.

The ordinary development command now refuses the completed experiment. An explicit
NEW `--output-root tmp/development-reproduction-N` is required for separate work.
Never run `scripts/evaluate_final_holdout.py` to start the website or rebuild a paper.

## Tests and website build

```powershell
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests website/backend -q
cd website
npm.cmd test
npm.cmd run build
```

Use the actual verification report for passed counts. UI tests mock chart rendering
and do not replace browser/mobile review. Serve the website normally for inspection;
do not rebuild research or publish Supabase to start it.

## Supabase and local website assets

`scripts/publish_revision_assets.py` prepares only selected aggregate CSV downloads
and a static explanatory summary from the dated revision reports. It does not
change the original research release or make cloud requests. Rebuild the website
afterward. The existing Supabase schema and imported release remain compatible.

Optional `website/supabase/003_verify_revision_evidence.sql` is SELECT-only inside
a read-only transaction, using the public role. It verifies the existing release,
818 eligible positives, partitions, and the existing final confusion counts. No
migration, new key, import, deployment, commit, or push is required for these checks.

Deployment is deliberately not performed during this local revision. Commit/push
and Render redeployment remain separate user-authorized actions.
