"""Chart generation."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from yei.config import PROCESSED_DATA_DIR, YEOI_SCORES_FILE


def plot_yeoi_ranking(scores: pd.DataFrame, year: int, output_dir: Path) -> Path:
    """Plot a YEOI ranking bar chart for the specified year."""
    subset = scores[scores["year"] == year].sort_values("yeoi_score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(subset["city"], subset["yeoi_score"], color="#2563eb")
    ax.set_xlabel("YEOI Score")
    ax.set_title(f"Youth Economic Opportunity Index — {year}")
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"yeoi_ranking_{year}.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_latest_ranking(output_dir: Path | None = None) -> Path:
    """Load the latest year index and generate chart."""
    scores = pd.read_csv(YEOI_SCORES_FILE)
    latest_year = int(scores["year"].max())
    target_dir = output_dir or PROCESSED_DATA_DIR / "figures"
    return plot_yeoi_ranking(scores, latest_year, target_dir)
