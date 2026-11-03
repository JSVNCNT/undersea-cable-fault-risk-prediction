"""Read-only publication of existing CSV/results. No training or evaluation.

Writes only website/public/data and website/backend/artifacts. Run from any cwd.
The binary copy is the trusted, frozen pipeline already evaluated on Nov 2.
"""
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "website"
FINAL = ROOT / "outputs/final_evaluation_2026-11-02"
EXPECTED_MODEL_HASH = "4228e0bb067a895e4035229a275d0eb77007afc65c8f832b5ff8461673b56bfb"


def rows(relative):
    with (ROOT / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def main():
    protocol = json.loads((FINAL / "protocol.json").read_text(encoding="utf-8"))
    record = json.loads((FINAL / "evaluation_record.json").read_text(encoding="utf-8"))
    model = FINAL / "frozen/random_forest.joblib"
    if sha(model) != EXPECTED_MODEL_HASH or record["model_sha256"] != EXPECTED_MODEL_HASH:
        raise ValueError("Frozen model fingerprint changed; do not publish.")
    for name, expected in record["artifact_sha256"].items():
        if sha(FINAL / name) != expected:
            raise ValueError(f"Completed evaluation artifact changed: {name}")
    sources = [
        "UnderseaCableRisk/undersea_cables_master.csv",
        "data/model_ready/model_ready_supervised.csv",
        "outputs/tables/final_data_dictionary.csv",
        "outputs/tables/model_comparison_validation.csv",
        "outputs/tables/model_interpretation/random_forest_feature_importance.csv",
        "outputs/tables/indicator_analysis/indicator_registry.csv",
        "outputs/tables/data_split_summary.csv",
        "data/external/context_indicators.csv", "data/external/historical_incidents.csv",
        "outputs/final_evaluation_2026-11-02/evaluation_record.json",
        "outputs/final_evaluation_2026-11-02/partition_metrics.csv",
    ]
    fingerprints = {p: sha(ROOT / p) for p in sources}
    release_id = "final-2026-11-02-" + hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    predictors = protocol["predictors"]
    categorical = {"ocean_route", "operator_type", "chokepoint"}
    integers = {"age_years", "fiber_pairs", "n_landing_countries", "protected_burial", "route_redundancy", "fault_this_year"}
    observations = []
    for row in rows("data/model_ready/model_ready_supervised.csv"):
        item = {"cable_id": row["cable_id"], "year": int(row["year"])}
        item.update({p: row[p] if p in categorical else int(float(row[p])) if p in integers else float(row[p]) for p in predictors})
        item["fault_next_year"] = int(float(row["fault_next_year"]))
        item["partition"] = "train" if item["year"] <= 2022 else "validation" if item["year"] <= 2024 else "final_test"
        observations.append(item)
    if len(observations) != 4315 or len({(r["cable_id"], r["year"]) for r in observations}) != 4315:
        raise ValueError("Unexpected supervised panel or duplicate keys.")
    train = [r for r in observations if r["partition"] == "train"]
    registry = {r["feature"]: r for r in rows("outputs/tables/indicator_analysis/indicator_registry.csv")}
    dictionary = rows("outputs/tables/final_data_dictionary.csv")
    features = []
    for p in predictors:
        definition = registry[p]
        values = [r[p] for r in train]
        features.append({"name": p, "label": definition["label"], "group": definition["indicator_group"],
                         "unit": definition["unit"], "description": definition["interpretation"],
                         "qualification": definition["qualification"], "kind": "category" if p in categorical else "integer" if p in integers else "number",
                         "categories": sorted(set(values)) if p in categorical else [],
                         "train_min": None if p in categorical else min(values),
                         "train_max": None if p in categorical else max(values),
                         "missing_train": 0})
    validations = rows("outputs/tables/model_comparison_validation.csv")
    metric_keys = ["accuracy", "precision", "recall", "f1", "pr_auc", "roc_auc", "TN", "FP", "FN", "TP"]
    def metrics(row):
        return {k: int(row[k]) if k in {"TN", "FP", "FN", "TP"} else float(row[k]) for k in metric_keys}
    models = [{"id": r["model"], "selected": r["model"] == "random_forest", "validation": metrics(r),
               "parameters": json.loads(r["parameters"]), "final_test": record["final_test"] if r["model"] == "random_forest" else None} for r in validations]
    splits = [{**r, **{k: float(r[k]) if k == "prevalence" else int(r[k]) for k in ["min_year", "max_year", "rows", "unique_cables", "positives", "negatives", "prevalence"]}} for r in rows("outputs/tables/data_split_summary.csv")]
    for split in splits:
        actual = [r for r in observations if r["partition"] == split["partition"]]
        if len(actual) != split["rows"] or sum(r["fault_next_year"] for r in actual) != split["positives"]:
            raise ValueError("Split totals do not match exported records.")
    # Verify published validation and final-test confusion matrices, without inference.
    for result in [r["validation"] for r in models] + [record["final_test"]]:
        n = sum(result[k] for k in ["TN", "FP", "FN", "TP"])
        if abs((result["TN"] + result["TP"]) / n - result["accuracy"]) > 1e-12:
            raise ValueError("Saved confusion counts do not reconcile with accuracy.")
    importance = [{"feature": r["feature"], "importance": float(r["importance"])} for r in rows("outputs/tables/model_interpretation/random_forest_feature_importance.csv")]
    grouped = defaultdict(float)
    for row in importance:
        encoded = row["feature"].split("__", 1)[1]
        key = next((p for p in predictors if encoded == p or encoded.startswith(p + "_")), None)
        if key is None:
            raise ValueError(f"Unmapped encoded feature: {encoded}")
        grouped[key] += row["importance"]
    raw = rows("UnderseaCableRisk/undersea_cables_master.csv")
    if len(raw) != 4821 or any(not r[p] for r in raw for p in predictors):
        raise ValueError("Source row count or missing-predictor audit changed.")
    context = [{**r, "value": float(r["value"])} for r in rows("data/external/context_indicators.csv")]
    incidents = [{**r, "telecom_cables_damaged": int(r["telecom_cables_damaged"]) if r["telecom_cables_damaged"] else None} for r in rows("data/external/historical_incidents.csv")]
    if any(not r["source_url"].startswith("https://") for r in context + incidents):
        raise ValueError("External records require source URLs.")
    snapshot = {
        "schema_version": 1, "release_id": release_id, "title": "Predicting Next-Year Fault Occurrence in Global Undersea Cable Systems Using Infrastructure and Operational Indicators",
        "completed_at": record["completed_at_utc"], "model_sha256": EXPECTED_MODEL_HASH,
        "source_url": "https://www.kaggle.com/datasets/sergionefedov/undersea-cables-and-global-digital-infrastructure",
        "origin": "Publisher-declared 100% computer-generated (synthetic) dataset; not a verified cable-fault registry.",
        "counts": {"raw": len(raw), "eligible": len(observations), "cables_raw": len({r["cable_id"] for r in raw}), "unlabeled": sum(not r["fault_next_year"] for r in raw), "unresolved": 6, "predictors": len(predictors), "encoded": len(importance)},
        "features": features, "dictionary": dictionary, "splits": splits, "models": models,
        "partition_metrics": [{**r, **metrics(r), "rows": int(r["rows"])} for r in rows("outputs/final_evaluation_2026-11-02/partition_metrics.csv")],
        "importance_encoded": importance,
        "importance_grouped": sorted([{"feature": k, "importance": v} for k, v in grouped.items()], key=lambda r: -r["importance"]),
        "context": context, "incidents": incidents, "source_sha256": fingerprints,
        "example": {p: train[0][p] for p in predictors},
        "example_source": {"cable_id": train[0]["cable_id"], "year": train[0]["year"], "partition": "train"},
    }
    destination = WEB / "public/data"
    write_json(destination / "research.json", snapshot)
    write_json(destination / "observations.json", observations)
    write_json(WEB / "src/release.json", {"release_id": release_id, "model_sha256": EXPECTED_MODEL_HASH})
    artifact_dir = WEB / "backend/artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(model, artifact_dir / "random_forest.joblib")
    write_json(artifact_dir / "manifest.json", {"release_id": release_id, "model_sha256": EXPECTED_MODEL_HASH,
               "predictors": predictors, "features": features, "versions": protocol["versions"], "decision_rule": protocol["decision_rule"]})
    print(f"Published {release_id}: {len(observations)} existing rows, {len(models)} saved validation results. No model fitted or evaluated.")


if __name__ == "__main__":
    main()
