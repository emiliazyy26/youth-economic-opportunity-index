"""YEOI weight sensitivity analysis."""

from __future__ import annotations

import pandas as pd

from yei.build_index import build_scores
from yei.clean_data import clean_city_panel, load_raw_data
from yei.config import YEOI_WEIGHTS


def _rank_by_weights(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """Recompute yeoi_score and rank with given weights (reusing build_scores dimension scores)."""
    base_scores = build_scores(df)
    merged = df.merge(
        base_scores[
            [
                "city",
                "year",
                "job_opportunity_score",
                "starting_income_score",
                "living_cost_score",
                "enterprise_opportunity_score",
                "growth_potential_score",
                "city_base_score",
            ]
        ],
        on=["city", "year"],
        how="left",
    )
    merged["yeoi_score"] = sum(merged[col] * w for col, w in weights.items())
    frames = []
    for year, group in merged.groupby("year"):
        g = group.copy()
        g["rank"] = g["yeoi_score"].rank(ascending=False, method="min").astype("Int64")
        frames.append(g[["city", "year", "yeoi_score", "rank"]])
    return pd.concat(frames, ignore_index=True)


def sensitivity_shift(
    df: pd.DataFrame | None = None,
    *,
    shift: float = 0.05,
) -> pd.DataFrame:
    """Test the impact of +/-shift on each dimension weight for the latest year Top-5 city ranking."""
    panel = df if df is not None else clean_city_panel(load_raw_data())
    baseline = build_scores(panel)
    latest_year = int(baseline["year"].max())
    base_top = baseline[baseline["year"] == latest_year].nsmallest(5, "rank")[
        ["city", "rank"]
    ].set_index("city")["rank"]

    records: list[dict] = []
    for dim in YEOI_WEIGHTS:
        for direction in ("+", "-"):
            weights = YEOI_WEIGHTS.copy()
            delta = shift if direction == "+" else -shift
            weights[dim] = max(0.0, weights[dim] + delta)
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}
            alt = _rank_by_weights(panel, weights)
            alt_top = alt[alt["year"] == latest_year].set_index("city")["rank"]
            changed = int((base_top - alt_top.reindex(base_top.index)).fillna(0).ne(0).sum())
            records.append(
                {
                    "dimension": dim,
                    "direction": direction,
                    "weight_delta": delta,
                    "top5_rank_changes": changed,
                }
            )
    return pd.DataFrame(records)


def run_sensitivity_report(output_path: str | None = None) -> pd.DataFrame:
    report = sensitivity_shift()
    if output_path:
        report.to_csv(output_path, index=False)
    return report
