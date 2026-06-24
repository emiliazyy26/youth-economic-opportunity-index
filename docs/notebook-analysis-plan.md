# Notebooks Analysis Plan

This document describes the purpose, analysis order, and output goals of each notebook in the `notebooks/` directory, consistent with the research questions and methodology in [project-design.md](project-design.md).

## 1. General Principles

`notebooks/` serves as the **research narrative line**, not the production pipeline. Reproducible computation logic lives in `src/yei/`; notebooks are responsible for presenting:

- Where data comes from and whether it is credible
- What patterns exist across cities
- How the index should be interpreted
- Whether conclusions are robust

Recommended analysis thread:

```text
Data credibility -> Indicator distribution -> Income vs housing pressure trade-off -> YEOI ranking -> Group interpretation and robustness -> Conclusion
```

Notebook order:

```text
01_data_sources.ipynb
 02_data_cleaning.ipynb
 03_exploratory_analysis.ipynb
 04_index_calculation.ipynb
 05_explanatory_model.ipynb
```

Before running, complete data preparation:

```bash
uv run yeoi-download
uv run yeoi-build
```

Notebooks primarily read:

| File | Purpose |
|------|---------|
| `data/raw/city_panel.csv` | Raw wide panel |
| `data/raw/source_observations.csv` | Per-observation source records |
| `data/raw/data_sources.csv` | Source summary |
| `data/raw/missing_data_report.csv` | Gap report |
| `data/processed/city_economic_opportunity.csv` | Cleaned panel |
| `data/processed/yeoi_scores.csv` | Sub-scores and rankings |

---

## 2. Notebook Plans

### 01 Data Sources — Can the data be trusted?

**Goal:** Establish sample and source credibility documentation.

**Suggested content:**

- 20 cities x 2021-2025 sample design
- City groups: megacities, strong second-tier, transition/growth, control group (see `CITIES` in `src/yei/config.py`)
- Summarize source types from `source_observations.csv`, `data_sources.csv`
- Proportion of official sources, third-party mirrors, manual supplements
- Display `missing_data_report.csv`, explain current main gaps
- Clarify caliber and limitations of `innovation_index = rd_expenditure`

**Core outputs:**

- City group table
- Indicator coverage table
- Source type proportions
- Missing data list

**Length:** Keep concise, serving the "data is credible, process is reproducible" narrative.

---

### 02 Data Cleaning — How raw data becomes an analyzable panel

**Goal:** Explain the transformation from raw observations to analysis panel.

**Suggested content:**

- Read `data/raw/city_panel.csv`, verify row count is 100 (20 cities x 5 years)
- Core field missing value check
- Show derived fields:
  - `population_growth` (computed from population series)
  - `housing_burden` (housing price index / disposable income)
  - `innovation_index` (currently equals `rd_expenditure`)
- Explain project principle: no proxy, no arbitrary estimation, only source-backed data
- **Explain** missing values rather than forcing imputation

**Implementation note:** Authoritative cleaning logic is in `src/yei/clean_data.py` and `src/yei/download_data.py`; this notebook focuses on explanation and verification, not duplicating cleaning code.

**Core outputs:**

- Missing value table or heatmap
- Field unit and caliber documentation
- Per-year coverage rates for 2021-2025

---

### 03 Exploratory Analysis — Exploratory analysis (prioritize completion)

**Goal:** Answer the three economic questions from [project-design.md](project-design.md):

1. Are high-income cities still worth the higher housing cost?
2. Does housing pressure offset the economic opportunities a city offers?
3. Which cities have better long-term attractiveness and growth potential?

**Suggested analysis:**

- Latest year income ranking (`disposable_income`)
- Latest year housing pressure ranking (`housing_burden`, higher = more pressure)
- GDP per capita vs disposable income comparison
- Income vs housing burden scatter plot (colored by city group)
- Population growth time trend (`population_growth`)
- Innovation indicator time trend (`innovation_index`)
- City group box plots

**Core charts (corresponding to project-design section 8):**

| # | Chart | Variables |
|---|-------|-----------|
| 1 | Income ranking | `disposable_income` |
| 2 | Housing burden ranking | `housing_burden` |
| 3 | GDP per capita comparison | `gdp_per_capita` |
| 4 | Population growth trend | `population_growth` |
| 5 | (Optional) Income vs housing burden scatter | Two variables + city group |

**Economic interpretation directions:**

- Tier-1 cities: high income, high housing pressure
- Some strong second-tier: may be more balanced between income and housing pressure
- Population growth: distinguish "high income but declining attractiveness" vs "moderate income but strong growth"

**Priority:** This notebook produces the most charts and narrative; **prioritize completion**.

---

### 04 Index Calculation — How YEOI is computed, whether rankings are reasonable

**Goal:** Transparently present index construction and ranking results.

**Suggested content:**

- Same-year cross-section Min-Max normalization (see [methodology.md](methodology.md))
- Six sub-scores:
  - `job_opportunity_score`
  - `starting_income_score`
  - `living_cost_score`
  - `big_company_score`
  - `growth_potential_score`
  - `city_base_score`
- Weights and composite score
- Latest year YEOI ranking
- 2021-2025 ranking changes
- Top city sub-score comparison (radar chart or stacked bar)

**Index formula (consistent with code):**

The code inverse-normalizes `living_cost_score`, so higher scores indicate lower housing pressure:

```text
YEOI = 0.25 x JobOpportunityScore + 0.20 x StartingIncomeScore
     + 0.20 x LivingCostScore + 0.15 x BigCompanyScore
     + 0.10 x GrowthPotentialScore + 0.10 x CityBaseScore
```

> Weights are defined by `YEOI_WEIGHTS` in `src/yei/config.py`.

**Core charts:**

- Latest year Top 10 YEOI ranking
- Ranking change over time line chart
- City group average YEOI
- Top city sub-score comparison

**Priority:** Complete after 03.

---

### 05 Explanatory Model — Explanation and robustness (not causal)

**Goal:** Discuss which factors are associated with YEOI rankings and test weight sensitivity. **No** complex machine learning or causal inference.

**Suggested content:**

- Correlation of each sub-score with `yeoi_score`
- City group average score comparison
- Top / Bottom city indicator differences
- **Weight sensitivity analysis:**
  - Baseline weights
  - Increase housing weight
  - Increase population growth weight
  - Decrease innovation weight
- Compare ranking stability under different weights

**Core outputs:**

- Sub-score vs YEOI correlation bar chart
- Top / Bottom city sub-score difference table
- Sensitivity ranking change table
- Stable ranking cities vs sensitive ranking cities

**Expression principle:**

```text
This is an explanatory index analysis, not a causal model.
```

Write "under the current index specification, income and GDP sub-scores contribute more to rankings," not "income causes higher city opportunity."

**Priority:** Complete last, supplementing robustness and limitations.

---

## 3. Cross-cutting Core Questions

| # | Question |
|---|----------|
| 1 | Which cities have the highest income opportunity? |
| 2 | Which cities have the lowest housing pressure? |
| 3 | Which cities remain attractive in population growth? |
| 4 | Does high income necessarily mean high economic opportunity? |
| 5 | Which cities are more balanced between "high income + acceptable housing pressure"? |
| 6 | What type of advantage do top-ranked YEOI cities primarily rely on? |
| 7 | If housing pressure weight is increased, do rankings change significantly? |
| 8 | Which conclusions are most affected by `rd_expenditure` gaps? |

---

## 4. Impact of Current Data Status on Analysis

As of the current project state (see `data/raw/missing_data_summary.md`):

| Indicator | Panel Coverage | Impact on Analysis |
|-----------|---------------|---------------------|
| `disposable_income` | 100/100 | Can fully do income ranking and scatter plots |
| `house_price` / `housing_burden` | 100/100 | Can fully do housing pressure analysis |
| `population_growth` | 100/100 | Can fully do growth trends |
| `gdp_per_capita` | 100/100 | Can fully do GDP comparison |
| `innovation_index` | 100/100 | Can fully do innovation analysis (including rd_expenditure) |
| `job_posting_count` | 100/100 | Year-specific data 2021-2025 |
| `entry_salary` | 100/100 | Year-specific data 2021-2025 |

In 04, 05: mark that cities with missing years require cautious interpretation of innovation sub-scores and composite rankings.

---

## 5. Implementation Priority

| Order | Notebook | Rationale |
|-------|----------|----------|
| 1 | `03_exploratory_analysis.ipynb` | Produces core charts and economic narrative |
| 2 | `04_index_calculation.ipynb` | Rankings, sub-scores, weight explanation |
| 3 | `05_explanatory_model.ipynb` | Robustness and sensitivity |
| 4 | `01_data_sources.ipynb` | Keep concise, support credibility |
| 5 | `02_data_cleaning.ipynb` | Keep concise, point to `src/yei/` |

---

## 6. Connection to Report and Dashboard

| Output | Destination |
|--------|-------------|
| 5 core charts from 03 | `reports/` static charts or report figures |
| Ranking tables from 04 | Report Results section |
| Sensitivity conclusions from 05 | Report Limitations / Discussion |
| Interactive needs from 04 | `app/streamlit_app.py` already implements year, city, sub-score queries |

Notebook conclusions should serve [project-design.md](project-design.md) section 10 report structure: Introduction -> Data -> Methodology -> Results -> Discussion -> Limitations -> Conclusion.

---

## 7. Related Documents

- [Project Design](project-design.md)
- [Methodology](methodology.md)
- [Data Design](data-design.md)
- [Architecture and Commands](architecture.md)
