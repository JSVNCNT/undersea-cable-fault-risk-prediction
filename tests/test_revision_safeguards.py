from copy import deepcopy
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config
from src.data_loading import load_csv, load_master_data
from src.data_validation import add_temporal_label_audit, forward_label_consistency, validate_values
from src.feature_engineering import add_causal_features, ENGINEERED_FEATURES
from src.preprocessing import build_preprocessor
from src.revision_analysis import clustered_ap_interval, require_development, validation_subgroups
from src.statistics import holm_adjust


def small_panel():
    return pd.DataFrame(dict(cable_id=["A","A","A","B"],year=[2020,2021,2023,2020],
                             fault_this_year=[0,1,0,0],fault_next_year=[1,0,np.nan,np.nan]))


def test_temporal_consecutive_gap_terminal_and_unsorted():
    frame = small_panel().iloc[[2,0,3,1]]
    result = add_temporal_label_audit(frame)
    assert list(result.index) == list(frame.index)
    assert result.loc[0,"label_temporally_valid"]
    assert not result.loc[1,"label_temporally_valid"]
    assert not result.loc[2,"label_temporally_valid"]
    assert not result.loc[3,"label_temporally_valid"]


def test_successor_label_consistency_detects_disagreement_without_bridging_gap():
    frame = small_panel()
    check = forward_label_consistency(frame)
    assert check.checkable.sum() == 1
    assert check.loc[0,"agrees_with_successor"]
    frame.loc[0,"fault_next_year"] = 0
    assert not forward_label_consistency(frame).loc[0,"agrees_with_successor"]


def test_real_source_full_validation_and_unique_keys():
    frame = load_master_data()
    validate_values(frame)
    assert not frame.duplicated(["cable_id","year"]).any()
    # True predictor missingness is permitted for the training-fitted imputer;
    # corruption, invalid values and missing calendar/ID fields are different.
    frame["age_years"] = frame["age_years"].astype(float)
    frame.loc[0,["age_years","length_km"]] = np.nan
    frame.loc[0,"ocean_route"] = np.nan
    validate_values(frame)


@pytest.mark.parametrize("field,value,match",[("protected_burial",2,"binary"),("length_km",-1,"Non-positive"),("age_years",0.5,"Non-integer"),("utilization_pct",101,"bounds"),("ocean_route","","Blank category")])
def test_value_validation_fails_closed(field,value,match):
    frame = load_master_data()
    if field == "age_years":
        frame[field] = frame[field].astype(float)
    frame.loc[0,field] = value
    with pytest.raises(ValueError,match=match):
        validate_values(frame)


def test_duplicate_keys_are_rejected():
    frame = load_master_data()
    frame = pd.concat([frame,frame.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match="Duplicate"):
        validate_values(frame)


def test_numeric_corruption_is_separate_from_blank_and_literal_none(tmp_path):
    path = tmp_path/"input.csv"
    path.write_text("year,chokepoint,fault_next_year\n2020,None,\nwrong,None,1\n",encoding="utf-8")
    with pytest.raises(ValueError,match="Numeric parsing failed in year"):
        load_csv(path,target_nullable=True)
    audit = load_csv(path,target_nullable=True,strict_numeric=False)
    assert audit.chokepoint.tolist() == ["None","None"]
    rows = {r["variable"]:r for r in audit.attrs["numeric_parsing_audit"]}
    assert rows["year"]["numeric_parse_failures"] == 1
    assert rows["fault_next_year"]["intentional_blanks"] == 1
    assert rows["fault_next_year"]["numeric_parse_failures"] == 0


def test_preprocessing_statistics_and_unseen_categories_use_training_only():
    train = pd.DataFrame(dict(age_years=[1.,3.,np.nan],ocean_route=["A","A",np.nan]))
    transformer = build_preprocessor(False,categorical_predictors=["ocean_route"],numerical_predictors=["age_years"])
    transformer.fit(train)
    statistics = deepcopy(transformer.named_transformers_["numeric"].named_steps["imputer"].statistics_)
    category_statistics = deepcopy(transformer.named_transformers_["categorical"].named_steps["imputer"].statistics_)
    result = transformer.transform(pd.DataFrame(dict(age_years=[1000.,np.nan],ocean_route=["NEW","A"])))
    np.testing.assert_array_equal(statistics,[2.])
    np.testing.assert_array_equal(category_statistics,["A"])
    np.testing.assert_array_equal(transformer.named_transformers_["numeric"].named_steps["imputer"].statistics_,statistics)
    assert np.asarray(result)[1,0] == 2.
    assert np.asarray(result)[0,1:].sum() == 0


def test_future_labels_and_future_observations_cannot_change_earlier_features():
    frame = load_master_data().query("cable_id == 'CAB0001'").copy()
    baseline = add_causal_features(frame)
    perturbed = frame.copy()
    perturbed["fault_next_year"] = 1 - perturbed["fault_next_year"]
    pd.testing.assert_frame_equal(baseline[ENGINEERED_FEATURES],add_causal_features(perturbed)[ENGINEERED_FEATURES])
    future = frame.year.gt(2018)
    perturbed.loc[future,"fault_this_year"] = 1 - perturbed.loc[future,"fault_this_year"]
    perturbed.loc[future,"lit_capacity_tbps"] += 10000
    pd.testing.assert_frame_equal(baseline.loc[~future,ENGINEERED_FEATURES],add_causal_features(perturbed).loc[~future,ENGINEERED_FEATURES])


def test_lag_does_not_bridge_missing_calendar_year():
    frame = load_master_data().query("cable_id == 'CAB0001'").copy().sort_values("year")
    # Removing a record must not make a two-year difference a one-year lag.
    middle = int(frame.year.iloc[1])
    frame = frame[frame.year.ne(middle)]
    result = add_causal_features(frame)
    assert result.loc[result.year.eq(middle+1),"fault_previous_year"].isna().all()
    assert result.loc[result.year.eq(middle+1),"lit_capacity_change_yoy"].isna().all()


def test_holm_matches_known_order_and_preserves_missing():
    np.testing.assert_allclose(holm_adjust([0.04,0.01,0.03]),[0.06,0.03,0.06])
    assert np.isnan(holm_adjust([np.nan,0.1])[0])


def test_supplementary_helpers_reject_final_year():
    with pytest.raises(ValueError,match="development"):
        require_development(pd.DataFrame(dict(cable_id=["A"],year=[2025])))


def load_script(name):
    path = Path(__file__).resolve().parents[1]/"scripts"/(name+".py")
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_development_runner_cannot_overwrite_completed_experiment(monkeypatch,tmp_path):
    runner = load_script("run_pipeline")
    (tmp_path/"outputs/final_evaluation_2026-11-02").mkdir(parents=True)
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    with pytest.raises(PermissionError,match="Final evaluation already exists"):
        runner.prepare_output_scope()
    for destination in [tmp_path, tmp_path/"outputs/replacement",tmp_path/"data/replacement",tmp_path.parent]:
        with pytest.raises(ValueError,match="protected"):
            runner.prepare_output_scope(destination)


def test_final_runner_refuses_repeat_before_loading_any_model(monkeypatch,tmp_path):
    runner = load_script("evaluate_final_holdout")
    reserved = tmp_path/"completed"; reserved.mkdir()
    monkeypatch.setattr(runner,"RUN",reserved)
    monkeypatch.setattr(runner.joblib,"load",lambda *_: pytest.fail("No model should be loaded for a repeat request"))
    with pytest.raises(FileExistsError,match="already reserved or completed"):
        runner.preflight()


def test_validation_bootstrap_is_reproducible_and_paired():
    frame = pd.DataFrame(dict(cable_id=["A","A","B","B","C","C"],year=[2023,2024]*3,fault_next_year=[0,1]*3))
    scores={"random_forest":np.array([.1,.8]*3),"logistic_regression":np.array([.2,.7]*3)}
    first=clustered_ap_interval(frame,scores,repeats=20)
    pd.testing.assert_frame_equal(first,clustered_ap_interval(frame,scores,repeats=20))
    assert first.iloc[-1].estimate == 0
    assert first.iloc[-1].ci_low == 0
