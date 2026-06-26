"""Tests for Streamlit dashboard helper and figure-building functions."""

import pandas as pd
import plotly.graph_objects as go

from streamlit_app import (
    DIMENSION_KEYS,
    add_city_group,
    build_dimension_bar,
    build_group_boxplot,
    build_radar_chart,
    build_ranking_chart,
    build_sensitivity_chart,
    build_top5_radar,
    build_tradeoff_scatter,
    build_trend_chart,
    format_dimension_scores,
)


def _make_scores_df(n_cities: int = 5, year: int = 2025) -> pd.DataFrame:
    cities = ["Beijing", "Shanghai", "Shenzhen", "Hangzhou", "Harbin"][:n_cities]
    rows = []
    for i, city in enumerate(cities):
        row = {"city": city, "year": year, "yeoi_score": 80.0 - i * 10, "rank": i + 1}
        for col in DIMENSION_KEYS:
            row[col] = 60.0 - i * 5
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# add_city_group
# ---------------------------------------------------------------------------


def test_add_city_group_assigns_correct_groups():
    df = pd.DataFrame({"city": ["Beijing", "Hangzhou", "Harbin", "Unknown City"]})
    result = add_city_group(df)
    assert result.loc[0, "city_group"] == "megacity"
    assert result.loc[1, "city_group"] == "strong_second_tier"
    assert result.loc[2, "city_group"] == "control"
    assert result.loc[3, "city_group"] == "control"


def test_add_city_group_does_not_mutate_input():
    df = pd.DataFrame({"city": ["Beijing"]})
    original = df.copy()
    add_city_group(df)
    pd.testing.assert_frame_equal(df, original)


# ---------------------------------------------------------------------------
# format_dimension_scores
# ---------------------------------------------------------------------------


def test_format_dimension_scores_returns_tidy_df():
    row = pd.Series({k: 50.0 + i * 5 for i, k in enumerate(DIMENSION_KEYS)})
    result = format_dimension_scores(row)
    assert len(result) == 6
    assert list(result.columns) == ["dimension", "score", "weight"]
    assert result["dimension"].iloc[0] == "Job Opportunity"
    assert result["weight"].sum() == 1.0


def test_format_dimension_scores_handles_missing_keys():
    row = pd.Series({"job_opportunity_score": 70.0})
    result = format_dimension_scores(row)
    assert len(result) == 6
    assert result["score"].iloc[0] == 70.0
    assert pd.isna(result["score"].iloc[1])


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def test_build_ranking_chart_returns_figure():
    scores = _make_scores_df()
    fig = build_ranking_chart(scores, highlight_city="Beijing")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 5


def test_build_ranking_chart_no_highlight():
    scores = _make_scores_df()
    fig = build_ranking_chart(scores, highlight_city=None)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 5


def test_build_dimension_bar_returns_figure():
    row = pd.Series({k: 60.0 for k in DIMENSION_KEYS})
    avg = pd.Series({k: 50.0 for k in DIMENSION_KEYS})
    top5 = pd.Series({k: 70.0 for k in DIMENSION_KEYS})
    fig = build_dimension_bar(row, avg, top5)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3


def test_build_dimension_bar_without_optionals():
    row = pd.Series({k: 60.0 for k in DIMENSION_KEYS})
    fig = build_dimension_bar(row, None, None)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_build_radar_chart_returns_figure():
    row = pd.Series({k: 60.0 for k in DIMENSION_KEYS})
    avg = pd.Series({k: 50.0 for k in DIMENSION_KEYS})
    fig = build_radar_chart(row, avg, None)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_build_tradeoff_scatter_returns_figure():
    df = pd.DataFrame(
        {
            "city": ["Beijing", "Shanghai", "Harbin"],
            "year": [2025, 2025, 2025],
            "entry_salary": [80000.0, 85000.0, 50000.0],
            "housing_burden": [0.65, 0.60, 0.20],
            "yeoi_score": [70.0, 65.0, 30.0],
            "rank": [1, 2, 10],
        }
    )
    fig = build_tradeoff_scatter(df, "entry_salary", "housing_burden", "Beijing")
    assert isinstance(fig, go.Figure)


def test_build_tradeoff_scatter_empty_data():
    df = pd.DataFrame({"city": [], "entry_salary": [], "housing_burden": []})
    fig = build_tradeoff_scatter(df, "entry_salary", "housing_burden", "Beijing")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_trend_chart_returns_figure():
    cities = ["Beijing", "Shanghai", "Harbin"]
    rows = []
    for year in range(2021, 2026):
        for i, city in enumerate(cities):
            rows.append(
                {
                    "city": city,
                    "year": year,
                    "yeoi_score": 70.0 - i * 5,
                    "rank": i + 1,
                }
            )
    scores = pd.DataFrame(rows)
    fig = build_trend_chart(scores, cities, "yeoi_score")
    assert isinstance(fig, go.Figure)


def test_build_trend_chart_rank_reverses_yaxis():
    cities = ["Beijing", "Shanghai"]
    rows = []
    for year in range(2021, 2026):
        for i, city in enumerate(cities):
            rows.append({"city": city, "year": year, "rank": i + 1})
    scores = pd.DataFrame(rows)
    fig = build_trend_chart(scores, cities, "rank")
    assert isinstance(fig, go.Figure)


def test_build_sensitivity_chart_returns_figure():
    df = pd.DataFrame(
        {
            "dimension": ["job_opportunity_score", "city_base_score"],
            "direction": ["+", "-"],
            "weight_delta": [0.05, -0.05],
            "top5_rank_changes": [0, 4],
        }
    )
    fig = build_sensitivity_chart(df)
    assert isinstance(fig, go.Figure)


def test_build_sensitivity_chart_empty_returns_empty_figure():
    fig = build_sensitivity_chart(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_group_boxplot_returns_figure():
    scores = _make_scores_df()
    fig = build_group_boxplot(scores)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0


def test_build_top5_radar_returns_figure():
    scores = _make_scores_df()
    fig = build_top5_radar(scores)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 5
