# Feature extension and additional-data plan

This plan preserves the approved synthetic-data study and the primary predictor
set. New variables are sensitivity candidates only until the instructor approves
their inclusion and the feature manifest is frozen.

## Implemented safely from the existing panel

`data/model_ready/model_ready_engineered_sensitivity.csv` contains causal,
current/prior-year features: capacity headroom, lit/design ratio, consecutive
year changes in lit capacity/utilization/redundancy, previous-year fault, prior
three-year fault count, and years since the previous fault. The generator uses
strictly earlier calendar years for history and does not use `fault_next_year`.
Gaps are not bridged. The primary model remains unchanged.

## External data candidates

External environmental data cannot currently be joined to `CAB####` because the
supplied identifiers are synthetic and have no real coordinates or cable-name
crosswalk. Do not assign synthetic IDs to real routes. If a future empirical
geometry/cable-ID layer is approved, candidate covariates include GEBCO depth and
slope, NOAA IBTrACS cyclone exposure, USGS earthquake exposure, ERA5 or
Copernicus wave/current extremes, and Global Fishing Watch AIS vessel presence.
Each source requires a dated snapshot, license/attribution record, spatial join
rule, temporal availability rule, and missingness audit.

## Variables not suitable for primary inclusion

- `fault_cause`: contemporaneous/post-event information.
- `vulnerability_index`: formula and timing are undocumented.
- `is_low_redundancy`: deterministic duplicate of `route_redundancy`.
- Target-encoded route/operator historical rates: high leakage risk unless built
  inside each temporal training fold.
- `remaining_design_life`: exact rescaling of age because design life is constant.

## Required safeguards

Outcome-aware EDA and statistics use only 2015–2024. The 2025 final test is not
used for feature engineering, tuning, threshold selection, or model comparison.
Any new external source or primary predictor requires a proposal correction entry
and instructor approval before it changes reported results.

## Development validation added

The runner now creates expanding-window temporal folds (2015–2018 → 2019,
through 2019 → 2020, through 2020 → 2021, and through 2021 → 2022) in
`outputs/tables/temporal_cv_scores.csv` and summarizes PR-AUC/F1/recall in
`temporal_cv_summary.csv`. The engineered sensitivity models are compared on
the unchanged 2023–2024 validation partition in
`sensitivity_model_comparison_validation.csv`; they do not replace the primary
model selection record.
