from pathlib import Path
from typing import Dict
import pandas as pd

from . import config

NUMERIC_COLUMNS = [
    "year", "rfs_year", "age_years", "fiber_pairs", "length_km",
    "n_landing_countries", "design_capacity_tbps", "lit_capacity_tbps",
    "utilization_pct", "protected_burial", "design_life_years",
    "route_redundancy", "is_low_redundancy", "vulnerability_index",
    "fault_this_year", "fault_next_year",
]

def load_csv(path: Path, *, target_nullable: bool = False) -> pd.DataFrame:
    """Read CSV while preserving literal ``None`` as a category."""
    frame = pd.read_csv(path, keep_default_na=False, na_values=[])
    for col in frame.columns:
        if col in NUMERIC_COLUMNS:
            if target_nullable and col == config.TARGET_COLUMN:
                frame[col] = pd.to_numeric(frame[col].replace({"": pd.NA}), errors="coerce")
            else:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
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

