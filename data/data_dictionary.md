# Data Dictionary

This file defines the core fields used by the Urban Economic Opportunity Index. Source-backed raw observations remain in `data/raw/`; derived intermediate tables are written to `data/interim/`; cleaned analysis-ready outputs are written to `data/processed/`.

## Core Panel Fields

| Field | Type | Meaning | Preferred Source | Notes |
|------|------|---------|------------------|-------|
| `city` | string | City name in English | Project city list | Use stable English names across all files. |
| `year` | int | Data year | Official statistical publication | The target panel is 2021-2025. |
| `gdp_per_capita` | float | GDP per capita, RMB | National Bureau of Statistics / city statistical yearbooks | Keep units consistent across cities. |
| `disposable_income` | float | Per capita disposable income, RMB | City statistical yearbooks / statistical communiques | Prefer all-resident disposable income when available. |
| `house_price` | float | Comparable housing price level | NBS 70-city index or yearbook-derived average | 19 cities use the NBS 70-city new-home price index annual mean (~100); Suzhou is NOT in the 70-city list, and its value is derived from Jiangsu Statistical Yearbook as `商品房销售额(亿元)/商品房销售面积(万㎡)×10000` yielding yuan/sqm. Min-Max normalization within each year makes these two sources comparable for ranking. |
| `housing_burden` | float | Housing pressure relative to income | Derived field | Default formula: `house_price / disposable_income`. With index-based `house_price`, this is a relative pressure indicator, not an actual house-price-to-income ratio. |
| `population` | float | Permanent resident population | Statistical yearbooks / communiques | Used to derive `population_growth`; unit is persons. Missing official values remain blank. |
| `population_growth` | float | Year-on-year population growth rate | Derived field | `(population_t - population_t-1) / population_t-1`. It is only computed when both current-year and previous-year population are source-backed. |
| `university_resource` | int | Number of higher education institutions | Ministry of Education school list | Auxiliary explanatory variable, currently treated as a 2025 manual count repeated across analysis years. |
| `innovation_index` | float | Innovation proxy used in scoring | Official R&D / patent / science expenditure source | Current source-backed implementation maps available `rd_expenditure` observations to this field. Missing official innovation data remains blank. |
| `source` | string | Short source label | Manual collection metadata | Keep source labels readable. |
| `source_url` | string | Source URL or publication reference | Official source | Use stable official links where possible. |
| `notes` | string | Unit, coverage, or treatment notes | Manual collection metadata | Record assumptions and imputation notes here. |

## Score Fields

| Field | Meaning |
|------|---------|
| `income_score` | Min-max standardized disposable income score, 0-100. |
| `gdp_score` | Min-max standardized GDP per capita score, 0-100. |
| `population_growth_score` | Min-max standardized population growth score, 0-100. |
| `innovation_score` | Min-max standardized innovation score, 0-100. |
| `housing_burden_score` | Inverted min-max standardized housing burden score, 0-100. Higher means lower pressure. |
| `ueoi_score` | Weighted Urban Economic Opportunity Index score. |
| `rank` | Within-year city rank by `ueoi_score`. |

## Data Quality Rules

- Do not edit raw source files in place.
- Use lowercase `snake_case` column names.
- Record source and unit assumptions for every manually collected field.
- Do not write estimated, peer-proxy, or project-proxy values into raw/source observations; leave missing values blank and report them in `data/raw/missing_data_report.csv`.
- Standardize scores within each year, not across all years at once.
- Keep unverifiable commercial housing data out of the core index.
