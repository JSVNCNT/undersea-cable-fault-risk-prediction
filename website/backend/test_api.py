import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from website.backend import app as module

PUBLIC = Path(__file__).resolve().parents[1] / "public/data"
SNAPSHOT = json.loads((PUBLIC / "research.json").read_text(encoding="utf-8"))
EXAMPLE = SNAPSHOT["example"]  # existing TRAINING record only, never a new final-test evaluation


@pytest.fixture
def client():
    module.recent_requests.clear()
    with TestClient(module.app) as instance:
        yield instance


def test_health_hash_and_valid_inference(client):
    assert client.get("/api/health").json()["status"] == "ready"
    response = client.post("/api/predict", json=EXAMPLE)
    assert response.status_code == 200
    result = response.json()
    direct = module.app.state.pipeline.predict_proba(pd.DataFrame([EXAMPLE], columns=module.app.state.manifest["predictors"]))[0]
    assert result["prediction"] == int(np.argmax(direct))
    assert result["positive_class_score"] == pytest.approx(float(direct[1]), abs=1e-15)
    assert result["model_sha256"] == module.EXPECTED_HASH
    assert result["release_id"] == SNAPSHOT["release_id"]


@pytest.mark.parametrize("change", [{"fault_next_year": 1}, {"age_years": -1}, {"age_years": True}, {"age_years": "3"}, {"utilization_pct": 101}, {"fiber_pairs": 2.5}, {"protected_burial": 2}, {"ocean_route": "unknown"}, {"chokepoint": ""}])
def test_reject_bad_inputs(client, change):
    assert client.post("/api/predict", json={**EXAMPLE, **change}).status_code == 422


def test_missing_and_nonfinite(client):
    assert client.post("/api/predict", json={}).status_code == 422
    assert client.post("/api/predict", content=json.dumps({**EXAMPLE, "length_km": float("inf")}), headers={"Content-Type": "application/json"}).status_code == 422


def test_none_is_literal_category(client):
    assert client.post("/api/predict", json={**EXAMPLE, "chokepoint": "None"}).status_code == 200


def test_out_of_training_range_warning(client):
    response = client.post("/api/predict", json={**EXAMPLE, "age_years": 100})
    assert response.status_code == 200
    assert "age_years" in response.json()["warnings"][0]


def test_unavailable_never_mocks(client):
    original = module.app.state.pipeline
    module.app.state.pipeline = None
    try:
        assert client.get("/api/health").status_code == 503
        assert client.post("/api/predict", json=EXAMPLE).status_code == 503
    finally:
        module.app.state.pipeline = original


def test_limits_and_cors(client):
    assert client.post("/api/predict", content="x" * 9000).status_code == 413
    response = client.options("/api/predict", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    response = client.options("/api/predict", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers


def test_model_artifact_unchanged():
    assert hashlib.sha256((module.ARTIFACTS / "random_forest.joblib").read_bytes()).hexdigest() == module.EXPECTED_HASH


def test_published_importance_matches_the_frozen_pipeline(client):
    pipeline = module.app.state.pipeline
    names = list(pipeline.named_steps["preprocess"].get_feature_names_out())
    actual = dict(zip(names, pipeline.named_steps["model"].feature_importances_))
    assert len(actual) == 31
    for row in SNAPSHOT["importance_encoded"]:
        assert actual[row["feature"]] == pytest.approx(row["importance"], abs=1e-14)


def test_model_hash_failure_prevents_deserialization(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"model_sha256": module.EXPECTED_HASH}), encoding="utf-8")
    (tmp_path / "random_forest.joblib").write_bytes(b"invalid test artifact")
    monkeypatch.setattr(module, "ARTIFACTS", tmp_path)
    def forbidden_load(*args, **kwargs):
        pytest.fail("An untrusted model must never be deserialized")
    monkeypatch.setattr(module.joblib, "load", forbidden_load)
    with pytest.raises(ValueError, match="integrity"):
        module.load_frozen_pipeline()


def test_incompatible_runtime_prevents_deserialization(monkeypatch):
    monkeypatch.setattr(module, "version", lambda distribution: "0.0.0")
    def forbidden_load(*args, **kwargs):
        pytest.fail("An incompatible runtime must not load the model")
    monkeypatch.setattr(module.joblib, "load", forbidden_load)
    with pytest.raises(ValueError, match="Incompatible"):
        module.load_frozen_pipeline()


def test_startup_failure_is_unavailable(monkeypatch):
    def unavailable():
        raise ValueError("Simulated integrity failure")
    monkeypatch.setattr(module, "load_frozen_pipeline", unavailable)
    with TestClient(module.app) as instance:
        assert instance.get("/api/health").status_code == 503
        assert instance.post("/api/predict", json=EXAMPLE).status_code == 503


def test_global_rate_limit_and_busy_service(client):
    module.recent_requests.extend([module.time.monotonic()] * 60)
    limited = client.post("/api/predict", json=EXAMPLE)
    assert limited.status_code == 429 and limited.headers["retry-after"] == "60"
    module.recent_requests.clear()
    assert module.inference_slot.acquire(blocking=False)
    try:
        busy = client.post("/api/predict", json=EXAMPLE)
        assert busy.status_code == 429 and busy.headers["retry-after"] == "3"
    finally:
        module.inference_slot.release()
