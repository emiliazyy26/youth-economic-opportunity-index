"""Streamlit Dashboard 入口。"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SCORES_FILE = PROCESSED_DIR / "yeoi_scores.csv"
CITY_FILE = PROCESSED_DIR / "city_economic_opportunity.csv"
SENSITIVITY_FILE = PROCESSED_DIR / "sensitivity_report.csv"
MISSING_FILE = RAW_DIR / "missing_data_report.csv"


@st.cache_data
def load_scores() -> pd.DataFrame:
    if not SCORES_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(SCORES_FILE)


@st.cache_data
def load_panel() -> pd.DataFrame:
    if not CITY_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(CITY_FILE)


@st.cache_data
def load_sensitivity() -> pd.DataFrame:
    if not SENSITIVITY_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(SENSITIVITY_FILE)


@st.cache_data
def load_missing() -> pd.DataFrame:
    if not MISSING_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(MISSING_FILE)


def _scatter(fig_title: str, data: pd.DataFrame, x: str, y: str, hover: str = "city") -> None:
    fig = px.scatter(
        data,
        x=x,
        y=y,
        text=hover,
        title=fig_title,
        labels={x: x.replace("_", " "), y: y.replace("_", " ")},
    )
    fig.update_traces(textposition="top center", marker={"size": 10})
    fig.update_layout(height=420, margin={"t": 48, "b": 40})
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="YEOI Dashboard", layout="wide")
    st.title("Youth Economic Opportunity Index (YEOI)")
    st.caption(
        "中国青年城市机会指数 — 就业、起薪、生活成本与城市吸引力的数据分析"
    )

    scores = load_scores()
    if scores.empty:
        st.warning(
            "尚未生成指数结果。请先准备 `data/raw/city_panel.csv`，然后运行：\n\n"
            "`uv run ueoi-build`"
        )
        return

    years = sorted(scores["year"].unique())
    selected_year = st.selectbox("年份", years, index=len(years) - 1)

    year_scores = scores[scores["year"] == selected_year].copy()
    cities = sorted(year_scores["city"].unique())
    selected_city = st.selectbox("城市", cities)

    city_row = year_scores[year_scores["city"] == selected_city].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("YEOI Score", f"{city_row['yeoi_score']:.1f}")
    with col2:
        st.metric("Rank", f"No.{int(city_row['rank'])} / {len(cities)}")
    with col3:
        st.metric("Living Cost Score", f"{city_row['living_cost_score']:.1f}")

    st.subheader("分项得分")
    score_cols = [
        "job_opportunity_score",
        "starting_income_score",
        "living_cost_score",
        "big_company_score",
        "growth_potential_score",
        "city_base_score",
    ]
    breakdown = city_row[score_cols]
    st.bar_chart(breakdown)

    st.subheader("指标来源（主指数维度）")
    source_cols = [
        "job_opportunity_source",
        "starting_income_source",
        "living_cost_source",
    ]
    st.dataframe(
        city_row[source_cols].to_frame("metric_source").T,
        use_container_width=True,
    )

    panel = load_panel()
    year_merged = year_scores.merge(panel, on=["city", "year"], how="left", suffixes=("", "_raw"))

    st.subheader("城市对比：机会 vs 生活成本")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        _scatter(
            "就业机会 vs 生活成本可负担性",
            year_merged,
            "living_cost_score",
            "job_opportunity_score",
        )
    with chart_col2:
        _scatter(
            "起薪/收入 vs 生活成本可负担性",
            year_merged,
            "living_cost_score",
            "starting_income_score",
        )

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        _scatter(
            "大企业机会 vs 生活成本可负担性",
            year_merged,
            "living_cost_score",
            "big_company_score",
        )
    with chart_col4:
        if "rent_burden" in year_merged.columns and year_merged["rent_burden"].notna().any():
            income_col = (
                "entry_salary"
                if year_merged["entry_salary"].notna().any()
                else "disposable_income"
            )
            raw = year_merged.dropna(subset=["rent_burden", income_col])
            if not raw.empty:
                _scatter(
                    "租金压力 vs 收入（原始指标）",
                    raw,
                    "rent_burden",
                    income_col,
                )
            else:
                st.info("起薪/租金原始指标暂不可用。")
        else:
            st.info("租金负担数据暂不可用。")

    if not panel.empty:
        city_panel = panel[
            (panel["year"] == selected_year) & (panel["city"] == selected_city)
        ]
        if not city_panel.empty:
            st.subheader("原始指标快照")
            raw_cols = [
                c
                for c in [
                    "disposable_income",
                    "entry_salary",
                    "rent_monthly",
                    "rent_burden",
                    "housing_burden",
                    "listed_company_count",
                    "job_posting_count",
                    "population_growth",
                    "innovation_index",
                    "tertiary_ratio",
                ]
                if c in city_panel.columns
            ]
            st.dataframe(city_panel[["city", "year", *raw_cols]], hide_index=True)

    st.subheader(f"{selected_year} 年城市排名")
    ranking = year_scores.sort_values("rank")
    display_cols = ["city", "rank", "yeoi_score", *score_cols]
    st.dataframe(ranking[display_cols], use_container_width=True, hide_index=True)

    missing = load_missing()
    if not missing.empty:
        st.subheader("数据缺口与补充信号")
        core_missing = missing[
            (missing["category"] == "core") & (missing["year"] == selected_year)
        ]
        if not core_missing.empty:
            st.caption("以下核心青年指标尚未采集，当前排名使用 fallback 指标。")
            st.dataframe(
                core_missing.groupby("metric").size().reset_index(name="missing_cities"),
                hide_index=True,
            )
        supp = missing[
            (missing["category"] == "supplementary") & (missing["year"] == selected_year)
        ]
        if not supp.empty:
            st.caption("`tertiary_ratio` 等为补充字段，不进入 YEOI 主公式。")

    sensitivity = load_sensitivity()
    if not sensitivity.empty:
        st.subheader("权重敏感性（Top-5 排名变动）")
        st.dataframe(sensitivity, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
