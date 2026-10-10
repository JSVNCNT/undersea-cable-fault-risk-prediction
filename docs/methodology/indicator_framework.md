# Infrastructure and operational indicator framework

The approved title is retained. The analysis groups the existing 13 predictors
by their principal analytical role. This grouping does not certify a physical
fault mechanism and does not require new or generated observations.

| Group | Existing predictors | Research meaning |
| --- | --- | --- |
| Infrastructure (9) | ocean_route, chokepoint, age_years, fiber_pairs, length_km, n_landing_countries, design_capacity_tbps, protected_burial, route_redundancy | Physical configuration, asset lifecycle, geographic setting, protection, and network multiplicity |
| Operational (4) | operator_type, lit_capacity_tbps, utilization_pct, fault_this_year | Organizational context, activated capacity, operating-load indicator, and fault experience available when year t closes |

Age and redundancy can change each year; the grouping follows meaning rather
than whether a field changes. Lit capacity depends on both equipment and
activation decisions. Operator category is context rather than an observed
maintenance procedure. Route redundancy is the supplied count of cables on a
route-year, not proof of spare capacity or geographic independence.

Every predictor is interpreted at the end of year t, with `fault_next_year`
representing the year t+1 outcome. No t+1 predictor, target-derived index,
unverified vulnerability score, or cause field enters this comparison.

## Reproduction

Run `scripts/analyze_indicator_groups.py` in the project environment. It reads
the preserved source, applies the existing temporal-label audit, and fits fixed
logistic-regression and random-forest models to each of three feature blocks:
infrastructure, operational, and combined. Training remains 2015–2022 (2,960
rows), with validation in 2023–2024 (891 rows, 170 positives). Imputation and
encoding fit only training rows. The final 2025 holdout remains locked.

The report calls average precision `pr_auc` to match the existing repository.
All comparisons use the same observations, estimator parameters, seed, and
default classification threshold. Saved primary models and the original
model-selection record are not replaced. The new results are exploratory
development evidence because the validation data have already been examined.

## Recorded results

| Model | Infrastructure AP | Operational AP | Combined AP |
| --- | ---: | ---: | ---: |
| Logistic regression | 0.291911 | 0.257556 | 0.310512 |
| Random forest | 0.326551 | 0.257390 | 0.317149 |

Validation prevalence is 0.190797. Both blocks contain ranking information in
the supplied panel. Combining blocks improves logistic-regression AP relative
to either block alone. Infrastructure-only random forest has slightly higher
AP than the combined forest. These are descriptive point estimates, not proof
of a statistically reliable improvement or superiority on an independent
final test. Existing primary model selection is preserved.

## Evidence and disclosure

The publisher declares the source panel synthetic. The data dictionary also
identifies synthetic cable IDs. That material source fact remains in the
abstract, dataset-source section, and limitations of the revised papers. Real
ITU, ICPC, and other previously verified references explain the domain context;
they do not authenticate the panel or convert its identifiers into real assets.

Outputs are stored in `outputs/tables/indicator_analysis/`:

- `indicator_registry.csv`: definitions, grouping, units, timing, and qualifications.
- `indicator_block_validation.csv`: six model/block comparisons and confusion counts.
- `numeric_indicator_associations.csv` and `categorical_indicator_associations.csv`: existing statistical evidence joined to indicator definitions, not new source observations.

`outputs/reports/indicator_analysis_metadata.json` records the scope and hashes
of source files, selection record, and final-test status. No final-test outcomes
were scored, no new cable records were generated, and no causal conclusions are
drawn from this comparison.
