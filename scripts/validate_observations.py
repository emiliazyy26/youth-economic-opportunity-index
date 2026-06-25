#!/usr/bin/env python3
"""Data quality validation script: time-series smoothness + cross-city comparability + caliber consistency.

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

# City tiers (for cross-city comparability checks)
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
    "weighted_university_score",
]

PANEL_METRIC_TO_OBS: dict[str, str] = {
    "disposable_income": "disposable_income",
    "gdp_per_capita": "gdp_per_capita",
    "population": "population",
    "innovation_index": "rd_expenditure",
    "house_price": "house_price",
    "weighted_university_score": "weighted_university_score",
    "population_growth": "population",
    "housing_burden": "house_price",
    "gdp_total": "gdp_total",
}

# Reasonable ranges for each metric
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

# P0/P1 manual review guidance (embedded in recommended_action)
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
        "source": "verify_official: check if source_url is from statistics bureau / government official source",
        "range": "verify_official: value outside reasonable range, verify against original communique",
        "spike": "check_caliber: verify if there is a statistical caliber switch or OCR extraction error",
        "gdp_consistency": "verify_official: check gdp_total unit (100M yuan) and population caliber",
        "income_gdp_ratio": "check_caliber: verify if income is all-resident or urban-resident caliber",
        "census_baseline": "check_caliber: 7th census baseline and subsequent yearbook population caliber may differ",
        "yeoi_incomplete": "leave_as_missing: supplement official rd_expenditure then rebuild index",
        "missing": "leave_as_missing: add official values in manual_source_observations.csv",
        "tier": "review: city tier inversion may reflect real economic pattern, not necessarily a data error",
        "rd_low": "verify_official: confirm R&D is city-wide general public budget science & technology expenditure",
        "rd_high": "review: high value may be broad caliber, verify communique definition",
    }
    return defaults.get(rule_type, "review: manually verify this observation")


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
                "detail": f"{metric}={row[metric]:.4g} outside reasonable range {lo}-{hi}",
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
                    direction = "up" if curr > prev else "down"
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
                            f"{city} {metric}: {prev_year}={prev:.1f}->{curr_year}={curr:.1f} "
                            f"({direction} {rate * 100:.1f}%, threshold {threshold * 100:.0f}%)"
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
                    f"gdp_total/pop×10^8={derived:.0f}, deviation {deviation * 100:.1f}%"
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
                            f"{city} {year}: gdp_total={gdp_total_val:.1f} 100M yuan inconsistent with population/gdp_per_capita"
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
                        f"{city} disposable_income: adjacent YoY {g1 * 100:.1f}%->{g2 * 100:.1f}%, "
                        "possible caliber switch"
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
                        f"{row['city']} {year}: population negative growth {row['population_growth'] * 100:.2f}%"
                        f" but income growth {income_growth * 100:.1f}%"
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
                "detail": f"{city} {year}: rd_expenditure={val:.2f} 100M yuan abnormally low (<1)",
            })
        if val > 600:
            warnings.append({
                "type": "rd_high",
                "severity": "LOW",
                "city": city,
                "year": year,
                "metric": "innovation_index",
                "value": float(val),
                "detail": f"{city} {year}: rd_expenditure={val:.1f} 100M yuan, high but may be broad caliber",
            })
    return warnings


def check_source_provenance(panel: pd.DataFrame, obs: pd.DataFrame) -> list[dict]:
    """Source credibility audit: non-official sources, mirror sites, OCR extraction."""
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
                issues.append("non-official source")
            if any(part in url for part in suspicious_url_parts):
                issues.append(f"third-party mirror/reprint ({url[:60]})")
            if method in suspicious_methods:
                issues.append(f"extraction_method={method}")

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
    """Income/GDP ratio should fall within 0.35-0.55 range."""
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
                f"(reasonable range {lo}-{hi})"
            ),
        })
    return warnings


def check_population_census_baseline(panel: pd.DataFrame, obs: pd.DataFrame) -> list[dict]:
    """Detect population jumps between 7th census year (2020) and subsequent years."""
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
                        f"{city} {year}: population={row['population']:.0f} vs "
                        f"2020 census={baseline:.0f} (deviation {rate * 100:.1f}%)"
                    ),
                })
    return warnings


def check_yeoi_completeness(panel: pd.DataFrame, scores: pd.DataFrame) -> list[dict]:
    """YEOI missing: core dimension missing causes yeoi_score to be NaN."""
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
                    f"{city} {year}: {metric} missing causes yeoi_score to be NaN "
                    f"(missing dimensions: {', '.join(missing_metrics)})"
                ),
            })
    return warnings


def check_missing_cells(panel: pd.DataFrame) -> list[dict]:
    """Missing values in core dimensions."""
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
                    "detail": f"{city} {year}: {metric} missing",
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
    """Final status for each city-year-metric (takes most severe)."""
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
    """20 cities x 6 dimensions: take most severe status across years."""
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
        "weighted_university_score": "univ",
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
    print("\nLegend: .=OK  ?=SUSPICIOUS  !=CRITICAL  -=MISSING  i=INFO")


def print_report(warnings: list[dict], title: str) -> None:
    if not warnings:
        print(f"\n✅ {title}: all passed")
        return

    high = [w for w in warnings if w["severity"] == "HIGH"]
    medium = [w for w in warnings if w["severity"] == "MEDIUM"]
    low = [w for w in warnings if w["severity"] == "LOW"]

    print(
        f"\n⚠️  {title}: {len(warnings)} warnings "
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
    print("🔧 Fix Suggestions")
    print("=" * 70)

    by_type: dict[str, list[dict]] = {}
    for w in warnings:
        by_type.setdefault(w["type"], []).append(w)

    if "range" in by_type:
        print("\n[Range anomalies] Values outside reasonable range, manual source verification needed:")
        for w in by_type["range"]:
            print(f"  - {w['city']} {w['year']} {w['metric']}={w['value']}")
            print("    -> Check source_observations.csv for this row's source_url credibility")

    if "spike" in by_type:
        print("\n[Time-series spikes] Spikes may be caused by caliber switch, data error, or real policy change:")
        for w in sorted(by_type["spike"], key=lambda item: item.get("rate", 0), reverse=True):
            if w["severity"] == "HIGH":
                print(f"  - {w['detail']}")

    if "gdp_consistency" in by_type:
        print("\n[GDP consistency] gdp_per_capita does not match gdp_total/population for these cities:")
        for w in sorted(
            by_type["gdp_consistency"],
            key=lambda item: item.get("deviation", 0),
            reverse=True,
        ):
            print(f"  - {w['detail']}")

    if "source" in by_type:
        print("\n[Source credibility] Non-official / mirror / OCR sources:")
        high_src = [w for w in by_type["source"] if w["severity"] == "HIGH"]
        for w in high_src[:15]:
            print(f"  - {w['detail']}")
        if len(high_src) > 15:
            print(f"  ... {len(high_src) - 15} more HIGH source warnings")

    if "income_gdp_ratio" in by_type:
        print("\n[Income/GDP ratio] Outside 0.35-0.55 reasonable range:")
        for w in by_type["income_gdp_ratio"]:
            print(f"  - {w['detail']}")

    if "census_baseline" in by_type:
        print("\n[Population baseline] Deviation >5% from 2020 7th census:")
        for w in by_type["census_baseline"]:
            print(f"  - {w['detail']}")

    if "yeoi_incomplete" in by_type:
        print("\n[YEOI completeness] Missing dimensions prevent score calculation:")
        for w in by_type["yeoi_incomplete"]:
            print(f"  - {w['detail']}")

    if "missing" in by_type:
        rd_missing = [w for w in by_type["missing"] if w["metric"] == "innovation_index"]
        if rd_missing:
            print("\n[R&D missing]")
            for w in rd_missing:
                print(f"  - {w['detail']}")

    print(f"\nTotal {len(warnings)} warnings, prioritize 🔴 HIGH severity first.")
    print("Fix: edit data/raw/manual_source_observations.csv then rerun:")
    print("    uv run yeoi-download && uv run yeoi-build")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YEOI data quality validation")
    parser.add_argument("--fix", action="store_true", help="Output fix suggestions")
    parser.add_argument(
        "--report-csv",
        nargs="?",
        const=str(DEFAULT_REPORT_FILE),
        default=None,
        help="Write structured CSV report (default: data/raw/data_quality_report.csv)",
    )
    parser.add_argument("--matrix", action="store_true", help="Output 20-city x 6-dimension status matrix")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 70)
    print("Youth Economic Opportunity Index — Data Quality Validation")
    print("=" * 70)
    print(f"Panel: {PANEL_FILE}")
    print(f"Observations: {OBS_FILE}")

    panel, obs = load_data()
    scores = load_yeoi_scores()
    cities = sorted(panel["city"].unique())
    print(f"Panel: {len(panel)} rows, Observations: {len(obs)} records")

    check_sections = [
        ("1. Range validity check", check_range_validity(panel)),
        ("2. Time-series smoothness", check_time_series_spikes(panel)),
        ("3. Cross-city tier consistency", check_cross_city_tiers(panel)),
        ("4. GDP caliber consistency", check_gdp_consistency(panel)),
        ("5. Disposable income caliber", check_income_consistency(panel)),
        ("6. Population vs income", check_population_vs_income_rank(panel)),
        ("7. R&D expenditure outliers", check_rd_outliers(panel)),
        ("8. Source credibility", check_source_provenance(panel, obs)),
        ("9. Income/GDP ratio", check_income_gdp_ratio(panel)),
        ("10. Population baseline consistency", check_population_census_baseline(panel, obs)),
        ("11. YEOI completeness", check_yeoi_completeness(panel, scores)),
        ("12. Core dimension missing", check_missing_cells(panel)),
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
        f"Total: {len(all_warnings)} warnings "
        f"(🔴 HIGH={summary.get('HIGH', 0)}, "
        f"🟡 MEDIUM={summary.get('MEDIUM', 0)}, "
        f"🔵 LOW={summary.get('LOW', 0)})"
    )

    cell_status = build_cell_status(all_warnings, panel)
    if args.matrix:
        print(f"\n{'=' * 70}")
        print("City x Dimension status matrix (most severe across years)")
        print_matrix(cell_status, cities)

    if args.report_csv is not None:
        report_path = Path(args.report_csv)
        report_df = build_report_dataframe(all_warnings, obs)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_df.to_csv(report_path, index=False)
        critical = report_df[report_df["status"] == "CRITICAL"]
        print(f"\n📄 Report written: {report_path} ({len(report_df)} rows, CRITICAL={len(critical)})")

    if args.fix and all_warnings:
        generate_fix_suggestions(all_warnings)

    if summary.get("HIGH", 0) > 10:
        sys.exit(1)


if __name__ == "__main__":
    main()
