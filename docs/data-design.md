# Data Design

## Target Data Table

The final panel data is saved as `data/processed/city_economic_opportunity.csv`.

### Field Definitions

| Field | Type | Description | Data Tier |
|-------|------|-------------|-----------|
| `city` | string | City name in English | — |
| `year` | int | Year | — |
| `gdp_per_capita` | float | GDP per capita (RMB) | A |
| `disposable_income` | float | Per capita disposable income (RMB) | A |
| `house_price` | float | Housing price level | A/C |
| `housing_burden` | float | Housing burden `house_price / disposable_income` | derived |
| `population_growth` | float | YoY population growth rate | derived |
| `university_quality` | float | Quality-weighted university score | A |
| `innovation_index` | float | R&D expenditure | A |
| `listed_company_count` | float | A-share listed company count by domicile | B |
| `high_tech_company_count` | float | National high-tech enterprise count (火炬中心/科技厅) | B |
| `job_posting_count` | float | Job posting count (platform sample) | C |
| `entry_salary` | float | Entry-level / graduate starting salary | C |
| `rent_monthly` | float | 1BR city-center monthly rent (RMB) | C |
| `rent_burden` | float | Rent burden `rent_monthly x 12 / disposable_income` | derived |
| `tertiary_ratio` | float | Tertiary sector share of GDP (%) — **supplementary**, not in main index | A |

### Index Output Table

`data/processed/yeoi_scores.csv` appends YEOI six-dimension scores, `yeoi_score`, `rank`, and dimension source labels on top of the raw fields.

## Data Layers

```text
data/raw/        # source-backed raw observations
data/interim/    # derived tables (housing index, population growth, etc.)
data/processed/  # cleaned panel + YEOI scores + sensitivity report
```

External youth / enterprise indicators:

```text
data/raw/external/listed_companies_by_city.csv   # Tier B
data/raw/external/high_tech_companies_by_city.csv  # Tier B (high-tech enterprise counts 2021-2025)
data/raw/external/youth_platform_indicators.csv  # Tier C (rent, job postings, entry salary)
```

Missing data report `data/raw/missing_data_report.csv` includes `data_tier` (A/B/C/D) and `category` (core/supplementary).

## Main Index Data Quality Threshold

- City coverage >= 80% (`CORE_METRIC_COVERAGE_THRESHOLD`) to qualify as a primary indicator
- Platform data must record collection date, keywords, sampling rules, and source URL
- Indicators failing the threshold automatically fall back, with `*_source` field annotation

## Data Sources

### Tier A: Official Statistics

- NBS, city statistical yearbooks, statistical communiques
- Usage: income, GDP, population, R&D, housing price index

### Tier B: Institutional Public Data

- A-share listed company domicile statistics (`listed_companies_by_city.csv`)
- National high-tech enterprise counts from Torch Center / provincial science bureaus (`high_tech_companies_by_city.csv`)
- Usage: enterprise opportunity dimension (composite scoring)

### Tier C: Platform Samples

- Numbeo rent (`youth_platform_indicators.csv`)
- Recruitment platform job postings / entry salary (collected; currently fallback to innovation + population growth, disposable income)

### Tier D: Excluded

- Unverifiable media screenshots, opaque caliber rankings

## Data Collection Priority

1. **Required (main index fallback available):** disposable income, housing burden, population growth, innovation, university quality
2. **Important (youth dimension):** rent, listed company count, high-tech company count
3. **Extension (Tier C):** job postings, entry salary
4. **Supplementary:** `tertiary_ratio` (not in main formula)

## Data Quality Checklist

- [x] 20 cities x 2021-2025 panel complete
- [x] `listed_company_count`, `high_tech_company_count`, `rent_monthly` written to source observations
- [x] Core field gaps classified by core/supplementary in missing report
- [x] Platform data has source_url and collection notes
- [x] `uv run yeoi-build` generates `yeoi_scores.csv`
