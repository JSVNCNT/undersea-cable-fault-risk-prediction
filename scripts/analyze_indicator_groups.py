"""Reproduce indicator definitions, associations and block comparisons.

Run: .venv/Scripts/python.exe scripts/analyze_indicator_groups.py
Outputs stay in outputs/tables/indicator_analysis and outputs/reports.
Source files and the primary model-selection record are read-only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config
from src.data_loading import load_master_data
from src.data_validation import add_temporal_label_audit
from src.indicator_analysis import compare_indicator_blocks, indicator_registry


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protected = [config.MASTER_PATH, config.REFERENCE_PATH, config.DICTIONARY_PATH,
                 config.METRICS_DIR / "model_selection.json", config.METRICS_DIR / "final_test_status.txt"]
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    audited = add_temporal_label_audit(load_master_data())
    eligible = audited[audited.label_temporally_valid & audited.year.isin(config.TRAIN_YEARS + config.VALIDATION_YEARS)].copy()
    train = eligible[eligible.year.isin(config.TRAIN_YEARS)].copy()
    validation = eligible[eligible.year.isin(config.VALIDATION_YEARS)].copy()
    registry = indicator_registry()
    directory = config.TABLES_DIR / "indicator_analysis"
    directory.mkdir(parents=True, exist_ok=True)
    registry.to_csv(directory / "indicator_registry.csv", index=False)
    comparison = compare_indicator_blocks(train, validation)
    comparison.to_csv(directory / "indicator_block_validation.csv", index=False)
    numeric = pd.read_csv(config.TABLES_DIR / "statistics/numeric_comparisons.csv")
    categorical = pd.read_csv(config.TABLES_DIR / "statistics/categorical_associations.csv")
    for frame, filename in ((numeric, "numeric_indicator_associations.csv"),
                            (categorical, "categorical_indicator_associations.csv")):
        frame.merge(registry[["feature", "indicator_group", "label", "unit"]],
                    left_on="variable", right_on="feature", how="left", validate="one_to_one").to_csv(directory / filename, index=False)
    for path in protected:
        if before[str(path.relative_to(ROOT))] != digest(path):
            raise RuntimeError(f"Protected input changed: {path}")
    metadata = dict(generated_at=datetime.now(timezone.utc).isoformat(), train_years=config.TRAIN_YEARS,
                    validation_years=config.VALIDATION_YEARS, train_rows=len(train), validation_rows=len(validation),
                    data_origin="publisher-declared synthetic panel", final_test_evaluated=False,
                    primary_model_selection_changed=False, protected_input_sha256=before,
                    grouping="9 infrastructure and 4 operational predictors; analytical role, not causal certification",
                    interpretation="Exploratory block comparison on reused validation data; no independent significance or final-performance claim.")
    (config.REPORTS_DIR / "indicator_analysis_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(comparison[["indicator_group", "model", "predictor_count", "pr_auc", "recall", "f1"]].to_string(index=False))


if __name__ == "__main__":
    main()
