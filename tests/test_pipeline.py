import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config
from src.data_loading import load_master_data
from src.data_validation import add_temporal_label_audit
from src.preprocessing import build_preprocessor
from src.evaluation import final_test_guard

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

