# Youth Economic Opportunity Index — Project Design

## 1. Project Positioning

**Youth Economic Opportunity Index (YEOI)** is an economic data analysis project focused on comparing Chinese cities from the perspective of **young professionals and early-career workers**. The project examines the core trade-offs graduates and young workers face when choosing a city: job opportunities, starting income, living cost, big-company opportunities, and long-term growth potential.

English title:

```text
Youth Economic Opportunity Index for Young Professionals in China:
A Data-Driven Analysis of Jobs, Starting Income and Living Cost
```

The project does not produce a simple housing price ranking or real estate investment advice. The research focus is: **which Chinese cities offer young people a better balance between job opportunity and living cost**.

## 2. Research Questions

Core question:

```text
For young people, which Chinese cities provide the best balance
between economic opportunity and living cost?
```

Decomposed into three economic questions:

1. Are high-income cities still worth the higher housing cost?
2. Does housing pressure offset the economic opportunities a city offers?
3. Which cities have better long-term attractiveness and growth potential?

The analysis target is urban economic opportunity, not the housing market itself. Housing prices and housing pressure enter the index only as living cost constraints.

## 3. Project Boundaries

### In Scope

| Direction | Description |
|-----------|-------------|
| Youth urban opportunity comparison | Compare job opportunities, starting income, living cost, big-company count, growth potential |
| Transparent index construction | Use an interpretable linear weighted model (YEOI) |
| Credible data first | Official statistics + verifiable institutional data + platform samples passing quality thresholds |
| Python data analysis | Use pandas, numpy, plotly, matplotlib for analysis and visualization |
| Streamlit dashboard | Provide interactive city queries and ranking display |

### Out of Scope

| Excluded | Reason |
|----------|--------|
| Housing price ranking | Easily becomes a real estate project, drifts from the economics theme |
| Real estate investment advice | Does not match project goals |
| Machine learning prediction | Data scale is small; transparent model is more appropriate |
| Large-scale web scraping | Weak data verifiability, high maintenance cost |

## 4. Sample Design

### Time Range

The analysis covers **2021-2025**.

An additional **2020 resident population** is collected to compute the 2021 population growth rate:

```text
PopulationGrowth_2021 = (Population_2021 - Population_2020) / Population_2020
```

Data download plan:

| Purpose | Download Range |
|---------|----------------|
| Core analysis | 2022-2026 editions of China City Statistical Yearbook, covering 2021-2025 data |
| Population growth | Additional 2021 edition yearbook for 2020 population |

The final analysis table maintains **20 cities x 5 years = 100 rows**.

### City Coverage

The project selects 20 cities to avoid nationwide sprawl and form meaningful group comparisons.

| City Type | Cities |
|-----------|--------|
| Megacities | Beijing, Shanghai, Shenzhen, Guangzhou |
| Strong second-tier | Hangzhou, Nanjing, Suzhou, Chengdu, Wuhan, Xi'an |
| Transition and growth | Hefei, Changsha, Qingdao, Xiamen, Zhengzhou, Chongqing |
| Control group | Harbin, Shenyang, Kunming, Nanchang |

City selection logic:

1. Cover first-tier, strong second-tier, growth, and transition cities;
2. Balance eastern, inland, northeastern, and southwestern regions;
3. Most cities have continuous data in official statistical publications;
4. Sample size is manageable for collection, cleaning, analysis, and presentation within a short cycle.

## 5. Data Design

### Raw Panel Table

The raw data table is stored at:

```text
data/raw/city_panel.csv
```

Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `city` | string | City name in English |
| `year` | int | Data year |
| `gdp_per_capita` | float | GDP per capita |
| `disposable_income` | float | Per capita disposable income |
| `house_price` | float | Housing price level or comparable price derived from official index |
| `housing_burden` | float | Housing burden |
| `population` | float | Resident population, used for population growth calculation |
| `population_growth` | float | Resident population growth rate |
| `weighted_university_score` | float | Quality-weighted university score |
| `tertiary_ratio` | float | Tertiary sector share of GDP (%) |
| `innovation_index` | float | Innovation indicator (R&D expenditure) |
| `source` | string | Data source shorthand |
| `source_url` | string | Original URL |
| `notes` | string | Unit, caliber, or processing notes |

Core computation fields in the project code:

```text
city
year
gdp_per_capita
disposable_income
house_price
housing_burden
population_growth
weighted_university_score
tertiary_ratio
innovation_index
```

`population`, `source`, `source_url`, and `notes` are auxiliary fields retained from the collection process.

### Output Tables

Cleaned panel data:

```text
data/processed/city_economic_opportunity.csv
```

Index score table:

```text
data/processed/yeoi_scores.csv
```

Score table fields:

| Field | Description |
|-------|-------------|
| `job_opportunity_score` | Standardized job opportunity score |
| `starting_income_score` | Standardized starting income / disposable income score |
| `living_cost_score` | Living cost affordability score (higher = lower pressure) |
| `big_company_score` | Big company / listed company opportunity score |
| `growth_potential_score` | Growth potential score |
| `city_base_score` | Human capital and city base score |
| `yeoi_score` | Composite Youth Economic Opportunity Index |
| `rank` | Within-year city ranking |
| `*_source` | Metric source label actually used for each dimension |

## 6. Data Source Plan

### GDP, GDP per Capita, and Population

Preferred sources:

1. National Bureau of Statistics (NBS);
2. China City Statistical Yearbook;
3. City-level statistical yearbooks;
4. City-level national economic and social development communiques.

Usage:

- `gdp_per_capita` measures city economic base;
- `population` is used to compute `population_growth`;
- Population growth represents a composite result of city attractiveness and job opportunities.

### Resident Income

Core indicator:

```text
disposable_income = per capita disposable income
```

Prefer all-resident per capita disposable income. If only urban-rural split data is available, maintain consistent caliber across all cities and document in `notes`.

Income carries the highest weight in YEOI because it directly reflects the income opportunity and actual purchasing power for young people in a city.

### Housing Price and Housing Burden

Housing data must be handled carefully. The project should not rely on Lianjia screenshots, Beike reports, financial articles, or unverifiable online average prices.

Recommended primary source:

```text
NBS 70 large and medium city commercial residential sales price index
```

Advantages: official, continuous, verifiable. Disadvantage: it is an index, not an absolute price. Processing approach:

```text
HousePrice_t = BasePrice_2025 x HousingIndex_t / HousingIndex_2025
```

If a reliable absolute benchmark price is not available in the short term, the official housing index can be used to construct relative housing pressure, with explicit documentation:

```text
HousingBurden = HousingIndex / DisposableIncome
```

The ideal definition is:

```text
HousingBurden = HousePrice / DisposableIncome
```

The project's interpretive focus should be on housing pressure as a constraint on economic opportunity, not on housing prices themselves.

### Innovation

The innovation indicator should be kept simple. Prefer one official, continuous, and easily interpretable variable:

1. R&D expenditure;
2. R&D intensity (R&D / GDP);
3. High-tech industry value-added;
4. Patent grants.

If multiple cities lack the same indicator, prioritize simplicity and choose the variable with the most complete coverage, rather than constructing an unverifiable complex composite index.

### University Resources

University resources enter the YEOI formula as the human capital dimension (weight 0.10 in city base).

Recommended source:

```text
MOE national higher education institution list + 985/211/Double First-Class official lists
```

Indicator definition:

```text
weighted_university_score = count_985 x 5.0 + count_211_non985 x 2.5 + count_other x 0.3
```

This weighting scheme distinguishes university tiers: top research universities (985) carry approximately 17x the weight of ordinary universities, accurately reflecting the difference in high-end human capital supply. For example, Beijing (8 985 universities) scores far higher than Shenzhen (0 985 universities), while a simple count would fail to capture this gap.

University counts and tiers change little over the 2021-2025 period; the 2025 list is used as an approximation, with this assumption documented in the report.

## 7. Index Methodology

### Design Principles

YEOI uses a transparent linear weighted model, not machine learning.

Rationale:

1. Data volume is approximately 100 rows, unsuitable for complex predictive models;
2. Economics projects prioritize variable definition, mechanism explanation, and robustness;
3. Transparent models allow readers to verify results;
4. The dashboard can directly display sub-scores and final rankings.

### Normalization

All indicators are Min-Max normalized within the same year's city cross-section.

Positive indicators:

```text
Score_i = (x_i - min(x)) / (max(x) - min(x)) x 100
```

Housing burden is a negative indicator (lower is better):

```text
HousingBurdenScore_i = (max(x) - x_i) / (max(x) - min(x)) x 100
```

If all cities have the same value for an indicator in a given year, the score is set to 50 to avoid division by zero.

### Index Formula

```text
YEOI = 0.25 x JobOpportunity
     + 0.20 x StartingIncome
     + 0.20 x LivingCostAffordability
     + 0.15 x BigCompanyOpportunity
     + 0.10 x GrowthPotential
     + 0.10 x HumanCapitalCityBase
```

### Weight Interpretation

| Dimension | Weight | Interpretation |
|-----------|--------|----------------|
| Job Opportunity | 0.25 | Job postings or employment capacity, directly reflecting whether young people can find work |
| Starting Income | 0.20 | Starting salary preferred, fallback to disposable income |
| Living Cost | 0.20 | Rent burden preferred, fallback to housing burden |
| Big Company | 0.15 | Listed company / large enterprise count |
| Growth Potential | 0.10 | Population growth + innovation activity |
| City Base | 0.10 | University quality + GDP per capita (down-weighted to avoid macro ranking dominance) |

Third-party data (job postings, rent) enters the main index only after passing credibility thresholds; otherwise it automatically falls back.

## 8. Analysis Outputs

### Core Charts

At least 5 charts:

1. Income ranking;
2. Housing burden ranking;
3. GDP per capita comparison;
4. Population growth trend;
5. YEOI final ranking.

Optional extension charts:

1. Income vs housing burden scatter plot;
2. YEOI ranking change line chart;
3. City group box plot;
4. Indicator correlation heatmap.

### Dashboard Output

The Streamlit dashboard supports:

1. Year selection;
2. City selection;
3. Viewing city YEOI total score;
4. Viewing city ranking;
5. Viewing sub-scores for income, GDP, population growth, innovation, housing burden;
6. Viewing all-city ranking table for a given year.

City page example:

| Indicator | Output |
|-----------|--------|
| YEOI Score | 82.0 |
| Rank | No.3 / 20 |
| Income Score | 95 |
| GDP Score | 92 |
| Housing Burden Score | 45 |

## 9. Technical Implementation

### Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Primary language |
| uv | Dependency and virtual environment management |
| pandas | Data cleaning and panel processing |
| numpy | Numerical computation |
| matplotlib | Static report charts |
| plotly | Interactive charts |
| streamlit | Dashboard |
| pytest | Unit testing |
| ruff | Code linting |

### Project Structure

```text
youth-economic-opportunity-index/
├── app/
│   └── streamlit_app.py
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── project-design.md
│   ├── overview.md
│   ├── data-design.md
│   ├── methodology.md
│   └── architecture.md
├── notebooks/
├── src/
│   └── yei/
│       ├── config.py
│       ├── clean_data.py
│       ├── build_index.py
│       └── visualize.py
└── tests/
```

### Data Pipeline

```text
data/raw/city_panel.csv
        |
        v
src/yei/clean_data.py
        |
        v
data/processed/city_economic_opportunity.csv
        |
        v
src/yei/build_index.py
        |
        v
data/processed/yeoi_scores.csv
        |
        ├── data/processed/sensitivity_report.csv
        ├── reports / figures
        └── Streamlit Dashboard
```

### Common Commands

```bash
uv sync
uv run yeoi-build
uv run pytest
uv run ruff check src tests
uv run streamlit run app/streamlit_app.py
```

## 10. Report Structure

The final report should be approximately 8 pages.

| Section | Content |
|---------|---------|
| Introduction | Research question, city selection background |
| Literature / Context | Urban opportunity, income, housing burden, population flow |
| Data | Data sources, variable definitions, sample scope |
| Methodology | Normalization, weights, YEOI formula and fallback |
| Results | Rankings, charts, city group comparisons |
| Discussion | Trade-offs between high-income high-cost cities and growth cities |
| Limitations | Housing price index, data gaps, weight subjectivity |
| Conclusion | Which cities are more balanced, and implications for young people |

## 11. Execution Plan

| Time | Task | Output |
|------|------|--------|
| Day 1-3 | Download statistical yearbooks and housing price index, compile `city_panel.csv` | Raw data table |
| Day 4 | Clean data, unify units, handle missing values | `city_economic_opportunity.csv` |
| Day 5 | Build YEOI standardized scores | `yeoi_scores.csv` |
| Day 6 | Generate core charts and sensitivity analysis | figures + sensitivity_report |
| Day 7-9 | Develop Streamlit dashboard | Interactive page |
| Day 10 | Add city comparison, ranking table, and sub-score display | Dashboard complete |
| Day 11-12 | Write economics report | Report draft |
| Day 13 | Check data sources, add limitation and sensitivity | Report finalized |
| Day 14 | GitHub cleanup, README and final review | Complete portfolio |

## 12. Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| Some cities lack complete income data | Prioritize communique supplementation; if still missing, document and consider dropping the city |
| Housing absolute price unverifiable | Use official 70-city index to construct relative housing pressure |
| Innovation indicator caliber inconsistent | Choose the single indicator with highest coverage |
| Weights are subjective | Include sensitivity analysis in the report |
| Data collection takes too long | First complete 20-city core 5 indicators, then supplement universities and innovation |

## 13. Success Criteria

The project is complete when:

1. `data/raw/city_panel.csv` covers 20 cities x 2021-2025;
2. Every core data point has a source record;
3. `uv run yeoi-build` successfully generates index results;
4. At least 5 report-ready charts are produced;
5. Streamlit dashboard supports city and year selection;
6. The report clearly explains why the project is a "youth urban opportunity index," not a "housing price study."

## 14. Project Value

This project is suitable as an economics and data analysis portfolio piece because it simultaneously demonstrates:

1. Economic question awareness;
2. Official data collection and cleaning ability;
3. Index construction and quantitative comparison ability;
4. Python data analysis skills;
5. Dashboard productization ability;
6. Understanding of model limitations and data caliber.

The final narrative should remain simple:

```text
This project measures urban economic opportunity in China by combining
income, economic scale, population attraction, innovation potential and
housing burden into a transparent, reproducible index.
```
