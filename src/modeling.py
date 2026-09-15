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
        "dummy_baseline": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=config.RANDOM_SEED),
        "decision_tree": DecisionTreeClassifier(max_depth=6, min_samples_leaf=10, class_weight="balanced", random_state=config.RANDOM_SEED),
        "random_forest": RandomForestClassifier(n_estimators=250, max_depth=10, min_samples_leaf=3, max_features="sqrt", class_weight="balanced", random_state=config.RANDOM_SEED, n_jobs=-1),
    }

def make_pipeline(name: str, estimator=None, *, predictors=None):
    if estimator is None: estimator = candidate_estimators()[name]
    predictors = list(predictors or config.PREDICTORS)
    categorical = [c for c in config.CATEGORICAL_PREDICTORS if c in predictors]
    numeric = [c for c in predictors if c not in categorical]
    return Pipeline([("preprocess", build_preprocessor(scale_numeric=(name == "logistic_regression"), categorical_predictors=categorical, numerical_predictors=numeric)), ("model", estimator)])

def fit_and_compare(train: pd.DataFrame, validation: pd.DataFrame, *, predictors=None, artifact_suffix=""):
    predictors = list(predictors or config.PREDICTORS)
    X_train, y_train = train[predictors], train[config.TARGET_COLUMN].astype(int)
    X_val, y_val = validation[predictors], validation[config.TARGET_COLUMN].astype(int)
    rows = []; fitted = {}
    for name in candidate_estimators():
        pipe = make_pipeline(name, predictors=predictors); pipe.fit(X_train, y_train)
        metrics = evaluate_pipeline(pipe, X_val, y_val)
        metrics.update({"model": name, "parameters": json.dumps(pipe.named_steps["model"].get_params(), default=str, sort_keys=True)})
        rows.append(metrics); fitted[name] = pipe
        joblib.dump(pipe, config.MODELS_DIR / f"{name}{artifact_suffix}.joblib")
    return pd.DataFrame(rows), fitted

def expanding_window_folds(df: pd.DataFrame):
    """Return chronological train/validation folds within 2015–2022."""
    folds = []
    for validation_year in range(2019, 2023):
        train = df[df[config.YEAR_COLUMN] < validation_year].copy()
        validation = df[df[config.YEAR_COLUMN] == validation_year].copy()
        if len(train) and len(validation) and train[config.TARGET_COLUMN].nunique() == 2 and validation[config.TARGET_COLUMN].nunique() == 2:
            folds.append((f"through_{validation_year-1}_to_{validation_year}", train, validation))
    return folds

def temporal_cv_scores(df: pd.DataFrame, *, predictors=None) -> pd.DataFrame:
    predictors = list(predictors or config.PREDICTORS)
    rows = []
    for fold_name, train, validation in expanding_window_folds(df):
        for name in candidate_estimators():
            pipe = make_pipeline(name, predictors=predictors)
            pipe.fit(train[predictors], train[config.TARGET_COLUMN].astype(int))
            metrics = evaluate_pipeline(pipe, validation[predictors], validation[config.TARGET_COLUMN].astype(int))
            metrics.update({"model": name, "fold": fold_name, "train_max_year": int(train[config.YEAR_COLUMN].max()), "validation_year": int(validation[config.YEAR_COLUMN].iloc[0]), "n_train": len(train), "n_validation": len(validation)})
            rows.append(metrics)
    return pd.DataFrame(rows)

def select_model(comparison: pd.DataFrame) -> str:
    ranked = comparison.sort_values(["pr_auc", "f1", "recall"], ascending=False, kind="mergesort")
    return str(ranked.iloc[0]["model"])
