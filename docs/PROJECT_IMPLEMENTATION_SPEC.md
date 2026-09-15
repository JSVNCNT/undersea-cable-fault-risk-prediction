# Master Project Implementation Specification

**Project:** Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators  
**Course:** Introduction to Data Science (COPE0683X), Section K44  
**Specification date:** 2026-09-16  
**Status:** Planning pass only; no analytical pipeline or model has been implemented  
**Controlling evidence reviewed:** the complete current instructor document, the complete revised proposal, the current repository, all three supplied CSV files, and live Kaggle metadata

> **STOP GATE — instructor decision required before Prelim implementation.** The live Kaggle metadata explicitly describes every observation as **100% synthetic** and procedurally generated with a fixed seed. This contradicts any treatment of the records as empirical measurements of real cable systems and materially affects compliance with the course prohibition against generated records presented as real data. The group must obtain written instructor approval to continue as a clearly labeled synthetic-data educational study, or replace the dataset with a legitimate, traceable empirical source and revise the proposal. No statistical or predictive result may be represented as evidence about real cables.

## 1. Project summary

This is a panel-classification project whose proposed unit is one cable-year record. Using information said to be available at the end of year *t*, it would predict the binary `fault_next_year` outcome for year *t + 1*. The approved analytical comparison is a majority/prior dummy baseline, logistic regression, decision tree, and random forest under chronological validation.

The proposed workflow is technically feasible on the supplied files, but the data are not empirical. The current project can proceed only through one of two instructor-approved branches:

1. **Synthetic-data branch:** Retain the title only if the paper consistently says it predicts labels in a synthetic cable-system simulation. Rewrite real-world user claims as educational/scenario-analysis claims. Preserve a prominent synthetic-data disclaimer in the paper, README, slides, tables, figures, and defense.
2. **Replacement-data branch:** Replace the dataset with a traceable empirical source, then re-audit the unit, questions, variables, target, sample size, methods, splits, and this specification before implementation. Do not assume the current model or variable plan transfers unchanged.

Until that decision is documented, implementation may create only source-verification and correction records; it must not clean data, run inferential tests, train models, or generate claimed findings.

## 2. Approved title/problem/questions/objectives

### Approved proposal title

**Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators**

Because the source is verified synthetic, the title is conditionally acceptable only if the instructor approves synthetic-data use. A safer synthetic-branch title would explicitly include “synthetic,” but changing the approved title requires instructor approval.

### General problem

Determine whether infrastructure and operational information available at the end of an observation year can distinguish cable-year records with a following-year fault label, and identify the approved classifier with the most defensible balance of fault detection, performance, stability, and interpretability under chronological testing.

### Research questions

- **RQ1:** What are the distributions and operational characteristics of cable-year observations by route, operator type, age, length, fiber pairs, landing-country count, capacity, utilization, burial protection, redundancy, vulnerability, current-year fault history, and next-year fault status?
- **RQ2:** Which selected infrastructure and operational variables are statistically associated with `fault_next_year`, accounting for variable type and repeated cable-year observations, without causal interpretation?
- **RQ3:** How well do the majority-class baseline, logistic regression, decision tree, and random forest predict the next-year label using only information available before the held-out prediction year?
- **RQ4:** Which candidate gives the most appropriate balance of precision, recall, F1, PR-AUC, ROC-AUC, error pattern, stability, and interpretability on chronologically held-out data?

### General objective

Develop and evaluate a leakage-aware, chronologically validated workflow for predicting next-year fault occurrence in the supplied cable-year records using infrastructure and operational indicators.

### Specific objectives

1. Describe the approved variables with suitable statistics and visualizations.
2. Test selected categorical and numeric associations with `fault_next_year`, and use a multivariable logistic association model with cable-cluster-aware interpretation when assumptions permit.
3. Prepare a leakage-aware analytical dataset by validating prediction timing and the forward label, separating unlabeled rows, handling missingness, encoding categories, auditing redundant/derived variables, and learning preprocessing from training data only.
4. Train the majority/prior baseline and the three approved classifiers with chronological development and tuning.
5. Compare locked candidates using required metrics and interpretation evidence; document errors, uncertainty, limitations, and responsible-use boundaries.

### Intended users, beneficiaries, and boundary

The proposal names cable operations/reliability teams, carrier and hyperscaler resilience planners, public-sector infrastructure analysts, researchers, and IT students. With the verified synthetic source, only educational method demonstration and synthetic scenario analysis are supportable. The data cannot support maintenance, routing, investment, regulatory, safety, or engineering decisions about any real asset.

## 3. Course requirements summary

The current instructor file is `2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx`. Its Word metadata reports **163 pages**, not the 164 pages anticipated in the planning brief. The document was reviewed through its complete OOXML text, including General Instructions, proposal, Prelim, Midterm, Final, rubrics, suggested-project guidance, and APA/AI rules.

The controlling requirements are:

- Maintain one integrated, approved project through the semester; do not change the problem, dataset, questions, objectives, target, or major direction without approval.
- Use Python as the primary language and maintain a clean-copy-reproducible workflow with no personal paths, credentials, hidden steps, or manual result copying.
- Use a legitimate, traceable, ethically obtained dataset with at least 1,000 usable observations unless an alternative is approved. Do not present generated data as real observations.
- Preserve the untouched raw source; save each cleaned/model-ready stage as a new documented version.
- Document source, access date, owner/custodian, coverage, unit, original dimensions, license/use conditions, quality limitations, and hashes/version notes.
- Audit missingness, duplicates, types, ranges, invalid/impossible values, categories, units, dates/periods, outliers, imbalance, conflicting sources, and leakage. Justify every treatment.
- Generate numbered, titled, labeled, sourced, interpreted, code-reproducible tables and figures tied to a research question.
- Match statistical methods to questions and assumptions; report hypotheses where applicable, alpha, test statistic, degrees of freedom where applicable, p-value, effect size/practical importance, 95% CI, contextual conclusion, and limitations. Association is not causation.
- Split before learned preprocessing. Fit imputers, encoders, scalers, feature selection, class treatment, tuning, and threshold selection on development data only. Use chronological splitting for time-dependent data.
- Include a defensible baseline and only approved candidate models. Compare on identical partitions and procedures. Do not select solely by the highest score.
- Keep the final test separate and use it once after the complete model/threshold decision is locked. A disappointing test result must not trigger retuning.
- Complete error, interpretation, robustness, subgroup/bias, ethics, privacy, and responsible-use reviews.
- Maintain correction and contribution records, meaningful version history, supporting technical files, printed/digital consistency, defense slides, runnable demonstrations, and individual preparedness.
- Complete one six-chapter paper, with APA 7 citations/references and verified sources. Report unexpected results honestly and disclose AI assistance when required.

## 4. Prelim deliverables

Prelim is approximately 50% of the foundation. Required or planned deliverables are:

- Corrected and instructor-approved proposal, including the synthetic-data decision.
- Printed Prelim documentation: cover, TOC, Chapter 1, Chapter 2, initial Chapter 3, dictionary, quality report, raw-versus-cleaned summary, descriptive results, EDA figures, correction records, contribution record, and printed rubrics.
- Source record and official Kaggle metadata snapshot; raw files only where permitted.
- Untouched raw source files plus hashes and immutable-source rules.
- Versioned cleaned dataset created by code, only after the source gate is approved.
- Complete, updated data dictionary.
- Data-quality and forward-target audit, including the six observed year gaps.
- Reproducible source/audit, cleaning, and EDA notebook/script work; no modeling or final model selection.
- Descriptive statistics, initial EDA, target feasibility/imbalance assessment, ethics/privacy/governance assessment, and leakage inventory.
- README/environment setup sufficient to reproduce Prelim.
- Defense slides, live technical demonstration, backups, group contribution record, proposal correction record, and Prelim consultation/defense correction record.
- If required, complete defense recording named per instructor rules; screenshots are not a substitute for execution.

Prelim technical demonstration must import raw data, show dimensions/types/missingness/duplicates, demonstrate selected coded cleaning, create the cleaned version, compare raw and cleaned data, reproduce statistics/figures, trace one record, run from a clean copy, and permit a minor correction.

## 5. Midterm deliverables

Midterm is approximately 75% complete and must include:

- All Prelim corrections and an updated correction record.
- A newly versioned finalized cleaned dataset; do not overwrite the Prelim version.
- A versioned model-ready dataset or reproducible materialization procedure.
- Updated dictionary and quality report consistent with data, code, paper, and slides.
- Expanded development-only EDA and multicollinearity review.
- Statistical plan mapped to RQ2, assumption results, effect sizes, 95% CIs, p-values, and contextual interpretations.
- Leakage-safe feature preparation; saved split indices/manifests and partition counts.
- Majority/prior baseline, logistic regression, decision tree, and random forest on identical chronological partitions.
- Development-only temporal cross-validation/tuning, untuned-versus-tuned records, initial comparison, error analysis, interpretation, and responsible-use review.
- Revised Chapters 1–2, completed Chapter 3, and initial Chapter 4.
- Complete notebooks/scripts for work performed, requirements/environment record, generated outputs, README/execution guide, Midterm slides/demo, updated contribution log, and Midterm consultation/defense correction record.

## 6. Final deliverables

Final is 100% complete and must include:

- Every Prelim/Midterm correction and the final correction record.
- Complete six-chapter paper with verified APA 7 citations and matching evidence.
- Final source record; final cleaned and model-ready versions; final dictionary and quality report.
- Complete Python workflow and final statistical results.
- Locked preprocessing pipeline, split manifest, baseline/candidates, validation and tuning records, fair comparison, selection record, and one-time untouched-test evaluation.
- Confusion matrices, precision, recall, F1, ROC-AUC, PR-AUC, and accuracy as secondary context; raw predictions and metric outputs generated by code.
- Final error analysis, model interpretation, robustness/stability review where justified, operational subgroup review, ethics/privacy assessment, and responsible-use boundaries.
- Saved final preprocessing pipeline and selected model when applicable, with encoders/scalers, final feature list, category mappings, parameters, version/date, metrics, and library versions.
- README and execution guide; final figures/tables; final presentation; clean-copy technical demonstration; final contribution log; final defense correction log; and required printed/digital files and rubrics.

## 7. Dataset inventory

### Current repository files

| Path | Type | Size (bytes) | Current role/status |
|---|---:|---:|---|
| `.gitignore` | text | 0 | Tracked but empty; does not exclude `.venv`, secrets, caches, or outputs. |
| `2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx` | DOCX | 250,673 | Latest instructor document found; currently untracked; Word metadata says 163 pages. |
| `Undersea_Cable_Fault_Risk_Project_Proposal_REVISED (1).docx` | DOCX | 131,159 | Current revised/approved analytical specification; tracked. |
| `README.md` | Markdown | 5,841 | Preliminary README; source warning is now stale because synthetic status is verified. |
| `requirements.txt` | text | 4,616 | Full environment freeze for Python 3.13-era venv; must later be tested/minimized or deliberately retained. |
| `UnderseaCableRisk/undersea_cables_master.csv` | CSV | 510,525 | Master cable-year dataset; tracked; SHA-256 `091DC4AE90F0D7DD615318BC58F002542ADDC3BFF2E4C09CA3F4E5A7498A41B4`. |
| `UnderseaCableRisk/cables_reference.csv` | CSV | 27,309 | Static cable/reference dataset; tracked; SHA-256 `2965659E4B1663922A0155BD7BA55A4385279D6A9FC7C7CD02C15E8435F7D09F`. |
| `UnderseaCableRisk/data_dictionary.csv` | CSV | 1,349 | 21-row dictionary; tracked; SHA-256 `AD4A16734A61E25FA1C663545B0CB711666859B119B635AD7D8082CD4E7AABCB`. |

No XLSX/XLS, IPYNB, or PY files currently exist outside `.venv`. Existing project directories are `data/raw`, `data/processed`, `docs`, `notebooks`, `outputs/figures`, `outputs/models`, `outputs/tables`, `src`, and `UnderseaCableRisk`; all planned analytical/code directories are currently empty. The repository-local `.venv` reports Python 3.13.14 but is machine-specific and must not be committed.

### CSV schemas

| File | Dimensions | Columns / inferred CSV types |
|---|---:|---|
| `undersea_cables_master.csv` | 4,821 × 21 | `year` int; `cable_id` string; `ocean_route` string; `operator_type` string; `rfs_year` int; `age_years` int; `fiber_pairs` int; `length_km` float; `n_landing_countries` int; `chokepoint` string; `design_capacity_tbps` float; `lit_capacity_tbps` float; `utilization_pct` float; `protected_burial` int; `design_life_years` int; `route_redundancy` int; `is_low_redundancy` int; `vulnerability_index` float; `fault_cause` string; `fault_this_year` int; `fault_next_year` float/nullable. |
| `cables_reference.csv` | 500 × 8 | `cable_id` string; `ocean_route` string; `operator_type` string; `rfs_year` int; `fiber_pairs` int; `length_km` float; `n_landing_countries` int; `chokepoint` string. |
| `data_dictionary.csv` | 21 × 3 | `column`, `type`, `description`, all strings. |

## 8. Verified dataset facts

### A. Verified facts

- Master dimensions are 4,821 rows × 21 columns, with 500 unique `cable_id` values and years 2015–2026.
- `cable_id + year` is unique; there are zero exact duplicate rows.
- `fault_next_year` has 4,321 labeled rows and 500 blanks: 820 positives and 3,501 negatives; positive prevalence is **18.9771%**.
- Proposed split counts before any approved treatment are exact: training 2015–2022 = 2,960 labeled/570 positive; validation 2023–2024 = 897 labeled/172 positive; final test 2025 = 464 labeled/78 positive.
- All 500 blank targets are the last available observation for their cable. They occur in 2023 (1), 2024 (2), 2025 (15), and 2026 (482), so “blank only for 2026” is false.
- Six cables have a missing calendar year between observed rows: `CAB0035`, `CAB0084`, `CAB0102`, and `CAB0317` skip 2025; `CAB0037` and `CAB0219` skip 2024. No other within-cable gaps were found.
- For consecutive observations, `fault_next_year` exactly matches the following row’s `fault_this_year`. The six pre-gap labels also happen to match the next observed row two years later, but the intended *next calendar year* outcome cannot be verified because that row is absent.
- Only `fault_next_year` is structurally blank. `chokepoint` contains no blanks; the literal category `None` appears 3,986 times.
- `design_life_years` is constant at 25 and provides no model discrimination.
- `age_years = year - rfs_year` for every row; keeping all three as predictors would be exact redundancy.
- `route_redundancy` equals the count of records in the same `year × ocean_route` group for every row.
- `is_low_redundancy` is exactly `1(route_redundancy < 40)` for every row. The dictionary calls it “bottom-quartile” but does not document why 40 is the threshold or whether future years were used to set it.
- `fault_cause = none` exactly when `fault_this_year = 0`; a non-`none` cause appears exactly when the current-year fault is 1.
- All static fields in the 500-row reference file match the corresponding master rows; all master IDs have exactly one reference record.
- The dictionary has one entry for each master column and no extras.
- Basic range checks found no nonpositive lengths/counts/capacities, no `rfs_year > year`, no utilization outside 0–100, no vulnerability value outside 0–100, and no lit capacity above design capacity.
- Capacity relationships: design capacity is constant within every cable; lit capacity varies over time for 392 cables; lit capacity is positively correlated with design capacity (Pearson `r = 0.8128`) and never exceeds it. `utilization_pct` is not simply `100 × lit/design` (mean absolute difference 23.09 percentage points; correlation 0.5276), so its precise definition requires source documentation.
- Categorical values are internally consistent with the supplied dictionary/proposal: nine routes; four operator types; eight chokepoint values including `None`; five fault-cause values; binary 0/1 flags.
- The live Kaggle metadata (version 1, last updated 2026-07-13) names Sergey Nefedov/`sergionefedov` as creator, specifies CC0, and explicitly states all records are synthetic and generated with a fixed seed.

### B. Proposal claims not yet fully verified

- The formula and input timing for `vulnerability_index` are not provided. Kaggle calls it a computed exposure score, which does not prove it is target/future-safe.
- The simulator code and fixed seed are not supplied in this repository, so the raw records cannot be regenerated from primary code.
- The exact construction of capacity, fault probability, row omissions, the `<40` low-redundancy threshold, and the six time gaps is undocumented.
- The claimed calibration references should be verified individually if discussed, but Kaggle states they informed simulator design and were not reproduced as observations.
- Instructor approval status for fully synthetic observations is not present in the repository.

### C. Data-quality concerns

- Six missing cable-year periods make six nominal next-year labels unverifiable against the next calendar year.
- Five hundred missing labels are structurally expected final observations, but 18 occur before 2026 and must not be casually described as 2026-only missingness.
- `None` in `chokepoint` is a real string category, not a blank. It should be normalized only for presentation consistency, not imputed as missing.
- Constant `design_life_years`; exact age/year/RFS redundancy; highly related design/lit capacity; deterministic redundancy features; conditional `fault_cause`; and broad synthetic categories require explicit treatment.
- Several variables contain rounded/generated quantities, and external empirical accuracy cannot be evaluated.

### D. Leakage concerns

- `fault_next_year` is a forward target derived from future `fault_this_year`; it must never appear among predictors or in learned preprocessing.
- `vulnerability_index` is unresolved and must be excluded from primary modeling until its formula/timing is verified.
- `is_low_redundancy` is derived from `route_redundancy` using a global undocumented threshold. Recompute inside a training-safe process or exclude it; do not use the supplied flag blindly.
- `route_redundancy` uses the complete route-year cross-section. It is permissible only if that cross-sectional count would truly be available at the end of year *t*; otherwise exclude.
- `fault_cause` almost encodes the same current-year event as `fault_this_year`. Exclude it from the primary model; consider only a separately approved sensitivity analysis with an explicit end-of-year prediction point.
- Full-dataset target-aware EDA/statistics before model lock could leak information from the 2025 final test into feature/model choices. Restrict outcome-aware development work to 2015–2024.
- Repeated cables across years are intended for forecasting known synthetic cables, but no cable-specific target encoding, aggregates using future years, or `cable_id` predictor is allowed.

### E. Source/provenance/license concerns

- The observations are confirmed synthetic, not empirical. This is a course-compliance and external-validity issue, not merely a caveat.
- The Kaggle page claims calibration to TeleGeography, CRS, and ICPC summaries but states no source data are reproduced. These organizations are contextual references, not upstream empirical custodians of these rows.
- CC0 permits copying, modifying, and distributing the work, including commercially, without permission. Therefore raw-file redistribution in a public Git repository is license-permitted based on the current metadata. Course citation, accurate provenance, non-endorsement, and repository policy still apply.
- The current CSVs are already tracked in Git. Do not describe them as confidential or empirical.

## 9. Unresolved source/license/provenance issues

### Source-verification checklist

- [x] Record dataset title: *Undersea Cables & Global Digital Infrastructure*.
- [x] Record Kaggle owner/creator: Sergey Nefedov (`sergionefedov`).
- [x] Record current Kaggle version and update date: version 1; 2026-07-13.
- [x] Record exact current license: **CC0: Public Domain**.
- [x] Confirm CC0 redistribution terms from Creative Commons: copying, modification, and distribution are permitted without permission; do not imply endorsement.
- [x] Determine whether only IDs are pseudonymized: **No.** Kaggle explicitly says all observations are synthetic.
- [x] Determine whether observations are empirical: **No.** Every row is described as procedurally generated with a fixed seed.
- [x] Determine public Git raw-data posture: permitted under current CC0 metadata, with dataset citation and synthetic disclaimer.
- [ ] Save a dated PDF/screenshot or JSON snapshot of the Kaggle metadata to `docs/source_record/` during implementation.
- [ ] Record access/download requirements and access date in the source record.
- [ ] Record whether the original Kaggle archive is available and hash it; it is not currently present.
- [ ] Verify that local CSV hashes match a freshly downloaded Kaggle version 1 archive.
- [ ] Verify each simulator-calibration source if used in narrative claims; do not treat it as row-level provenance.
- [ ] Obtain written instructor decision: approved synthetic educational analysis **or** empirical dataset replacement.
- [ ] If approved synthetic, revise proposal/title/user claims/SDG contribution and log corrections.
- [ ] If replacement is required, stop and re-plan after inspecting the replacement source.

Primary online records: [Kaggle dataset page](https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure), [Kaggle public metadata API](https://www.kaggle.com/api/v1/datasets/view/sergionefedov/undersea-cables-and-global-digital-infrastructure), and [CC0 1.0 deed](https://creativecommons.org/publicdomain/zero/1.0/).

## 10. Variable decision table

All statuses are provisional until the source gate and six-gap target treatment are approved.

| Variable | Planned status | Decision and reason |
|---|---|---|
| `year` | time/index variable; candidate predictor under review | Required for splitting and trend analysis. Including raw year may model simulator drift; compare a model without it and never scale/derive it using future data. |
| `cable_id` | identifier/grouping variable; exclude predictor | Use for uniqueness checks, clustered inference/bootstrap, traceability, and grouped sensitivity only. It is synthetic and could act as a memorization key. |
| `ocean_route` | predictor/grouping variable | One-hot encode with unknown handling; broad synthetic route categories may hide heterogeneity. |
| `operator_type` | predictor/grouping variable | One-hot encode; synthetic category, not a named organization. Use for subgroup error review if counts permit. |
| `rfs_year` | redundant/review; likely exclude primary | Exact relation `rfs_year = year - age_years`; primary plan retains `age_years`, not both. |
| `age_years` | predictor | Interpretable end-of-year feature; verify nonlinear form for logistic model without using test data. |
| `fiber_pairs` | predictor | Positive count; correlated with capacity/generation; retain subject to development-only collinearity review. |
| `length_km` | predictor | Positive continuous variable; inspect skew/outliers and transformations on training only. |
| `n_landing_countries` | predictor | Count feature; broad proxy, not exact landing geography. |
| `chokepoint` | predictor | Contains literal `None`, not missing. One-hot encode; rare levels require fold/count review. |
| `design_capacity_tbps` | predictor/redundancy review | Constant within cable and correlated with lit capacity. Consider log transform and collinearity alternatives using development data only. |
| `lit_capacity_tbps` | predictor/redundancy review | Time-varying and never above design capacity; compare with design/utilization for redundancy. |
| `utilization_pct` | predictor; definition review | Range 1–100, not equal to lit/design ratio. Retain only with clear definition and synthetic limitation. |
| `protected_burial` | predictor | Binary synthetic protection indicator; no depth/method detail. |
| `design_life_years` | likely exclusion | Constant at 25 in all 4,821 rows. Keep in dictionary/audit, omit from model matrix. |
| `route_redundancy` | derived predictor requiring audit | Exactly route-year row count. Retain only if full same-year cross-section is available at prediction time; document construction. |
| `is_low_redundancy` | likely exclusion / rederive training-safely | Exact duplicate threshold feature `route_redundancy < 40`; undocumented “bottom-quartile” rule may use future data and duplicates its parent. |
| `vulnerability_index` | unresolved; exclude primary | Formula unavailable; possible target/future leakage and synthetic composite. May be used only after formula and timing are verified, preferably as sensitivity rather than primary input. |
| `fault_cause` | leakage/duplication risk; exclude primary | Non-`none` exactly signals `fault_this_year = 1`; cause is conditional post-event information. |
| `fault_this_year` | predictor/history variable | Allowed only because prediction point is end of year *t*. Keep explicit timing; no future shift or aggregate. |
| `fault_next_year` | target | Binary supervised target. Exclude 500 structural blanks; six pre-gap labels require instructor-approved treatment. |

## 11. Data-quality plan

`01_source_and_data_audit.ipynb` and `src/data_validation.py` will create an auditable, assertion-based report before cleaning:

1. Verify filenames, sizes, SHA-256 hashes, schemas, encoding, dimensions, key uniqueness, row duplicates, ordering, memory use, head/tail, and dictionary coverage.
2. Profile missingness as blank, null, sentinel, and literal category separately; specifically preserve the distinction between blank and `None`.
3. Validate numeric domains, binary values, category sets/case/whitespace, units, year/RFS/age relations, static reference consistency, and capacity constraints.
4. Validate panel continuity per cable and list every gap and final observation.
5. Validate the forward label only against the next calendar year, not merely the next row. Mark the six gap-preceding labels as unresolved/invalid for next-calendar-year prediction until approved.
6. Audit class counts overall and by development partition without using final-test feature/outcome relationships.
7. Audit each derived variable’s formula, input timing, and dependence on full data/future years.
8. Produce machine-readable validation results and a narrative report with issue, detection rule, affected count, risk, proposed treatment, approval status, and post-treatment check.

No outlier will be removed automatically. Synthetic but valid extreme values will be retained unless a documented rule proves invalidity; robust summaries/transforms are preferred to deletion.

## 12. Cleaning plan

Cleaning begins only after instructor approval of the data-source branch. It must be deterministic and preserve row-level lineage.

- Read only from the immutable source path; never edit CSVs in Excel.
- Normalize column whitespace/case only if actual anomalies are found; keep original names because they already match the dictionary.
- Parse integer, float, category, and nullable target types explicitly; assert conversion success.
- Keep `chokepoint="None"` as an explicit category; optionally display as `No named chokepoint` while retaining a documented mapping.
- Keep all valid ranges and unexpected values; do not winsorize by default.
- Exclude `design_life_years` from modeling but retain it in the cleaned dataset and dictionary with a constant-feature flag.
- Preserve all 500 structural unlabeled rows in a separate eligibility flag/table; do not impute their target.
- For the six gap-preceding labels, preferred technical treatment is to mark the target unavailable for next-calendar-year modeling because the required following year is absent. This change needs instructor approval because it changes the proposal’s validation count.
- Add audit columns only to interim outputs (for example, `source_row_id`, `label_eligible`, `exclusion_reason`); do not silently alter the semantic variables.
- Save an immutable versioned cleaned file plus manifest containing source hashes, code version, timestamp, row/column counts, exclusions, and validation status.

## 13. EDA plan

RQ1 EDA will use the cleaned dataset, with outcome-aware work restricted to 2015–2024 until the final model is locked.

- Counts of rows/unique cables by year, route, operator, label availability, and label.
- Missingness/structural-unavailability table and panel coverage/gap visualization.
- Numeric summaries: count, mean, SD, median, IQR, min/max, and selected quantiles for age, length, fiber pairs, landings, capacities, utilization, redundancy, and vulnerability (the latter labeled unresolved).
- Categorical frequencies and percentages for route, operator, chokepoint, burial, current fault/cause, and next-year label.
- Histograms/ECDFs or carefully justified density plots; box/violin plots by development label; route/operator stacked proportions; annual prevalence trends; correlation/Spearman matrix for numeric predictors; missingness and redundancy diagrams.
- Compare design versus lit capacity and utilization without claiming utilization is their ratio.
- Separate data-quality figures from substantive figures. Every final table/figure gets number, title, labels/units, note/source, sample size, and a paragraph stating pattern, RQ link, limitation, and next decision.
- After final test evaluation, `08_final_analysis.ipynb` may generate full-period descriptive summaries, clearly labeled post-lock and never used to revise the model.

## 14. Statistical-analysis plan

### Mapping to questions

- **RQ1 / Objective 1:** descriptive estimates and 95% CIs where useful; no hypothesis fishing.
- **RQ2 / Objective 2:** predefined categorical and numeric association analyses plus an adjusted logistic association model.
- **RQ3–RQ4:** predictive evaluation, not inferential association testing.

### Procedures

- Set two-sided `alpha = 0.05` before analysis. Report exact p-values, estimates, effect sizes, 95% CIs, and practical meaning. If many exploratory univariate tests are retained, propose Benjamini–Hochberg correction as a sensitivity and obtain instructor confirmation.
- Categorical predictors: contingency tables; Pearson chi-square when expected counts are adequate; report expected-count diagnostics and Cramér’s V. For sparse tables, use an exact/Monte Carlo alternative appropriate to table size or combine levels only with a domain/documented rule. Do not pretend ordinary Fisher’s exact directly handles arbitrary large tables without an implementation decision.
- Numeric predictors by binary outcome: inspect distribution, skew, outliers, and group sizes. Use Welch’s t-test with Hedges’ *g* if mean-based assumptions are reasonable; otherwise Mann–Whitney with rank-biserial correlation/Cliff’s delta. Because rows repeat by cable, treat these row-level tests as exploratory unless a clustered bootstrap or cable-level design is used.
- Multivariable logistic association model: development years only; exclude identifiers, unresolved leakage variables, and exact redundancy. Check linearity of the logit for continuous terms, multicollinearity, sparse levels, separation, influential observations, and specification. Report adjusted odds ratios with 95% cluster-robust CIs by `cable_id` where statsmodels supports the fitted specification. If cluster-robust estimation is unstable, report the limitation and consider instructor-approved GEE/sensitivity analysis rather than silently reverting to independent rows.
- Repeated observations: use cable-clustered SE/cluster bootstrap where feasible and explicitly distinguish a population-average synthetic association from a causal effect.
- Maintain a statistical decision register: question, variables, test, assumptions, diagnostics, fallback, estimate, CI, p-value, effect size, conclusion, limitation, and output path.

## 15. Feature-preparation plan

- Create an explicit eligibility mask before `X/y` construction.
- Use a scikit-learn `ColumnTransformer` inside each model `Pipeline`.
- Categorical: `SimpleImputer(strategy="most_frequent")` only if training data actually contain missing categories, then `OneHotEncoder(handle_unknown="ignore")`. Preserve category mappings.
- Numeric: training-fitted median imputation only if needed. Standardize numeric features for logistic regression. Do not scale merely for trees.
- Assess log transforms for skewed positive quantities using development data; apply a fixed `log1p` transform only if documented and applied identically across candidates where fairness requires it.
- Exclude `cable_id`, target, constant feature, unresolved composite, and primary-excluded cause/duplicate features.
- Keep feature names retrievable after transformation and save the ordered feature list.
- Compare a compact primary feature set with limited, predeclared sensitivity sets; do not conduct target-driven feature fishing on validation/test data.

## 16. Leakage-prevention plan

1. Define prediction timestamp: immediately after year *t* data are complete, before any year *t + 1* event.
2. Freeze raw hashes and row IDs.
3. Separate development (2015–2024) and final test (2025) before outcome-aware EDA or learned transformations.
4. Exclude 2026 unlabeled rows from supervised modeling; preserve for provenance only.
5. Fit every learned transform inside a pipeline on the current training fold.
6. Never derive thresholds, category grouping, imputations, scaling, feature selection, class weights, or probability thresholds from final-test information.
7. Compute time-derived features per row using data available through that row only; use `.shift(1)`/expanding windows with explicit assertions when histories are introduced. No future-centered rolling windows.
8. Exclude `cable_id`; prohibit target encoding and full-panel cable summaries.
9. Audit `route_redundancy`, `is_low_redundancy`, `vulnerability_index`, `fault_cause`, and the forward-label shift separately.
10. Save split manifests and automated assertions proving disjoint row IDs, allowed years, target exclusion, and transform fit boundaries.

## 17. Data-versioning plan

Use immutable, manifest-backed semantic versions:

- `UnderseaCableRisk/*.csv`: existing untouched source-of-record; never rename or overwrite.
- `data/raw/manifest_kaggle_v1.json`: hashes, metadata snapshot path, access date, license, synthetic status, and mapping to existing raw files. Do not duplicate raw files unless the group deliberately chooses a canonical copy and documents both hashes.
- `data/interim/cable_year_audit_v1.parquet` or CSV: audit flags only; reproducibly generated.
- `data/processed/cable_year_clean_prelim_v1.csv`.
- `data/processed/cable_year_clean_midterm_v2.csv`.
- `data/processed/cable_year_clean_final_v3.csv`.
- `data/model_ready/model_ready_midterm_v1.*` and `model_ready_final_v2.*`, plus feature/split manifests.

Each manifest records source hashes, generator notebook/script, Git commit when available, creation time, schema, counts, exclusion/treatment totals, and validation result. Never overwrite a submitted version; increment it and update the correction record.

## 18. Chronological splitting strategy

Starting plan, subject to approved treatment of the six gap labels:

| Partition | Years | Current labeled rows | Current positives | Purpose |
|---|---:|---:|---:|---|
| Training | 2015–2022 | 2,960 | 570 | Preprocessing fit and expanding-window tuning. |
| Validation/model selection | 2023–2024 | 897 | 172 | Locked candidate/threshold comparison after inner tuning. Six labels are unresolved. |
| Final test | 2025 | 464 | 78 | One-time 2026-label evaluation after full lock. |
| Unlabeled | Mainly 2026, plus earlier final rows | 500 | N/A | Preserve; never use as labeled examples. |

Within training, use expanding-window folds such as train through 2018→validate 2019, then through 2019→2020, through 2020→2021, and through 2021→2022, after checking each fold’s class counts. Do not use ordinary shuffled CV.

The same cable may appear in earlier and later chronological partitions because the intended task is forecasting an existing cable’s future state. This is compatible only if `cable_id`, future aggregates, and cable target encodings are excluded. Add a secondary group-held-out sensitivity analysis, if sample sizes allow, to measure generalization to unseen synthetic cable IDs; it does not replace the primary chronological design.

After model/threshold lock, refit the selected pipeline on 2015–2024 only, using locked settings, then evaluate 2025 once. Save exact row IDs and class counts.

## 19. Baseline plan

Use `DummyClassifier(strategy="prior")`. Its hard prediction is the training majority class while its probability is the training prior, matching the proposal’s intended majority/prior reference. Fit it in the same pipeline framework and temporal folds, and evaluate it with every required metric. Its accuracy may look high while recall/F1 for faults is zero; this is precisely why accuracy is secondary. Preserve its predictions and metrics in all comparison tables.

## 20. Logistic Regression plan

- Pipeline: categorical one-hot encoding; numeric imputation/scaling; `LogisticRegression` with L2 regularization and fixed solver/seed where applicable.
- Initial grid: `C ∈ {0.01, 0.1, 1, 10, 100}`, `class_weight ∈ {None, "balanced"}`; keep solver/max iterations constant and documented.
- Check convergence, coefficient stability, collinearity, separation symptoms, and validation drift.
- Interpretation: transformed feature coefficients and odds ratios with clear reference categories. Predictive coefficients are not causal effects; do not substitute scikit-learn coefficients for the cluster-robust inferential model without explanation.

## 21. Decision Tree plan

- Pipeline uses the same eligible raw predictors/partitions; one-hot categories; no required scaling.
- Initial grid: `criterion ∈ {"gini", "entropy"}`, `max_depth ∈ {3, 5, 8, 12, None}`, `min_samples_split ∈ {2, 10, 25, 50}`, `min_samples_leaf ∈ {1, 5, 10, 25}`, and `class_weight ∈ {None, "balanced"}`. Reduce only for compute limits and record the change.
- Evaluate overfitting using training-versus-temporal-validation gaps and tree complexity.
- Interpretation: limited-depth rendered tree/rules for the selected setting; do not present a massive tree as explanatory evidence.

## 22. Random Forest plan

- Pipeline uses the identical eligible features/partitions; fixed `random_state`; parallelism documented.
- Search `n_estimators` around 300–500, `max_depth` among constrained values plus `None`, `min_samples_leaf`, `max_features`, and `class_weight` (`None`, `balanced`, or `balanced_subsample`).
- Prefer a documented randomized search with a fixed candidate budget to uncontrolled grid expansion.
- Check out-of-time stability and training/validation gap. Interpret with held-out permutation importance, not impurity importance alone; label correlated-feature dilution.

## 23. Hyperparameter-tuning plan

- Tune within 2015–2022 using expanding-window folds and pipeline-contained preprocessing.
- Use PR-AUC/average precision as the primary search score because the positive class is about 19%; store all fold scores and variability.
- Preserve default and tuned results. Limit the search space to proposal-approved hyperparameters and document seeds, library versions, candidate count, runtime, and failures.
- Compare tuned candidates on the same 2023–2024 validation rows. Do not repeatedly alter grids after seeing that holdout.
- Use the default 0.50 threshold for probability-model comparison. Any alternative operating threshold must have an instructor/decision-cost rationale, be selected on validation only, be logged, and be locked before test.
- Do not use oversampling in the primary plan. Compare class weights only when justified; any later resampling requires approval and fold-internal application.

## 24. Evaluation plan

For each baseline/candidate on identical validation/test partitions, generate:

- confusion matrix with TN/FP/FN/TP counts;
- precision, recall, F1, ROC-AUC, PR-AUC/average precision, and accuracy as secondary context;
- class prevalence and threshold used;
- temporal-fold mean, SD/range, and preferably cluster-bootstrap 95% CIs on validation; test CIs by cable/row bootstrap because 2025 has one row per included cable;
- training versus validation performance, runtime where meaningful, model complexity, interpretability, and error consequences;
- calibration plot/Brier score as a supporting probability-quality diagnostic if included consistently and approved, not as a new selection target.

All values must be exported from code to raw JSON/CSV and presentation tables; no hand-copied numbers.

## 25. Final-model-selection rule

Pre-register this rule before viewing final-test performance:

1. Disqualify any model with leakage, failed execution, degenerate minority detection, or unacceptable instability.
2. Primary rank is development temporal-CV and 2023–2024 validation PR-AUC.
3. Use recall, precision, F1, ROC-AUC, calibration, error consequences, temporal variability, and training/validation gap as supporting evidence.
4. When performance is practically indistinguishable within uncertainty, choose the simpler and more interpretable stable model (normally logistic regression before tree/forest).
5. Record the chosen hyperparameters, feature set, preprocessing, threshold, rationale, rejected alternatives, and approval date before test evaluation.

No model is presumed best. A candidate need not be selected merely because it has the largest point estimate.

## 26. Untouched-final-test rule

The 2025 final-test labels may be used now only for source/schema/quality and predeclared class-count confirmation. Before development begins, seal their row IDs and hash. Do not run outcome-aware plots, associations, feature selection, tuning, threshold selection, or candidate comparisons on 2025. After the selection record is signed, run one final evaluation. Preserve predictions and do not retune, switch models, or change cleaning because of the result. Any code correction after unblinding must be documented and, if it can change results, reviewed by the instructor.

## 27. Error-analysis plan

- Preserve row-level validation/final predictions with row ID, year, true label, score, threshold, and error type.
- Compare false negatives and false positives by route, operator, chokepoint, burial, age band, current fault, and other adequately sized groups.
- Examine whether gaps, rare categories, extreme synthetic values, missingness treatment, class imbalance, or omitted variables explain patterns.
- Identify recurring conditions, practical implications in the synthetic scenario, cases requiring human review, and what the model cannot predict.
- Never remove difficult observations to improve metrics. Keep subgroup tables suppressed/qualified when cell counts are too small.

## 28. Model-interpretation plan

- Logistic: standardized coefficient direction, magnitude, odds ratio, reference level, and uncertainty where obtained from the inferential model.
- Decision tree: depth, leaves, top rules, and representative paths.
- Random forest: validation/test permutation importance with repeated shuffles and variability; optionally partial-dependence plots only for a small approved set after checking feature dependence.
- Compare interpretations with development EDA and statistical results. Explain disagreements, correlation effects, synthetic construction, instability, and non-causality.
- Provide one traceable observation walkthrough through raw values, preprocessing, transformed features, probability, threshold, and predicted class.

## 29. Robustness/stability plan

- Report fold/year variation and validation-to-test change.
- Compare default versus class-weighted versions and 0.50 versus any locked operating threshold.
- Check coefficient/importance rank stability and tree structural instability.
- Conduct a sensitivity excluding `year`, capacity alternatives, route-derived features, current fault history, and unresolved composite features—predeclared and development-only.
- Add group-held-out-cable sensitivity if feasible to distinguish known-cable forecasting from unseen-cable generalization.
- Assess influential observations for the association model. Do not claim robustness without evidence or when the synthetic/gap limitations dominate.

## 30. Bias/ethics/responsible-use plan

- No direct personal data are present; privacy risk is low. Still keep repositories credential-free and protect any later replacement dataset according to its terms.
- Bias sources are simulator assumptions, route/operator representation, broad categories, omitted engineering/environmental factors, constructed labels, and undocumented composites.
- Route/operator performance is an operational subgroup analysis, not demographic fairness. Report sample sizes and uncertainty.
- Intended use: education, reproducible methods, and synthetic scenario analysis if approved.
- Prohibited use: real cable fault warnings, maintenance/routing/investment decisions, national infrastructure ranking, regulatory enforcement, safety certification, or claims about named operators/countries.
- Require domain-expert review, authenticated empirical data, external validation, monitoring, security controls, and retraining rules before any real deployment.
- Cite AI assistance when required; the group must understand and defend every submitted line of code/text. Preserve inconvenient results.

## 31. Repository structure

Do not move or rename existing original files. Build around them:

```text
undersea-cable-fault-risk-prediction/
├── 2026-2027 INTRODUCTION TO DATA SCIENCE PROJECT.docx
├── Undersea_Cable_Fault_Risk_Project_Proposal_REVISED (1).docx
├── UnderseaCableRisk/                 # existing immutable source-of-record
│   ├── undersea_cables_master.csv
│   ├── cables_reference.csv
│   └── data_dictionary.csv
├── data/
│   ├── raw/                           # metadata/archive/hash manifest; no altered data
│   ├── interim/                       # audit flags and lineage products
│   ├── processed/                     # versioned cleaned datasets
│   └── model_ready/                   # versioned eligible/model-ready data + manifests
├── notebooks/
│   ├── 01_source_and_data_audit.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_exploratory_analysis.ipynb
│   ├── 04_statistical_analysis.ipynb
│   ├── 05_feature_preparation.ipynb
│   ├── 06_model_development.ipynb
│   ├── 07_model_evaluation.ipynb
│   └── 08_final_analysis.ipynb
├── src/
│   ├── config.py
│   ├── data_loading.py
│   ├── data_validation.py
│   ├── preprocessing.py
│   ├── statistics.py
│   ├── modeling.py
│   ├── evaluation.py
│   └── visualization.py
├── outputs/
│   ├── figures/
│   ├── tables/
│   ├── metrics/
│   ├── models/
│   └── predictions/
├── docs/
│   ├── PROJECT_IMPLEMENTATION_SPEC.md
│   ├── source_record/
│   ├── data_quality/
│   ├── methodology/
│   ├── ethics/
│   ├── corrections/
│   ├── contributions/
│   └── validation/
├── reports/
│   ├── paper/
│   ├── prelim/
│   ├── midterm/
│   └── final/
├── README.md
├── requirements.txt
└── .gitignore
```

## 32. Notebook responsibilities

| Notebook | Responsibility | Stage/output |
|---|---|---|
| `01_source_and_data_audit` | Enforce source gate; inventory/hashes; schema/key/missing/gap/target/derived-variable audit; produce source and quality evidence. | Prelim; source record, audit tables. |
| `02_data_cleaning` | Apply approved, logged treatments; produce lineage, cleaned version, raw-vs-clean summary, and validation assertions. | Prelim→Final; versioned cleaned data. |
| `03_exploratory_analysis` | Development-safe descriptive tables/figures mapped to RQ1; correct and rerun at each version. | Prelim/Midterm; EDA artifacts. |
| `04_statistical_analysis` | RQ2 plan, assumptions, tests, clustered association model, effects/CIs, diagnostics. | Midterm/Final; statistics tables. |
| `05_feature_preparation` | Eligibility, feature decisions, split manifests, leakage assertions, preprocessing pipeline prototypes. | Midterm; model-ready manifests. |
| `06_model_development` | Baseline and approved candidates, temporal CV, tuning, default/tuned results, validation predictions. | Midterm/Final; model candidates. |
| `07_model_evaluation` | Locked comparison/selection record, one-time final test, errors, interpretation, stability, bias/responsible-use outputs. | Final only for test. |
| `08_final_analysis` | Assemble post-lock final tables/figures and objective evidence map; no retuning. | Final; paper/presentation outputs. |

Each notebook imports reusable functions from `src`, uses relative `pathlib` paths, has a stage header and input/output contract, saves artifacts, and passes restart-and-run-all.

## 33. Python-module responsibilities

- `config.py`: project root discovery, relative paths, seeds, dataset versions, feature-role lists, and approved year partitions.
- `data_loading.py`: typed CSV loading, immutable hash checks, dictionary/reference joins/checks, and versioned saves.
- `data_validation.py`: schemas, ranges, categories, keys, panel continuity, label shifting, leakage checks, and validation reports.
- `preprocessing.py`: feature eligibility, `ColumnTransformer`, model-specific pipelines, and feature-name recovery.
- `statistics.py`: assumption diagnostics, effect sizes/CIs, contingency tests, robust/clustered association models, and result tables.
- `modeling.py`: dummy/logistic/tree/forest constructors, temporal folds, searches, threshold utilities, and locked refit.
- `evaluation.py`: metrics/CIs, comparisons, saved predictions, error groups, calibration and stability utilities.
- `visualization.py`: consistent, accessible, numbered/savable figure functions with labels/units/notes.

## 34. Required outputs/artifacts

Every stage records input, output, code owner, checks, RQ/objective, and term:

| Pipeline stage | Input | Output/artifact | Code/check | RQ/stage |
|---|---|---|---|---|
| Source verification | Kaggle page/API, proposal, local files | Source record, license/authenticity decision, hashes | Notebook 01; metadata/hash match | Gate/Prelim |
| Preserved raw data | Existing CSVs/archive | Immutable raw manifest | Loader hash assertion | All/Prelim |
| Raw audit | Master/reference/dictionary | Quality report and issue registry | Schema/key/gap/target checks | RQ1/Prelim |
| Cleaning | Raw + approved decisions | Cleaned version + lineage + comparison | Notebook 02 assertions | RQ1/Prelim |
| EDA | Clean development data | Numbered tables/figures | Notebook 03, saved source data | RQ1/Prelim–Midterm |
| Statistics | Development data + plan | Assumptions/effects/CIs/tests/model | Notebook 04 | RQ2/Midterm |
| Feature preparation | Clean data + role table | Pipelines, feature/split manifests | Notebook 05 leakage tests | Obj. 3/Midterm |
| Chronological development | Training folds | Baseline/candidates/tuning records | Notebook 06 identical folds | RQ3/Midterm |
| Model selection | Validation predictions | Signed selection/threshold record | Notebook 07 pre-test assertion | RQ4/Final |
| Final test | Locked pipeline + 2025 | Metrics, confusion matrix, predictions | One-time run log | RQ3–4/Final |
| Errors/interpretation | Saved predictions/models | Error, importance, rule, stability outputs | Notebook 07 | RQ4/Final |
| Responsible-use review | All evidence | Ethics/bias/use-boundary report | Checklist and subgroup checks | All/Final |
| Final assembly | Generated outputs | Paper, README, slides, models | Notebook 08; consistency checks | All/Final |
| Reproducibility | Clean clone/copy | Execution log and validation report | Run in documented order | All/Final |

## 35. Git strategy

- Make no commit during this planning pass.
- Before implementation, populate `.gitignore` for `.venv/`, credentials, caches, notebook checkpoints, OS/editor files, temporary renders, and any restricted data. Do not ignore required reproducible outputs indiscriminately.
- Use small, meaningful commits by artifact or decision: source record, audit, cleaning rule, EDA figure set, statistics, feature pipeline, baseline, each candidate/tuning set, evaluation, paper/README updates.
- Never commit secrets, machine-specific paths, temporary files, or claims not reproduced by code.
- Raw CSVs are currently tracked and CC0 permits redistribution; retain exact hashes and synthetic provenance. Do not rewrite their Git history or move/rename them without explicit instruction.
- Tag or record submitted Prelim/Midterm/Final versions. Require review before merge where team workflow permits.

## 36. Contribution-log strategy

Maintain `docs/contributions/contribution_log.csv` (or an approved table) with:

`date, member, assigned_task, work_completed, artifact_or_file, commit_or_version, reviewer, testing_completed, status, evidence_link`

Entries must be contemporaneous and factual. Every member should contribute meaningfully across data work, code, analysis, documentation, presentation, and defense, while understanding the full workflow. Do not fabricate or backfill contribution claims.

## 37. Correction-log strategy

Maintain separate, append-only records:

- `proposal_corrections.csv`
- `prelim_consultation_and_defense_corrections.csv`
- `midterm_consultation_and_defense_corrections.csv`
- `final_defense_corrections.csv`

Required fields: `comment_or_recommendation, required_action, responsible_member, affected_section_or_file, date_assigned, date_completed, status, evidence, reviewer`. The synthetic-data approval/replacement decision and six-gap target decision must be first-class entries. Never overwrite prior wording; close with evidence.

## 38. README requirements

The final README must state title, synthetic/empirical status, description, group members, course, Python version, required libraries, folder structure, source/license/download instructions, immutable raw-file rule, setup/install commands, execution order, notebook/script roles, result reproduction, final-model loading/prediction, output generation, limitations, responsible-use boundary, and troubleshooting.

Immediate implementation correction: replace the current unresolved “synthetic ID” warning with the verified fact that the full dataset is synthetic. Keep README, requirements, dataset versions, paper, and generated outputs synchronized.

## 39. Clean-copy reproducibility checklist

- [ ] Clone/copy to a new directory outside the developer’s normal working copy.
- [ ] Confirm `.venv`, caches, secrets, and personal paths are absent.
- [ ] Install the documented Python version and requirements successfully.
- [ ] Verify raw hashes and source manifest.
- [ ] Run notebooks/scripts in documented order from a restarted environment.
- [ ] Reproduce cleaned and model-ready versions from raw files.
- [ ] Reproduce quality/statistical tables and all numbered figures.
- [ ] Reproduce split manifests, baseline, candidates, tuning, and locked comparison.
- [ ] Reload the saved preprocessing pipeline/model and reproduce final predictions/metrics without refitting.
- [ ] Scan notebooks for execution errors, stale outputs, absolute paths, and hidden/manual dependencies.
- [ ] Compare generated metric files with the paper/slides; no manually transcribed discrepancy.
- [ ] Record OS, Python, package versions, start/end time, commands, hashes, and pass/fail evidence.

## 40. Six-chapter paper mapping

| Chapter | Required project content |
|---|---|
| 1 — Introduction/problem | Background, approved problem/RQs/objectives, significance, users, scope/limitations, IT relevance, SDG 9, key definitions, and explicit synthetic-data boundary. |
| 2 — Literature/studies | Related cable-infrastructure literature, data science studies, datasets, statistics, classifiers/tools, synthesis and gap; distinguish empirical literature from this simulator. |
| 3 — Methodology | Design, source/coverage/unit/variables/dictionary, acquisition, ethics/governance, environment, quality/cleaning, EDA/statistics/assumptions, features/splits, models/CV/tuning/metrics/selection/test, error/interpretation/bias/reproducibility. |
| 4 — Implementation/development | File organization, import, quality findings, cleaning implementation, final data, EDA/statistics implementation, feature preparation, splits, baseline/candidates, tuning/comparison/selection, technical limitations. |
| 5 — Results/evaluation/discussion | Final descriptive/statistical results, validation/tuning/test metrics, errors, interpretation, robustness, subgroup/bias/responsible use, literature comparison, and evidence for every objective. |
| 6 — Conclusions/limitations/recommendations | Conclusions mapped one-to-one to RQs/objectives; dataset/statistical/model/ethical limits; responsible-use boundary; recommendations for users/research/model/data. No new results. |

## 41. Prelim defense mapping

Slides and live execution cover approved title/corrections, problem/objectives/scope, verified synthetic source/license, unit/variables/target, ethics, dictionary, quality and gap findings, cleaning decisions/results, descriptive/EDA evidence, limitations, and Midterm plan. Every member must explain a variable, quality issue, cleaning rule, code block, chart, raw-to-clean trace, and personal contribution.

## 42. Midterm defense mapping

Cover Prelim corrections, finalized cleaned version/dictionary, expanded development EDA, statistical question/method/assumptions/results, feature decisions, chronological split, leakage controls, baseline and three candidates, temporal CV/tuning, metrics/comparison, initial errors/interpretation, bias/responsible use, limitations, and Final plan. Demonstrate actual pipelines and saved outputs, not screenshots.

## 43. Final defense mapping

Cover the complete evidence chain: corrections; source and synthetic boundary; final data; EDA/statistics; preprocessing/splits/leakage; baseline/candidates/tuning; signed selection; one-time test metrics; errors; interpretation; robustness; subgroup/bias; ethics/responsible use; RQ/objective answers; conclusions/limitations/recommendations; reproducibility; and member contributions. Be ready to reload the final pipeline, produce a prediction on an appropriate synthetic case, change a safe parameter during demonstration, and explain why that does not authorize retuning the reported model.

## 44. Requirement-to-artifact traceability matrix

| Requirement | Source document/section | Stage | RQ/objective | Planned artifact | Notebook/script | Verification method | Current status |
|---|---|---|---|---|---|---|---|
| Instructor approval of dataset/direction | Instructor General §1; Proposal instructions | Proposal/Prelim | All | Signed approval/correction entry | Notebook 01 gate | Written approval attached | **Blocked: synthetic decision required** |
| Legitimate, traceable, ≥1,000 observations | General §4; proposal dataset rules; Prelim §2 | Prelim | All | Source record and audit | 01 / data_validation | Metadata, counts, hashes | Size verified; legitimacy for course unresolved |
| License/access/provenance | General §§4–5; Prelim §§2–3 | Prelim→Final | All | Source/license record | 01 | Kaggle API snapshot + CC0 deed | License and synthetic status verified; snapshot pending |
| Preserve untouched raw data | General §8; Prelim §2 | All | Obj. 3 | Raw manifest/hashes | data_loading | Hash assertion | Existing files intact/tracked |
| Ethics/privacy/governance | General §5; each term | All | All | Ethics checklist/use boundaries | 01, 07 | Checklist/review | Planned; core risk identified |
| Raw import and inspection | Prelim §5 | Prelim | RQ1 | Audit tables/log | 01 | Head/tail/schema/count tests | Planning audit complete; notebook absent |
| Complete data dictionary | Prelim §6; Midterm §3; Final §3 | All | Obj. 3 | Versioned dictionary | 01, 02 | Column/schema reconciliation | Supplied dictionary aligns; enhancements pending |
| Data-quality assessment | Prelim §7; rubrics | Prelim→Final | RQ1/Obj. 3 | Quality report/issue register | 01, 02 | Automated assertions + affected counts | Planning audit complete |
| Missing periods/forward label | Prelim §7; proposal target rule | Prelim | RQ3–4 | Gap/label decision record | 01, 02 | Calendar-year shift assertion | **Six unresolved labels** |
| Reproducible cleaning/new versions | Prelim §§8–9; Midterm §2; Final §§2–4 | All | Obj. 3 | Clean v1/v2/v3 + lineage | 02 | Raw-vs-clean reconciliation | Not implemented |
| Descriptive statistics | Prelim §10 | Prelim→Final | RQ1 | Numbered tables | 03 | Recomputed from cleaned hash | Not implemented |
| EDA figures and interpretation | General §9; Prelim §11; Midterm §4 | Prelim→Final | RQ1 | Numbered figures/notes | 03, 08 | Code regeneration + paper link | Not implemented |
| Statistical question/method map | Midterm §5 | Midterm | RQ2/Obj. 2 | Statistical analysis registry | 04 | One-to-one RQ mapping | Planned |
| Assumption checks | Midterm §6; Final §17 | Midterm/Final | RQ2 | Assumption tables | 04 | Diagnostic pass/fallback log | Not implemented |
| Effects/CIs/p-values/interpretation | General §10; Midterm §7 | Midterm/Final | RQ2 | Statistical result tables | 04 | Independent code checks | Not implemented |
| Repeated cable observations | Proposal H.4/limitations | Midterm | RQ2 | Clustered inference record | statistics.py | Cluster counts/robust covariance | Planned |
| Feature preparation | Midterm §8; Final §4 | Midterm→Final | Obj. 3 | Feature manifest/pipeline | 05 / preprocessing | Feature names and fit-boundary tests | Planned |
| Leakage prevention | General §12; Midterm §9 | Midterm→Final | Obj. 3–5 | Leakage audit/assertions | 05 | Unit tests/split checks | Risks identified |
| Chronological partitions | Midterm §10; proposal validation | Midterm | RQ3–4 | Split manifest | 05 | Year/row disjointness and counts | Counts verified; gap decision pending |
| Majority/prior baseline | General §11; Midterm §11 | Midterm→Final | RQ3 | Baseline model/metrics | 06 | Same folds/features/metrics | Planned |
| Logistic regression | Proposal H.6.1 | Midterm→Final | RQ3–4 | Pipeline/search/interpretation | 06, 07 | Temporal CV + validation | Planned |
| Decision tree | Proposal H.6.2 | Midterm→Final | RQ3–4 | Pipeline/search/tree rules | 06, 07 | Temporal CV + validation | Planned |
| Random forest | Proposal H.6.3 | Midterm→Final | RQ3–4 | Pipeline/search/permutation importance | 06, 07 | Temporal CV + validation | Planned |
| Cross-validation/tuning without test | Midterm §§13–14; Final §8 | Midterm→Final | RQ3–4 | Search records/fold metrics | 06 | Fold chronology/test-access guard | Planned |
| Fair model comparison | Midterm §16; Final §9 | Midterm→Final | RQ4 | Comparison table | 06, 07 | Identical partitions/primary metric | Planned |
| Final selection before test | Final §10 | Final | RQ4/Obj. 5 | Signed selection record | 07 | Timestamp/hash before test run | Planned |
| Untouched one-time test | General §12; Final §11/rubric | Final | RQ3–4 | Test run log/predictions/metrics | 07 | Access/run counter and hashes | Not used for model evaluation |
| Required classification metrics | General §13; proposal evaluation | Midterm/Final | RQ3–4 | Metric JSON/CSV/tables | evaluation.py | Recalculate from predictions | Planned |
| Error analysis | Midterm §17; Final §12 | Midterm/Final | RQ4 | Error rows/group tables | 07 | Prediction reconciliation | Planned |
| Interpretation | Midterm §18; Final §13 | Midterm/Final | RQ2/RQ4 | Coefficients/rules/importance | 04, 07 | Stability and direction checks | Planned |
| Robustness/stability | Final §14 | Final | RQ4 | Sensitivity/fold report | 07 | Predeclared comparisons | Planned |
| Bias/fairness/responsible use | Midterm §19; Final §§15–16 | Midterm/Final | All | Subgroup/ethics report | 07 | Count/metric/safeguard review | Planned |
| Six-chapter paper | General §16; Final §20 | All | All | Editable paper + PDF | 08 outputs | Evidence/objective consistency audit | Not created |
| APA/citation verification | APA instructions pp.151–163; Final §21 | All | All | Citation audit/references | Documentation process | Link/DOI and bidirectional match | Proposal references not reverified in this pass |
| Python workflow/environment | General §§6,14; each term | All | All | Notebooks/src/requirements | All | Clean run, versions, no paths | Structure only; current venv machine-specific |
| README/execution guide | Final §24 | Prelim→Final | All | README | All | Independent evaluator test | Preliminary and currently stale |
| Saved pipeline/model artifacts | Final §23 | Final | RQ3–4 | Pipeline/model/feature metadata | 07 | Reload and reproduce predictions | Not implemented |
| Meaningful Git history | General §18 | All | All | Commits/tags | N/A | Log review | Existing history not assessed; no commit made |
| Contribution records | General §18; each term | All | All | Contribution log | N/A | Commit/artifact evidence | Not present |
| Correction records | Each term correction section | All | All | Four correction logs | N/A | Status/evidence audit | Not present |
| Defense/demo preparedness | General §19; term defense sections | All | All | Slides/demo checklist/backups | Stage notebooks | Clean live execution/Q&A rehearsal | Planned |
| Clean-copy reproducibility | Final §25/rubric | Final | All | Validation log | All | Fresh environment end-to-end run | Planned |

## 45. Exact implementation order

1. Read this specification and current repository; confirm no newer instructor/proposal file exists.
2. Create the proposal correction entry for the verified 100% synthetic source.
3. Obtain and archive the instructor’s written decision: synthetic branch or replacement branch. **Stop if absent.**
4. If replacement is ordered, acquire it lawfully, preserve it, inspect it, and revise the proposal/specification before any analysis.
5. If synthetic use is approved, revise title/claims/beneficiaries/scope as instructed and update README with an unmistakable synthetic disclaimer.
6. Complete the source record: Kaggle metadata snapshot, CC0 record, access date, hashes, archive/version comparison, and citation.
7. Configure `.gitignore`, relative paths, Python version, minimal reproducible requirements, seeds, and folders—without moving/renaming originals.
8. Implement `config`, loading, and validation utilities; create and run Notebook 01.
9. Present the six-gap/label audit and get instructor approval for label eligibility treatment. Freeze the decision.
10. Implement cleaning/lineage in Notebook 02; create clean Prelim v1 and quality/raw-vs-clean reports; validate it.
11. Implement development-safe Notebook 03 EDA and all Prelim artifacts; update Chapters 1–3, README, logs, and defense materials.
12. Perform Prelim clean-copy run, defense rehearsal, correction capture, and submitted-version freeze.
13. Apply Prelim corrections; create finalized clean Midterm v2 and updated dictionary/quality report.
14. Implement Notebook 04 statistics with assumption/fallback/effect/CI/cluster records.
15. Implement Notebook 05 feature roles, leakage-safe pipelines, and immutable chronological split manifests.
16. Implement Notebook 06: baseline first, then logistic, tree, forest; expanding-window tuning; locked validation comparison; initial errors/interpretation.
17. Complete Chapters 3–4, Midterm artifacts, README/logs/slides/demo, clean-copy run, and version freeze.
18. Apply Midterm corrections. Re-run data/source/label validations and create final clean/model-ready versions without overwriting earlier ones.
19. Freeze feature set, preprocessing, hyperparameters, primary metric, selection rule, and threshold; sign/hash the selection record.
20. Refit the selected locked pipeline on 2015–2024, then authorize and run the 2025 final test exactly once in Notebook 07.
21. Complete final error, interpretation, robustness, subgroup/bias, ethics, and responsible-use artifacts without retuning.
22. Run Notebook 08 to assemble final generated tables/figures and objective-to-evidence mapping.
23. Complete Chapters 5–6, references/citation audit, README/model-loading guide, slides, demonstrations, contribution/correction records, and printed/digital consistency checks.
24. Run a clean-folder reproducibility test, reload artifacts, compare paper values to machine outputs, fix execution-only errors transparently, and freeze the final package.
25. Do not commit or push unless explicitly requested; when authorized, use small meaningful commits and preserve all source/version records.

## IMPLEMENTATION HANDOFF

Read this specification completely before acting. Inspect the current repository and check for newer instructor/proposal files before modifying anything. Implement in the exact documented order and start with the Prelim source-approval gate unless specifically instructed otherwise. The supplied records are verified 100% synthetic; do not run the analytical pipeline until written instructor approval or a replacement-dataset decision exists.

Preserve every original/raw file and its hash. Never fabricate or suppress results. Run and verify every notebook/script you create. Stop and update the issue/correction record if actual data contradict this specification. Never allow validation, test, or future information into training, preprocessing, feature selection, tuning, or threshold choice. Keep the 2025 final test untouched until the model, feature set, preprocessing, hyperparameters, threshold, and selection record are locked and final evaluation is authorized.

Use relative `pathlib` paths, version cleaned/model-ready datasets, and generate all metrics/tables/figures through code. Keep README and requirements synchronized with the implementation, and keep paper/slides values identical to saved machine outputs. Maintain contribution and separate correction records with evidence. Do not commit or push unless the user explicitly requests it.
