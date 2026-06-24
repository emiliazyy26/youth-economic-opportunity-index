#!/usr/bin/env python3
"""数据质量校验脚本：时间序列平滑性 + 跨城市可比性 + 口径一致性。

Usage:
    uv run python scripts/validate_observations.py
    uv run python scripts/validate_observations.py --fix
    uv run python scripts/validate_observations.py --report-csv \
        data/raw/data_quality_report.csv --matrix
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PANEL_FILE = RAW_DIR / "city_panel.csv"
OBS_FILE = RAW_DIR / "source_observations.csv"
YEOI_FILE = PROCESSED_DIR / "yeoi_scores.csv"
DEFAULT_REPORT_FILE = RAW_DIR / "data_quality_report.csv"

# 城市层级（用于跨城市可比性检验）
CITY_TIERS: dict[str, int] = {
    "Beijing": 1, "Shanghai": 1, "Shenzhen": 1, "Guangzhou": 1,
    "Hangzhou": 2, "Nanjing": 2, "Suzhou": 2, "Chengdu": 2,
    "Wuhan": 2, "Xi'an": 2,
    "Hefei": 2, "Changsha": 2, "Qingdao": 2, "Xiamen": 2,
    "Zhengzhou": 2, "Chongqing": 2,
    "Harbin": 3, "Shenyang": 3, "Kunming": 3, "Nanchang": 3,
}

CORE_MATRIX_METRICS = [
    "disposable_income",
    "gdp_per_capita",
    "population",
    "innovation_index",
    "house_price",
    "university_quality",
]

PANEL_METRIC_TO_OBS: dict[str, str] = {
    "disposable_income": "disposable_income",
    "gdp_per_capita": "gdp_per_capita",
    "population": "population",
    "innovation_index": "rd_expenditure",
    "house_price": "house_price",
    "university_quality": "university_quality",
    "population_growth": "population",
    "housing_burden": "house_price",
    "gdp_total": "gdp_total",
}

# 各指标合理范围
REASONABLE_RANGES: dict[str, tuple[float, float]] = {
    "gdp_per_capita": (30000, 300000),
    "disposable_income": (20000, 120000),
    "population": (3_000_000, 35_000_000),
    "innovation_index": (0.5, 800),
    "housing_burden": (0.10, 0.90),
    "population_growth": (-0.05, 0.12),
}

INCOME_GDP_RATIO_RANGE = (0.25, 0.85)
CENSUS_BASELINE_THRESHOLD = 0.13

SPIKE_THRESHOLD: dict[str, float] = {
    "gdp_per_capita": 0.30,
    "disposable_income": 0.25,
    "population": 0.10,
    "innovation_index": 0.50,
}

STATUS_RANK = {"OK": 0, "INFO": 1, "MISSING": 2, "SUSPICIOUS": 3, "CRITICAL": 4}
SEVERITY_TO_STATUS = {
    "HIGH": "CRITICAL",
    "MEDIUM": "SUSPICIOUS",
    "LOW": "SUSPICIOUS",
    "INFO": "INFO",
}

# P0/P1 人工核查指引（嵌入 recommended_action）
MANUAL_ACTIONS: dict[tuple[str, int, str], str] = {
    ("Kunming", 2024, "disposable_income"): (
        "verified: 2024 all-resident disposable income corrected to 47301 yuan "
        "(urban value was 57444 yuan); see data/raw/quality_notes.md"
    ),
    ("Harbin", 2023, "disposable_income"): (
        "verified: 2023 urban disposable income corrected to 45784 yuan "
        "(original 56961 was an extraction error); all-resident value not available"
    ),
}

REPORT_COLUMNS = [
    "city",
    "year",
    "metric",
    "value",
    "status",
    "severity",
    "rule_type",
    "detail",
    "source_url",
    "is_official_source",
    "extraction_method",
    "recommended_action",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(PANEL_FILE)
    obs = pd.read_csv(OBS_FILE)
    return panel, obs


def load_yeoi_scores() -> pd.DataFrame:
    if not YEOI_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(YEOI_FILE)


def lookup_source(obs: pd.DataFrame, city: str, year: int, metric: str) -> dict:
    obs_metric = PANEL_METRIC_TO_OBS.get(metric, metric)
    match = obs[
        (obs["city"] == city)
        & (obs["year"] == year)
        & (obs["metric"] == obs_metric)
    ]
    if match.empty:
        return {
            "source_url": "",
            "is_official_source": "",
            "extraction_method": "",
        }
    row = match.iloc[0]
    return {
        "source_url": str(row.get("source_url", "") or ""),
        "is_official_source": row.get("is_official_source", ""),
        "extraction_method": str(row.get("extraction_method", "") or ""),
    }


def recommended_action(city: str, year: int, metric: str, rule_type: str) -> str:
    key = (city, year, metric)
    if key in MANUAL_ACTIONS:
        return MANUAL_ACTIONS[key]

    defaults = {
        "source": "verify_official: 核对 source_url 是否为统计局/政府官方来源",
        "range": "verify_official: 数值超出合理范围，核对原始公报",
        "spike": "check_caliber: 核实是否存在统计口径切换或OCR提取错误",
        "gdp_consistency": "verify_official: 核对 gdp_total 单位(亿元)与 population 口径",
        "income_gdp_ratio": "check_caliber: 核实收入为全体居民还是城镇居民口径",
        "census_baseline": "check_caliber: 七普基期与后续年报人口口径可能不一致",
        "yeoi_incomplete": "leave_as_missing: 补录官方 rd_expenditure 后重建指数",
        "missing": "leave_as_missing: 在 manual_source_observations.csv 补录官方值",
        "tier": "review: 城市层级倒挂可能反映真实经济格局，非必为数据错误",
        "rd_low": "verify_official: 确认 R&D 为全市一般公共预算科学技术支出",
        "rd_high": "review: 偏高值可能属宽口径，核对公报定义",
    }
    return defaults.get(rule_type, "review: 人工复核该观测")


def make_report_row(
    *,
    city: str,
    year: int,
    metric: str,
    value,
    status: str,
    severity: str,
    rule_type: str,
    detail: str,
    obs: pd.DataFrame,
) -> dict:
    src = lookup_source(obs, city, year, metric)
    return {
        "city": city,
        "year": year,
        "metric": metric,
        "value": value if pd.notna(value) else "",
        "status": status,
        "severity": severity,
        "rule_type": rule_type,
        "detail": detail,
        "source_url": src["source_url"],
        "is_official_source": src["is_official_source"],
        "extraction_method": src["extraction_method"],
        "recommended_action": recommended_action(city, year, metric, rule_type),
    }


def warning_to_report_row(w: dict, obs: pd.DataFrame) -> dict:
    status = SEVERITY_TO_STATUS.get(w["severity"], "SUSPICIOUS")
    if w.get("type") == "range" and w["metric"] == "population_growth":
        if abs(w.get("value", 0)) > 0.15:
            status = "CRITICAL"
    return make_report_row(
        city=w["city"],
        year=int(w["year"]),
        metric=w["metric"],
        value=w.get("value", ""),
        status=status,
        severity=w["severity"],
        rule_type=w["type"],
        detail=w["detail"],
        obs=obs,
    )


def check_range_validity(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    for metric, (lo, hi) in REASONABLE_RANGES.items():
        if metric not in panel.columns:
            continue
        rows = panel[panel[metric].notna() & ((panel[metric] < lo) | (panel[metric] > hi))]
        for _, row in rows.iterrows():
            warnings.append({
                "type": "range",
                "severity": "HIGH",
                "city": row["city"],
                "year": int(row["year"]),
                "metric": metric,
                "value": float(row[metric]),
                "bound": f"[{lo}, {hi}]",
                "detail": f"{metric}={row[metric]:.4g} 超出合理范围 {lo}-{hi}",
            })
    return warnings


def check_time_series_spikes(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    for city, group in panel.groupby("city"):
        group = group.sort_values("year")
        for metric, threshold in SPIKE_THRESHOLD.items():
            if metric not in group.columns:
                continue
            values = group[["year", metric]].dropna().reset_index(drop=True)
            if len(values) < 2:
                continue
            for i in range(1, len(values)):
                prev = values.loc[i - 1, metric]
                curr = values.loc[i, metric]
                prev_year = int(values.loc[i - 1, "year"])
                curr_year = int(values.loc[i, "year"])
                if prev == 0:
                    continue
                rate = abs(curr / prev - 1)
                if rate > threshold:
                    direction = "↑" if curr > prev else "↓"
                    severity = "HIGH" if rate > threshold * 1.5 else "MEDIUM"
                    if (city, curr_year, metric) in MANUAL_ACTIONS:
                        severity = "HIGH"
                    warnings.append({
                        "type": "spike",
                        "severity": severity,
                        "city": city,
                        "year": curr_year,
                        "metric": metric,
                        "value": float(curr),
                        "prev_value": float(prev),
                        "prev_year": prev_year,
                        "rate": float(rate),
                        "detail": (
                            f"{city} {metric}: {prev_year}={prev:.1f}→{curr_year}={curr:.1f} "
                            f"({direction}{rate * 100:.1f}%, 阈值 {threshold * 100:.0f}%)"
                        ),
                    })
    return warnings


def check_cross_city_tiers(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    for year in sorted(panel["year"].unique()):
        year_data = panel[panel["year"] == year].copy()
        year_data["tier"] = year_data["city"].map(CITY_TIERS)

        for metric in ["gdp_per_capita", "disposable_income", "innovation_index"]:
            if metric not in year_data.columns:
                continue
            valid = year_data[year_data[metric].notna() & year_data["tier"].notna()]

            for tier in [1, 2]:
                tier_cities = valid[valid["tier"] == tier]
                lower_tier = valid[valid["tier"] == tier + 1]
                if tier_cities.empty or lower_tier.empty:
                    continue
                tier_min = tier_cities[metric].min()
                lower_max = lower_tier[metric].max()
                if tier_min < lower_max:
                    outliers = lower_tier[lower_tier[metric] > tier_min]
                    for _, row in outliers.iterrows():
                        warnings.append({
                            "type": "tier",
                            "severity": "LOW",
                            "city": row["city"],
                            "year": int(year),
                            "metric": metric,
                            "value": float(row[metric]),
                            "detail": (
                                f"{row['city']}(Tier{tier + 1}) {metric}={row[metric]:.0f} > "
                                f"Tier {tier} min {tier_min:.0f} ({year})"
                            ),
                        })
    return warnings


def check_gdp_consistency(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    mask = (
        panel["gdp_per_capita"].notna()
        & panel["gdp_total"].notna()
        & panel["population"].notna()
        & (panel["population"] > 0)
    )
    for _, row in panel[mask].iterrows():
        derived = row["gdp_total"] * 100_000_000 / row["population"]
        reported = row["gdp_per_capita"]
        if derived == 0:
            continue
        deviation = abs(reported / derived - 1)
        if deviation > 0.15:
            city = row["city"]
            year = int(row["year"])
            severity = "HIGH" if deviation > 0.25 else "MEDIUM"
            warnings.append({
                "type": "gdp_consistency",
                "severity": severity,
                "city": city,
                "year": year,
                "metric": "gdp_per_capita",
                "value": float(reported),
                "deviation": float(deviation),
                "detail": (
                    f"{city} {year}: gdp_per_capita={reported:.0f}, "
                    f"gdp_total/pop×10^8={derived:.0f}, 偏差 {deviation * 100:.1f}%"
                ),
            })
            metrics_for_cell = {
                w["metric"]
                for w in warnings
                if w["city"] == city and w["year"] == year
            }
            if "gdp_total" not in metrics_for_cell:
                gdp_total_val = float(row["gdp_total"])
                gdp_total_in_manual = (city, year, "gdp_total") in MANUAL_ACTIONS
                if gdp_total_in_manual or deviation > 0.25:
                    warnings.append({
                        "type": "gdp_consistency",
                        "severity": severity,
                        "city": city,
                        "year": year,
                        "metric": "gdp_total",
                        "value": gdp_total_val,
                        "detail": (
                            f"{city} {year}: gdp_total={gdp_total_val:.1f}亿 与人口/人均GDP不自洽"
                        ),
                    })
    return warnings


def check_income_consistency(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    for city, group in panel.groupby("city"):
        income = group[["year", "disposable_income"]].dropna().sort_values("year")
        if len(income) < 3:
            continue
        for i in range(2, len(income)):
            g1 = (
                income.iloc[i - 1]["disposable_income"]
                / income.iloc[i - 2]["disposable_income"]
                - 1
            )
            g2 = (
                income.iloc[i]["disposable_income"]
                / income.iloc[i - 1]["disposable_income"]
                - 1
            )
            if abs(g1) < 0.01 and abs(g2) > 0.10:
                warnings.append({
                    "type": "income_stutter",
                    "severity": "LOW",
                    "city": city,
                    "year": int(income.iloc[i]["year"]),
                    "metric": "disposable_income",
                    "value": float(income.iloc[i]["disposable_income"]),
                    "detail": (
                        f"{city} disposable_income: 邻年增{g1 * 100:.1f}%→{g2 * 100:.1f}%，"
                        "可能存在口径切换"
                    ),
                })
    return warnings


def check_population_vs_income_rank(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    for year in sorted(panel["year"].unique()):
        year_panel = panel[panel["year"] == year]
        data = year_panel.dropna(subset=["population_growth", "disposable_income"])
        neg_pop = data[data["population_growth"] < 0]
        if neg_pop.empty:
            continue
        for _, row in neg_pop.iterrows():
            prev = panel[
                (panel["city"] == row["city"]) & (panel["year"] == year - 1)
            ]["disposable_income"]
            if prev.empty or prev.iloc[0] == 0:
                continue
            income_growth = row["disposable_income"] / prev.iloc[0] - 1
            if income_growth > 0.10:
                warnings.append({
                    "type": "pop_income_inversion",
                    "severity": "LOW",
                    "city": row["city"],
                    "year": int(year),
                    "metric": "disposable_income",
                    "value": float(row["disposable_income"]),
                    "detail": (
                        f"{row['city']} {year}: 人口负增长{row['population_growth'] * 100:.2f}%"
                        f"但收入增{income_growth * 100:.1f}%"
                    ),
                })
    return warnings


def check_rd_outliers(panel: pd.DataFrame) -> list[dict]:
    warnings = []
    rd = panel[panel["innovation_index"].notna()]
    for _, row in rd.iterrows():
        val = row["innovation_index"]
        city = row["city"]
        year = int(row["year"])
        if val < 1.0:
            warnings.append({
                "type": "rd_low",
                "severity": "MEDIUM",
                "city": city,
                "year": year,
                "metric": "innovation_index",
                "value": float(val),
                "detail": f"{city} {year}: rd_expenditure={val:.2f}亿元 异常低（<1亿）",
            })
        if val > 600:
            warnings.append({
                "type": "rd_high",
                "severity": "LOW",
                "city": city,
                "year": year,
                "metric": "innovation_index",
                "value": float(val),
                "detail": f"{city} {year}: rd_expenditure={val:.1f}亿元，偏高但可能属宽口径",
            })
    return warnings


def check_source_provenance(panel: pd.DataFrame, obs: pd.DataFrame) -> list[dict]:
    """来源可信度审计：非官方来源、镜像站、OCR 提取。"""
    warnings = []
    suspicious_url_parts = ("hongheiku", "gotohui", "tjcn.org", "people.com.cn")
    suspicious_methods = ("regex_or_ocr",)

    for _, row in panel.iterrows():
        city = row["city"]
        year = int(row["year"])
        for metric in CORE_MATRIX_METRICS:
            if metric not in panel.columns or pd.isna(row.get(metric)):
                continue

            src = lookup_source(obs, city, year, metric)
            url = src["source_url"].lower()
            method = src["extraction_method"]
            is_official = src["is_official_source"]

            issues = []
            if is_official is False or is_official == "False":
                issues.append("非官方来源")
            if any(part in url for part in suspicious_url_parts):
                issues.append(f"第三方镜像/转载 ({url[:60]})")
            if method in suspicious_methods:
                issues.append(f"提取方式={method}")

            if not issues:
                continue

            severity = "MEDIUM"
            if metric == "house_price":
                severity = "LOW"

            warnings.append({
                "type": "source",
                "severity": severity,
                "city": city,
                "year": year,
                "metric": metric,
                "value": float(row[metric]),
                "detail": f"{city} {year} {metric}: " + "; ".join(issues),
            })
    return warnings


def check_income_gdp_ratio(panel: pd.DataFrame) -> list[dict]:
    """收入/GDP 比率应在 0.35–0.55 区间。"""
    warnings = []
    lo, hi = INCOME_GDP_RATIO_RANGE
    mask = panel["disposable_income"].notna() & panel["gdp_per_capita"].notna()
    for _, row in panel[mask].iterrows():
        ratio = row["disposable_income"] / row["gdp_per_capita"]
        if lo <= ratio <= hi:
            continue
        city = row["city"]
        year = int(row["year"])
        severity = "HIGH" if ratio > 0.70 or ratio < 0.25 else "MEDIUM"
        warnings.append({
            "type": "income_gdp_ratio",
            "severity": severity,
            "city": city,
            "year": year,
            "metric": "disposable_income",
            "value": float(row["disposable_income"]),
            "detail": (
                f"{city} {year}: income/gdp_per_capita={ratio:.3f} "
                f"(合理区间 {lo}-{hi})"
            ),
        })
    return warnings


def check_population_census_baseline(panel: pd.DataFrame, obs: pd.DataFrame) -> list[dict]:
    """七普年(2020)与后续年份人口跳变检测。"""
    warnings = []
    census = obs[(obs["year"] == 2020) & (obs["metric"] == "population")]
    if census.empty:
        return warnings

    census_pop = census.set_index("city")["value"].to_dict()
    for city, group in panel.groupby("city"):
        if city not in census_pop:
            continue
        baseline = census_pop[city]
        if baseline == 0:
            continue
        for _, row in group.sort_values("year").iterrows():
            year = int(row["year"])
            if year < 2021 or pd.isna(row.get("population")):
                continue
            rate = abs(row["population"] / baseline - 1)
            if rate > CENSUS_BASELINE_THRESHOLD:
                warnings.append({
                    "type": "census_baseline",
                    "severity": "HIGH" if rate > 0.08 else "MEDIUM",
                    "city": city,
                    "year": year,
                    "metric": "population",
                    "value": float(row["population"]),
                    "detail": (
                        f"{city} {year}: 人口={row['population']:.0f} vs "
                        f"2020七普={baseline:.0f} (偏差 {rate * 100:.1f}%)"
                    ),
                })
    return warnings


def check_yeoi_completeness(panel: pd.DataFrame, scores: pd.DataFrame) -> list[dict]:
    """YEOI 缺失：核心维度缺失导致 yeoi_score 为 NaN。"""
    warnings = []
    if scores.empty:
        return warnings

    score_cols = [
        "disposable_income",
        "gdp_per_capita",
        "population_growth",
        "innovation_index",
        "housing_burden",
    ]

    incomplete = scores[scores["yeoi_score"].isna()]
    seen: set[tuple[str, int, str]] = set()
    for _, srow in incomplete.iterrows():
        city = srow["city"]
        year = int(srow["year"])
        prow = panel[(panel["city"] == city) & (panel["year"] == year)]
        if prow.empty:
            continue
        prow = prow.iloc[0]
        missing_metrics = [m for m in score_cols if pd.isna(prow.get(m))]
        for metric in missing_metrics:
            key = (city, year, metric)
            if key in seen:
                continue
            seen.add(key)
            warnings.append({
                "type": "yeoi_incomplete",
                "severity": "HIGH" if metric == "innovation_index" else "MEDIUM",
                "city": city,
                "year": year,
                "metric": metric,
                "value": "",
                "detail": (
                    f"{city} {year}: {metric} 缺失导致 yeoi_score 无法计算 "
                    f"(缺失分项: {', '.join(missing_metrics)})"
                ),
            })
    return warnings


def check_missing_cells(panel: pd.DataFrame) -> list[dict]:
    """核心维度缺失值。"""
    warnings = []
    for _, row in panel.iterrows():
        city = row["city"]
        year = int(row["year"])
        for metric in CORE_MATRIX_METRICS:
            if metric not in panel.columns:
                continue
            if pd.isna(row.get(metric)):
                warnings.append({
                    "type": "missing",
                    "severity": "MEDIUM" if metric == "innovation_index" else "LOW",
                    "city": city,
                    "year": year,
                    "metric": metric,
                    "value": "",
                    "detail": f"{city} {year}: {metric} 缺失",
                })
    return warnings


def run_all_checks(
    panel: pd.DataFrame,
    obs: pd.DataFrame,
    scores: pd.DataFrame,
) -> list[dict]:
    checks = [
        check_range_validity(panel),
        check_time_series_spikes(panel),
        check_cross_city_tiers(panel),
        check_gdp_consistency(panel),
        check_income_consistency(panel),
        check_population_vs_income_rank(panel),
        check_rd_outliers(panel),
        check_source_provenance(panel, obs),
        check_income_gdp_ratio(panel),
        check_population_census_baseline(panel, obs),
        check_yeoi_completeness(panel, scores),
        check_missing_cells(panel),
    ]
    all_warnings: list[dict] = []
    for result in checks:
        all_warnings.extend(result)
    return all_warnings


def build_report_dataframe(all_warnings: list[dict], obs: pd.DataFrame) -> pd.DataFrame:
    rows = [warning_to_report_row(w, obs) for w in all_warnings]
    if not rows:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    report = pd.DataFrame(rows)
    report = report.drop_duplicates(
        subset=["city", "year", "metric", "rule_type", "detail"],
        keep="first",
    )
    sort_order = {"CRITICAL": 0, "SUSPICIOUS": 1, "INFO": 2, "MISSING": 3, "OK": 4}
    report["_sort"] = report["status"].map(sort_order).fillna(5)
    report = report.sort_values(["_sort", "city", "year", "metric"]).drop(columns=["_sort"])
    return report[REPORT_COLUMNS]


def build_cell_status(
    all_warnings: list[dict],
    panel: pd.DataFrame,
) -> dict[tuple[str, int, str], str]:
    """每个 city-year-metric 的最终状态（取最严重）。"""
    status: dict[tuple[str, int, str], str] = {}

    for _, row in panel.iterrows():
        city = row["city"]
        year = int(row["year"])
        for metric in CORE_MATRIX_METRICS:
            key = (city, year, metric)
            if metric not in panel.columns or pd.isna(row.get(metric)):
                status[key] = "MISSING"
            else:
                status[key] = "OK"

    for w in all_warnings:
        key = (w["city"], int(w["year"]), w["metric"])
        new_status = SEVERITY_TO_STATUS.get(w["severity"], "SUSPICIOUS")
        if w["type"] == "missing":
            new_status = "MISSING"
        if w["type"] == "range" and w["metric"] == "population_growth":
            if abs(w.get("value", 0)) > 0.15:
                new_status = "CRITICAL"
        current = status.get(key, "OK")
        if STATUS_RANK.get(new_status, 0) >= STATUS_RANK.get(current, 0):
            status[key] = new_status

    return status


def print_matrix(cell_status: dict[tuple[str, int, str], str], cities: list[str]) -> None:
    """20 城 × 6 维：跨年份取最严重状态。"""
    symbols = {
        "OK": ".",
        "INFO": "i",
        "MISSING": "-",
        "SUSPICIOUS": "?",
        "CRITICAL": "!",
    }
    metric_labels = {
        "disposable_income": "income",
        "gdp_per_capita": "gdp_pc",
        "population": "pop",
        "innovation_index": "innov",
        "house_price": "price",
        "university_quality": "univ",
    }

    aggregated: dict[tuple[str, str], str] = {}
    for (city, _year, metric), stat in cell_status.items():
        key = (city, metric)
        prev = aggregated.get(key, "OK")
        if STATUS_RANK.get(stat, 0) >= STATUS_RANK.get(prev, 0):
            aggregated[key] = stat

    header = f"{'city':<12}" + "".join(f"{metric_labels[m]:>7}" for m in CORE_MATRIX_METRICS)
    print(header)
    print("-" * len(header))
    for city in cities:
        cells = "".join(
            f"{symbols.get(aggregated.get((city, m), 'OK'), '?'):>7}"
            for m in CORE_MATRIX_METRICS
        )
        print(f"{city:<12}{cells}")
    print("\n图例: .=OK  ?=SUSPICIOUS  !=CRITICAL  -=MISSING  i=INFO")


def print_report(warnings: list[dict], title: str) -> None:
    if not warnings:
        print(f"\n✅ {title}: 全部通过")
        return

    high = [w for w in warnings if w["severity"] == "HIGH"]
    medium = [w for w in warnings if w["severity"] == "MEDIUM"]
    low = [w for w in warnings if w["severity"] == "LOW"]

    print(
        f"\n⚠️  {title}: {len(warnings)} 条警告 "
        f"(🔴 HIGH={len(high)}, 🟡 MEDIUM={len(medium)}, 🔵 LOW={len(low)})"
    )

    for w in sorted(
        warnings,
        key=lambda item: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item["severity"]],
            item.get("city", ""),
        ),
    ):
        emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}[w["severity"]]
        print(f"  {emoji} [{w['type']}] {w['detail']}")


def generate_fix_suggestions(warnings: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("🔧 修复建议")
    print("=" * 70)

    by_type: dict[str, list[dict]] = {}
    for w in warnings:
        by_type.setdefault(w["type"], []).append(w)

    if "range" in by_type:
        print("\n【范围异常】以下值超出合理区间，需人工核实来源：")
        for w in by_type["range"]:
            print(f"  - {w['city']} {w['year']} {w['metric']}={w['value']}")
            print("    → 检查 source_observations.csv 该条的 source_url 是否可信")

    if "spike" in by_type:
        print("\n【时间序列突变】以下突变可能由口径切换、数据错误或真实政策变化导致：")
        for w in sorted(by_type["spike"], key=lambda item: item.get("rate", 0), reverse=True):
            if w["severity"] == "HIGH":
                print(f"  - {w['detail']}")

    if "gdp_consistency" in by_type:
        print("\n【GDP一致性】以下城市的 gdp_per_capita 与 gdp_total/population 推算值不匹配：")
        for w in sorted(
            by_type["gdp_consistency"],
            key=lambda item: item.get("deviation", 0),
            reverse=True,
        ):
            print(f"  - {w['detail']}")

    if "source" in by_type:
        print("\n【来源可信度】非官方/镜像/OCR 来源：")
        high_src = [w for w in by_type["source"] if w["severity"] == "HIGH"]
        for w in high_src[:15]:
            print(f"  - {w['detail']}")
        if len(high_src) > 15:
            print(f"  ... 另有 {len(high_src) - 15} 条 HIGH 来源警告")

    if "income_gdp_ratio" in by_type:
        print("\n【收入/GDP比率】超出 0.35-0.55 合理区间：")
        for w in by_type["income_gdp_ratio"]:
            print(f"  - {w['detail']}")

    if "census_baseline" in by_type:
        print("\n【人口基期】与2020七普偏差 >5%：")
        for w in by_type["census_baseline"]:
            print(f"  - {w['detail']}")

    if "yeoi_incomplete" in by_type:
        print("\n【YEOI完整性】缺失导致无法计算总分：")
        for w in by_type["yeoi_incomplete"]:
            print(f"  - {w['detail']}")

    if "missing" in by_type:
        rd_missing = [w for w in by_type["missing"] if w["metric"] == "innovation_index"]
        if rd_missing:
            print("\n【R&D缺失】")
            for w in rd_missing:
                print(f"  - {w['detail']}")

    print(f"\n总计 {len(warnings)} 条警告，建议优先处理 🔴 HIGH 级别。")
    print("修复方式：编辑 data/raw/manual_source_observations.csv 对应行后重新运行")
    print("    uv run yeoi-download && uv run yeoi-build")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YEOI 数据质量校验")
    parser.add_argument("--fix", action="store_true", help="输出修复建议")
    parser.add_argument(
        "--report-csv",
        nargs="?",
        const=str(DEFAULT_REPORT_FILE),
        default=None,
        help="写出结构化 CSV 报告（默认 data/raw/data_quality_report.csv）",
    )
    parser.add_argument("--matrix", action="store_true", help="输出 20城×6维 状态矩阵")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 70)
    print("Youth Economic Opportunity Index — 数据质量校验")
    print("=" * 70)
    print(f"Panel: {PANEL_FILE}")
    print(f"Observations: {OBS_FILE}")

    panel, obs = load_data()
    scores = load_yeoi_scores()
    cities = sorted(panel["city"].unique())
    print(f"面板: {len(panel)} 行, 观测: {len(obs)} 条")

    check_sections = [
        ("1. 数值范围检验", check_range_validity(panel)),
        ("2. 时间序列平滑性", check_time_series_spikes(panel)),
        ("3. 跨城市层级一致性", check_cross_city_tiers(panel)),
        ("4. GDP 口径一致性", check_gdp_consistency(panel)),
        ("5. 可支配收入口径", check_income_consistency(panel)),
        ("6. 人口 vs 收入", check_population_vs_income_rank(panel)),
        ("7. 科技支出异常值", check_rd_outliers(panel)),
        ("8. 来源可信度", check_source_provenance(panel, obs)),
        ("9. 收入/GDP比率", check_income_gdp_ratio(panel)),
        ("10. 人口基期一致性", check_population_census_baseline(panel, obs)),
        ("11. YEOI完整性", check_yeoi_completeness(panel, scores)),
        ("12. 核心维度缺失", check_missing_cells(panel)),
    ]

    all_warnings: list[dict] = []
    for title, warnings in check_sections:
        print(f"\n--- {title} ---")
        all_warnings.extend(warnings)
        print_report(warnings, title.split(". ", 1)[-1])

    summary: dict[str, int] = {}
    for w in all_warnings:
        summary[w["severity"]] = summary.get(w["severity"], 0) + 1
    print(f"\n{'=' * 70}")
    print(
        f"总计: {len(all_warnings)} 条警告 "
        f"(🔴 HIGH={summary.get('HIGH', 0)}, "
        f"🟡 MEDIUM={summary.get('MEDIUM', 0)}, "
        f"🔵 LOW={summary.get('LOW', 0)})"
    )

    cell_status = build_cell_status(all_warnings, panel)
    if args.matrix:
        print(f"\n{'=' * 70}")
        print("城市 × 维度 状态矩阵（跨年份取最严重状态）")
        print_matrix(cell_status, cities)

    if args.report_csv is not None:
        report_path = Path(args.report_csv)
        report_df = build_report_dataframe(all_warnings, obs)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_df.to_csv(report_path, index=False)
        critical = report_df[report_df["status"] == "CRITICAL"]
        print(f"\n📄 报告已写入: {report_path} ({len(report_df)} 行, CRITICAL={len(critical)})")

    if args.fix and all_warnings:
        generate_fix_suggestions(all_warnings)

    if summary.get("HIGH", 0) > 10:
        sys.exit(1)


if __name__ == "__main__":
    main()
