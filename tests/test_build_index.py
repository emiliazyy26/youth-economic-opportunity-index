"""UEOI 测试。"""

import pandas as pd

from uei.build_index import build_scores, min_max_score
from uei.clean_data import derive_housing_burden
from uei.config import UEOI_WEIGHTS


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


def test_housing_affordability_weight_is_positive_after_inversion():
    assert UEOI_WEIGHTS["housing_burden_score"] > 0


def test_build_scores_rewards_lower_housing_burden():
    df = pd.DataFrame(
        {
            "city": ["A", "B"],
            "year": [2025, 2025],
            "disposable_income": [50_000.0, 50_000.0],
            "gdp_per_capita": [100_000.0, 100_000.0],
            "population_growth": [0.01, 0.01],
            "innovation_index": [10.0, 10.0],
            "housing_burden": [0.20, 0.30],
        }
    )

    scores = build_scores(df).set_index("city")

    assert scores.loc["A", "housing_burden_score"] == 100.0
    assert scores.loc["B", "housing_burden_score"] == 0.0
    assert scores.loc["A", "ueoi_score"] > scores.loc["B", "ueoi_score"]
