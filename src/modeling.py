from pathlib import Path
from typing import Dict
import json
import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from . import config
from .preprocessing import build_preprocessor
from .evaluation import evaluate_pipeline

def candidate_estimators() -> Dict[str, object]:
    return {
        "dummy_baseline": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=config.RANDOM_SEED),
        "decision_tree": DecisionTreeClassifier(max_depth=6, min_samples_leaf=10, class_weight="balanced", random_state=config.RANDOM_SEED),
        "random_forest": RandomForestClassifier(n_estimators=250, max_depth=10, min_samples_leaf=3, max_features="sqrt", class_weight="balanced", random_state=config.RANDOM_SEED, n_jobs=-1),
    }

def make_pipeline(name: str, estimator=None) -> Pipeline:
    if estimator is None: estimator = candidate_estimators()[name]
    return Pipeline([("preprocess", build_preprocessor(scale_numeric=(name == "logistic_regression"))), ("model", estimator)])

def fit_and_compare(train: pd.DataFrame, validation: pd.DataFrame):
    X_train, y_train = train[config.PREDICTORS], train[config.TARGET_COLUMN].astype(int)
    X_val, y_val = validation[config.PREDICTORS], validation[config.TARGET_COLUMN].astype(int)
    rows = []; fitted = {}
    for name in candidate_estimators():
        pipe = make_pipeline(name); pipe.fit(X_train, y_train)
        metrics = evaluate_pipeline(pipe, X_val, y_val)
        metrics.update({"model": name, "parameters": json.dumps(pipe.named_steps["model"].get_params(), default=str, sort_keys=True)})
        rows.append(metrics); fitted[name] = pipe
        joblib.dump(pipe, config.MODELS_DIR / f"{name}.joblib")
    return pd.DataFrame(rows), fitted

def select_model(comparison: pd.DataFrame) -> str:
    ranked = comparison.sort_values(["pr_auc", "f1", "recall"], ascending=False, kind="mergesort")
    return str(ranked.iloc[0]["model"])

