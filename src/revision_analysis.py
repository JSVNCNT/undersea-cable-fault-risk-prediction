"""Supplementary development diagnostics, never final-test model selection.

These functions consume existing records/predictions. They do not fit a
classifier, select a threshold, invent observations, or infer physical causes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from . import config
from .evaluation import classification_metrics
from .statistics import categorical_associations, holm_adjust, numeric_comparisons


def require_development(frame: pd.DataFrame) -> None:
    if frame.empty or not frame.year.le(2024).all():
        raise ValueError("Supplementary analysis requires development years through 2024 only")
    if frame.duplicated([config.ID_COLUMN, config.YEAR_COLUMN]).any():
        raise ValueError("Duplicate cable-year key in supplementary analysis")


def association_report(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """13 omnibus comparisons form one Holm family, defined before this run.

    Multiplicity adjustment does NOT repair repeated-row dependence. Original
    independent-row statistics are retained and labeled as exploratory.
    """
    require_development(frame)
    numeric = numeric_comparisons(frame)
    categorical = categorical_associations(frame)
    family = np.concatenate([numeric.p_value.to_numpy(), categorical.p_value.to_numpy()])
    adjusted = holm_adjust(family)
    for result, values in [(numeric, adjusted[:len(numeric)]), (categorical, adjusted[len(numeric):])]:
        result["p_value_holm_13_tests"] = values
        result["alpha"] = config.ALPHA
        result["evidence_scope"] = "exploratory development association; not independent-row confirmation"
    return numeric, categorical


def cable_level_sensitivity(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """One latest eligible development record per ID, chosen without outcomes.

    A different question/population from pooled cable-years. This removes
    within-ID repetition but does not establish physical independence of cables.
    """
    require_development(frame)
    subset = frame.sort_values(["cable_id", "year"]).groupby("cable_id", sort=False).tail(1)
    numeric, categorical = association_report(subset)
    return subset[["cable_id", "year", config.TARGET_COLUMN]], numeric, categorical


def validation_subgroups(validation: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    require_development(validation)
    if not validation.year.isin(config.VALIDATION_YEARS).all():
        raise ValueError("Subgroups require the original 2023-2024 validation partition")
    if predictions.duplicated(["cable_id", "year"]).any():
        raise ValueError("Duplicate prediction keys")
    frame = validation.merge(predictions, on=["cable_id", "year", config.TARGET_COLUMN],
                             how="left", validate="one_to_one", indicator=True)
    if len(frame) != len(predictions) or frame._merge.ne("both").any() or frame.predicted.isna().any():
        raise ValueError("Saved validation predictions do not match original keys and outcomes")
    frame["age_band"] = pd.cut(frame.age_years, [-np.inf, 9, 19, np.inf], labels=["0-9", "10-19", "20+"], right=True)
    frame["redundancy_band"] = pd.cut(frame.route_redundancy, [-np.inf, 39, 59, np.inf], labels=["0-39", "40-59", "60+"], right=True)
    rows = []
    for field in ["year", "ocean_route", "operator_type", "age_band", "redundancy_band"]:
        for group, part in frame.groupby(field, observed=True, sort=True):
            metrics = classification_metrics(part[config.TARGET_COLUMN], part.predicted, part.predicted_probability)
            positives = int(part[config.TARGET_COLUMN].sum())
            rows.append(dict(grouping=field, group=str(group), n=len(part), positives=positives,
                             negatives=len(part)-positives, distinct_ids=part.cable_id.nunique(),
                             small_sample_warning=len(part)<30 or positives<10,
                             **metrics))
    return pd.DataFrame(rows)


def clustered_ap_interval(frame: pd.DataFrame, scores: dict[str, np.ndarray], *, repeats=1000, seed=42) -> pd.DataFrame:
    """Paired percentile bootstrap of whole validation IDs; predictions fixed.

    This estimates resampling uncertainty conditional on the already selected
    period/model, not new independent confirmation or simulator uncertainty.
    """
    require_development(frame)
    if not frame.year.isin(config.VALIDATION_YEARS).all():
        raise ValueError("Bootstrap requires validation only")
    if repeats < 2:
        raise ValueError("At least two bootstrap replicates required")
    frame = frame.reset_index(drop=True)
    groups = list(frame.groupby("cable_id", sort=True).indices.values())
    y = frame[config.TARGET_COLUMN].to_numpy(dtype=int)
    arrays = {name: np.asarray(value, dtype=float) for name, value in scores.items()}
    if any(len(s) != len(y) or not np.isfinite(s).all() for s in arrays.values()):
        raise ValueError("Scores must be finite and aligned with validation rows")
    rng = np.random.default_rng(seed)
    results = {name: [] for name in arrays}
    difference = []
    for _ in range(repeats):
        indices = np.concatenate([groups[i] for i in rng.integers(len(groups), size=len(groups))])
        if np.unique(y[indices]).size < 2:
            continue
        values = {name: float(average_precision_score(y[indices], s[indices])) for name, s in arrays.items()}
        for name, value in values.items():
            results[name].append(value)
        if {"random_forest", "logistic_regression"} <= arrays.keys():
            difference.append(values["random_forest"] - values["logistic_regression"])
    rows = []
    for name, values in results.items():
        lo, hi = np.quantile(values, [0.025, 0.975])
        rows.append(dict(measure=f"AP {name}", estimate=float(average_precision_score(y, arrays[name])),
                         ci_low=float(lo), ci_high=float(hi), valid_repeats=len(values), requested_repeats=repeats, seed=seed))
    if difference:
        lo, hi = np.quantile(difference, [0.025, 0.975])
        rows.append(dict(measure="AP random_forest minus logistic_regression",
                         estimate=float(average_precision_score(y, arrays["random_forest"])-average_precision_score(y, arrays["logistic_regression"])),
                         ci_low=float(lo), ci_high=float(hi), valid_repeats=len(difference), requested_repeats=repeats, seed=seed))
    return pd.DataFrame(rows)


def group_importances(encoded: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in encoded.itertuples(index=False):
        value = str(row.feature).split("__", 1)[-1]
        matching = [p for p in config.PREDICTORS if value == p or value.startswith(p + "_")]
        if len(matching) != 1:
            raise ValueError(f"Encoded feature has no unambiguous original input: {value}")
        rows.append({"feature": matching[0], "importance": float(row.importance)})
    result = pd.DataFrame(rows).groupby("feature", as_index=False).importance.sum()
    if set(result.feature) != set(config.PREDICTORS) or not np.isclose(result.importance.sum(), 1.0):
        raise ValueError("Grouped importance does not reconcile with all original predictors")
    return result.sort_values("importance", ascending=False)
