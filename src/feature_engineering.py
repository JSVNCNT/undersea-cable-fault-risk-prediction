"""Causal, leakage-safe features derived from the cable-year panel.

These are materialized as a sensitivity dataset only. The primary model keeps
the approved feature list in ``config.PREDICTORS`` unchanged.
"""
import pandas as pd

from . import config

ENGINEERED_FEATURES = [
    "lit_capacity_change_yoy",
    "utilization_change_yoy",
    "route_redundancy_change_yoy",
    "fault_previous_year",
    "fault_count_prior_3_calendar_years",
    "years_since_previous_fault",
    "capacity_headroom_tbps",
    "lit_to_design_ratio",
]

def add_causal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add only information available no later than the current row's year.

    Year-over-year changes are populated only for an observed consecutive year;
    this prevents a two-year gap from being treated as a one-year change.
    Historical fault features use ``fault_this_year`` from strictly earlier
    calendar years and never use ``fault_next_year``.
    """
    out = df.copy()
    out["capacity_headroom_tbps"] = out["design_capacity_tbps"] - out["lit_capacity_tbps"]
    out["lit_to_design_ratio"] = (out["lit_capacity_tbps"] / out["design_capacity_tbps"].where(out["design_capacity_tbps"] != 0))
    out["lit_capacity_change_yoy"] = pd.NA
    out["utilization_change_yoy"] = pd.NA
    out["route_redundancy_change_yoy"] = pd.NA
    out["fault_previous_year"] = pd.NA
    out["fault_count_prior_3_calendar_years"] = 0
    out["years_since_previous_fault"] = pd.NA
    for cable_id, group in out.groupby(config.ID_COLUMN, sort=False):
        idx = group.sort_values(config.YEAR_COLUMN).index
        years = out.loc[idx, config.YEAR_COLUMN].astype(int).tolist()
        faults = out.loc[idx, "fault_this_year"]
        fault_by_year = {int(y): (None if pd.isna(v) else int(v)) for y, v in zip(years, faults)}
        for pos, row_idx in enumerate(idx):
            year = years[pos]
            if pos > 0 and years[pos - 1] == year - 1:
                prev_idx = idx[pos - 1]
                for col in ["lit_capacity_tbps", "utilization_pct", "route_redundancy"]:
                    out.loc[row_idx, f"{col.replace('_pct','').replace('_tbps','')}_change_yoy"] = out.loc[row_idx, col] - out.loc[prev_idx, col]
                out.loc[row_idx, "fault_previous_year"] = faults.loc[prev_idx]
            prior = [v for y, v in fault_by_year.items() if year - 3 <= y < year and v is not None]
            out.loc[row_idx, "fault_count_prior_3_calendar_years"] = sum(prior)
            prior_fault_years = [y for y, v in fault_by_year.items() if y < year and v == 1]
            if prior_fault_years:
                out.loc[row_idx, "years_since_previous_fault"] = year - max(prior_fault_years)
    for col in ENGINEERED_FEATURES:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out
