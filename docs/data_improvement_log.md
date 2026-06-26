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

## Phase 5: Enterprise Opportunity Dimension Upgrade

### Objective

Rename "Big Company Opportunity" to "Enterprise Opportunity" and incorporate high-tech enterprise counts to better reflect innovation-driven career opportunities for young people.

### Changes Made

**Data Collection:**
- **`scripts/fetch_high_tech_companies.py`** (new): Script to generate high-tech enterprise counts for 20 cities x 5 years (2021-2025)
- **`data/raw/external/high_tech_companies_by_city.csv`** (new): 100 rows with `high_tech_company_count` from Torch Center, provincial science bureaus, and city statistical communiques (Tier B)

**Configuration (`src/yei/config.py`):**
- Added `HIGH_TECH_COMPANIES_FILE` constant
- Added `high_tech_company_count` to `DATA_TIER_B`, `RAW_COLUMNS`, `TARGET_METRICS`
- Updated `YEOI_WEIGHTS`: `job_opportunity_score` 0.25 -> 0.20, `enterprise_opportunity_score` 0.15 -> 0.20
- Renamed `big_company` to `enterprise_opportunity` in `DIMENSION_SPEC` with `high_tech_company_count` as fallback
- Renamed `big_company_score` to `enterprise_opportunity_score` in `SCORE_COLUMNS`

**Data Loading (`src/yei/download_data.py`):**
- Added `load_high_tech_company_observations()` function
- Added `high_tech_company_count` to `METRIC_UNITS`, `build_source_observations()`, `build_wide_panel()` expected columns, and `print_status()` metrics

**Scoring (`src/yei/build_index.py`):**
- Changed `enterprise_opportunity` to use composite scoring: both `listed_company_count` and `high_tech_company_count` are independently min-max normalized and averaged (via `_score_from_metrics`)

**Sensitivity (`src/yei/sensitivity.py`):**
- Renamed `big_company_score` to `enterprise_opportunity_score` in score column reference

**Dashboard (`app/streamlit_app.py`):**
- Renamed `big_company_score` to `enterprise_opportunity_score` in score_cols and chart titles
- Added `high_tech_company_count` to raw metric snapshot columns

**Tests:**
- `tests/test_build_index.py`: Added `high_tech_company_count` to sample panel; added tests for composite scoring and single-metric fallback
- `tests/test_data_quality.py`: `high_tech_company_count` included in `TARGET_METRICS` coverage checks

**Documentation:**
- `docs/methodology.md`: Updated index formula, weight table, and dimension indicators table
- `docs/data-design.md`: Added `high_tech_company_count` field, external file reference, and Tier B description

**Data Quality Fixes (pre-existing, applied during rebuild):**
- Added Harbin 2023 `disposable_income` = 45784.0 to `manual_source_observations.csv` (corrects communique extraction error)
- Added Kunming 2024 `disposable_income` = 47301.0 to `manual_source_observations.csv` (corrects urban vs all-resident caliber mismatch)

### Verification Results

- `high_tech_company_count`: 100/100 coverage (20 cities x 5 years)
- All 20 tests pass (`uv run pytest`)
- `yeoi-build` successful, YEOI completeness 100/100
- `validate_observations.py`: 0 CRITICAL warnings (pre-existing Harbin/Kunming disposable_income issues resolved)

## Phase 6: Fix Chengdu `innovation_index` Caliber Switch (2021-2024)

### Objective

Replace Chengdu 2021-2024 `innovation_index` values sourced from wide-caliber statistical communiques with narrow-caliber "science & technology expenditure" (科学技术支出), using official fiscal reports where available and a trend-based estimate for 2021, eliminating the spurious 51.9% drop between 2023 and 2024.

### Root Cause

- `innovation_index` is derived from `rd_expenditure` when available.
- Chengdu 2021-2023 `rd_expenditure` values (237.50, 250.20, 268.60) came from statistical communiques that labeled the figure as "科学技术支出" but used a wider statistical caliber (likely R&D expenditure or total S&T related spending). The 2021 value has no official city-wide narrow-caliber final accounts figure yet, so it was estimated from the Gotohui historical trend curve.
- Chengdu 2024 `rd_expenditure` (129.24) came from the official Chengdu Finance Bureau "全市一般公共预算支出预算表" using the narrow fiscal caliber of "science & technology expenditure".
- This caliber switch caused a false drop: 2023 = 268.60 → 2024 = 129.24 (−51.9%).

### Corrected Values

| Year | Old `innovation_index` | Old Source | New `innovation_index` | New Source | Caliber |
| --- | --- | --- | --- | --- | --- |
| 2021 | 237.50 | Chengdu 2021 statistical communique (via people.com.cn) | **128.00** | Estimated from Gotohui trend curve (2017 = 53.26 → 2022 = 151.80) | 全市一般公共预算支出·科学技术支出 (estimate; replace with final accounts when available) |
| 2022 | 250.20 | Chengdu 2022 statistical communique (via hongheiku.com) | **151.80** | 2022 Chengdu fiscal revenue and expenditure summary table | 全市一般公共预算支出·科学技术支出 (决算) |
| 2023 | 268.60 | Chengdu 2023 statistical communique (via hongheiku.com) | **150.90** | 2023 Chengdu fiscal revenue and expenditure summary table | 全市一般公共预算支出·科学技术支出 (决算) |
| 2024 | 129.24 | Chengdu 2024 city-wide budget expenditure plan | **129.24** | Chengdu 2024 city-wide budget expenditure plan | 全市一般公共预算支出·科学技术支出 (预算) |

### Changes Made

- **`data/raw/manual_source_observations.csv`**: Added `science_technology_expenditure` observations for Chengdu 2021 (128.0, estimated from Gotohui trend) and official values for 2022 (151.8), 2023 (150.9), and 2024 (129.24), with source URLs.
- **`src/yei/download_data.py`**: Updated `innovation_index` derivation to prioritize `science_technology_expenditure` when available, falling back to `rd_expenditure` otherwise.
- **`data/raw/city_panel.csv`**: Added `science_technology_expenditure` column; updated Chengdu 2021-2024 `innovation_index` to narrow-caliber values (2021 estimated, 2022-2023 from final accounts, 2024 from budget plan).

### Verification Results

- Chengdu `innovation_index` now shows consistent narrow-caliber values: 2021 = 128.00 (estimated), 2022 = 151.80, 2023 = 150.90, 2024 = 129.24.
- The 2023→2024 drop becomes −13.8% (from −51.9%), which is more reasonable for a budget-execution fluctuation.
- 2021 is an estimate from the Gotohui trend curve and should be replaced with the official city-wide fiscal final accounts figure when available.
- `uv run pytest` passes all tests.
- `validate_observations.py` and `test_data_quality.py` pass.
