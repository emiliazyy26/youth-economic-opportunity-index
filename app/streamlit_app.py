"""Streamlit Dashboard entry point — conclusion-supporting layout.

Narrative flow: Ranking → Dimension Explanation → Income-Cost Tradeoff →
Time Stability → Weight Robustness → Balanced Opportunity Conclusion.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from yei.config import (
    CITIES,
    CITY_DATA_FILE,
    MISSING_DATA_REPORT_FILE,
    YEOI_SCORES_FILE,
    YEOI_WEIGHTS,
)
from yei.config import PROCESSED_DATA_DIR as _PDIR

SENSITIVITY_FILE = _PDIR / "sensitivity_report.csv"

# Dimension display labels (short) and full labels with weight
DIMENSION_KEYS = [
    "job_opportunity_score",
    "starting_income_score",
    "living_cost_score",
    "business_ecosystem_score",
    "growth_potential_score",
    "city_base_score",
]

DIMENSION_LABELS = {
    "job_opportunity_score": "Job Opportunity",
    "starting_income_score": "Starting Income",
    "living_cost_score": "Living Cost (inv.)",
    "business_ecosystem_score": "Business Ecosystem",
    "growth_potential_score": "Growth Potential",
    "city_base_score": "City Base",
}

# Map old sensitivity dimension names to current ones
_SENSITIVITY_DIM_MAP = {
    "big_company_score": "business_ecosystem_score",
}

# Fixed color palette for city groups
GROUP_COLORS = {
    "megacity": "#2563eb",
    "strong_second_tier": "#16a34a",
    "transition": "#f59e0b",
    "control": "#dc2626",
}

GROUP_LABELS = {
    "megacity": "Megacity",
    "strong_second_tier": "Strong Second Tier",
    "transition": "Transition",
    "control": "Control",
}

# Raw metric groups for City Profile snapshot
METRIC_GROUPS = {
    "Income": ["disposable_income", "entry_salary", "average_wage"],
    "Cost": ["house_price", "housing_burden", "rent_monthly", "rent_burden"],
    "Jobs": ["job_posting_count"],
    "Ecosystem": ["listed_company_count", "high_tech_company_count", "rd_expenditure"],
    "Growth": ["population_growth", "innovation_index"],
    "City Base": ["gdp_per_capita", "weighted_university_score", "tertiary_ratio"],
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data
def load_scores() -> pd.DataFrame:
    if not YEOI_SCORES_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(YEOI_SCORES_FILE)


@st.cache_data
def load_panel() -> pd.DataFrame:
    if not CITY_DATA_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(CITY_DATA_FILE)


@st.cache_data
def load_sensitivity() -> pd.DataFrame:
    if not SENSITIVITY_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(SENSITIVITY_FILE)
    if not df.empty and "dimension" in df.columns:
        df["dimension"] = df["dimension"].replace(_SENSITIVITY_DIM_MAP)
    return df


@st.cache_data
def load_missing() -> pd.DataFrame:
    if not MISSING_DATA_REPORT_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(MISSING_DATA_REPORT_FILE)
    if len(df) == 0:
        return pd.DataFrame()
    return df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _city_group_map() -> dict[str, str]:
    """Reverse lookup: city -> group name."""
    mapping: dict[str, str] = {}
    for group, cities in CITIES.items():
        for city in cities:
            mapping[city] = group
    return mapping


def add_city_group(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'city_group' column based on CITIES config. Returns a copy."""
    gmap = _city_group_map()
    out = df.copy()
    out["city_group"] = out["city"].map(gmap).fillna("control")
    return out


def format_dimension_scores(row: pd.Series) -> pd.DataFrame:
    """Return a tidy DataFrame of dimension scores with labels and weights."""
    rows = []
    for key in DIMENSION_KEYS:
        rows.append(
            {
                "dimension": DIMENSION_LABELS[key],
                "score": row.get(key, float("nan")),
                "weight": YEOI_WEIGHTS.get(key, 0.0),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Chart builders (all return plotly Figure objects)
# ---------------------------------------------------------------------------


def build_ranking_chart(
    year_scores: pd.DataFrame,
    highlight_city: str | None = None,
    n: int = 20,
) -> go.Figure:
    """Horizontal bar chart of YEOI ranking, optionally highlighting one city."""
    data = year_scores.sort_values("yeoi_score", ascending=True).head(n).copy()
    data["color"] = data["city"].apply(
        lambda c: GROUP_COLORS.get(
            _city_group_map().get(c, "control"), "#94a3b8"
        )
    )
    data["highlight"] = data["city"] == highlight_city if highlight_city else False

    fig = go.Figure()
    for _, row in data.iterrows():
        fig.add_trace(
            go.Bar(
                y=[row["city"]],
                x=[row["yeoi_score"]],
                orientation="h",
                marker_color=row["color"],
                marker_line_width=3 if row["highlight"] else 0,
                marker_line_color="#000000" if row["highlight"] else None,
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['city']}</b><br>"
                    f"YEOI: {row['yeoi_score']:.1f}<br>"
                    f"Rank: {int(row['rank'])}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        xaxis_title="YEOI Score",
        yaxis_title="",
        height=500,
        margin={"t": 30, "b": 30},
        yaxis={"categoryorder": "total ascending"},
    )
    return fig


def build_group_boxplot(year_scores: pd.DataFrame) -> go.Figure:
    """Box plot of YEOI scores by city group, with individual city scatter overlay."""
    data = add_city_group(year_scores.copy())
    data["group_label"] = data["city_group"].map(GROUP_LABELS).fillna(data["city_group"])
    group_order = list(GROUP_LABELS.values())

    fig = go.Figure()
    for label in group_order:
        subset = data[data["group_label"] == label]
        if subset.empty:
            continue
        fig.add_trace(
            go.Box(
                y=subset["yeoi_score"],
                name=label,
                marker_color=GROUP_COLORS.get(
                    {v: k for k, v in GROUP_LABELS.items()}.get(label, "control"),
                    "#94a3b8",
                ),
                boxpoints=False,
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[label] * len(subset),
                y=subset["yeoi_score"],
                mode="markers",
                marker=dict(size=8, opacity=0.7, color=GROUP_COLORS.get(
                    {v: k for k, v in GROUP_LABELS.items()}.get(label, "control"),
                    "#94a3b8",
                )),
                text=subset["city"],
                hovertemplate="<b>%{text}</b><br>YEOI: %{y:.1f}<extra></extra>",
                showlegend=False,
            )
        )
    fig.update_layout(
        yaxis_title="YEOI Score",
        xaxis_title="",
        height=450,
        margin={"t": 30, "b": 30},
    )
    return fig


def build_top5_radar(year_scores: pd.DataFrame) -> go.Figure:
    """Radar chart comparing sub-scores for the top 5 cities."""
    data = year_scores.dropna(subset=["yeoi_score"]).nsmallest(5, "rank")
    dims = [DIMENSION_LABELS[k] for k in DIMENSION_KEYS]

    fig = go.Figure()
    for _, row in data.iterrows():
        values = [row.get(k, 0) for k in DIMENSION_KEYS]
        values += values[:1]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=dims + [dims[0]],
                fill="toself",
                name=row["city"],
                hovertemplate=f"<b>{row['city']}</b><br>"
                + "<br>".join(
                    f"{d}: %{{r[{i}]}}" for i, d in enumerate(dims)
                )
                + "<extra></extra>",
            )
        )
    fig.update_layout(
        polar={"radialaxis": {"range": [0, 100]}},
        height=450,
        margin={"t": 30, "b": 30},
        legend={"orientation": "h", "y": -0.1},
    )
    return fig


def build_dimension_bar(
    city_row: pd.Series, avg_row: pd.Series | None, top5_avg_row: pd.Series | None
) -> go.Figure:
    """Grouped bar chart: selected city vs year average vs top-5 average."""
    dims = [DIMENSION_LABELS[k] for k in DIMENSION_KEYS]
    city_vals = [city_row.get(k, 0) for k in DIMENSION_KEYS]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(name="Selected City", x=dims, y=city_vals, marker_color="#2563eb")
    )
    if avg_row is not None:
        avg_vals = [avg_row.get(k, 0) for k in DIMENSION_KEYS]
        fig.add_trace(
            go.Bar(name="Year Average", x=dims, y=avg_vals, marker_color="#94a3b8")
        )
    if top5_avg_row is not None:
        top5_vals = [top5_avg_row.get(k, 0) for k in DIMENSION_KEYS]
        fig.add_trace(
            go.Bar(name="Top 5 Average", x=dims, y=top5_vals, marker_color="#16a34a")
        )
    fig.update_layout(
        barmode="group",
        yaxis_title="Score (0-100)",
        xaxis_title="",
        height=400,
        margin={"t": 30, "b": 30},
        legend={"orientation": "h", "y": 1.12},
    )
    return fig


def build_radar_chart(
    city_row: pd.Series, avg_row: pd.Series | None, top5_avg_row: pd.Series | None
) -> go.Figure:
    """Radar chart comparing selected city vs year avg vs top-5 avg."""
    dims = [DIMENSION_LABELS[k] for k in DIMENSION_KEYS]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=[city_row.get(k, 0) for k in DIMENSION_KEYS] + [city_row.get(DIMENSION_KEYS[0], 0)],
            theta=dims + [dims[0]],
            fill="toself",
            name="Selected City",
            line_color="#2563eb",
        )
    )
    if avg_row is not None:
        fig.add_trace(
            go.Scatterpolar(
                r=[avg_row.get(k, 0) for k in DIMENSION_KEYS] + [avg_row.get(DIMENSION_KEYS[0], 0)],
                theta=dims + [dims[0]],
                fill="toself",
                name="Year Average",
                line_color="#94a3b8",
                opacity=0.5,
            )
        )
    if top5_avg_row is not None:
        fig.add_trace(
            go.Scatterpolar(
                r=[
                    top5_avg_row.get(k, 0)
                    for k in DIMENSION_KEYS
                ] + [top5_avg_row.get(DIMENSION_KEYS[0], 0)],
                theta=dims + [dims[0]],
                fill="toself",
                name="Top 5 Average",
                line_color="#16a34a",
                opacity=0.5,
            )
        )
    fig.update_layout(
        polar={"radialaxis": {"range": [0, 100]}},
        height=450,
        margin={"t": 30, "b": 30},
        legend={"orientation": "h", "y": -0.1},
    )
    return fig


def build_tradeoff_scatter(
    year_merged: pd.DataFrame,
    x_col: str,
    y_col: str,
    selected_city: str,
    x_label: str = "",
    y_label: str = "",
) -> go.Figure:
    """Scatter plot of income vs cost burden, colored by city group with highlight."""
    data = year_merged.dropna(subset=[x_col, y_col]).copy()
    if data.empty:
        return go.Figure()
    data = add_city_group(data)
    data["group_label"] = data["city_group"].map(GROUP_LABELS).fillna(data["city_group"])
    data["size"] = data["city"].apply(lambda c: 16 if c == selected_city else 10)
    data["opacity"] = data["city"].apply(lambda c: 1.0 if c == selected_city else 0.7)

    hover_data = {}
    for col in ["city", "rank", "yeoi_score", x_col, y_col]:
        if col in data.columns:
            hover_data[col] = True

    fig = px.scatter(
        data,
        x=x_col,
        y=y_col,
        color="group_label",
        color_discrete_map={v: GROUP_COLORS.get(k, "#94a3b8") for k, v in GROUP_LABELS.items()},
        size="size",
        size_max=18,
        opacity=0.7,
        hover_name="city",
        hover_data=hover_data,
        labels={
            x_col: x_label or x_col.replace("_", " "),
            y_col: y_label or y_col.replace("_", " "),
        },
    )

    # Highlight selected city with a marker outline
    sel = data[data["city"] == selected_city]
    if not sel.empty:
        fig.add_trace(
            go.Scatter(
                x=sel[x_col],
                y=sel[y_col],
                mode="markers",
                marker=dict(size=20, color="rgba(0,0,0,0)", line=dict(width=3, color="#000000")),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Median reference lines
    x_med = data[x_col].median()
    y_med = data[y_col].median()
    fig.add_hline(y=y_med, line_dash="dash", line_color="gray", opacity=0.4)
    fig.add_vline(x=x_med, line_dash="dash", line_color="gray", opacity=0.4)

    fig.update_layout(height=480, margin={"t": 30, "b": 30})
    return fig


def build_trend_chart(
    scores: pd.DataFrame, focus_cities: list[str], value_col: str = "yeoi_score"
) -> go.Figure:
    """Line chart of YEOI score or rank trends across years."""
    data = scores[scores["city"].isin(focus_cities)].dropna(subset=[value_col]).copy()
    if data.empty:
        return go.Figure()

    data = add_city_group(data)
    data["group_label"] = data["city_group"].map(GROUP_LABELS).fillna(data["city_group"])

    is_rank = value_col == "rank"
    fig = px.line(
        data,
        x="year",
        y=value_col,
        color="city",
        line_group="city",
        markers=True,
        labels={value_col: "Rank" if is_rank else "YEOI Score", "year": "Year"},
    )
    if is_rank:
        fig.update_yaxes(autorange="reversed", title="Rank")
    fig.update_layout(
        height=450,
        margin={"t": 30, "b": 30},
        legend={"orientation": "h", "y": -0.15},
        xaxis={"dtick": 1},
    )
    return fig


def build_sensitivity_chart(sensitivity: pd.DataFrame) -> go.Figure:
    """Bar chart of top-5 rank changes by dimension and direction."""
    if sensitivity.empty:
        return go.Figure()
    data = sensitivity.copy()
    data["label"] = data["dimension"].map(DIMENSION_LABELS).fillna(
        data["dimension"].str.replace("_score", "").str.replace("_", " ").str.title()
    )
    data["direction_label"] = data["direction"].apply(lambda d: f"+{d}" if d == "+" else d)
    data["combo"] = data["label"] + " " + data["direction_label"]

    fig = px.bar(
        data,
        x="combo",
        y="top5_rank_changes",
        color="top5_rank_changes",
        color_continuous_scale="Blues",
        labels={"combo": "Dimension & Direction", "top5_rank_changes": "Top-5 Rank Changes"},
    )
    fig.update_layout(
        height=400,
        margin={"t": 30, "b": 60},
        xaxis={"tickangle": -45},
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------


def _render_national_overview(
    year_scores: pd.DataFrame,
    selected_year: int,
) -> None:
    st.title("Youth Economic Opportunity Index (YEOI)")
    st.caption(
        "Which Chinese cities offer the best balance of jobs, income, "
        "and living costs for young professionals?"
    )
    st.markdown(
        "**Research Question:** Which Chinese cities offer young professionals "
        "the best balance between job opportunities, starting income, and living costs?"
    )

    # --- Sample-level KPI ---
    n_cities = len(year_scores)
    mean_score = year_scores["yeoi_score"].mean()
    median_score = year_scores["yeoi_score"].median()
    top_row = year_scores.nsmallest(1, "rank").iloc[0]
    score_range = year_scores["yeoi_score"].max() - year_scores["yeoi_score"].min()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Cities", n_cities)
    with col2:
        st.metric("YEOI Mean", f"{mean_score:.1f}")
    with col3:
        st.metric("YEOI Median", f"{median_score:.1f}")
    with col4:
        st.metric("Top City", f"{top_row['city']} ({top_row['yeoi_score']:.1f})")
    with col5:
        st.metric("Score Range", f"{score_range:.1f}")

    # --- Ranking chart ---
    top5 = year_scores.nsmallest(5, "rank")
    st.markdown(f"**Top 5 Cities in {selected_year}:** "
                + ", ".join(f"{r['city']} (#{int(r['rank'])})" for _, r in top5.iterrows()))

    st.markdown(f"#### {selected_year} City Ranking")
    st.plotly_chart(
        build_ranking_chart(year_scores, highlight_city=None),
        use_container_width=True,
    )

    # --- Full ranking table ---
    st.markdown("#### Full Ranking Table")
    table_data = add_city_group(year_scores.sort_values("rank"))
    table_data["city_group"] = table_data["city_group"].map(GROUP_LABELS).fillna(table_data["city_group"])
    display_cols = ["rank", "city", "city_group", "yeoi_score"] + DIMENSION_KEYS
    available_cols = [c for c in display_cols if c in table_data.columns]
    st.dataframe(
        table_data[available_cols],
        hide_index=True,
        use_container_width=True,
    )

    # --- Group boxplot + Top5 radar ---
    col_box, col_radar = st.columns(2)
    with col_box:
        st.markdown("#### YEOI by City Group")
        st.plotly_chart(
            build_group_boxplot(year_scores),
            use_container_width=True,
        )
    with col_radar:
        st.markdown("#### Top 5 Dimension Radar")
        st.plotly_chart(
            build_top5_radar(year_scores),
            use_container_width=True,
        )


def _render_city_profile(
    year_scores: pd.DataFrame,
    selected_city: str,
    selected_year: int,
    city_row: pd.Series,
    panel: pd.DataFrame,
) -> None:
    # City-level KPI header
    n_cities = len(year_scores)
    gmap = _city_group_map()
    group = gmap.get(selected_city, "—")
    percentile = (1 - city_row["rank"] / n_cities) * 100

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("YEOI Score", f"{city_row['yeoi_score']:.1f}")
    with col2:
        st.metric("Rank", f"#{int(city_row['rank'])} / {n_cities}")
    with col3:
        st.metric("Percentile", f"{percentile:.0f}%")
    with col4:
        st.metric("City Group", GROUP_LABELS.get(group, group))
    with col5:
        st.metric("Living Cost Score", f"{city_row['living_cost_score']:.1f}")

    # Dimension bar chart
    avg_row = year_scores[DIMENSION_KEYS].mean()
    top5 = year_scores.nsmallest(5, "rank")
    top5_avg = top5[DIMENSION_KEYS].mean()

    col_bar, col_radar = st.columns(2)
    with col_bar:
        st.markdown("#### Dimension Scores (with weight)")
        dim_df = format_dimension_scores(city_row)
        for _, r in dim_df.iterrows():
            st.text(f"  {r['dimension']:<25s}  {r['score']:6.1f}  (w={r['weight']:.0%})")
        st.plotly_chart(
            build_dimension_bar(city_row, avg_row, top5_avg),
            use_container_width=True,
        )
    with col_radar:
        st.markdown("#### Radar Comparison")
        st.plotly_chart(
            build_radar_chart(city_row, avg_row, top5_avg),
            use_container_width=True,
        )

    # Raw metric snapshot grouped by category
    st.markdown("#### Raw Metric Snapshot")
    city_panel = panel[(panel["year"] == selected_year) & (panel["city"] == selected_city)]
    if not city_panel.empty:
        row = city_panel.iloc[0]
        snap_cols = []
        for group_name, cols in METRIC_GROUPS.items():
            available = [c for c in cols if c in row.index and pd.notna(row[c])]
            if available:
                snap_cols.append((group_name, available))

        n_groups = len(snap_cols)
        if n_groups > 0:
            cols = st.columns(min(n_groups, 3))
            for i, (group_name, group_cols) in enumerate(snap_cols):
                with cols[i % len(cols)]:
                    st.markdown(f"**{group_name}**")
                    for c in group_cols:
                        val = row[c]
                        if isinstance(val, float):
                            if abs(val) < 1:
                                st.text(f"  {c.replace('_', ' '):.<30s} {val:.4f}")
                            else:
                                st.text(f"  {c.replace('_', ' '):.<30s} {val:,.1f}")
                        else:
                            st.text(f"  {c.replace('_', ' '):.<30s} {val}")

    # Metric source table
    st.markdown("#### Metric Sources")
    source_cols = ["job_opportunity_source", "starting_income_source", "living_cost_source"]
    available_sources = [c for c in source_cols if c in city_row.index]
    if available_sources:
        source_df = pd.DataFrame(
            {
                "Dimension": [
                    DIMENSION_LABELS.get(
                        c.replace("_source", "_score"), c
                    )
                    for c in available_sources
                ],
                "Source Metric": [city_row[c] for c in available_sources],
            }
        )
        st.dataframe(source_df, hide_index=True, use_container_width=True)


def _render_tradeoffs(
    year_scores: pd.DataFrame,
    panel: pd.DataFrame,
    selected_city: str,
    selected_year: int,
) -> None:
    st.markdown(
        "Higher income cities often carry higher housing/rent pressure. "
        "This tab visualizes the core trade-off young professionals face."
    )

    year_merged = year_scores.merge(
        panel, on=["city", "year"], how="left", suffixes=("", "_raw")
    )

    # Toggle between housing_burden and rent_burden
    burden_options = []
    if "housing_burden" in year_merged.columns and year_merged["housing_burden"].notna().any():
        burden_options.append("housing_burden")
    if "rent_burden" in year_merged.columns and year_merged["rent_burden"].notna().any():
        burden_options.append("rent_burden")

    if not burden_options:
        st.info("Housing and rent burden data currently unavailable.")
        return

    burden_col = st.radio("Cost Burden Metric", burden_options, horizontal=True)
    income_col = "entry_salary" if "entry_salary" in year_merged.columns else "disposable_income"

    burden_label = (
        "Housing Burden (house price / income)"
        if burden_col == "housing_burden"
        else "Rent Burden (rent / income)"
    )
    income_label = (
        "Entry Salary (RMB/year)"
        if income_col == "entry_salary"
        else "Disposable Income (RMB/year)"
    )

    st.plotly_chart(
        build_tradeoff_scatter(
            year_merged, income_col, burden_col, selected_city,
            x_label=income_label, y_label=burden_label,
        ),
        use_container_width=True,
    )

    st.caption(
        "Dashed lines show sample medians. Cities in the upper-right quadrant "
        "have high income but also high cost pressure; lower-right quadrant "
        "represents better income-cost balance."
    )


def _render_trends(scores: pd.DataFrame, selected_city: str) -> None:
    st.markdown(
        "**Note:** YEOI scores are cross-sectionally standardized within each year. "
        "Trends show relative standing, not absolute economic growth."
    )

    # Default focus: 2025 Top 5 + Harbin / Kunming as controls
    latest_year = int(scores["year"].max())
    latest = scores[scores["year"] == latest_year].dropna(subset=["yeoi_score"])
    top5_cities = latest.nsmallest(5, "rank")["city"].tolist()
    default_focus = top5_cities + ["Harbin", "Kunming"]
    default_focus = [c for c in default_focus if c in scores["city"].unique()]

    all_cities = sorted(scores["city"].unique())
    extra = st.multiselect(
        "Additional cities to compare", all_cities, default=default_focus
    )

    col_score, col_rank = st.columns(2)
    with col_score:
        st.markdown("#### YEOI Score Trend")
        st.plotly_chart(
            build_trend_chart(scores, extra, "yeoi_score"),
            use_container_width=True,
        )
    with col_rank:
        st.markdown("#### Rank Trend")
        st.plotly_chart(
            build_trend_chart(scores, extra, "rank"),
            use_container_width=True,
        )


def _render_sensitivity(
    sensitivity: pd.DataFrame, missing: pd.DataFrame
) -> None:
    st.markdown("#### Weight Sensitivity Analysis")
    st.markdown(
        "Each bar shows how many Top-5 cities change when a dimension's weight "
        "is adjusted by ±5 percentage points. Lower bars indicate more robust conclusions."
    )

    if sensitivity.empty:
        st.info("Sensitivity report not available. Run `uv run yeoi-build` to generate it.")
    else:
        st.plotly_chart(
            build_sensitivity_chart(sensitivity),
            use_container_width=True,
        )

        max_change = int(sensitivity["top5_rank_changes"].max())
        if max_change <= 2:
            st.success(
                f"Maximum Top-5 rank change is {max_change} city/cities — "
                "the Top-5 conclusion is robust to weight perturbations."
            )
        else:
            st.warning(
                f"Maximum Top-5 rank change is {max_change} cities — "
                "some weight adjustments can partially reshape the Top-5."
            )

    st.markdown("---")
    st.markdown("#### Data Credibility Tiers")
    st.markdown(
        "| Tier | Description | Metrics |\n"
        "|------|-------------|----------|\n"
        "| **A** | Official / statistical bureau | GDP, disposable income, "
        "population, house price, R&D, innovation index, university score |\n"
        "| **B** | Institutional public sources | Listed company count, "
        "high-tech company count, average wage |\n"
        "| **C** | Platform sample data | Job posting count, entry salary, "
        "rent |\n"
        "| **D** | Unverifiable / proxy | Youth unemployment proxy |"
    )

    st.markdown("#### Data Gaps")
    if missing.empty or len(missing) == 0:
        st.info("No core missing records in current processed output.")
    else:
        core = missing[missing.get("category", "") == "core"]
        if core.empty:
            st.info("No core missing records in current processed output.")
        else:
            st.dataframe(
                core.groupby("metric").size().reset_index(name="missing_cities"),
                hide_index=True,
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# Sidebar helpers
# ---------------------------------------------------------------------------


def _sidebar_year(scores: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    """Sidebar with Year selector only (for National Overview pages)."""
    st.sidebar.markdown("### Controls")
    years = sorted(scores["year"].unique())
    selected_year = st.sidebar.selectbox("Year", years, index=len(years) - 1)
    year_scores = scores[scores["year"] == selected_year].copy()
    return selected_year, year_scores


def _sidebar_year_and_city(
    scores: pd.DataFrame,
) -> tuple[int, pd.DataFrame, str, pd.Series]:
    """Sidebar with Year + City selectors (for City Analysis pages)."""
    st.sidebar.markdown("### Controls")
    years = sorted(scores["year"].unique())
    selected_year = st.sidebar.selectbox("Year", years, index=len(years) - 1)
    year_scores = scores[scores["year"] == selected_year].copy()
    cities_sorted = year_scores.sort_values("rank")["city"].tolist()
    selected_city = st.sidebar.selectbox("City", cities_sorted, index=0)
    city_row = year_scores[year_scores["city"] == selected_city].iloc[0]
    return selected_year, year_scores, selected_city, city_row


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="YEOI Dashboard", layout="wide")

    scores = load_scores()
    if scores.empty:
        st.warning(
            "Index results not yet generated. "
            "Please prepare `data/raw/city_panel.csv`, then run:\n\n"
            "`uv run yeoi-build`"
        )
        return

    panel = load_panel()
    sensitivity = load_sensitivity()
    missing = load_missing()

    # --- Page functions (closures over shared data) ---

    def _page_ranking_groups() -> None:
        year, year_scores = _sidebar_year(scores)
        _render_national_overview(year_scores, year)

    def _page_methodology() -> None:
        _sidebar_year(scores)
        _render_sensitivity(sensitivity, missing)

    def _page_city_profile() -> None:
        year, year_scores, city, city_row = _sidebar_year_and_city(scores)
        _render_city_profile(year_scores, city, year, city_row, panel)

    def _page_tradeoffs() -> None:
        year, year_scores, city, _ = _sidebar_year_and_city(scores)
        _render_tradeoffs(year_scores, panel, city, year)

    def _page_trends() -> None:
        _, _, city, _ = _sidebar_year_and_city(scores)
        _render_trends(scores, city)

    pages = {
        "National Overview": [
            st.Page(_page_ranking_groups, title="Ranking & Groups", icon="🌐"),
            st.Page(_page_methodology, title="Methodology & Data", icon="📋"),
        ],
        "City Analysis": [
            st.Page(_page_city_profile, title="City Profile", icon="🏙️"),
            st.Page(_page_tradeoffs, title="Trade-offs", icon="⚖️"),
            st.Page(_page_trends, title="Trends", icon="📈"),
        ],
    }
    pg = st.navigation(pages, position="sidebar")
    pg.run()


if __name__ == "__main__":
    main()
