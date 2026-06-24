"""YEOI Youth Economic Opportunity Index construction."""

import pandas as pd

from yei.clean_data import clean_city_panel, load_raw_data, save_processed
from yei.config import (
    CITY_BASE_METRICS,
    DIMENSION_SPEC,
    GROWTH_POTENTIAL_METRICS,
    SCORE_COLUMNS,
    YEOI_SCORES_FILE,
    YEOI_WEIGHTS,
)
from yei.data_quality import select_dimension_metric


def min_max_score(series: pd.Series, *, invert: bool = False) -> pd.Series:
    """Min-Max normalize to 0-100 within each year cross-section."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series(float("nan"), index=series.index)

    min_val = valid.min()
    max_val = valid.max()
    normalized = pd.Series(float("nan"), index=series.index)
    if max_val == min_val:
        normalized.loc[valid.index] = 50.0
    else:
        normalized.loc[valid.index] = (valid - min_val) / (max_val - min_val) * 100

    if invert:
        normalized = 100 - normalized
    return normalized


def _score_from_metrics(group: pd.DataFrame, metrics: list[str]) -> pd.Series:
    """Normalize multiple positive metrics independently and take the mean."""
    parts = [min_max_score(group[m]) for m in metrics if m in group.columns]
    if not parts:
        return pd.Series(float("nan"), index=group.index)
    return pd.concat(parts, axis=1).mean(axis=1)


def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute YEOI dimension scores and overall ranking for each year cross-section."""
    frames: list[pd.DataFrame] = []

    for _year, group in df.groupby("year"):
        scored = group.copy()

        for dimension, score_col in [
            ("job_opportunity", "job_opportunity_score"),
            ("starting_income", "starting_income_score"),
            ("living_cost", "living_cost_score"),
            ("big_company", "big_company_score"),
        ]:
            _metric_name, values, source_label = select_dimension_metric(group, dimension)
            invert = DIMENSION_SPEC[dimension]["invert"]
            scored[score_col] = min_max_score(values, invert=invert)
            source_col = score_col.replace("_score", "_source")
            scored[source_col] = source_label

        scored["growth_potential_score"] = _score_from_metrics(
            scored, GROWTH_POTENTIAL_METRICS
        )
        scored["city_base_score"] = _score_from_metrics(scored, CITY_BASE_METRICS)

        scored["yeoi_score"] = sum(
            scored[column] * weight for column, weight in YEOI_WEIGHTS.items()
        )
        scored["rank"] = pd.Series(pd.NA, index=scored.index, dtype="Int64")
        valid_scores = scored["yeoi_score"].notna()
        scored.loc[valid_scores, "rank"] = (
            scored.loc[valid_scores, "yeoi_score"]
            .rank(ascending=False, method="min")
            .astype("Int64")
        )
        frames.append(scored)

    result = pd.concat(frames, ignore_index=True)
    return result[SCORE_COLUMNS]


def run_pipeline() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean raw data and output YEOI index results."""
    raw = load_raw_data()
    cleaned = clean_city_panel(raw)
    save_processed(cleaned)

    scores = build_scores(cleaned)
    YEOI_SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(YEOI_SCORES_FILE, index=False)
    return cleaned, scores


def main() -> None:
    cleaned, scores = run_pipeline()
    print(f"Processed rows: {len(cleaned)}")
    print(f"YEOI scores saved: {YEOI_SCORES_FILE}")
    print(scores.sort_values(["year", "rank"]).head())


if __name__ == "__main__":
    main()
