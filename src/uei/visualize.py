"""图表生成。"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from uei.config import PROCESSED_DATA_DIR, UEOI_SCORES_FILE


def plot_ueoi_ranking(scores: pd.DataFrame, year: int, output_dir: Path) -> Path:
    """绘制指定年份的 UEOI 排名条形图。"""
    subset = scores[scores["year"] == year].sort_values("ueoi_score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(subset["city"], subset["ueoi_score"], color="#2563eb")
    ax.set_xlabel("UEOI Score")
    ax.set_title(f"Urban Economic Opportunity Index — {year}")
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ueoi_ranking_{year}.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_latest_ranking(output_dir: Path | None = None) -> Path:
    """读取最新年份指数并出图。"""
    scores = pd.read_csv(UEOI_SCORES_FILE)
    latest_year = int(scores["year"].max())
    target_dir = output_dir or PROCESSED_DATA_DIR / "figures"
    return plot_ueoi_ranking(scores, latest_year, target_dir)
