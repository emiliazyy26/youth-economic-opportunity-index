# Data Dictionary

This file defines the core fields used by the Youth Economic Opportunity Index (YEOI). Source-backed raw observations remain in `data/raw/`; derived intermediate tables are written to `data/interim/`; cleaned analysis-ready outputs are written to `data/processed/`.

## Core Panel Fields

| Field | Type | Meaning | Tier | Preferred Source | Notes |
|------|------|---------|------|------------------|-------|
| `city` | string | City name in English | — | Project city list | Stable English names. |
| `year` | int | Data year | — | Official publication | Panel: 2021–2025. |
| `gdp_per_capita` | float | GDP per capita, RMB | A | NBS / city yearbooks | City base dimension input. |
| `disposable_income` | float | Per capita disposable income, RMB | A | City yearbooks / communiques | Starting income fallback. |
| `house_price` | float | Comparable housing price | A/C | NBS 70-city index or gotohui yuan/sqm | Used for housing_burden. |
| `housing_burden` | float | Housing pressure / income | derived | `house_price / disposable_income` | Living cost fallback. |
| `population_growth` | float | YoY population growth | derived | Population series | Growth potential input. |
| `weighted_university_score` | float | Quality-weighted HE score | A | MOE lists | City base input. |
| `innovation_index` | float | R&D expenditure proxy | A | Official R&D source | Job/growth fallback input. |
| `listed_company_count` | float | A-share listings by domicile | B | `listed_companies_by_city.csv` | Big company dimension. |
| `job_posting_count` | float | Job postings (platform) | C | Boss/Zhaopin etc. | Job opportunity primary. |
| `entry_salary` | float | Entry-level salary | C | Recruitment platforms | Starting income primary. |
| `rent_monthly` | float | 1BR city-centre rent, RMB/month | C | Numbeo / rental platforms | Living cost primary input. |
| `rent_burden` | float | Rent pressure / income | derived | `rent_monthly × 12 / disposable_income` | Living cost primary score. |
| `tertiary_ratio` | float | Tertiary share of GDP, % | A | Communiques | **Supplementary only**; not in YEOI formula. |

## Score Fields

| Field | Weight | Meaning |
|------|--------|---------|
| `job_opportunity_score` | 0.20 | Job postings or innovation+population growth fallback. |
| `starting_income_score` | 0.20 | Entry salary or disposable income fallback. |
| `living_cost_score` | 0.20 | Inverted rent_burden or housing_burden. |
| `business_ecosystem_score` | 0.20 | Listed company count + high-tech company count (composite). |
| `growth_potential_score` | 0.10 | Mean of population_growth and innovation scores. |
| `city_base_score` | 0.10 | Mean of weighted_university_score and gdp_per_capita scores. |
| `yeoi_score` | — | Weighted Youth Economic Opportunity Index. |
| `rank` | — | Within-year rank by `yeoi_score`. |
| `job_opportunity_source` | — | Metric label used for job dimension. |
| `starting_income_source` | — | Metric label used for income dimension. |
| `living_cost_source` | — | Metric label used for living cost dimension. |

## Data Quality Rules

- Do not edit raw source files in place.
- Use lowercase `snake_case` column names.
- Tier C metrics enter the core index only when ≥80% city coverage in a year slice.
- Record platform collection rules in `notes` and `source_url`.
- `missing_data_report.csv` includes `data_tier` and `category` (core/supplementary).
- Standardize scores within each year, not across all years at once.
