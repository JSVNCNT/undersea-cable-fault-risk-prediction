# Authorized final evaluation — November 2, 2026

This is the completed one-time evaluation of the already-selected, unchanged
random forest. Do not delete this folder to rerun an exposed test. The runner
rejects an existing folder before loading a model. Documentation revisions must
reuse the saved outputs. No fit, parameter search, recalibration or new threshold
selection was performed.

`protocol.json` was saved before final prediction. It records authorization,
model/data/source hashes, ordered inputs, settings, decision rule and environment.
`evaluation_started.json` reserves the run. `evaluation_record.json` records
completion and hashes the two CSV outputs. `frozen/` preserves the selected model,
selection record and metadata. The original artifacts are unchanged.

The ordinary development script `scripts/run_pipeline.py` can overwrite generated
models and status files. It is not the final-test entry point. Preserve this
completed experiment; do not select a revised model against its exposed test.

## final_test_predictions.csv

One row is an existing eligible cable-year observation from predictor year 2025.

- `cable_id`: publisher-supplied computer-generated cable identifier.
- `year`: predictor observation year t = 2025.
- `fault_next_year`: supplied binary outcome for t+1 = 2026.
- `predicted`: frozen-model class, 0 or 1, from the saved argmax decision rule.
- `predicted_probability`: uncalibrated model score for class 1.
- `error_type`: TN (0/0), FP (0/1), FN (1/0), or TP (1/1), label/prediction order.

## partition_metrics.csv

One row summarizes the same already-fitted forest on train, validation or final_test.

- `partition`, `model`: sample identifier and estimator name.
- `rows`: number of evaluated records.
- `predictor_min_year`, `predictor_max_year`: observation-year range.
- `positives`, `prevalence`: class-1 count and positives divided by rows.
- `accuracy`: (TP + TN) / rows.
- `precision`: TP / (TP + FP).
- `recall`: TP / (TP + FN).
- `f1`: 2TP / (2TP + FP + FN).
- `TN`, `FP`, `FN`, `TP`: confusion counts.
- `roc_auc`: positive-score ROC ranking area.
- `pr_auc`: sklearn average precision, not necessarily trapezoidal PR area.

All rates are decimals. Training metrics are in-sample diagnostics, not a refit.
Only the selected forest has final scores; no final candidate comparison occurred.
Pandas and NumPy versions changed since training; sklearn/joblib versions match,
and validation predictions and metrics were reproduced before test prediction.
The source panel is publisher-declared computer-generated and does not establish
real cable fault probabilities, causal effects or operational deployment fitness.
