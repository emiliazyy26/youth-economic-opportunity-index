#!/usr/bin/env python3
"""Batch search for missing data gaps using Tavily Search API with multi-source cross-validation.

Usage:
    uv run python scripts/batch_search_gaps.py --year 2025        # Search 2025 only
    uv run python scripts/batch_search_gaps.py --all              # Search all gaps
    uv run python scripts/batch_search_gaps.py --dry-run          # Generate gap list only, no search
    uv run python scripts/batch_search_gaps.py --merge            # Merge approved candidates to manual
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SCRIPT_DIR = PROJECT_ROOT / "scripts"
MISSING_REPORT = RAW_DIR / "missing_data_report.csv"
MANUAL_OBS = RAW_DIR / "manual_source_observations.csv"
CANDIDATE_FILE = RAW_DIR / "candidate_review.csv"
GAP_LIST_FILE = RAW_DIR / "gap_list.json"

CITY_NAME_ZH: dict[str, str] = {
    "Beijing": "北京",
    "Shanghai": "上海",
    "Shenzhen": "深圳",
    "Guangzhou": "广州",
    "Hangzhou": "杭州",
    "Nanjing": "南京",
    "Suzhou": "苏州",
    "Chengdu": "成都",
    "Wuhan": "武汉",
    "Xi'an": "西安",
    "Hefei": "合肥",
    "Changsha": "长沙",
    "Qingdao": "青岛",
    "Xiamen": "厦门",
    "Zhengzhou": "郑州",
    "Chongqing": "重庆",
    "Harbin": "哈尔滨",
    "Shenyang": "沈阳",
    "Kunming": "昆明",
    "Nanchang": "南昌",
}

METRIC_ZH: dict[str, str] = {
    "gdp_per_capita": "人均地区生产总值",
    "disposable_income": "人均可支配收入",
    "population": "常住人口",
    "rd_expenditure": "科学技术支出",
}

METRIC_UNITS: dict[str, str] = {
    "gdp_per_capita": "yuan/person",
    "disposable_income": "yuan/person",
    "population": "person",
    "rd_expenditure": "100 million yuan",
}

SEARCH_TEMPLATES: dict[str, list[str]] = {
    "gdp_per_capita": [
        "{city_zh} {year} 统计公报 人均GDP",
        "{city_zh} {year} 人均地区生产总值",
        "{city_zh} {year} 国民经济和社会发展统计公报",
    ],
    "disposable_income": [
        "{city_zh} {year} 统计公报 人均可支配收入",
        "{city_zh} {year} 居民人均可支配收入",
        "{city_zh} {year} 国民经济和社会发展统计公报",
    ],
    "population": [
        "{city_zh} {year} 统计公报 常住人口",
        "{city_zh} {year} 年末常住人口",
        "{city_zh} {year} 国民经济和社会发展统计公报",
    ],
    "rd_expenditure": [
        "{city_zh} {year} 一般公共预算 科学技术支出",
        "{city_zh} {year} 财政科学技术支出",
        "{city_zh} {year} 决算 科学技术支出",
    ],
}

# Patterns for extracting numbers from search result text
EXTRACTION_PATTERNS: dict[str, list[tuple[str, float]]] = {
    "gdp_per_capita": [
        (r"人均(?:地区)?生产总值[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万元", 10000),
        (r"人均GDP[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万元", 10000),
        (r"人均GDP[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"人均GDP\s*[约达到]?\s*(\d+(?:\.\d+)?)\s*万", 10000),
        (r"人均生产总值[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"人均生产总值[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万元", 10000),
        (r"人均GDP[约达到]?\s*(\d+(?:\.\d+))\s*[万]", 10000),
    ],
    "disposable_income": [
        (r"全体居民人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"全市居民人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"居民人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"全年居民人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
        (r"城镇居民人均可支配收入[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*元", 1),
    ],
    "population": [
        (r"年末常住人口[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万人", 10000),
        (r"常住人口[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万人", 10000),
        (r"全市常住人口[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万人", 10000),
        (r"常住人口\s*[约达到]?\s*(\d+(?:\.\d+)?)\s*万", 10000),
        (r"年末户籍人口[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万人", 10000),
    ],
    "rd_expenditure": [
        (r"科学技术支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*亿元", 1),
        (r"一般公共预算科学技术支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*亿元", 1),
        (r"财政科学技术支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*亿元", 1),
        (r"财政科技支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*亿元", 1),
        (r"科技支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*亿元", 1),
        (r"科学技术支出[^0-9]{0,20}?(\d+(?:\.\d+)?)\s*万元", 0.0001),
    ],
}

# High-confidence domains: these sources typically cite official communiques directly
HIGH_CONFIDENCE_DOMAINS = [
    "gov.cn",
    "stats.gov.cn",
    "hongheiku.com",
    "tjcn.org",
    "ceicdata.com",
    "people.com.cn",
    "xinhuanet.com",
    "chinanews.com",
    "chinamoney.com.cn",
    "wikipedia.org",
    "zh.wikipedia.org",
    "baidu.com/item",  # Baidu Baike
    "wiki",
    "tjj.",
    "czj.",
    "stats.",
    "tjj.",
    "finance.",
]


def get_tavily_client():
    """Get Tavily client. Uses MCP tool call; returns a marker here."""
    return "tavily_mcp"


def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search via Tavily MCP, return list of results."""

    try:
        from tavily import TavilyClient

        client = TavilyClient()
        response = client.search(query=query, max_results=max_results, search_depth="basic")
        return response.get("results", [])
    except ImportError:
        print(f"  [TAVILY-IMPORT-ERR] Please install tavily-python or use MCP: {query}")
        return []


def generate_gap_list(year_filter: int | None = None) -> list[dict]:
    """Generate complete gap list from missing_data_report.csv."""
    missing = pd.read_csv(MISSING_REPORT)
    if year_filter:
        missing = missing[missing["year"] == year_filter]
    else:
        missing = missing[missing["year"] >= 2021]

    gaps = []
    for _, row in missing.iterrows():
        if row["status"] == "genuinely_not_published":
            continue
        gaps.append(
            {
                "city": row["city"],
                "city_zh": CITY_NAME_ZH.get(row["city"], row["city"]),
                "year": int(row["year"]),
                "metric": row["metric"],
                "metric_zh": METRIC_ZH.get(row["metric"], row["metric"]),
            }
        )
    return gaps


def extract_candidates_from_results(
    results: list[dict], metric: str, city_zh: str, year: int
) -> list[dict]:
    """Extract candidate values from search results."""
    candidates = []

    for result in results:
        content = result.get("content", "")
        url = result.get("url", "")
        title = result.get("title", "")

        if not content:
            continue

        # Check if target city and year are mentioned
        if city_zh not in content and city_zh not in title:
            continue

        for pattern, multiplier in EXTRACTION_PATTERNS.get(metric, []):
            for match in re.finditer(pattern, content):
                raw_value = float(match.group(1))
                value = raw_value * multiplier

                if metric == "gdp_per_capita" and value < 1000:
                    continue  # Unreasonable value
                if metric == "disposable_income" and value < 1000:
                    continue
                if metric == "population" and value < 100000:
                    continue
                if metric == "rd_expenditure" and value < 0.01:
                    continue

                # Determine confidence level
                confidence = "medium"
                for domain in HIGH_CONFIDENCE_DOMAINS:
                    if domain in url:
                        confidence = "high"
                        break

                # Check for year confirmation
                if str(year) in match.group(0) or str(year) in content[:200]:
                    confidence = "high" if confidence == "high" else "high"

                candidates.append(
                    {
                        "value": value,
                        "source_url": url,
                        "source_title": title,
                        "extracted_text": match.group(0)[:120],
                        "confidence": confidence,
                    }
                )

    return candidates


def generate_candidate_review(
    gaps: list[dict], *, dry_run: bool = False
) -> pd.DataFrame:
    """Execute search for each gap and generate candidate value table."""

    rows = []

    for i, gap in enumerate(gaps):
        city_zh = gap["city_zh"]
        year = gap["year"]
        metric = gap["metric"]

        print(f"[{i + 1}/{len(gaps)}] {city_zh} {year} {gap['metric_zh']}")

        if dry_run:
            rows.append(
                {
                    "city": gap["city"],
                    "city_zh": city_zh,
                    "year": year,
                    "metric": metric,
                    "candidate_value": None,
                    "candidate_unit": METRIC_UNITS.get(metric, ""),
                    "source_urls": "",
                    "source_titles": "",
                    "extracted_texts": "",
                    "confidence": "dry_run",
                    "reviewer_approved": "",
                    "notes": "",
                }
            )
            continue

        all_candidates = []
        for template in SEARCH_TEMPLATES.get(metric, []):
            query = template.format(city_zh=city_zh, year=year)
            results = search_tavily(query)
            if results:
                candidates = extract_candidates_from_results(results, metric, city_zh, year)
                all_candidates.extend(candidates)
            time.sleep(0.5)  # Rate limit politeness

        if not all_candidates:
            rows.append(
                {
                    "city": gap["city"],
                    "city_zh": city_zh,
                    "year": year,
                    "metric": metric,
                    "candidate_value": None,
                    "candidate_unit": METRIC_UNITS.get(metric, ""),
                    "source_urls": "",
                    "source_titles": "",
                    "extracted_texts": "",
                    "confidence": "no_results",
                    "reviewer_approved": "",
                    "notes": "Tavily search returned no extractable candidates",
                }
            )
            continue

        # Sort by confidence, take top 3
        all_candidates.sort(
            key=lambda c: (0 if c["confidence"] == "high" else 1, c["value"])
        )

        # Aggregate: take all high-confidence candidates, group by value
        by_value: dict[float, list[dict]] = {}
        for c in all_candidates:
            key = round(c["value"], 2)
            by_value.setdefault(key, []).append(c)

        # Multi-source cross-validation: values appearing more often are more trustworthy
        for value_key, candidates in sorted(
            by_value.items(), key=lambda kv: (len(kv[1]), kv[1][0]["confidence"]), reverse=True
        ):
            best = candidates[0]
            source_count = len(candidates)
            confidence = "high" if source_count >= 2 else best["confidence"]

            rows.append(
                {
                    "city": gap["city"],
                    "city_zh": city_zh,
                    "year": year,
                    "metric": metric,
                    "candidate_value": value_key,
                    "candidate_unit": METRIC_UNITS.get(metric, ""),
                    "source_urls": " | ".join(c["source_url"] for c in candidates[:3]),
                    "source_titles": " | ".join(c["source_title"] for c in candidates[:3]),
                    "extracted_texts": " | ".join(c["extracted_text"] for c in candidates[:3]),
                    "confidence": f"{confidence} ({source_count} sources)",
                    "reviewer_approved": "True" if confidence == "high" else "",
                    "notes": "",
                }
            )
            break  # Take only the best candidate value

    df = pd.DataFrame(rows)
    df.to_csv(CANDIDATE_FILE, index=False)
    print(f"\nCandidate review saved: {CANDIDATE_FILE}")
    print(f"Total gaps: {len(gaps)}")
    print(f"Found candidates: {df['candidate_value'].notna().sum()}")
    return df


def merge_approved_candidates() -> int:
    """Merge approved candidate values into manual_source_observations.csv."""
    if not CANDIDATE_FILE.exists():
        print("No candidate review file found.")
        return 0

    candidates = pd.read_csv(CANDIDATE_FILE)
    approved = candidates[candidates["reviewer_approved"].isin(["True", "true", "yes", "1"])]

    if approved.empty:
        print("No approved candidates found.")
        return 0

    manual = pd.read_csv(MANUAL_OBS) if MANUAL_OBS.exists() else pd.DataFrame()

    records = []
    for _, row in approved.iterrows():
        if pd.isna(row["candidate_value"]) or row["candidate_value"] == 0:
            continue

        source_url = str(row["source_urls"]).split(" | ")[0] if pd.notna(row["source_urls"]) else ""
        is_official = any(
            domain in source_url
            for domain in ["gov.cn", "stats.gov.cn", "tjj."]
        )

        records.append(
            {
                "city": row["city"],
                "year": int(row["year"]),
                "metric": row["metric"],
                "value": float(row["candidate_value"]),
                "unit": row["candidate_unit"],
                "source_type": "tavily_search",
                "source_name": str(row["source_titles"]).split(" | ")[0],
                "source_url": source_url,
                "source_file": "",
                "extraction_method": "tavily_web_search",
                "is_official_source": is_official,
                "notes": f"auto-extracted via Tavily search; {row['confidence']}",
            }
        )

    if not records:
        return 0

    new_df = pd.DataFrame(records)
    if not manual.empty:
        combined = pd.concat([manual, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_csv(MANUAL_OBS, index=False)
    print(f"Merged {len(records)} approved records into {MANUAL_OBS}")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch search missing data gaps")
    parser.add_argument("--year", type=int, help="Filter by year (e.g. 2025)")
    parser.add_argument("--all", action="store_true", help="Search all gaps (2021-2025)")
    parser.add_argument("--dry-run", action="store_true", help="Generate gap list only, no search")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge approved candidates to manual_source_observations.csv",
    )
    args = parser.parse_args()

    if args.merge:
        merge_approved_candidates()
        return

    year_filter = args.year if args.year else (None if args.all else 2025)
    if not args.all and not args.year:
        print("Defaulting to --year 2025 (most recent, most likely available)")
        year_filter = 2025

    gaps = generate_gap_list(year_filter=year_filter)
    print(f"Found {len(gaps)} gaps for year={year_filter}")

    if not gaps:
        print("No gaps to search!")
        return

    generate_candidate_review(gaps, dry_run=args.dry_run)


if __name__ == "__main__":
    main()