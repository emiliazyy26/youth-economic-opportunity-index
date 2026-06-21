"""Streamlit Dashboard 入口。"""

from pathlib import Path

import pandas as pd
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
SCORES_FILE = PROCESSED_DIR / "ueoi_scores.csv"
CITY_FILE = PROCESSED_DIR / "city_economic_opportunity.csv"


@st.cache_data
def load_scores() -> pd.DataFrame:
    if not SCORES_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(SCORES_FILE)


def main() -> None:
    st.set_page_config(page_title="UEOI Dashboard", layout="wide")
    st.title("Urban Economic Opportunity Index")
    st.caption("中国城市经济机会指数 — 收入、住房压力与城市吸引力")

    scores = load_scores()
    if scores.empty:
        st.warning(
            "尚未生成指数结果。请先准备 `data/raw/city_panel.csv`，然后运行：\n\n"
            "`uv run ueoi-build`"
        )
        return

    years = sorted(scores["year"].unique())
    selected_year = st.selectbox("年份", years, index=len(years) - 1)

    cities = sorted(scores[scores["year"] == selected_year]["city"].unique())
    selected_city = st.selectbox("城市", cities)

    city_row = scores[(scores["year"] == selected_year) & (scores["city"] == selected_city)].iloc[
        0
    ]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("UEOI Score", f"{city_row['ueoi_score']:.1f}")
    with col2:
        st.metric("Rank", f"No.{int(city_row['rank'])} / {len(cities)}")

    st.subheader("分项得分")
    breakdown = city_row[
        [
            "income_score",
            "gdp_score",
            "population_growth_score",
            "innovation_score",
            "housing_burden_score",
        ]
    ]
    st.bar_chart(breakdown)

    st.subheader(f"{selected_year} 年城市排名")
    ranking = scores[scores["year"] == selected_year].sort_values("rank")
    st.dataframe(ranking, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
