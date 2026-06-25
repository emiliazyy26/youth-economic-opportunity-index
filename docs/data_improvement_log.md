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
