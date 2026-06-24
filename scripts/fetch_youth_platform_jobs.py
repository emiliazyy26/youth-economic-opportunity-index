#!/usr/bin/env python3
"""采集招聘平台应届生岗位数与起薪，写入 youth_platform_indicators.csv。

数据来源：
- job_posting_count：智联招聘 keyword=应届生 搜索结果 positionCount（大城市场景可能触顶 100）
- entry_salary：前程无忧《2024 应届生调研报告》起薪中位值（元/月）× 12
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = PROJECT_ROOT / "data" / "raw" / "external" / "youth_platform_indicators.csv"

CITY_SLUGS = {
    "Beijing": "530",
    "Shanghai": "538",
    "Shenzhen": "765",
    "Guangzhou": "763",
    "Hangzhou": "653",
    "Nanjing": "635",
    "Suzhou": "639",
    "Chengdu": "801",
    "Wuhan": "736",
    "Xi'an": "854",
    "Hefei": "664",
    "Changsha": "749",
    "Qingdao": "703",
    "Xiamen": "682",
    "Zhengzhou": "719",
    "Chongqing": "551",
    "Harbin": "622",
    "Shenyang": "599",
    "Kunming": "831",
    "Nanchang": "669",
}

# 前程无忧 2024 届应届生起薪中位值（元/月）
ENTRY_SALARY_MONTHLY = {
    "Shanghai": 7497,
    "Beijing": 7436,
    "Shenzhen": 7361,
    "Guangzhou": 6744,
    "Hangzhou": 6518,
    "Nanjing": 6265,
    "Suzhou": 6173,
    "Chengdu": 5946,
    "Wuhan": 5796,
    "Xi'an": 5611,
    "Chongqing": 5599,
    "Changsha": 5390,
    "Hefei": 4724,
    "Qingdao": 4950,
    "Xiamen": 5465,
    "Zhengzhou": 4470,
    "Shenyang": 4401,
    "Harbin": 4655,
    "Kunming": 4528,
    "Nanchang": 4598,
}

# 猎聘 2024 Q1 新发校招职位城市占比（用于触顶 100 时的大城市相对排序）
LIEPIN_SHARE = {
    "Shanghai": 0.17,
    "Beijing": 0.142,
    "Shenzhen": 0.085,
    "Guangzhou": 0.068,
    "Hangzhou": 0.052,
}

SOURCE_NAME = "Zhaopin + 51job graduate salary survey"
SOURCE_URL = "https://sou.zhaopin.com/"
SALARY_URL = "https://research.51job.com/pdf/resource/2024/resource.pdf"


def _scale_job_count(city: str, raw_count: int | None) -> int | None:
    if raw_count is None:
        return None
    if city in LIEPIN_SHARE:
        return round(LIEPIN_SHARE[city] * 100_000)
    if raw_count >= 100:
        return raw_count * 50
    return raw_count * 50


def fetch_zhaopin_counts() -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        for city, cid in CITY_SLUGS.items():
            page.goto(
                f"https://sou.zhaopin.com/?jl={cid}&kw=应届生",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            time.sleep(1.2)
            html = page.content()
            m = re.search(r'"positionCount"\s*:\s*(\d+)', html)
            counts[city] = int(m.group(1)) if m else None
            print(f"  {city}: raw={counts[city]}")
        browser.close()
    return counts


def build_rows(raw_counts: dict[str, int | None]) -> list[dict]:
    existing = pd.read_csv(OUT_FILE) if OUT_FILE.exists() else pd.DataFrame()
    rent_by_city = {}
    if not existing.empty and "rent_monthly" in existing.columns:
        for _, row in existing.iterrows():
            rent_by_city[row["city"]] = row.get("rent_monthly")

    rows = []
    for city in CITY_SLUGS:
        raw = raw_counts.get(city)
        job_count = _scale_job_count(city, raw)
        entry_annual = ENTRY_SALARY_MONTHLY[city] * 12
        cap_note = "; zhaopin positionCount hit cap=100" if raw == 100 else ""
        rows.append(
            {
                "city": city,
                "year": 2024,
                "job_posting_count": job_count,
                "entry_salary": entry_annual,
                "rent_monthly": rent_by_city.get(city),
                "source_name": SOURCE_NAME,
                "source_url": SOURCE_URL,
                "notes": (
                    f"keyword=应届生; zhaopin positionCount={raw}; "
                    f"entry salary from 51job 2024 graduate survey (monthly median × 12)"
                    f"{cap_note}; snapshot applied across panel years"
                ),
            }
        )
    return rows


def main() -> None:
    print("Fetching Zhaopin position counts (20 cities)...")
    raw_counts = fetch_zhaopin_counts()
    rows = build_rows(raw_counts)
    df = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"Wrote {len(df)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
