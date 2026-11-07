"""Isolated plotting inputs; no production data generation or model evaluation."""
import pytest

from scripts.analyze_external import monthly_series


def test_monthly_plot_preserves_real_zero_and_missing_month_gap():
    rows = [dict(area_id='fixture', metric='presence', period_start='2024-01-01', value=0),
            dict(area_id='fixture', metric='presence', period_start='2024-03-01', value=5)]
    months, values = monthly_series(rows, '2024-01-01', '2024-04-01')
    assert months == ['2024-01', '2024-02', '2024-03']
    assert values == [0, None, 5]


def test_empty_plot_window_has_no_invented_measurements():
    assert monthly_series([], '2024-12-01', '2025-02-01') == (['2024-12', '2025-01'], [None, None])


@pytest.mark.parametrize('extra', [
    dict(area_id='other', metric='presence', period_start='2024-02-01', value=2),
    dict(area_id='fixture', metric='fishing', period_start='2024-02-01', value=2),
    dict(area_id='fixture', metric='presence', period_start='2024-01-01', value=2),
    dict(area_id='fixture', metric='presence', period_start='2025-01-01', value=2),
])
def test_plot_rejects_mixed_or_ambiguous_observations(extra):
    with pytest.raises(ValueError):
        monthly_series([dict(area_id='fixture', metric='presence', period_start='2024-01-01', value=1), extra],
                       '2024-01-01', '2025-01-01')
