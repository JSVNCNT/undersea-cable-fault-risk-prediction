import pandas as pd
import pytest

from src import config
from src.indicator_analysis import indicator_blocks, indicator_registry, validate_development_split
from src.modeling import make_pipeline


def test_registry_partitions_approved_predictors():
    registry = indicator_registry()
    blocks = indicator_blocks()
    assert registry.feature.is_unique
    assert set(blocks["infrastructure"]).isdisjoint(blocks["operational"])
    assert set(blocks["infrastructure"] + blocks["operational"]) == set(config.PREDICTORS)


@pytest.mark.parametrize("predictors", [["age_years"], ["ocean_route"]])
def test_single_type_subset_does_not_restore_unrequested_features(predictors):
    # Numeric-only and category-only fits must work with just that column.
    frame = pd.DataFrame({"age_years": [1, 2, 3, 4], "ocean_route": ["A", "B", "A", "B"]})
    pipeline = make_pipeline("logistic_regression", predictors=predictors)
    pipeline.fit(frame[predictors], [0, 1, 0, 1])
    assert len(pipeline.predict(frame[predictors])) == 4


def test_block_analysis_rejects_holdout_year():
    train = pd.DataFrame({"year": [2021, 2022], "cable_id": ["A", "B"], "fault_next_year": [0, 1]})
    validation = pd.DataFrame({"year": [2024, 2025], "cable_id": ["A", "B"], "fault_next_year": [0, 1]})
    with pytest.raises(ValueError, match="holdout"):
        validate_development_split(train, validation)
