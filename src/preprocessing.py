from typing import Dict, Tuple
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config

def build_preprocessor(scale_numeric: bool = True, *, categorical_predictors=None, numerical_predictors=None) -> ColumnTransformer:
    categorical_predictors = list(categorical_predictors or config.CATEGORICAL_PREDICTORS)
    numerical_predictors = list(numerical_predictors or config.NUMERICAL_PREDICTORS)
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("numeric", numeric, numerical_predictors),
                              ("categorical", categorical, categorical_predictors)],
                             remainder="drop")

def make_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = [config.ID_COLUMN, config.YEAR_COLUMN] + config.PREDICTORS + [config.TARGET_COLUMN]
    return df.loc[:, cols].copy()

def chronological_split(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    return {
        "train": df[df[config.YEAR_COLUMN].isin(config.TRAIN_YEARS)].copy(),
        "validation": df[df[config.YEAR_COLUMN].isin(config.VALIDATION_YEARS)].copy(),
        "final_test": df[df[config.YEAR_COLUMN] == config.FINAL_TEST_YEAR].copy(),
    }

def split_summary(splits: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in splits.items():
        y = frame[config.TARGET_COLUMN].dropna().astype(int)
        rows.append({"partition": name, "min_year": frame[config.YEAR_COLUMN].min() if len(frame) else None,
                     "max_year": frame[config.YEAR_COLUMN].max() if len(frame) else None,
                     "rows": len(frame), "unique_cables": frame[config.ID_COLUMN].nunique(),
                     "positives": int((y == 1).sum()), "negatives": int((y == 0).sum()),
                     "prevalence": float((y == 1).mean()) if len(y) else None})
    return pd.DataFrame(rows)
