"""Lightweight original-evidence fingerprints; no model or data-library imports."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def protected_fingerprints():
    roots=["UnderseaCableRisk","data","outputs/models","outputs/tables","outputs/metrics","outputs/reports","outputs/final_evaluation_2026-11-02","website/public/data","website/backend/artifacts"]
    paths=[p for item in roots for p in (ROOT/item).rglob('*') if p.is_file()]
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def verify_historical_evidence(expected):
    """Keep all historic hashes; allow only separately manifested empirical additions.

    This does not rebaseline the November experiment or ignore arbitrary new data.
    Callers also validate the independent external acquisition manifest.
    """
    current = protected_fingerprints()
    if any(current.get(path) != sha for path, sha in expected.items()):
        raise AssertionError("Historical source/model/results missing or changed")
    allowed = ("data/external/world_bank/", "data/external/global_fishing_watch/", "data/external/open_undersea_cable_map/", "data/external/ofca/", "data/derived/external_empirical/")
    if any(not path.startswith(allowed) for path in current.keys() - expected.keys()):
        raise AssertionError("Unexpected addition outside the separate empirical data roots")
    return True
