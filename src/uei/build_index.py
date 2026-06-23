"""UEOI 指数构建。"""

import pandas as pd

from uei.clean_data import clean_city_panel, load_raw_data, save_processed
from uei.config import SCORE_COLUMNS, UEOI_SCORES_FILE, UEOI_WEIGHTS


def min_max_score(series: pd.Series, *, invert: bool = False) -> pd.Series:
    """按年份截面做 Min-Max 归一化到 0–100。"""
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


def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    """为每个年份截面计算分项得分与 UEOI。"""
    frames: list[pd.DataFrame] = []

    for year, group in df.groupby("year"):
        scored = group.copy()
        scored["income_score"] = min_max_score(scored["disposable_income"])
        scored["gdp_score"] = min_max_score(scored["gdp_per_capita"])
        scored["talent_capital_score"] = min_max_score(scored["university_quality"])
        scored["population_growth_score"] = min_max_score(scored["population_growth"])
        scored["innovation_score"] = min_max_score(scored["innovation_index"])
        scored["industry_structure_score"] = min_max_score(scored["tertiary_ratio"])
        scored["housing_burden_score"] = min_max_score(scored["housing_burden"], invert=True)

        scored["ueoi_score"] = sum(
            scored[column] * weight for column, weight in UEOI_WEIGHTS.items()
        )
        scored["rank"] = pd.Series(pd.NA, index=scored.index, dtype="Int64")
        valid_scores = scored["ueoi_score"].notna()
        scored.loc[valid_scores, "rank"] = (
            scored.loc[valid_scores, "ueoi_score"]
            .rank(ascending=False, method="min")
            .astype("Int64")
        )
        frames.append(scored)

    result = pd.concat(frames, ignore_index=True)
    return result[SCORE_COLUMNS]


def run_pipeline() -> tuple[pd.DataFrame, pd.DataFrame]:
    """清洗原始数据并输出指数结果。"""
    raw = load_raw_data()
    cleaned = clean_city_panel(raw)
    save_processed(cleaned)

    scores = build_scores(cleaned)
    UEOI_SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(UEOI_SCORES_FILE, index=False)
    return cleaned, scores


def main() -> None:
    cleaned, scores = run_pipeline()
    print(f"Processed rows: {len(cleaned)}")
    print(f"UEOI scores saved: {UEOI_SCORES_FILE}")
    print(scores.sort_values(["year", "rank"]).head())


if __name__ == "__main__":
    main()
