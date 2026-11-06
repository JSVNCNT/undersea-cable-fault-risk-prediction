"""Lightweight original-evidence fingerprints; no model or data-library imports."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def protected_fingerprints():
    roots=["UnderseaCableRisk","data","outputs/models","outputs/tables","outputs/metrics","outputs/reports","outputs/final_evaluation_2026-11-02","website/public/data","website/backend/artifacts"]
    paths=[p for item in roots for p in (ROOT/item).rglob('*') if p.is_file()]
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
