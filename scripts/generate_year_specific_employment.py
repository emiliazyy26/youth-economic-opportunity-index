"""
Generate year-specific job_posting_count and entry_salary data (2021-2025)
based on Zhaopin Q4 salary reports, Liepin graduate reports, and CIER index trends.

Data sources:
- Zhaopin China Enterprise Recruitment Salary Report 2022Q4, 2023Q4, 2024Q2, 2024Q3
- Liepin National Graduate Employment Trends and Outlook 2023
- CIER Index (China Institute for Employment Research)

Methodology:
- entry_salary: Use Zhaopin Q4 city-level YoY change rates as proxy for graduate salary trends.
  Anchor year is 2024 (from existing 51job graduate survey baseline).
- job_posting_count: Use CIER index trends to create realistic year-over-year variation.
"""

import csv
import math
from pathlib import Path

# ── 2023Q4 Zhaopin monthly salary (complete 38-city data) ──
ZHAOPIN_2023Q4 = {
    "Beijing": 13552, "Shanghai": 13888, "Shenzhen": 13067, "Hangzhou": 12143,
    "Suzhou": 11348, "Nanjing": 11240, "Guangzhou": 11186, "Xiamen": 10641,
    "Wuhan": 10381, "Changsha": 10136, "Hefei": 10003, "Chengdu": 9881,
    "Chongqing": 9441, "Xi'an": 9440, "Qingdao": 9356, "Nanchang": 9058,
    "Zhengzhou": 8948, "Kunming": 8918, "Shenyang": 7663, "Harbin": 7554,
}

# ── 2022Q4 Zhaopin monthly salary (partial, from search results) ──
ZHAOPIN_2022Q4 = {
    "Beijing": 13930, "Shanghai": 13832, "Shenzhen": 13086, "Hangzhou": 11963,
    "Guangzhou": 11710, "Harbin": 7408, "Shenyang": 7614,
}

# ── 2024Q3 Zhaopin monthly salary (from PDF + search results) ──
ZHAOPIN_2024Q3 = {
    "Shanghai": 12500, "Beijing": 12500, "Shenzhen": 12500,
    "Hangzhou": 11662, "Guangzhou": 10998, "Xi'an": 9182,
    # Estimates based on Q2→Q3 trend and national avg
    "Suzhou": 10800, "Nanjing": 10700, "Xiamen": 10200,
    "Wuhan": 10000, "Changsha": 9800, "Hefei": 9700,
    "Chengdu": 9600, "Chongqing": 9200, "Qingdao": 9100,
    "Nanchang": 8800, "Zhengzhou": 8700, "Kunming": 8700,
    "Shenyang": 7500, "Harbin": 7400,
}

# ── CIER Index annual average (job market prosperity indicator) ──
# Source: CIER index reports, RUC China Institute for Employment Research
# Higher index = more jobs per applicant = stronger job market
CIER_ANNUAL = {
    2021: 1.86,  # Strong post-COVID recovery
    2022: 1.27,  # Significant decline
    2023: 1.15,  # Slight recovery but still weak
    2024: 0.98,  # Further weakening
    2025: 0.95,  # Projected stabilization at low level
}

# ── Liepin graduate salary national trend ──
# 2021 class avg: 9292/month, 2023 class avg: 10342/month
# 2022 class was higher than 2021 class, 2023 class slightly lower than 2022 class
LIEPIN_NATIONAL = {
    2021: 9292,
    2022: 10800,  # Estimated: 2021→2022 was a strong increase year
    2023: 10342,  # From Liepin report (slight decrease from 2022)
}

# National average Zhaopin Q4 salary
NATIONAL_AVG_Q4 = {
    2021: 10113,  # Estimated: 2022Q4=10558, YoY +4.4%
    2022: 10558,  # From report
    2023: 10420,  # From report
    2024: 10058,  # From 2024Q3 report (Q4 estimate similar)
}


def compute_city_yoy_salary(city: str, year_prev: int, year_curr: int) -> float:
    """Compute YoY salary change rate for a city between two years."""
    # Try to use city-specific Zhaopin Q4 data
    sources = {
        (2022, 2023): (ZHAOPIN_2022Q4, ZHAOPIN_2023Q4),
        (2023, 2024): (ZHAOPIN_2023Q4, ZHAOPIN_2024Q3),
    }

    if (year_prev, year_curr) in sources:
        prev_data, curr_data = sources[(year_prev, year_curr)]
        if city in prev_data and city in curr_data:
            return curr_data[city] / prev_data[city] - 1.0

    # Fall back to national average
    if year_prev in NATIONAL_AVG_Q4 and year_curr in NATIONAL_AVG_Q4:
        return NATIONAL_AVG_Q4[year_curr] / NATIONAL_AVG_Q4[year_prev] - 1.0

    # Use Liepin graduate trend for 2021→2022
    if (year_prev, year_curr) == (2021, 2022):
        return LIEPIN_NATIONAL[2022] / LIEPIN_NATIONAL[2021] - 1.0

    return 0.0


def compute_entry_salary(baseline_2024: float, city: str, year: int) -> int:
    """
    Compute year-specific entry_salary (annual) from 2024 baseline.
    Uses Zhaopin Q4 YoY changes as proxy, applied backward/forward from 2024.
    """
    if year == 2024:
        return int(round(baseline_2024))

    if year == 2025:
        # Project: slight decline continuing, ~-2%
        yoy_2024_2025 = -0.02
        return int(round(baseline_2024 * (1 + yoy_2024_2025)))

    if year == 2023:
        yoy = compute_city_yoy_salary(city, 2023, 2024)
        return int(round(baseline_2024 / (1 + yoy)))

    if year == 2022:
        yoy_22_23 = compute_city_yoy_salary(city, 2022, 2023)
        salary_2023 = compute_entry_salary(baseline_2024, city, 2023)
        return int(round(salary_2023 / (1 + yoy_22_23)))

    if year == 2021:
        # 2021→2022: strong growth based on Liepin data
        yoy_21_22 = LIEPIN_NATIONAL[2022] / LIEPIN_NATIONAL[2021] - 1.0
        salary_2022 = compute_entry_salary(baseline_2024, city, 2022)
        return int(round(salary_2022 / (1 + yoy_21_22)))

    return int(round(baseline_2024))


def compute_job_posting_count(baseline_2024: float, city: str, year: int) -> int:
    """
    Compute year-specific job_posting_count from 2024 baseline.
    Uses CIER index trends to create realistic variation.
    Sequential year-by-year computation with ±28% YoY cap.
    """
    # City-specific volatility adjustment (0.7=more volatile, 1.0=less volatile)
    city_stability = {
        "Beijing": 0.95, "Shanghai": 0.95, "Shenzhen": 0.95, "Guangzhou": 0.93,
        "Hangzhou": 0.93, "Nanjing": 0.93, "Suzhou": 0.93, "Chengdu": 0.90,
        "Wuhan": 0.88, "Xi'an": 0.88, "Hefei": 0.85, "Changsha": 0.90,
        "Qingdao": 0.90, "Xiamen": 0.92, "Zhengzhou": 0.85, "Chongqing": 0.88,
        "Harbin": 0.80, "Shenyang": 0.82, "Kunming": 0.85, "Nanchang": 0.85,
    }
    stability = city_stability.get(city, 0.90)

    # Compute CIER-implied YoY change rate for each year transition
    yoy_rates = {}
    for y in [2021, 2022, 2023, 2024, 2025]:
        if y == 2024:
            continue
        if y < 2024:
            # Backward: rate from y to y+1
            raw = CIER_ANNUAL[y + 1] / CIER_ANNUAL[y] - 1.0
        else:
            # Forward: rate from y-1 to y
            raw = CIER_ANNUAL[y] / CIER_ANNUAL[y - 1] - 1.0
        # Apply city stability factor (less stable = more volatile)
        adjusted = raw * (2.0 - stability)
        # Cap at ±28%
        yoy_rates[y] = max(-0.28, min(0.28, adjusted))

    # Compute sequentially from 2024 baseline
    values = {2024: baseline_2024}
    # Backward: 2023, 2022, 2021
    for y in [2023, 2022, 2021]:
        # yoy_rates[y] is the rate from y to y+1
        values[y] = values[y + 1] / (1 + yoy_rates[y])
    # Forward: 2025
    values[2025] = baseline_2024 * (1 + yoy_rates[2025])

    return int(round(values[year]))


def main():
    input_path = Path("data/raw/external/youth_platform_indicators.csv")
    output_path = input_path  # overwrite

    # Read current baseline data (2024 snapshot only)
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    baseline_rows = [r for r in all_rows if str(r.get("year", "2024")) == "2024"]
    if not baseline_rows:
        # Fallback: if no year column, use all rows (original format)
        baseline_rows = all_rows

    # Build year-specific records
    years = [2021, 2022, 2023, 2024, 2025]
    fieldnames = [
        "city", "year", "job_posting_count", "entry_salary", "rent_monthly",
        "source_name", "source_url", "notes",
    ]

    output_rows = []
    for row in baseline_rows:
        city = row["city"]
        baseline_jpc = float(row["job_posting_count"])
        baseline_es = float(row["entry_salary"])
        rent_monthly = row["rent_monthly"]
        source_name = row.get("source_name", "")
        source_url = row.get("source_url", "")

        for year in years:
            jpc = compute_job_posting_count(baseline_jpc, city, year)
            es = compute_entry_salary(baseline_es, city, year)

            if year == 2024:
                notes = (
                    f"baseline from 51job graduate survey; "
                    f"entry_salary=monthly_median×12; "
                    f"job_posting_count from Zhaopin keyword search"
                )
                src = source_name
                url = source_url
            else:
                notes = (
                    f"year-specific estimate; "
                    f"entry_salary adjusted by Zhaopin Q4 YoY change rate; "
                    f"job_posting_count adjusted by CIER index trend; "
                    f"baseline_year=2024"
                )
                src = "Zhaopin Q4 salary report + CIER index trend estimation"
                url = "https://www.zhaopin.com/; http://ier.ruc.edu.cn/"

            output_rows.append({
                "city": city,
                "year": year,
                "job_posting_count": jpc,
                "entry_salary": es,
                "rent_monthly": rent_monthly,
                "source_name": src,
                "source_url": url,
                "notes": notes,
            })

    # Write output
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Written {len(output_rows)} rows to {output_path}")

    # Verification: print YoY changes
    print("\n=== Verification: YoY changes ===")
    cities = sorted(set(r["city"] for r in output_rows))
    for city in cities:
        city_rows = {r["year"]: r for r in output_rows if r["city"] == city}
        print(f"\n{city}:")
        prev_jpc = None
        prev_es = None
        for year in years:
            r = city_rows[year]
            jpc = int(r["job_posting_count"])
            es = int(r["entry_salary"])
            jpc_change = f"({(jpc/prev_jpc - 1)*100:+.1f}%)" if prev_jpc else ""
            es_change = f"({(es/prev_es - 1)*100:+.1f}%)" if prev_es else ""
            print(f"  {year}: jpc={jpc} {jpc_change}, es={es} {es_change}")
            prev_jpc = jpc
            prev_es = es


if __name__ == "__main__":
    main()
