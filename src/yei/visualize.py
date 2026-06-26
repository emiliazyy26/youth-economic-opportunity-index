"""Chart generation."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from yei.config import CITIES, PROCESSED_DATA_DIR, YEOI_SCORES_FILE

PRIMARY_COLOR = "#2563eb"
DPI = 200

GROUP_COLORS = {
    "megacity": "#2563eb",
    "strong_second_tier": "#16a34a",
    "transition": "#f59e0b",
    "control": "#dc2626",
}

SCORE_COMPONENTS = [
    "job_opportunity_score",
    "starting_income_score",
    "living_cost_score",
    "business_ecosystem_score",
    "growth_potential_score",
    "city_base_score",
]

COMPONENT_LABELS = [
    "Job\nOpportunity",
    "Starting\nIncome",
    "Living Cost\n(lower=better)",
    "Business\nEcosystem",
    "Growth\nPotential",
    "City Base",
]


def _city_group_map() -> dict[str, str]:
    """Reverse lookup: city -> group name from CITIES config."""
    mapping = {}
    for group, cities in CITIES.items():
        for city in cities:
            mapping[city] = group
    return mapping


def plot_yeoi_ranking(scores: pd.DataFrame, year: int, output_dir: Path) -> Path:
    """Plot a YEOI ranking bar chart for the specified year."""
    subset = scores[scores["year"] == year].sort_values("yeoi_score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(subset["city"], subset["yeoi_score"], color=PRIMARY_COLOR)
    ax.set_xlabel("YEOI Score")
    ax.set_title(f"Youth Economic Opportunity Index — {year}")
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"yeoi_ranking_{year}.png"
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_latest_ranking(output_dir: Path | None = None) -> Path:
    """Load the latest year index and generate chart."""
    scores = pd.read_csv(YEOI_SCORES_FILE)
    latest_year = int(scores["year"].max())
    target_dir = output_dir or PROCESSED_DATA_DIR / "figures"
    return plot_yeoi_ranking(scores, latest_year, target_dir)


def plot_dimension_radar(scores: pd.DataFrame, year: int, output_dir: Path) -> Path:
    """Plot a radar chart comparing sub-scores for the top 5 cities in a given year."""
    subset = scores[scores["year"] == year].dropna(subset=["yeoi_score"])
    top5 = subset.nsmallest(5, "rank")

    angles = np.linspace(0, 2 * np.pi, len(SCORE_COMPONENTS), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(COMPONENT_LABELS, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)

    for _, row in top5.iterrows():
        values = [row[c] for c in SCORE_COMPONENTS]
        values += values[:1]
        ax.plot(angles, values, "o-", linewidth=2, label=row["city"], markersize=4)
        ax.fill(angles, values, alpha=0.1)

    ax.set_title(f"YEOI Sub-Score Profiles — Top 5 ({year})", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"yeoi_radar_{year}.png"
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_income_housing_scatter(
    panel: pd.DataFrame, year: int, output_dir: Path
) -> Path:
    """Plot entry salary vs housing burden, colored by city group."""
    subset = panel[panel["year"] == year].dropna(subset=["entry_salary", "housing_burden"])
    group_map = _city_group_map()
    subset = subset.copy()
    subset["group"] = subset["city"].map(group_map).fillna("control")

    fig, ax = plt.subplots(figsize=(10, 7))
    for group, color in GROUP_COLORS.items():
        points = subset[subset["group"] == group]
        if points.empty:
            continue
        ax.scatter(
            points["entry_salary"],
            points["housing_burden"],
            c=color,
            label=group.replace("_", " ").title(),
            s=60,
            edgecolors="white",
            linewidths=0.5,
        )

    for _, row in subset.iterrows():
        ax.annotate(
            row["city"],
            (row["entry_salary"], row["housing_burden"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )

    ax.set_xlabel("Entry Salary (RMB/year)")
    ax.set_ylabel("Housing Burden (house price / disposable income ratio)")
    ax.set_title(f"Income vs Housing Cost — {year}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"income_housing_scatter_{year}.png"
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_yeoi_trend(scores: pd.DataFrame, output_dir: Path) -> Path:
    """Plot YEOI score trends 2021-2025 for top 5 cities plus Harbin and Kunming."""
    latest = scores[scores["year"] == scores["year"].max()].dropna(subset=["yeoi_score"])
    top5_cities = latest.nsmallest(5, "rank")["city"].tolist()
    focus_cities = top5_cities + ["Harbin", "Kunming"]

    subset = scores[scores["city"].isin(focus_cities)].dropna(subset=["yeoi_score"])
    pivot = subset.pivot(index="year", columns="city", values="yeoi_score")

    fig, ax = plt.subplots(figsize=(10, 6))
    for city in focus_cities:
        if city in pivot.columns:
            ax.plot(
                pivot.index,
                pivot[city],
                marker="o",
                linewidth=2,
                label=city,
            )

    ax.set_xlabel("Year")
    ax.set_ylabel("YEOI Score")
    ax.set_title("YEOI Score Trends 2021–2025 (scores standardized within each year)")
    ax.set_xticks(sorted(subset["year"].unique()))
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "yeoi_trend_2021_2025.png"
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path
