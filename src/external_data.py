"""Load and validate source-backed context data kept outside the model panel.

These files contain extracted facts and incident metadata from named public
references. They are intentionally not joined to the synthetic cable-year
panel: the panel's CAB#### identifiers have no real-world cable geometry or
crosswalk.
"""

from pathlib import Path
from typing import Tuple

import pandas as pd

from . import config


CONTEXT_REQUIRED_COLUMNS = {
    "metric_id", "metric", "value", "unit", "scope", "reference_period",
    "source_organization", "source_title", "source_url", "accessed_date",
    "source_note",
}
INCIDENT_REQUIRED_COLUMNS = {
    "incident_id", "incident_date", "location", "vessel_or_description",
    "cause_summary", "telecom_cables_damaged", "other_assets_damaged",
    "source_organization", "source_title", "source_url", "accessed_date",
}


def _read_external_csv(path: Path, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, keep_default_na=False)
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{path.name} must contain at least one source-backed row")
    return frame


def load_context_indicators() -> pd.DataFrame:
    """Return non-model contextual indicators with source provenance."""
    return _read_external_csv(config.EXTERNAL_CONTEXT_PATH, CONTEXT_REQUIRED_COLUMNS)


def load_historical_incidents() -> pd.DataFrame:
    """Return documented incidents; this is not a cable-year training table."""
    frame = _read_external_csv(config.EXTERNAL_INCIDENTS_PATH, INCIDENT_REQUIRED_COLUMNS)
    if frame["incident_id"].duplicated().any():
        raise ValueError("historical_incidents.csv contains duplicate incident_id values")
    return frame


def validate_external_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validate both files and return them for reporting or notebook use."""
    context = load_context_indicators()
    incidents = load_historical_incidents()
    if context["source_url"].eq("").any() or incidents["source_url"].eq("").any():
        raise ValueError("Every external row must retain a source URL")
    return context, incidents
