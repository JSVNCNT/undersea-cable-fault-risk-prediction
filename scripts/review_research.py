"""Build separate revision evidence from existing data and saved results.

Default: audit/report only, no estimator loaded. --model-diagnostics permits
frozen-model inference on 2023-2024 VALIDATION ONLY, never fit or final inference.
The completed final-evaluation directory, raw data and legacy results are hashed
before/after. A new output directory is required; no old result is overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from src import config
from src.evidence import protected_fingerprints
from src.data_loading import load_master_data
from src.data_validation import add_temporal_label_audit, forward_label_consistency, validate_values
from src.revision_analysis import association_report, cable_level_sensitivity, clustered_ap_interval, group_importances, validation_subgroups

DEFAULT_OUTPUT = ROOT / "outputs/revisions/2026-11-05"
MODEL_HASH = "4228e0bb067a895e4035229a275d0eb77007afc65c8f832b5ff8461673b56bfb"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_diagnostics(validation, saved, destination, summary):
    import joblib
    import sklearn
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import average_precision_score
    manifest = json.loads((ROOT/"website/backend/artifacts/manifest.json").read_text())
    # Compatibility must match the deployed, frozen environment before unpickling.
    expected = json.loads((ROOT/"outputs/final_evaluation_2026-11-02/protocol.json").read_text())["versions"]
    actual = dict(python=platform.python_version(), sklearn=sklearn.__version__, joblib=joblib.__version__, pandas=pd.__version__, numpy=np.__version__)
    if any(actual[k] != expected[k] for k in ["python", "sklearn", "joblib"]):
        raise RuntimeError("Use the recorded model-compatible research environment for --model-diagnostics")
    model_path = ROOT/"outputs/final_evaluation_2026-11-02/frozen/random_forest.joblib"
    if sha(model_path) != MODEL_HASH or manifest["model_sha256"] != MODEL_HASH:
        raise ValueError("Frozen-model fingerprint mismatch")
    forest = joblib.load(model_path)
    # Never load a final-test frame into this diagnostic function.
    assert validation.year.isin([2023,2024]).all()
    X, y = validation[config.PREDICTORS], validation[config.TARGET_COLUMN].astype(int)
    probabilities = forest.predict_proba(X)[:, 1]
    np.testing.assert_allclose(probabilities, saved.predicted_probability, rtol=1e-12, atol=1e-14)
    logistic = joblib.load(ROOT/"outputs/models/logistic_regression.joblib")
    lr_scores = logistic.predict_proba(X)[:, 1]
    recorded = pd.read_csv(ROOT/"outputs/tables/model_comparison_validation.csv")
    np.testing.assert_allclose(average_precision_score(y, lr_scores), float(recorded.loc[recorded.model.eq("logistic_regression"),"pr_auc"].iloc[0]), rtol=1e-12)
    intervals = clustered_ap_interval(validation, {"random_forest": probabilities, "logistic_regression": lr_scores}, repeats=1000)
    intervals.to_csv(destination/"validation_cluster_bootstrap.csv", index=False)
    print("Validation-only paired cluster bootstrap completed", flush=True)
    permutation = permutation_importance(forest, X, y, scoring="average_precision", n_repeats=5, random_state=42, n_jobs=1)
    pd.DataFrame(dict(feature=config.PREDICTORS, mean_ap_decrease=permutation.importances_mean,
                      sd_ap_decrease=permutation.importances_std, repeats=5, seed=42)).sort_values("mean_ap_decrease", ascending=False).to_csv(destination/"validation_permutation_importance.csv",index=False)
    summary["validation_cluster_bootstrap"] = intervals.to_dict("records")
    summary["validation_permutation_repeats"] = 5
    summary["model_diagnostics_performed"] = True
    summary["diagnostic_runtime"] = actual
    print("Validation-only permutation importance completed; no fit or final inference", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-diagnostics", action="store_true")
    args = parser.parse_args(argv)
    out = args.output_root.resolve()
    allowed = (ROOT/"outputs/revisions").resolve()
    if allowed not in out.parents or out.exists():
        raise ValueError("Use a NEW child directory of outputs/revisions; no existing output is overwritten")
    before = protected_fingerprints()
    if sha(ROOT/"outputs/models/random_forest.joblib") != MODEL_HASH:
        raise ValueError("Original model does not match frozen evidence")
    raw = load_master_data()
    validate_values(raw)
    audited = add_temporal_label_audit(raw)
    eligible = audited[audited.label_temporally_valid].copy()
    dev_raw = audited[audited.year.le(2024)].copy()
    dev = eligible[eligible.year.le(2024)].copy()
    validation = dev[dev.year.isin([2023,2024])].copy().reset_index(drop=True)
    out.mkdir(parents=True, exist_ok=False)
    protocol = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), development_years="through 2024",
        purpose="Post-feedback supplementary audit, not replacement primary selection or new independent confirmation",
        classifier_fitting=False, final_test_inference=False, threshold_selection=False,
        requested_model_diagnostics=args.model_diagnostics, bootstrap_unit="whole validation cable identifier; paired fixed scores; percentile 95%; 1000 replicates; seed 42",
        permutation="validation only; average precision; 5 repeats; seed 42; ungrouped row permutations are exploratory and not cluster-valid hypothesis tests",
        multiple_testing="Holm adjustment across the 10 numeric and 3 categorical omnibus tests together; alpha .05; repeated-row caveat retained",
        sensitivity="Latest eligible development record per identifier, selected by year without using its outcome; not a new unseen-system classifier experiment",
        bands="age 0-9 / 10-19 / 20+; redundancy 0-39 / 40-59 / 60+; subgroup warning n<30 or positives<10",
        protected_sha256=before)
    (out/"revision_protocol.json").write_text(json.dumps(protocol,indent=2),encoding="utf-8")
    pd.DataFrame(raw.attrs["numeric_parsing_audit"]).to_csv(out/"numeric_parsing_audit.csv",index=False)
    stages = [("raw", raw), ("labeled", audited[audited.fault_next_year.notna()]), ("unlabeled_terminal",audited[audited.fault_next_year.isna()]),
              ("nonconsecutive_excluded",audited[audited.fault_next_year.notna() & ~audited.has_consecutive_next_year]),
              ("supervised_eligible",eligible), ("development_eda",dev_raw), ("development_supervised",dev),
              ("train",eligible[eligible.year.isin(config.TRAIN_YEARS)]), ("validation",validation),
              ("final_test_existing_partition",eligible[eligible.year.eq(2025)])]
    reconciliation = pd.DataFrame([dict(stage=name,rows=len(part),distinct_ids=part.cable_id.nunique(),
                                        labeled=int(part.fault_next_year.notna().sum()), positives=int(part.fault_next_year.eq(1).sum()),negatives=int(part.fault_next_year.eq(0).sum())) for name,part in stages])
    reconciliation.to_csv(out/"record_reconciliation.csv",index=False)
    raw.groupby("year").agg(rows=("year","size"), unique_identifiers=("cable_id","nunique")).reset_index().to_csv(out/"annual_panel_coverage.csv",index=False)
    raw.groupby("cable_id").agg(first_year=("year","min"),last_year=("year","max"),observed_years=("year","size"),ready_for_service=("rfs_year","first")).reset_index().to_csv(out/"identifier_coverage.csv",index=False)
    gaps = audited[audited.fault_next_year.notna() & ~audited.has_consecutive_next_year]
    gaps[["cable_id","year","next_observed_year","fault_next_year"]].to_csv(out/"temporal_exclusion_examples.csv",index=False)
    # Generation/target mapping is independently checked only within development.
    forward = forward_label_consistency(dev_raw)
    forward.to_csv(out/"development_forward_label_audit.csv",index=False)
    numeric, categorical = association_report(dev)
    numeric.to_csv(out/"numeric_associations_holm.csv",index=False)
    categorical.to_csv(out/"categorical_associations_holm.csv",index=False)
    one_per_id, one_numeric, one_categorical = cable_level_sensitivity(dev)
    one_per_id.to_csv(out/"cable_level_sensitivity_population.csv",index=False)
    one_numeric.to_csv(out/"cable_level_numeric.csv",index=False)
    one_categorical.to_csv(out/"cable_level_categorical.csv",index=False)
    assoc = pd.read_csv(ROOT/"outputs/tables/statistics/logistic_association_results.csv")
    assoc.to_csv(out/"existing_cluster_robust_logistic_associations.csv",index=False)
    correlations = dev[["design_capacity_tbps","lit_capacity_tbps","utilization_pct"]].corr(method="spearman")
    correlations.rename_axis("variable").reset_index().to_csv(out/"capacity_spearman_correlations.csv",index=False)
    ratio = 100 * dev.lit_capacity_tbps / dev.design_capacity_tbps
    pd.DataFrame([dict(check="utilization_equals_100_lit_divided_by_design",rows=len(dev),exact_matches=int(np.isclose(ratio,dev.utilization_pct,rtol=0,atol=1e-8).sum()),
                       mean_absolute_difference=float((ratio-dev.utilization_pct).abs().mean()), interpretation="Numerical check only; publisher generation formula remains unknown")]).to_csv(out/"capacity_formula_audit.csv",index=False)
    saved = pd.read_csv(ROOT/"outputs/tables/validation_error_analysis.csv")
    # Explicit key order, not an accidental positional join.
    saved = validation[["cable_id","year","fault_next_year"]].merge(saved,on=["cable_id","year","fault_next_year"],validate="one_to_one",how="left")
    if saved.predicted.isna().any():
        raise ValueError("Missing saved validation predictions")
    subgroups = validation_subgroups(validation,saved)
    subgroups.to_csv(out/"validation_subgroup_errors.csv",index=False)
    group_importances(pd.read_csv(ROOT/"outputs/tables/model_interpretation/random_forest_feature_importance.csv")).to_csv(out/"original_predictor_importance.csv",index=False)
    cv = pd.read_csv(ROOT/"outputs/tables/temporal_cv_scores.csv")
    cv[["fold","train_max_year","validation_year","n_train","n_validation"]].drop_duplicates().assign(train_min_year=2015).to_csv(out/"expanding_window_folds.csv",index=False)
    summary = dict(record_reconciliation=reconciliation.to_dict("records"), primary_predictor_missing=int(raw[config.PREDICTORS].isna().sum().sum()),
        numeric_parse_failures=sum(r["numeric_parse_failures"] for r in raw.attrs["numeric_parsing_audit"]),
        development_forward_checkable=int(forward.checkable.sum()), development_forward_disagreements=int(forward.loc[forward.checkable,"agrees_with_successor"].eq(False).sum()),
        development_unlabeled=int(dev_raw.fault_next_year.isna().sum()), model_diagnostics_performed=False,
        latest_record_sensitivity_identifiers=len(one_per_id),
        train_validation_shared_ids=len(set(dev[dev.year.le(2022)].cable_id)&set(validation.cable_id)),validation_unique_ids=validation.cable_id.nunique(),
        synthetic_dataset_acceptance="Project owner confirmed instructor acceptance on 2026-11-05; approval date/document not supplied",
        final_test_acceptance="Instructor consultation required: user-authorized final run on 2026-11-02 preceded 2026-11-04 memorandum",
        original_model_sha256=MODEL_HASH, new_classifier_fit=False, new_final_inference=False)
    if args.model_diagnostics:
        model_diagnostics(validation,saved,out,summary)
    if protected_fingerprints() != before:
        raise RuntimeError("Protected research evidence changed during revision reporting")
    summary["protected_evidence_unchanged"] = True
    summary["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    (out/"revision_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == "__main__":
    main()
