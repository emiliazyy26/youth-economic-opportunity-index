"""Tests for YEOI index building."""

import pandas as pd

from yei.build_index import build_scores, min_max_score
from yei.clean_data import derive_housing_burden, derive_rent_burden
from yei.config import YEOI_WEIGHTS
from yei.data_quality import passes_core_threshold, select_dimension_metric
from yei.sensitivity import sensitivity_shift


def _sample_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city": ["A", "B"],
            "year": [2025, 2025],
            "disposable_income": [50_000.0, 50_000.0],
            "gdp_per_capita": [100_000.0, 100_000.0],
            "population_growth": [0.01, 0.01],
            "innovation_index": [10.0, 10.0],
            "weighted_university_score": [50.0, 50.0],
            "listed_company_count": [100.0, 50.0],
            "high_tech_company_count": [200.0, 80.0],
            "rent_burden": [0.20, 0.30],
            "housing_burden": [0.20, 0.30],
            "job_posting_count": [pd.NA, pd.NA],
            "entry_salary": [pd.NA, pd.NA],
            "rent_monthly": [2000.0, 3000.0],
            "tertiary_ratio": [50.0, 50.0],
        }
    )


def test_min_max_score_basic():
    series = pd.Series([10, 20, 30])
    result = min_max_score(series)
    assert result.tolist() == [0.0, 50.0, 100.0]


def test_min_max_score_invert():
    series = pd.Series([10, 20, 30])
    result = min_max_score(series, invert=True)
    assert result.tolist() == [100.0, 50.0, 0.0]


def test_derive_housing_burden_fills_missing_rows_only():
    df = pd.DataFrame(
        {
            "house_price": [20_000.0, 24_000.0, None],
            "disposable_income": [50_000.0, 60_000.0, 70_000.0],
            "housing_burden": [None, 0.5, None],
        }
    )

    result = derive_housing_burden(df)

    assert result["housing_burden"].iloc[0] == 0.4
    assert result["housing_burden"].iloc[1] == 0.5
    assert pd.isna(result["housing_burden"].iloc[2])


def test_derive_rent_burden():
    df = pd.DataFrame(
        {
            "rent_monthly": [2500.0, None],
            "disposable_income": [50_000.0, 50_000.0],
            "rent_burden": [None, None],
        }
    )
    result = derive_rent_burden(df)
    assert result["rent_burden"].iloc[0] == 0.6
    assert pd.isna(result["rent_burden"].iloc[1])


def test_living_cost_weight_is_positive_after_inversion():
    assert YEOI_WEIGHTS["living_cost_score"] > 0


def test_build_scores_rewards_lower_rent_burden():
    df = _sample_panel()
    scores = build_scores(df).set_index("city")

    assert scores.loc["A", "living_cost_score"] == 100.0
    assert scores.loc["B", "living_cost_score"] == 0.0
    assert scores.loc["A", "yeoi_score"] > scores.loc["B", "yeoi_score"]


def test_enterprise_opportunity_uses_composite_scoring():
    df = _sample_panel()
    scores = build_scores(df).set_index("city")

    # City A has more listed + high-tech companies, should score higher
    assert scores.loc["A", "enterprise_opportunity_score"] == 100.0
    assert scores.loc["B", "enterprise_opportunity_score"] == 0.0


def test_enterprise_opportunity_works_with_single_metric():
    df = _sample_panel()
    df = df.drop(columns=["high_tech_company_count"])
    scores = build_scores(df).set_index("city")

    # Should still work with only listed_company_count
    assert scores.loc["A", "enterprise_opportunity_score"] == 100.0
    assert scores.loc["B", "enterprise_opportunity_score"] == 0.0


def test_select_dimension_metric_uses_rent_when_available():
    group = _sample_panel()
    metric, _values, source = select_dimension_metric(group, "living_cost")
    assert metric == "rent_burden"
    assert source == "rent_burden"


def test_passes_core_threshold():
    assert passes_core_threshold(pd.Series([1, 2, 3, 4, None] * 4))
    assert not passes_core_threshold(pd.Series([1, None, None, None, None] * 4))


def test_sensitivity_shift_runs():
    report = sensitivity_shift(_sample_panel(), shift=0.05)
    assert not report.empty
    assert "top5_rank_changes" in report.columns
