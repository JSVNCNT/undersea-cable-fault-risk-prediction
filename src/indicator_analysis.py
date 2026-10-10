"""Explicit indicator definitions and development-only block comparisons.

The grouping describes each variable's analytical role, not a verified physical
fault mechanism. It never changes the approved primary feature list.
"""
import pandas as pd

from . import config
from .evaluation import evaluate_pipeline
from .modeling import make_pipeline


# feature, block, label, unit, interpretation, qualification
INDICATORS = [
    ("ocean_route", "infrastructure", "Route region", "category", "Broad geographic setting", "A regional category does not measure vessel exposure or route geometry."),
    ("chokepoint", "infrastructure", "Chokepoint corridor", "category", "Shared geographic corridor", "A corridor label does not locate a break or quantify anchoring activity."),
    ("age_years", "infrastructure", "Cable age", "years", "Asset lifecycle position", "Age changes annually; it does not certify wear, condition, or remaining life."),
    ("fiber_pairs", "infrastructure", "Fiber pairs", "count", "Physical optical configuration", "Pair count describes configuration, not fault tolerance by itself."),
    ("length_km", "infrastructure", "Cable length", "km", "Physical network extent", "Total length does not provide seabed conditions or per-kilometer failure exposure."),
    ("n_landing_countries", "infrastructure", "Landing-country count", "count", "Geographic connection extent", "Country count is not a landing-station inventory or dependency map."),
    ("design_capacity_tbps", "infrastructure", "Design capacity", "Tbps", "Potential transmission capacity", "Design potential differs from activated capacity and carried traffic."),
    ("protected_burial", "infrastructure", "Burial/armor flag", "0/1", "Reported physical protection", "A binary flag does not measure burial depth, protected extent, or verified protection quality."),
    ("route_redundancy", "infrastructure", "Route cable count", "count", "Route-year network multiplicity", "Other cables on a route do not establish independent paths or spare restoration capacity."),
    ("operator_type", "operational", "Operator category", "category", "Organizational operating context", "Owner class does not establish maintenance quality or response time."),
    ("lit_capacity_tbps", "operational", "Activated capacity", "Tbps", "Capacity put into service", "Activated capacity is not measured traffic; it also depends on infrastructure."),
    ("utilization_pct", "operational", "Capacity utilization", "%", "Supplied operating-load indicator", "No traffic telemetry or verified denominator is supplied."),
    ("fault_this_year", "operational", "Current-year fault", "0/1", "Prior experience at the prediction cutoff", "Available only after the current year closes; cause and repair condition remain unknown."),
]


def indicator_registry() -> pd.DataFrame:
    registry = pd.DataFrame(INDICATORS, columns=["feature", "indicator_group", "label", "unit", "interpretation", "qualification"])
    if registry.feature.duplicated().any() or set(registry.feature) != set(config.PREDICTORS):
        raise ValueError("Indicator registry must partition every approved primary predictor exactly once.")
    registry["prediction_cutoff"] = "end of observation year t; predict year t+1"
    registry["data_origin"] = "publisher-declared synthetic panel"
    return registry


def indicator_blocks() -> dict[str, list[str]]:
    registry = indicator_registry()
    blocks = {group: registry.loc[registry.indicator_group == group, "feature"].tolist()
              for group in ("infrastructure", "operational")}
    blocks["combined"] = list(config.PREDICTORS)
    return blocks


def validate_development_split(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    for name, frame, years in (("train", train, config.TRAIN_YEARS),
                               ("validation", validation, config.VALIDATION_YEARS)):
        if frame.empty or not frame[config.YEAR_COLUMN].isin(years).all():
            raise ValueError(f"{name} must contain only its approved development years; final holdout is prohibited.")
        if frame[config.TARGET_COLUMN].isna().any() or set(frame[config.TARGET_COLUMN].unique()) != {0, 1}:
            raise ValueError(f"{name} requires populated binary labels with both classes.")
        if frame.duplicated([config.ID_COLUMN, config.YEAR_COLUMN]).any():
            raise ValueError(f"{name} contains duplicate cable-year keys.")
    if train[config.YEAR_COLUMN].max() >= validation[config.YEAR_COLUMN].min():
        raise ValueError("Training years must precede validation years.")


def compare_indicator_blocks(train: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    """Compare fixed estimators without saving models or changing selection.

    Average precision uses the repository's pr_auc name. All six fits use the
    same rows, default decision threshold, seed and model parameters.
    """
    validate_development_split(train, validation)
    rows = []
    prevalence = float(validation[config.TARGET_COLUMN].mean())
    for group, predictors in indicator_blocks().items():
        for model in ("logistic_regression", "random_forest"):
            pipeline = make_pipeline(model, predictors=predictors)
            pipeline.fit(train[predictors], train[config.TARGET_COLUMN].astype(int))
            result = evaluate_pipeline(pipeline, validation[predictors], validation[config.TARGET_COLUMN].astype(int))
            result.update(indicator_group=group, model=model, predictor_count=len(predictors),
                          n_train=len(train), n_validation=len(validation),
                          validation_prevalence=prevalence, ap_above_prevalence=result["pr_auc"] - prevalence,
                          evidence_status="exploratory development comparison; final test locked")
            rows.append(result)
    return pd.DataFrame(rows)
