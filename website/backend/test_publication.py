"""Publication checks are read-only; never executes inference or database writes."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_publication_source_fingerprints_still_match():
    research = json.loads((ROOT / "website/public/data/research.json").read_text(encoding="utf-8"))
    for relative, expected in research["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def test_admin_import_uses_real_records_and_only_performed_evaluations():
    path = ROOT / "website/scripts/import_supabase.py"
    spec = importlib.util.spec_from_file_location("publication_import", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    research, tables = module.load_publication()
    assert len(tables["cable_year_observations"]) == 4315
    assert len(tables["variable_definitions"]) == 21
    assert len(tables["evaluation_results"]) == 5
    final = [r for r in tables["evaluation_results"] if r["partition"] == "final_test"]
    assert len(final) == 1 and final[0]["model_id"] == "random_forest"
    assert final[0]["tp"] == 29 and final[0]["fn"] == 49
    assert any(r["chokepoint"] == "None" for r in tables["cable_year_observations"])
    assert any(r["telecom_cables_damaged"] is None for r in tables["historical_incidents"])
    assert all(r["release_id"] == research["release_id"] for records in tables.values() for r in records)
