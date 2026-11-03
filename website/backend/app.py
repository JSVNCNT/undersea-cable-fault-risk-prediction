"""Inference only. Never imports training, scoring, or final-evaluation runners."""
from collections import deque
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from threading import BoundedSemaphore, Lock
import hashlib
import json
import logging
import os
import time

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
EXPECTED_HASH = "4228e0bb067a895e4035229a275d0eb77007afc65c8f832b5ff8461673b56bfb"
LIMITATION = "Academic demonstration using a publisher-declared computer-generated dataset. The score is not a calibrated real-world fault probability or an operational alert."
logger = logging.getLogger("undersea_api")


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    ocean_route: str = Field(min_length=1, max_length=40)
    operator_type: str = Field(min_length=1, max_length=40)
    chokepoint: str = Field(min_length=1, max_length=40)
    age_years: int = Field(ge=0, le=200)
    fiber_pairs: int = Field(ge=1, le=10000)
    length_km: float = Field(gt=0, le=100000)
    n_landing_countries: int = Field(ge=1, le=250)
    design_capacity_tbps: float = Field(gt=0, le=1000000)
    lit_capacity_tbps: float = Field(ge=0, le=1000000)
    utilization_pct: float = Field(ge=0, le=100)
    protected_burial: int = Field(ge=0, le=1)
    route_redundancy: int = Field(ge=0, le=100000)
    fault_this_year: int = Field(ge=0, le=1)


class PredictionOutput(BaseModel):
    prediction: int
    positive_class_score: float
    model: str
    model_sha256: str
    release_id: str
    decision_rule: str
    warnings: list[str]
    limitation: str


class BodyLimitMiddleware:
    """Bound request bytes before JSON parsing; no uploads are accepted."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        messages, size = deque(), 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 8192:
                return await JSONResponse({"detail": "Request exceeds 8 KiB limit."}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.popleft() if messages else await receive()
        await self.app(scope, replay, send)


def load_frozen_pipeline():
    manifest = json.loads((ARTIFACTS / "manifest.json").read_text(encoding="utf-8"))
    model_path = ARTIFACTS / "random_forest.joblib"
    if manifest["model_sha256"] != EXPECTED_HASH or hashlib.sha256(model_path.read_bytes()).hexdigest() != EXPECTED_HASH:
        raise ValueError("Frozen model integrity check failed.")
    # joblib/pickle is executable: ONLY load this hash-verified, repository-owned artifact.
    distributions = {"sklearn": "scikit-learn", "pandas": "pandas", "numpy": "numpy", "joblib": "joblib"}
    for key, distribution in distributions.items():
        if version(distribution) != manifest["versions"][key]:
            raise ValueError(f"Incompatible {distribution} runtime; use backend requirements.")
    pipeline = joblib.load(model_path)
    if list(pipeline.feature_names_in_) != manifest["predictors"] or list(pipeline.classes_) != [0, 1]:
        raise ValueError("Unexpected frozen pipeline schema.")
    return pipeline, manifest


@asynccontextmanager
async def lifespan(app):
    app.state.pipeline, app.state.manifest = None, None
    try:
        app.state.pipeline, app.state.manifest = load_frozen_pipeline()
    except Exception:
        logger.exception("Frozen model unavailable; prediction endpoints remain disabled.")
    yield


app = FastAPI(title="Undersea Research Prediction Demonstrator", version="1.0.0", lifespan=lifespan)
origins = [v.strip().rstrip("/") for v in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if v.strip()]
if "*" in origins:
    raise ValueError("ALLOWED_ORIGINS must list exact website origins, not *.")
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
inference_slot = BoundedSemaphore(1)
rate_lock = Lock()
recent_requests = deque()


@app.exception_handler(RequestValidationError)
async def validation_error(request, exception):
    # Do not echo user inputs; nonfinite JSON values must not break error serialization.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exception.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


@app.get("/api/health")
def health():
    ready = app.state.pipeline is not None
    return JSONResponse({"status": "ready" if ready else "unavailable", "model": "random_forest", "model_sha256": EXPECTED_HASH,
                         "release_id": app.state.manifest["release_id"] if ready else None}, status_code=200 if ready else 503)


def infer(values):
    if not inference_slot.acquire(blocking=False):
        raise HTTPException(429, "Prediction service busy; try again shortly.", headers={"Retry-After": "3"})
    try:
        frame = pd.DataFrame([values], columns=app.state.manifest["predictors"])
        probabilities = app.state.pipeline.predict_proba(frame)[0]
        # Use the saved [0, 1] class order and sklearn argmax rule, including ties to 0.
        return int(app.state.pipeline.classes_[int(np.argmax(probabilities))]), float(probabilities[1])
    finally:
        inference_slot.release()


@app.post("/api/predict", response_model=PredictionOutput)
async def predict(payload: PredictionInput, request: Request):
    if app.state.pipeline is None:
        raise HTTPException(503, "Prediction service unavailable. Frozen model is not ready.")
    with rate_lock:
        now = time.monotonic()
        while recent_requests and recent_requests[0] <= now - 60:
            recent_requests.popleft()
        # Per-process global cap, not a substitute for platform-level abuse protection.
        if len(recent_requests) >= 60:
            raise HTTPException(429, "Demonstrator limit reached; retry in a minute.", headers={"Retry-After": "60"})
        recent_requests.append(now)
    values = payload.model_dump()
    warnings = []
    for feature in app.state.manifest["features"]:
        value = values[feature["name"]]
        if feature["kind"] == "category" and value not in feature["categories"]:
            raise HTTPException(422, f"{feature['name']} must be one of the published training categories.")
        if feature["kind"] != "category" and not feature["train_min"] <= value <= feature["train_max"]:
            warnings.append(f"{feature['name']} is outside the observed training range ({feature['train_min']} to {feature['train_max']}).")
    try:
        prediction, score = await run_in_threadpool(infer, values)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Inference failed.")
        raise HTTPException(503, "Prediction service unavailable. No result was produced.") from None
    return PredictionOutput(prediction=prediction, positive_class_score=score, model="random_forest", model_sha256=EXPECTED_HASH,
                            release_id=app.state.manifest["release_id"], decision_rule=app.state.manifest["decision_rule"], warnings=warnings, limitation=LIMITATION)
