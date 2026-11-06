from pathlib import Path
from typing import Dict
import pandas as pd
import numpy as np

from . import config

NUMERIC_COLUMNS = [
    "year", "rfs_year", "age_years", "fiber_pairs", "length_km",
    "n_landing_countries", "design_capacity_tbps", "lit_capacity_tbps",
    "utilization_pct", "protected_burial", "design_life_years",
    "route_redundancy", "is_low_redundancy", "vulnerability_index",
    "fault_this_year", "fault_next_year",
]

def load_csv(path: Path, *, target_nullable: bool = False, strict_numeric: bool = True) -> pd.DataFrame:
    """Preserve literal ``None``; audit parsing separately from intentional blanks.

    Numeric corruption fails closed by default. ``strict_numeric=False`` is for
    an explicitly inspected audit, never an undocumented modeling fallback.
    Counts, rather than source values, are attached to ``frame.attrs``.
    """
    frame = pd.read_csv(path, keep_default_na=False, na_values=[])
    parsing = []
    for col in frame.columns:
        if col in NUMERIC_COLUMNS:
            text = frame[col].astype(str).str.strip()
            converted = pd.to_numeric(text.mask(text.eq("")), errors="coerce")
            failed = text.ne("") & converted.isna()
            parsing.append({"variable": col, "intentional_blanks": int(text.eq("").sum()),
                            "numeric_parse_failures": int(failed.sum())})
            if strict_numeric and failed.any():
                raise ValueError(f"Numeric parsing failed in {col}: {int(failed.sum())} nonblank values")
            frame[col] = converted
        elif col in config.CATEGORICAL_PREDICTORS:
            # A genuine blank is missing, unlike the valid literal category None.
            frame[col] = frame[col].astype(object).where(frame[col].astype(str).str.strip().ne(""), np.nan)
    frame.attrs["numeric_parsing_audit"] = parsing
    return frame

def load_master_data() -> pd.DataFrame:
    return load_csv(config.MASTER_PATH, target_nullable=True)

def load_reference_data() -> pd.DataFrame:
    return load_csv(config.REFERENCE_PATH)

def load_data_dictionary() -> pd.DataFrame:
    return load_csv(config.DICTIONARY_PATH)

def load_all_raw_data() -> Dict[str, pd.DataFrame]:
    return {"master": load_master_data(), "reference": load_reference_data(),
            "dictionary": load_data_dictionary()}

