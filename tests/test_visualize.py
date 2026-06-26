"""Tests for the visualize module."""

import pandas as pd

from yei.visualize import (
    plot_dimension_radar,
    plot_income_housing_scatter,
    plot_yeoi_ranking,
    plot_yeoi_trend,
)

SCORE_COLS = [
    "job_opportunity_score",
    "starting_income_score",
    "living_cost_score",
    "business_ecosystem_score",
    "growth_potential_score",
    "city_base_score",
]


def test_plot_yeoi_ranking_writes_file(tmp_path):
    scores = pd.DataFrame(
        {
            "city": ["A", "B"],
            "year": [2025, 2025],
            "yeoi_score": [80.0, 60.0],
        }
    )
    path = plot_yeoi_ranking(scores, 2025, tmp_path)
    assert path.exists()
    assert path.name == "yeoi_ranking_2025.png"


def test_plot_dimension_radar_writes_file(tmp_path):
    rows = []
    for i, city in enumerate(["A", "B", "C", "D", "E"]):
        row = {"city": city, "year": 2025, "yeoi_score": 80.0 - i * 10, "rank": i + 1}
        for col in SCORE_COLS:
            row[col] = 50.0 + i * 5
        rows.append(row)
    scores = pd.DataFrame(rows)
    path = plot_dimension_radar(scores, 2025, tmp_path)
    assert path.exists()
    assert path.name == "yeoi_radar_2025.png"


def test_plot_income_housing_scatter_writes_file(tmp_path):
    panel = pd.DataFrame(
        {
            "city": ["Beijing", "Shanghai", "Harbin"],
            "year": [2025, 2025, 2025],
            "entry_salary": [80000.0, 85000.0, 50000.0],
            "housing_burden": [0.65, 0.60, 0.20],
        }
    )
    path = plot_income_housing_scatter(panel, 2025, tmp_path)
    assert path.exists()
    assert path.name == "income_housing_scatter_2025.png"


def test_plot_yeoi_trend_writes_file(tmp_path):
    cities = ["Shanghai", "Beijing", "Shenzhen", "Guangzhou", "Hangzhou", "Harbin"]
    rows = []
    for year in range(2021, 2026):
        for i, city in enumerate(cities):
            rows.append(
                {
                    "city": city,
                    "year": year,
                    "yeoi_score": 70.0 - i * 5 + (year - 2021) * 0.5,
                    "rank": i + 1,
                }
            )
    scores = pd.DataFrame(rows)
    path = plot_yeoi_trend(scores, tmp_path)
    assert path.exists()
    assert path.name == "yeoi_trend_2021_2025.png"
