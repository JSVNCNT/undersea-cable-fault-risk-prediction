# Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems

**Introduction to Data Science â€” COPE0683X**  
**Section:** K44

## Project Overview

This repository contains the code, notebooks, documentation, and reproducible analytical workflow for the research project:

> **Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators**

The project investigates whether infrastructure and operational information available at the end of an observation year can distinguish cable-year records that experience a fault in the following year from those that do not.

The study is an experimental classification workflow using a publisher-declared **synthetic cable-year dataset**, not authenticated real-cable failure measurements or an operational warning system. The project owner confirmed instructor acceptance of clearly disclosed synthetic data on 5 November 2026; final-test authorization is a separate issue.

## Current finals revision

See [the execution guide](docs/revisions/2026-11-05/execution_guide.md),
[the 320-item correction matrix](docs/revisions/2026-11-05/compliance_matrix.csv),
and [the access-history record](docs/revisions/2026-11-05/final_test_access_record.md).
New supplementary reports are in `outputs/revisions/2026-11-05/`.
The original frozen forest and completed 2 November final evidence are unchanged.
Do not run the final-evaluation script again. Instructor treatment of that earlier
user-authorized run remains consultation, not an inferred instructor approval.

`python scripts/review_research.py --output-root outputs/revisions/my-new-review`
rebuilds audit/reporting evidence in a **new** directory without loading models.
Use `--model-diagnostics` only for documented validation-only diagnostics in the
compatible environment. The original development runner now refuses default
execution over the completed experiment; separate reproduction requires a new
`--output-root`. No commit, push, hosted import, or deployment is needed to inspect
the local revision. `requirements-research-frozen.txt` records model-compatible pins.

## Dataset Source

### Infrastructure and operational indicators

The 13 primary predictors are now explicitly grouped into nine infrastructure
indicators and four operational indicators. Definitions, timing, and a
development-only comparison of separate versus combined feature groups are
documented in [the indicator framework](docs/methodology/indicator_framework.md).
Reproduce the supplementary comparison with
`python scripts/analyze_indicator_groups.py`. Results are saved in
`outputs/tables/indicator_analysis/`; the original selection and completed
final-test evidence are preserved. Do not use this to reselect on the exposed test.

Historical indicator-stage paper copies can be rebuilt with
`python scripts/revise_indicator_documents.py build`. The document dependencies
are listed in `requirements-documents.txt`; test dependencies are in
`requirements-dev.txt`. The builder preserves the established formatted papers
and writes separate `INDICATOR_REVISED.docx` files. Render with
`scripts/render_indicator_documents.py`, refresh the contents lists using the
builder's `paginate --pdf-dir` command, then render again and run
`scripts/verify_indicator_documents.py --pdf-dir ... --check-pages` before use.

The working dataset is **Undersea Cables and Global Digital Infrastructure**, obtained from Kaggle:

- **Kaggle dataset:**  
  https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure
- **Dataset page account/handle:** `sergionefedov`

### Supplied Files

- `undersea_cables_master.csv`
- `cables_reference.csv`
- `data_dictionary.csv`

### Dataset Summary

- Observation period: 2015â€“2026
- Unit of analysis: one cable-year observation
- Master-file observations: 4,821
- Unique cable identifiers: 500
- Variables: 21
- Initially labeled observations: 4,321
- Positive next-year fault labels: 820
- Negative next-year fault labels: 3,501
- Target variable: `fault_next_year`

`fault_next_year = 1` is the supplied positive label for calendar year t+1. Supervised use requires an observed consecutive-year successor. It is not a verified real-cable fault event.

The final observation for each cable has no forward label and is excluded from supervised model training and evaluation while being preserved separately.

## Important Source-Verification Note

The supplied data dictionary describes `cable_id` as a **synthetic cable system ID**.

The retained publisher/source record describes synthetic, procedurally generated observations, not authenticated measurements of real submarine cable systems. The source record records CC0 reuse status and file hashes. The exact dataset version and complete generation formula are not established. The project owner confirmed instructor acceptance of clearly disclosed synthetic data; no original approval date or written decision is invented.

## Research Questions

1. What are the distributions and operational characteristics of the cable-year observations?
2. Which selected infrastructure and operational variables are statistically associated with `fault_next_year` without interpreting those associations as causal effects?
3. How well do a majority-class baseline, logistic regression, decision tree, and random forest predict next-year fault occurrence using only information available before the held-out prediction year?
4. Which candidate model provides the most appropriate balance of predictive performance, stability, interpretability, and fault-class detection?

## Implemented Analytical Workflow

1. Preserve and document the original source files.
2. Audit data types, ranges, duplicates, missing values, and data quality.
3. Verify the forward target and prediction timing.
4. Audit derived variables for possible data leakage.
5. Perform exploratory data analysis and statistical association testing.
6. Prepare categorical and numeric predictors using reproducible preprocessing pipelines.
7. Train a majority-class baseline.
8. Compare fixed candidate configurations; no hyperparameter-search history is claimed.
9. Compare all candidates on validation; retain the completed frozen-forest final evaluation only.
10. Interpret results, errors, uncertainty, limitations, and responsible-use boundaries.

## Candidate Models

### Majority-Class Baseline

A `DummyClassifier` provides training-prior scores and majority-class predictions.

### Logistic Regression

Used as an interpretable binary classifier and probability model.

### Decision Tree Classifier

Used to capture nonlinear thresholds and rule-like interactions while remaining relatively easy to interpret.

### Random Forest Classifier

Used as a more flexible ensemble model that can capture nonlinear relationships and interactions.

No model is assumed to be the best in advance.

## Validation Strategy

The project uses **chronological validation** rather than random splitting.

Recorded predictor-year split:

- Training: 2015â€“2022
- Validation/model selection: 2023â€“2024
- Final test: 2025 observations predicting 2026 fault occurrence

All preprocessing, including encoding, scaling, imputation, and any class-imbalance treatment, must be fitted only on the training portion.

## Evaluation Metrics

The project reports:

- Precision
- Recall
- F1-score
- Confusion matrix
- ROC-AUC
- Average precision (AP; internal field `pr_auc`, not trapezoidal PR area)
- Accuracy as a secondary metric

Accuracy will not be used alone because the target is imbalanced.

## Main Variables Under Review

The 13 primary predictors are:

- `ocean_route`
- `operator_type`
- `age_years`
- `fiber_pairs`
- `length_km`
- `n_landing_countries`
- `chokepoint`
- `design_capacity_tbps`
- `lit_capacity_tbps`
- `utilization_pct`
- `protected_burial`
- `route_redundancy`
- `fault_this_year`

Identifiers, year, the constant design-life field, duplicate low-redundancy flag,
ready-for-service year, undocumented vulnerability index, and fault cause are
excluded from primary inputs with documented timing/redundancy reasons.

## Repository Structure

```text
undersea-cable-fault-risk-prediction/
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/
â”‚   â””â”€â”€ processed/
â”œâ”€â”€ notebooks/
â”œâ”€â”€ src/
â”œâ”€â”€ outputs/
â”‚   â”œâ”€â”€ figures/
â”‚   â”œâ”€â”€ tables/
â”‚   â””â”€â”€ models/
â”œâ”€â”€ docs/
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .gitignore
â””â”€â”€ README.md
```

## Reproducible implementation (current)

Use the current revision execution guide above. The 2025 predictor-year test was
evaluated once on 2 November and is now exposed. Reporting must read saved final
predictions/metrics, not run final inference again. Separate development
reproduction uses a new isolated output scope. The supplementary revision checks
preserve the original data, model and results and do not turn synthetic records
into empirical evidence.

The implementation also materializes a separate engineered-feature sensitivity
dataset with causal lag/trend and capacity-headroom features. These features are
not silently added to the primary model. External environmental factors require
real cable geometry and an approved crosswalk; see
`docs/methodology/feature_extension_plan.md`.

## Source-backed context and incidents

The project keeps published real-world context separate from the synthetic
modeling panel. `data/external/context_indicators.csv` contains cited ITU,
ICPC, and TeleGeography indicators for international traffic share, fault
causes/frequency, design life, network growth, and capacity context.
`data/external/historical_incidents.csv` contains documented anchor-drag
incidents summarized by TeleGeography. These files are not fabricated and are
not joined to the `CAB####` records because the synthetic IDs have no real
geometry or cable-name crosswalk. Load and provenance checks are provided by
`src/external_data.py`.
