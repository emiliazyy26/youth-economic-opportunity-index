"""Generate all README charts to reports/figures/.

Prerequisite: run ``uv run yeoi-build`` first to produce processed CSVs.
Usage: ``uv run python scripts/generate_readme_charts.py``
"""

import pandas as pd

from yei.config import CITY_DATA_FILE, PROJECT_ROOT, YEOI_SCORES_FILE
from yei.visualize import (
    plot_dimension_radar,
    plot_income_housing_scatter,
    plot_yeoi_ranking,
    plot_yeoi_trend,
)

FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


def main() -> None:
    if not YEOI_SCORES_FILE.exists() or not CITY_DATA_FILE.exists():
        print("Processed CSVs not found. Run `uv run yeoi-build` first.")
        raise SystemExit(1)

    scores = pd.read_csv(YEOI_SCORES_FILE)
    panel = pd.read_csv(CITY_DATA_FILE)
    latest_year = int(scores["year"].max())

    paths = [
        plot_yeoi_ranking(scores, latest_year, FIGURES_DIR),
        plot_dimension_radar(scores, latest_year, FIGURES_DIR),
        plot_income_housing_scatter(panel, latest_year, FIGURES_DIR),
        plot_yeoi_trend(scores, FIGURES_DIR),
    ]

    for p in paths:
        print(f"Generated: {p}")


if __name__ == "__main__":
    main()
