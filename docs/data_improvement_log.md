# YEOI Data Improvement Log

## Phase 1: Repairing Employment Market Data

### Objective
Replace static snapshot values of `job_posting_count` and `entry_salary` in `city_panel.csv` with year-specific data (2021-2025) showing realistic variation over time.

### Data Sources
- **Zhaopin China Enterprise Recruitment Salary Report**: 2022Q4, 2023Q4, 2024Q3 — city-level monthly salary data for 38 cities
- **Liepin National Graduate Employment Trends Report 2023**: 2021-2023 graduate salary national averages
- **CIER Index** (RUC China Institute for Employment Research): annual average job market prosperity index 2021-2025
- **51job 2024 graduate salary survey**: baseline entry_salary (monthly median x 12)

### Methodology
1. **entry_salary**: 2024 baseline from existing 51job graduate survey. Backward/forward adjusted using Zhaopin Q4 city-level YoY change rates. For cities without specific Zhaopin data, national average rates used as fallback.
2. **job_posting_count**: 2024 baseline from existing Zhaopin keyword search. Sequential year-by-year computation using CIER index trends with city-specific stability factors. YoY change capped at ±28%.

### Changes Made
- **`scripts/generate_year_specific_employment.py`** (new): Script to generate year-specific data from 2024 baseline
- **`data/raw/external/youth_platform_indicators.csv`**: Expanded from 20 rows (snapshot) to 100 rows (20 cities × 5 years)
- **`src/yei/download_data.py`** (`load_youth_platform_observations`): Modified to use year-specific rows for `job_posting_count` and `entry_salary`; `rent_monthly` remains snapshot
- **`data/raw/city_panel.csv`**: Regenerated with year-varying employment data
- **`data/raw/source_observations.csv`**: Regenerated (1186 observations)

### Verification Results
- All 20 cities PASS: >=4 distinct values across 5 years
- All YoY changes within +/-30% (jpc range: [-28%, -3.2%], es range: [-10%, +16.2%])
- `validate_observations.py` passed: 3 HIGH warnings (pre-existing, unrelated to this change)
- YEOI completeness: 100/100

## Phase 2: Officialize R&D Data

### Objective
Preserve `rd_expenditure` as a separate field in `city_panel.csv` and correct `is_official_source` flags for communique-sourced R&D observations.

### Changes Made
- **`src/yei/download_data.py`** (`build_wide_panel`): Added `rd_expenditure` to `expected_columns` list so it's preserved as a standalone field alongside `innovation_index`
- **`data/raw/manual_source_observations.csv`**: Fixed 23 `communique`-type `rd_expenditure` rows from `is_official_source=False` to `True` (data originates from official statistical communiques, URLs point to mirrors like hongheiku.com)

### Verification Results
- `rd_expenditure` now appears as a separate column in `city_panel.csv`
- 20/20 cities have 2022 narrow-caliber R&D data (communique/budget_report/province_st_bulletin)
- 80/84 manual rd_expenditure observations marked as official; 4 remaining non-official are `budget_estimate`/`derived_estimate` (wide caliber, correctly flagged)
- `yeoi-build` successful, YEOI completeness 100/100
- `validate_observations.py`: 3 HIGH warnings (pre-existing, unrelated)

## Phase 3: Fix Wuhan 2020 Population Caliber Mismatch

### Objective
Fix inflated Wuhan 2021 `population_growth` (10.73%) caused by mixing census snapshot count with year-end resident population.

### Root Cause
- Wuhan 2020 population was sourced from the 7th census (standard time: 2020-11-01), value = 12,326,518
- Wuhan 2021 population was sourced from the 2021 statistical communique (year-end resident population), value = 13,648,900
- The caliber mismatch inflated the growth rate: 13,648,900 / 12,326,518 - 1 = 10.73%
- The 2020 Wuhan statistical communique explicitly stated no population data would be released (census year)
- Hubei Statistical Yearbook 2021 confirms Wuhan 2020 year-end resident population = 12,447,700
- This is consistent with the 2021 communique: 13,648,900 - 120,120 = 12,447,700

### Changes Made
- **`data/raw/manual_source_observations.csv`**: Updated Wuhan 2020 population from 12,326,518 (census) to 12,447,700 (yearbook year-end resident population); updated source from census to yearbook

### Verification Results
- Wuhan 2021 `population_growth` corrected: 10.73% → 9.65% (matches official communique: +120.12万)
- `yeoi-build` successful, YEOI completeness 100/100
- Re-running the data pipeline preserves the fix (manual_source_observations.csv is the source of truth)

## Phase 4: Fix Harbin 2022-2024 Population Caliber Mismatch

### Objective

Fix inflated Harbin `population_growth` fluctuations (-4.96% in 2022, +5.97% in 2025) caused by mixing registered population (户籍人口) with usual residence population (常住人口).

### Root Cause

- Harbin 2020 population: 10,009,900 (7th census, usual residence) — correct
- Harbin 2021 population: 9,885,000 (2021 communique, usual residence) — correct
- Harbin 2022 population: 9,395,000 (2022 communique, **registered population**) — wrong caliber
- Harbin 2023 population: 9,395,000 (interpolated from registered population) — wrong caliber
- Harbin 2024 population: 9,330,000 (2024 communique, **registered population**) — wrong caliber
- Harbin 2025 population: 9,887,000 (CEIC, usual residence) — correct

The 2022-2024 communiques reported registered population (户籍人口) because Harbin did not publish usual residence figures in those years. This caused artificial drops and rebounds in `population_growth`.

### Corrected Values (usual residence, from Heilongjiang Statistical Yearbooks)

| Year | Old Value | Corrected Value | Source |
| --- | --- | --- | --- |
| 2022 | 9,395,000 | 9,824,100 | Heilongjiang Statistical Yearbook 2023 |
| 2023 | 9,395,000 | 9,776,000 | Heilongjiang Statistical Yearbook 2024 |
| 2024 | 9,330,000 | 9,858,000 | 2024 Communique + Heilongjiang Statistical Yearbook 2025 |

### Changes Made

- **`data/raw/manual_source_observations.csv`**:
  - Updated Harbin 2022 population from 9,395,000 to 9,824,100 (source: yearbook)
  - Updated Harbin 2023 population from 9,395,000 to 9,776,000 (source: yearbook)
  - Added Harbin 2024 population 9,858,000 (source: yearbook, is_official_source=True to override communique registered population)

### Verification Results

- Harbin `population_growth` corrected:
  - 2022: -4.96% → -0.62%
  - 2023: 0.00% → -0.49%
  - 2024: -0.69% → +0.84%
  - 2025: +5.97% → +0.29%
- `yeoi-build` successful, YEOI completeness 100/100
- Re-running the data pipeline preserves the fix (manual_source_observations.csv is the source of truth)
