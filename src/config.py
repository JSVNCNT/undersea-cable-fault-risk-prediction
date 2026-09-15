from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "UnderseaCableRisk"
DATA_DIR = PROJECT_ROOT / "data"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_READY_DIR = DATA_DIR / "model_ready"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"
METRICS_DIR = OUTPUT_DIR / "metrics"
MODELS_DIR = OUTPUT_DIR / "models"
REPORTS_DIR = OUTPUT_DIR / "reports"

MASTER_PATH = RAW_DIR / "undersea_cables_master.csv"
REFERENCE_PATH = RAW_DIR / "cables_reference.csv"
DICTIONARY_PATH = RAW_DIR / "data_dictionary.csv"

RANDOM_SEED = 42
TARGET_COLUMN = "fault_next_year"
ID_COLUMN = "cable_id"
YEAR_COLUMN = "year"
ALPHA = 0.05
ALLOW_FINAL_TEST_EVALUATION = False

CATEGORICAL_PREDICTORS = ["ocean_route", "operator_type", "chokepoint"]
NUMERICAL_PREDICTORS = [
    "age_years", "fiber_pairs", "length_km", "n_landing_countries",
    "design_capacity_tbps", "lit_capacity_tbps", "utilization_pct",
    "protected_burial", "route_redundancy", "fault_this_year",
]
PREDICTORS = CATEGORICAL_PREDICTORS + NUMERICAL_PREDICTORS
TRAIN_YEARS = list(range(2015, 2023))
VALIDATION_YEARS = [2023, 2024]
FINAL_TEST_YEAR = 2025

def ensure_directories() -> None:
    for path in [INTERIM_DIR, PROCESSED_DIR, MODEL_READY_DIR, FIGURES_DIR,
                 TABLES_DIR, METRICS_DIR, MODELS_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    (FIGURES_DIR / "eda").mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "eda").mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "statistics").mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "model_interpretation").mkdir(parents=True, exist_ok=True)

