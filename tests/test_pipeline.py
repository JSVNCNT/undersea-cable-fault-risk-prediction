import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from src.data_loading import load_master_data
from src.data_validation import add_temporal_label_audit
from src.preprocessing import build_preprocessor
from src.evaluation import final_test_guard
from src.feature_engineering import add_causal_features
from src.modeling import expanding_window_folds
from src.data_validation import add_temporal_label_audit

def test_raw_load_and_schema():
    df=load_master_data(); assert df.shape==(4821,21); assert {"cable_id","year","fault_next_year"}.issubset(df.columns)
def test_none_and_target_values():
    df=load_master_data(); assert (df.chokepoint=="None").sum()==3986; assert set(df.fault_next_year.dropna().unique()) <= {0,1}
def test_temporal_gap_detection():
    df=add_temporal_label_audit(load_master_data()); assert int((~df.label_temporally_valid & df.fault_next_year.notna()).sum())==6
def test_redundancy_equivalence():
    df=load_master_data(); assert (df.is_low_redundancy==(df.route_redundancy<40).astype(int)).all()
def test_preprocessor_excludes_id():
    names=config.PREDICTORS; assert "cable_id" not in names; assert set(names)==set(config.CATEGORICAL_PREDICTORS+config.NUMERICAL_PREDICTORS)
def test_final_guard():
    try: final_test_guard(False)
    except PermissionError as exc: assert "locked" in str(exc).lower()
    else: raise AssertionError("final test guard did not raise")

def test_causal_features_do_not_use_target():
    df = load_master_data().sort_values(["cable_id", "year"])
    engineered = add_causal_features(df)
    assert "fault_next_year" in engineered.columns
    # The generated feature values are based on current/prior fields only.
    row = engineered[(engineered.cable_id == "CAB0001") & (engineered.year == 2017)].iloc[0]
    prior = engineered[(engineered.cable_id == "CAB0001") & (engineered.year == 2016)].iloc[0]
    assert row.fault_previous_year == prior.fault_this_year

def test_expanding_temporal_folds_are_ordered():
    df = add_temporal_label_audit(load_master_data())
    df = df[df.label_temporally_valid].copy()
    folds = expanding_window_folds(df)
    assert [v[2].year.iloc[0] for v in folds] == [2019, 2020, 2021, 2022]
    assert all(v[1].year.max() < v[2].year.min() for v in folds)
