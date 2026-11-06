# Finals revision handoff

The November 5 revision retains the approved research question and original frozen
random forest. It clarifies the accepted synthetic-data scope, strengthens data
validation and adds development-only statistical diagnostics. It does not add
invented cable observations or repeat the completed final evaluation.

## Where to start

- The clean final defense paper is in the Git-ignored local folder
  `deliverables/final_defense_copy_2026-11-05/`. It uses the instructor's suggested
  synthetic-label title, places the abstract directly after the cover and removes
  administrative review/checklist appendices. Scientific qualifications and actual
  evaluation history remain. The earlier detailed revision copy is preserved in
  `deliverables/final_research_paper_2026-11-05/`; correction/member records remain
  separate from the clean paper.
- `compliance_matrix.csv` maps all 320 numbered instructor comments to a response,
  revised location, evidence and status. Mapping is not instructor sign-off.
- `change_record.md` records actual assisted implementation.
- `member_review_record.csv` contains proposed review assignments. Members must
  supply their own actual work dates, evidence and confirmation.
- `execution_guide.md` gives safe reproduction and website commands.
- `final_test_access_record.md` discloses the actual evaluation sequence.

New analytical evidence is separate under `outputs/revisions/2026-11-05/`.
Each reconciliation row is an analysis population, each association row is one
variable, each subgroup row is a descriptive validation subgroup, and each
bootstrap row is one summary measure. These are reports derived from existing
records, not newly collected measurements. `final_data_dictionary.csv` describes
all 21 original fields; `added_audit_dictionary.csv` describes four non-predictive
cleaning fields. Rates are decimals unless a field explicitly says percent.

The website's Methodology page displays the revision evidence and offers 11
supporting CSV downloads. Its original published research release is unchanged.

## Verified locally

- 83 Python/API tests and 32 frontend/database tests passed.
- TypeScript checking and the Vite production build passed.
- All eight revised notebooks executed in temporary copies.
- A fresh working-copy development run reproduced the saved validation metrics,
  temporal CV scores and split counts within numerical tolerance. It reused the
  compatible environment; it was not a newly provisioned dependency installation.
- Original source data, saved models, final predictions and published-release
  artifacts remain fingerprint-identical.

## Still requires human action

1. Consult the instructor about the project-owner-authorized November 2 final
   evaluation, which preceded the November 4 memorandum. The same exposed test
   cannot become a new untouched test for a revised model.
2. Disclose that no pre-final hyperparameter-search history is available. Fixed
   settings are not completed tuning. Ask whether the retained experiment is
   accepted or a separate approved study and independent evaluation are needed.
3. Confirm the retained A4/justified institutional-template exception. The paper
   preserves the existing format; it does not infer approval over Letter/left
   defaults. Fresh chapter starts can leave chapter-end white space; no filler
   text or reduced type was used to force an exact page fill.
4. Complete genuine member review/contribution evidence and submission approvals.
5. Check the hosted website on the presentation computer and a mobile device.
   Native browser inspection stopped because its URL could not be reliably
   identified; no further UI control was attempted. DOM tests are not visual QA.
6. If required, demonstrate a newly installed clean environment independently.

Exact publisher version metadata and full simulator rules remain unavailable.
They are documented limitations, not values to invent.

No Supabase migration is required. Optional
`website/supabase/003_verify_revision_evidence.sql` is a read-only check of the
existing release, not an update script. Do not import the same release again.

No hosted import or redeployment was performed during this revision. The project
owner subsequently authorized local Git commits; pushing remains a separate action.
