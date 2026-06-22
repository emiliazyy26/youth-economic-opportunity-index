#!/usr/bin/env python3
"""数据质量校验脚本：时间序列平滑性 + 跨城市可比性 + 口径一致性。

Usage:
    uv run python scripts/validate_observations.py          # 全部校验
    uv run python scripts/validate_observations.py --fix    # 校验 + 输出修复建议
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PANEL_FILE = RAW_DIR / "city_panel.csv"
OBS_FILE = RAW_DIR / "source_observations.csv"
MANUAL_FILE = RAW_DIR / "manual_source_observations.csv"
UEOI_FILE = PROCESSED_DIR / "ueoi_scores.csv"

# 城市层级（用于跨城市可比性检验）
CITY_TIERS: dict[str, int] = {
    "Beijing": 1, "Shanghai": 1, "Shenzhen": 1, "Guangzhou": 1,
    "Hangzhou": 2, "Nanjing": 2, "Suzhou": 2, "Chengdu": 2,
    "Wuhan": 2, "Xi'an": 2,
    "Hefei": 2, "Changsha": 2, "Qingdao": 2, "Xiamen": 2,
    "Zhengzhou": 2, "Chongqing": 2,
    "Harbin": 3, "Shenyang": 3, "Kunming": 3, "Nanchang": 3,
}

# 各指标合理范围
REASONABLE_RANGES: dict[str, tuple[float, float]] = {
    "gdp_per_capita": (30000, 300000),       # 元/人
    "disposable_income": (20000, 120000),     # 元/人
    "population": (3000000, 35000000),        # 人
    "innovation_index": (0.5, 800),           # 亿元（科技支出）
    "housing_burden": (0.0005, 0.005),        # 比率
    "population_growth": (-0.05, 0.05),       # -5% ~ +5%
}

# 时间序列突变阈值（相对变化率）
SPIKE_THRESHOLD: dict[str, float] = {
    "gdp_per_capita": 0.30,      # 30% 以上变化标记
    "disposable_income": 0.25,   # 25%
    "population": 0.10,          # 人口 10%（含普查修正）
    "innovation_index": 0.50,    # 科技支出允许大波动（如哈尔滨 2024 增 64.6%）
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(PANEL_FILE)
    obs = pd.read_csv(OBS_FILE)
    return panel, obs


def check_range_validity(panel: pd.DataFrame) -> list[dict]:
    """检查每个值是否在合理范围内。"""
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
                "detail": f"{metric}={row[metric]:.1f} 超出合理范围 {lo}-{hi}",
            })
    return warnings


def check_time_series_spikes(panel: pd.DataFrame) -> list[dict]:
    """检查各城市各指标时间序列中是否存在突变。"""
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
                    warnings.append({
                        "type": "spike",
                        "severity": "HIGH" if rate > threshold * 1.5 else "MEDIUM",
                        "city": city,
                        "year": curr_year,
                        "metric": metric,
                        "value": float(curr),
                        "prev_value": float(prev),
                        "prev_year": prev_year,
                        "rate": float(rate),
                        "detail": (
                            f"{city} {metric}: {prev_year}={prev:.1f}→{curr_year}={curr:.1f} "
                            f"({direction}{rate*100:.1f}%, 阈值 {threshold*100:.0f}%)"
                        ),
                    })
    return warnings


def check_cross_city_tiers(panel: pd.DataFrame) -> list[dict]:
    """检查城市层级一致性：Tier 1 城市各指标应在 Tier 2 之上，Tier 2 > Tier 3。"""
    warnings = []
    for year in sorted(panel["year"].unique()):
        year_data = panel[panel["year"] == year].copy()
        year_data["tier"] = year_data["city"].map(CITY_TIERS)

        for metric in ["gdp_per_capita", "disposable_income", "innovation_index"]:
            if metric not in year_data.columns:
                continue
            valid = year_data[year_data[metric].notna() & year_data["tier"].notna()]

            for t in [1, 2]:
                tier_cities = valid[valid["tier"] == t]
                lower_tier = valid[valid["tier"] == t + 1]
                if tier_cities.empty or lower_tier.empty:
                    continue
                t_min = tier_cities[metric].min()
                lower_max = lower_tier[metric].max()
                if t_min < lower_max:
                    outliers = lower_tier[lower_tier[metric] > t_min]
                    for _, row in outliers.iterrows():
                        warnings.append({
                            "type": "tier",
                            "severity": "MEDIUM",
                            "city": row["city"],
                            "year": year,
                            "metric": metric,
                            "value": float(row[metric]),
                            "tier_low": t,
                            "tier_min": float(t_min),
                            "detail": (
                                f"{row['city']}(Tier{t + 1}) {metric}={row[metric]:.0f} > "
                                f"Tier {t} 最小值 {t_min:.0f} ({year})"
                            ),
                        })
    return warnings


def check_gdp_consistency(panel: pd.DataFrame) -> list[dict]:
    """检查 gdp_per_capita ≈ gdp_total / population 是否自洽（±15% 容忍度）。"""
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
            warnings.append({
                "type": "gdp_consistency",
                "severity": "HIGH" if deviation > 0.25 else "MEDIUM",
                "city": row["city"],
                "year": int(row["year"]),
                "metric": "gdp_per_capita",
                "value": float(reported),
                "derived": float(derived),
                "deviation": float(deviation),
                "detail": (
                    f"{row['city']} {int(row['year'])}: gdp_per_capita={reported:.0f}, "
                    f"gdp_total/pop×10^8={derived:.0f}, 偏差 {deviation*100:.1f}%"
                ),
            })
    return warnings


def check_income_consistency(panel: pd.DataFrame) -> list[dict]:
    """检查 disposable_income 时间序列中是否存在口径切换导致的突变。"""
    warnings = []
    for city, group in panel.groupby("city"):
        income = group[["year", "disposable_income"]].dropna().sort_values("year")
        if len(income) < 3:
            continue
        # 检测：连续两年增长 < 1%，第三年突然变化
        for i in range(2, len(income)):
            g1 = income.iloc[i - 1]["disposable_income"] / income.iloc[i - 2]["disposable_income"] - 1
            g2 = income.iloc[i]["disposable_income"] / income.iloc[i - 1]["disposable_income"] - 1
            if abs(g1) < 0.01 and abs(g2) > 0.10:
                warnings.append({
                    "type": "income_stutter",
                    "severity": "LOW",
                    "city": city,
                    "year": int(income.iloc[i]["year"]),
                    "metric": "disposable_income",
                    "value": float(income.iloc[i]["disposable_income"]),
                    "detail": (
                        f"{city} disposable_income: 邻年增{g1*100:.1f}%→{g2*100:.1f}%，"
                        f"可能存在口径切换"
                    ),
                })
    return warnings


def check_population_vs_income_rank(panel: pd.DataFrame) -> list[dict]:
    """检查人口 vs 收入排名倒挂（人口流出城市不应收入暴涨）。"""
    warnings = []
    for year in sorted(panel["year"].unique()):
        data = panel[panel["year"] == year].dropna(subset=["population_growth", "disposable_income"])
        if len(data) < 10:
            continue
        # 人口减速最低的 5 个城市里，可支配收入增长不应排前 5
        # 简化：人口负增长城市收入增长不应 > 人口正增长城市
        neg_pop = data[data["population_growth"] < 0]
        if neg_pop.empty:
            continue
        pos_pop_max_income_growth = data[data["population_growth"] > 0]["disposable_income"].max()
        for _, row in neg_pop.iterrows():
            prev = panel[(panel["city"] == row["city"]) & (panel["year"] == year - 1)]["disposable_income"]
            if prev.empty or prev.iloc[0] == 0:
                continue
            income_growth = row["disposable_income"] / prev.iloc[0] - 1
            if income_growth > 0.10:
                warnings.append({
                    "type": "pop_income_inversion",
                    "severity": "LOW",
                    "city": row["city"],
                    "year": year,
                    "metric": "disposable_income",
                    "value": float(row["disposable_income"]),
                    "detail": f"{row['city']} {year}: 人口负增长{row['population_growth']*100:.2f}%但收入增{income_growth*100:.1f}%",
                })
    return warnings


def check_rd_outliers(panel: pd.DataFrame) -> list[dict]:
    """检查 innovation_index 异常值（< 1 亿或 > 600 亿，但 rd 口径需确认）。"""
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
                "city": city, "year": year,
                "metric": "innovation_index",
                "value": float(val),
                "detail": f"{city} {year}: rd_expenditure={val:.2f}亿元 异常低（<1亿），请确认单位或口径",
            })
        if val > 600:
            warnings.append({
                "type": "rd_high",
                "severity": "LOW",
                "city": city, "year": year,
                "metric": "innovation_index",
                "value": float(val),
                "detail": f"{city} {year}: rd_expenditure={val:.1f}亿元，偏高但可能属宽口径",
            })
    return warnings


def print_report(warnings: list[dict], title: str) -> None:
    if not warnings:
        print(f"\n✅ {title}: 全部通过")
        return

    high = [w for w in warnings if w["severity"] == "HIGH"]
    medium = [w for w in warnings if w["severity"] == "MEDIUM"]
    low = [w for w in warnings if w["severity"] == "LOW"]

    print(f"\n⚠️  {title}: {len(warnings)} 条警告 "
          f"(🔴 HIGH={len(high)}, 🟡 MEDIUM={len(medium)}, 🔵 LOW={len(low)})")

    for w in sorted(warnings, key=lambda w: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[w["severity"]], w.get("city", ""))):
        emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}[w["severity"]]
        print(f"  {emoji} [{w['type']}] {w['detail']}")


def generate_fix_suggestions(warnings: list[dict]) -> None:
    """基于警告类型生成修复建议。"""
    print("\n" + "=" * 70)
    print("🔧 修复建议")
    print("=" * 70)

    by_type: dict[str, list[dict]] = {}
    for w in warnings:
        by_type.setdefault(w["type"], []).append(w)

    if "range" in by_type:
        print("\n【范围异常】以下值超出合理区间，需人工核实来源：")
        for w in by_type["range"]:
            print(f"  - {w['city']} {w['year']} {w['metric']}={w['value']} (合理范围 {w['bound']})")
            print(f"    → 检查 source_observations.csv 该条的 source_url 是否可信")

    if "spike" in by_type:
        print("\n【时间序列突变】以下突变可能由口径切换、数据错误或真实政策变化导致：")
        for w in sorted(by_type["spike"], key=lambda w: w["rate"], reverse=True):
            if w["severity"] == "HIGH":
                print(f"  - {w['detail']}")
                if w["metric"] == "innovation_index":
                    print(f"    → 若为科技支出口径，确认是否是全市 vs 市本级口径差异")
                elif w["metric"] == "population":
                    print(f"    → 检查是否引用了户籍人口 vs 常住人口")
                elif w["metric"] == "disposable_income":
                    print(f"    → 确认是否从城镇居民切换到全体居民口径")

    if "gdp_consistency" in by_type:
        print("\n【GDP一致性】以下城市的 gdp_per_capita 与 gdp_total/population 推算值不匹配：")
        for w in sorted(by_type["gdp_consistency"], key=lambda w: w["deviation"], reverse=True):
            print(f"  - {w['detail']}")
            print(f"    → 若偏差小(<25%)，可能因 population 年报与公报口径差异；若偏差大，检查 gdp_total 单位是否一致")

    if "rd_low" in by_type:
        print("\n【科技支出异常低】可能使用了市本级口径而非全市口径：")
        for w in by_type["rd_low"]:
            print(f"  - {w['detail']}")
            print(f"    → 确认是否为全市一般公共预算科学技术支出")

    if "tier" in by_type:
        print("\n【层级倒挂】较低层级城市指标超过了较高层级城市最小值：")
        for w in by_type["tier"]:
            print(f"  - {w['detail']}")

    if "income_stutter" in by_type:
        print("\n【收入口径切换】可能存在全体居民↔城镇居民口径切换：")
        for w in by_type["income_stutter"]:
            print(f"  - {w['detail']}")
            print(f"    → 检查 notes 字段是否标注口径（all-resident vs urban resident）")

    print(f"\n总计 {len(warnings)} 条警告，建议优先处理 🔴 HIGH 级别。")
    print("修复方式：编辑 data/raw/manual_source_observations.csv 对应行后重新运行")
    print("    uv run ueoi-download && uv run ueoi-build")


def main() -> None:
    fix_mode = "--fix" in sys.argv

    print("=" * 70)
    print("Urban Economic Opportunity Index — 数据质量校验")
    print("=" * 70)
    print(f"Panel: {PANEL_FILE}")
    print(f"Observations: {OBS_FILE}")

    panel, obs = load_data()
    print(f"面板: {len(panel)} 行, 观测: {len(obs)} 条")

    all_warnings: list[dict] = []

    print("\n--- 1. 数值范围检验 ---")
    w = check_range_validity(panel)
    all_warnings.extend(w)
    print_report(w, "数值范围")

    print("\n--- 2. 时间序列平滑性 ---")
    w = check_time_series_spikes(panel)
    all_warnings.extend(w)
    print_report(w, "时间序列突变")

    print("\n--- 3. 跨城市层级一致性 ---")
    w = check_cross_city_tiers(panel)
    all_warnings.extend(w)
    print_report(w, "城市层级一致性")

    print("\n--- 4. GDP 口径一致性 ---")
    w = check_gdp_consistency(panel)
    all_warnings.extend(w)
    print_report(w, "GDP PC vs gdp_total/pop")

    print("\n--- 5. 可支配收入口径 ---")
    w = check_income_consistency(panel)
    all_warnings.extend(w)
    print_report(w, "收入口径切换检测")

    print("\n--- 6. 人口 vs 收入 ---")
    w = check_population_vs_income_rank(panel)
    all_warnings.extend(w)
    print_report(w, "人口-收入倒挂")

    print("\n--- 7. 科技支出异常值 ---")
    w = check_rd_outliers(panel)
    all_warnings.extend(w)
    print_report(w, "科技支出异常")

    summary = {}
    for w in all_warnings:
        summary[w["severity"]] = summary.get(w["severity"], 0) + 1
    print(f"\n{'=' * 70}")
    print(f"总计: {len(all_warnings)} 条警告 "
          f"(🔴 HIGH={summary.get('HIGH', 0)}, "
          f"🟡 MEDIUM={summary.get('MEDIUM', 0)}, "
          f"🔵 LOW={summary.get('LOW', 0)})")

    if fix_mode and all_warnings:
        generate_fix_suggestions(all_warnings)

    if summary.get("HIGH", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
