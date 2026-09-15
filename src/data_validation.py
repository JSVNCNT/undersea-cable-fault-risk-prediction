from typing import Tuple
import pandas as pd

from . import config

def add_temporal_label_audit(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ordered = out.sort_values([config.ID_COLUMN, config.YEAR_COLUMN])
    out["next_observed_year"] = ordered.groupby(config.ID_COLUMN)[config.YEAR_COLUMN].shift(-1).reindex(out.index)
    out["has_consecutive_next_year"] = (out["next_observed_year"] == out[config.YEAR_COLUMN] + 1)
    out["label_temporally_valid"] = out[config.TARGET_COLUMN].notna() & out["has_consecutive_next_year"]
    return out

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

def audit_master(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validate_schema(df)
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
