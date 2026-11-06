from typing import Tuple
import numpy as np
import pandas as pd

from . import config

def add_temporal_label_audit(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ordered = out.sort_values([config.ID_COLUMN, config.YEAR_COLUMN])
    out["next_observed_year"] = ordered.groupby(config.ID_COLUMN)[config.YEAR_COLUMN].shift(-1).reindex(out.index)
    out["has_consecutive_next_year"] = (out["next_observed_year"] == out[config.YEAR_COLUMN] + 1)
    out["label_temporally_valid"] = out[config.TARGET_COLUMN].notna() & out["has_consecutive_next_year"]
    return out


def forward_label_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Audit observed t+1 agreement, without claiming to recover simulator rules.

    This is a label audit only. The successor fields must never enter predictors.
    Missing years are not bridged and input order/index are preserved.
    """
    ordered = df.sort_values([config.ID_COLUMN, config.YEAR_COLUMN])
    successor_year = ordered.groupby(config.ID_COLUMN)[config.YEAR_COLUMN].shift(-1).reindex(df.index)
    successor_fault = ordered.groupby(config.ID_COLUMN)["fault_this_year"].shift(-1).reindex(df.index)
    checkable = successor_year.eq(df[config.YEAR_COLUMN] + 1) & df[config.TARGET_COLUMN].notna() & successor_fault.notna()
    out = df[[config.ID_COLUMN, config.YEAR_COLUMN, config.TARGET_COLUMN]].copy()
    out["next_observed_year"] = successor_year
    out["next_observed_fault"] = successor_fault
    out["checkable"] = checkable
    out["agrees_with_successor"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    out.loc[checkable, "agrees_with_successor"] = df.loc[checkable, config.TARGET_COLUMN].eq(successor_fault[checkable])
    return out


def validate_values(df: pd.DataFrame) -> None:
    """Fail on invalid primary data, rather than merely reporting bad counts."""
    validate_schema(df)
    if not df.index.is_unique:
        raise ValueError("Input row index must be unique for temporal reindexing")
    if df[config.ID_COLUMN].isna().any() or df[config.ID_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError("Cable identifiers must be populated")
    if df.duplicated([config.ID_COLUMN, config.YEAR_COLUMN]).any():
        raise ValueError("Duplicate cable-year keys")
    integer_columns = ["year", "rfs_year", "age_years", "fiber_pairs", "n_landing_countries",
                       "route_redundancy", "design_life_years", "protected_burial", "is_low_redundancy", "fault_this_year"]
    for col in integer_columns + ["length_km", "design_capacity_tbps", "lit_capacity_tbps", "utilization_pct", "vulnerability_index"]:
        values = pd.to_numeric(df[col], errors="coerce")
        if (df[col].notna() & values.isna()).any() or not np.isfinite(values.dropna().to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite or invalid numeric values: {col}")
        if col not in config.NUMERICAL_PREDICTORS and values.isna().any():
            raise ValueError(f"Missing required audit/calendar field: {col}")
        if col in integer_columns and not values.dropna().eq(np.floor(values.dropna())).all():
            raise ValueError(f"Non-integer values: {col}")
    for col in ["protected_burial", "is_low_redundancy", "fault_this_year", config.TARGET_COLUMN]:
        if not df[col].dropna().isin([0, 1]).all():
            raise ValueError(f"Invalid binary values: {col}")
    for col in ["age_years", "route_redundancy", "lit_capacity_tbps"]:
        if df[col].lt(0).any():
            raise ValueError(f"Negative values: {col}")
    for col in ["fiber_pairs", "length_km", "n_landing_countries", "design_capacity_tbps", "design_life_years"]:
        if df[col].le(0).any():
            raise ValueError(f"Non-positive values: {col}")
    if not df.year.between(2015, 2026).all() or not df.utilization_pct.dropna().between(0, 100).all() or not df.vulnerability_index.between(0, 100).all():
        raise ValueError("Year, utilization or vulnerability outside documented bounds")
    known_age = df.age_years.notna()
    if not df.loc[known_age,"age_years"].eq(df.loc[known_age,"year"] - df.loc[known_age,"rfs_year"]).all():
        raise ValueError("Age does not equal observation year minus ready-for-service year")
    for col in config.CATEGORICAL_PREDICTORS:
        if df[col].dropna().astype(str).str.strip().eq("").any():
            raise ValueError(f"Blank category requires an explicit missing-value decision: {col}")
    audit = forward_label_consistency(df)
    if audit.loc[audit.checkable, "agrees_with_successor"].eq(False).any():
        raise ValueError("Forward label disagrees with consecutive successor fault")

def temporal_gap_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cable_id, group in df.groupby(config.ID_COLUMN):
        years = sorted(group[config.YEAR_COLUMN].astype(int))
        for year, next_year in zip(years[:-1], years[1:]):
            if next_year != year + 1:
                rows.append({config.ID_COLUMN: cable_id, "year": year,
                             "next_observed_year": next_year,
                             "gap_years": next_year - year,
                             "label_temporally_valid": False})
    return pd.DataFrame(rows, columns=[config.ID_COLUMN, "year", "next_observed_year", "gap_years", "label_temporally_valid"])

def validate_schema(df: pd.DataFrame) -> None:
    expected = {"year", "cable_id", "ocean_route", "operator_type", "rfs_year", "age_years",
                "fiber_pairs", "length_km", "n_landing_countries", "chokepoint",
                "design_capacity_tbps", "lit_capacity_tbps", "utilization_pct", "protected_burial",
                "design_life_years", "route_redundancy", "is_low_redundancy", "vulnerability_index",
                "fault_cause", "fault_this_year", "fault_next_year"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    unexpected = set(df.columns) - expected
    if unexpected:
        raise ValueError(f"Unexpected raw-source columns: {sorted(unexpected)}")

def audit_master(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validate_values(df)
    temporal = add_temporal_label_audit(df)
    gaps = temporal_gap_audit(df)
    target = temporal[config.TARGET_COLUMN].dropna().astype(int)
    target_dist = pd.DataFrame({"target": [0, 1], "count": [int((target == 0).sum()), int((target == 1).sum())]})
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append({"variable": col, "dtype": str(s.dtype), "rows": len(s),
                     "missing_count": int(s.isna().sum()), "unique_count": int(s.nunique(dropna=False)),
                     "literal_none_count": int((s == "None").sum()) if s.dtype == object else 0})
    variable = pd.DataFrame(rows)
    summary = pd.DataFrame([
        {"check": "rows", "value": len(df)},
        {"check": "columns", "value": len(df.columns)},
        {"check": "unique_cables", "value": df[config.ID_COLUMN].nunique()},
        {"check": "min_year", "value": df[config.YEAR_COLUMN].min()},
        {"check": "max_year", "value": df[config.YEAR_COLUMN].max()},
        {"check": "labeled_rows", "value": int(df[config.TARGET_COLUMN].notna().sum())},
        {"check": "positive_labels", "value": int((df[config.TARGET_COLUMN] == 1).sum())},
        {"check": "negative_labels", "value": int((df[config.TARGET_COLUMN] == 0).sum())},
        {"check": "positive_prevalence", "value": float((df[config.TARGET_COLUMN].dropna() == 1).mean())},
        {"check": "duplicate_rows", "value": int(df.duplicated().sum())},
        {"check": "duplicate_cable_year", "value": int(df.duplicated([config.ID_COLUMN, config.YEAR_COLUMN]).sum())},
        {"check": "chokepoint_literal_None", "value": int((df["chokepoint"] == "None").sum())},
        {"check": "design_life_unique", "value": int(df["design_life_years"].nunique())},
        {"check": "low_redundancy_equivalence", "value": bool((df["is_low_redundancy"] == (df["route_redundancy"] < 40).astype(int)).all())},
        {"check": "temporally_valid_labeled", "value": int(temporal["label_temporally_valid"].sum())},
    ])
    return summary, gaps, target_dist, variable
