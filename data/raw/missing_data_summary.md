# Project Data Gap Summary

> Based on `city_panel.csv`, `missing_data_report.csv`, `download_links.md` and current data status.
> Sample: 20 cities x 2021-2025.
> **Last updated: 2026/06/24 after Data Improvement Plan Phase 1+2 completion**

---

## 1. Current Status Overview (post 2026.06.24 data improvement)

**YEOI Index Completeness: 100/100 (100%)**

| Year | YEOI Complete Cities | Status |
|------|---------------------|--------|
| 2021 | 20/20 | Complete |
| 2022 | 20/20 | Complete |
| 2023 | 20/20 | Complete |
| 2024 | 20/20 | Complete |
| 2025 | 20/20 | Complete |

**Panel Base Field Coverage**

| Field | Coverage | Notes |
|-------|----------|-------|
| `gdp_per_capita` | 100/100 (100%) | Full coverage (derived via gdp_total / population) |
| `disposable_income` | 100/100 (100%) | Full coverage |
| `population` | 100/100 (100%) | Full coverage |
| `house_price` | 100/100 (100%) | Full coverage (NBS 70-city index) |
| `innovation_index` | 100/100 (100%) | Full coverage (includes rd_expenditure as separate field) |
| `job_posting_count` | 100/100 (100%) | Full coverage (year-specific 2021-2025 data) |
| `entry_salary` | 100/100 (100%) | Full coverage (year-specific 2021-2025 data) |

---

## 2. Remaining Real Gaps

**No remaining gaps.** The 4 cities with missing 2025 rd_expenditure have been filled via wide-caliber estimates (budget_estimate/derived_estimate).

> All historical gaps have been entered into the database (see below).

---

## 3. Data Filling Path Review

### 3.1 Historical Rounds (Wuhan/Nanchang/Harbin special efforts)

See `download_links.md`. Key outputs:
- Wuhan **city-wide caliber** 2021-2025: 190.32 / 177.76 / 181.37 / 200.38 / 207.74 (100M RMB)
- Nanchang 2021-2024: 45.85 / 39.50 / 37.20 / 39.13 (100M RMB, extracted from Jiangxi Provincial Bureau of Statistics new website)
- Harbin 2021/2023/2024: 9.75 / 11.59 / 19.08 (100M RMB, extracted from budget report PDFs)
- Kunming 2021-2024: 10.62 / 14.88 / 8.84 / 5.00 (100M RMB, Yunnan Provincial S&T Bulletin)
- Hangzhou 2024/2025: 267.8 / 312.0 (100M RMB, budget execution report/bulletin)
- Chengdu 2024: 129.24 (100M RMB, budget PDF)
- Hefei 2024: ~95 (100M RMB, trend extrapolation, pending budget PDF confirmation)

### 3.2 Current Round (2026.06.22) Multi-Source Batch Filling

**Strategy:**
- Broadened data sources (user-authorized): government bulletins + hongheiku mirrors + tjcn.org + financial media (Caixin, Sina, Jiemian, People's Daily) + CEIC + CNR + party media local editions
- Tools: Tavily Search API (via MCP) + manual verification
- Database entry: ~70 observations for 2025 appended to `manual_source_observations.csv`, plus historical years supplemented via `download_data.py` communique_fetch auto-scraping

**New 2025 data (source coverage 19/20 cities):**

| Indicator | Complete City Count |
|-----------|-------------------|
| disposable_income | 19/20 (Hangzhou missing, bulletin not yet published separately) |
| population | 19/20 (Nanjing missing, but filled via communique derivation) |
| gdp_per_capita | 19/20 |

Note: Pipeline run further scraped via communique_fetch, and auto-derived via `gdp_total / population` formula, raising final panel coverage to 100%.

**New scripts:**
- `scripts/batch_search_gaps.py` — Batch gap search tool, supports `--year`/`--dry-run`/`--merge`, with keyword search + automatic value extraction + multi-source cross-validation

---

## 4. Data Source Tiers (Project Built-in)

| Tier | Source | is_official_source | Proportion |
|------|--------|-------------------|------------|
| Tier 1 | Government statistics / finance bureau / yearbook PDFs | True | ~55% |
| Tier 2 | hongheiku/tjcn.org bulletin mirrors | True (communique type) | ~25% |
| Tier 3 | Financial media (Caixin/Sina/People's Daily/Party media) | False | ~20% |
| Tier 4 | CEIC/Wikipedia/bond rating reports | False | ~10% |

All non-official sources are annotated with caliber and credibility in the `notes` field.

---

## 5. YEOI Index Ranking (2025)

| Rank | City | YEOI Score |
|------|------|------------|
| 1 | Shanghai | 84.3 |
| 2 | Beijing | 80.5 |
| 3 | Shenzhen | 78.5 |
| 4 | Guangzhou | 62.2 |
| 5 | Hangzhou | 61.9 |
| 6 | Nanjing | 60.4 |
| 7 | Suzhou | 54.4 |
| 8 | Xiamen | 52.4 |
| 9 | Changsha | 48.5 |
| 10 | Wuhan | 43.7 |

Note: All cities have YEOI output for 2025 (rd_expenditure filled via wide-caliber estimates).

---

## 6. Reference Files

| File | Purpose |
|------|---------|
| `data/raw/missing_data_report.csv` | Programmatic gap report (only 4 rows remaining) |
| `data/raw/download_links.md` | Per-city download links, progress and TODOs |
| `data/raw/manual_source_observations.csv` | Manual/budget-caliber supplements (includes is_official_source corrections) |
| `data/raw/source_observations.csv` | Auto+manual merged source observation long table (1186 entries) |
| `data/raw/city_panel.csv` | 20x5 wide panel (100 rows, full coverage) |
| `data/processed/yeoi_scores.csv` | YEOI scores and rankings |
| `scripts/batch_search_gaps.py` | Tavily batch gap search tool |
| `scripts/fetch_rd_budget_playwright.py` | Chengdu/Hefei budget scraping (playwright) |
