# Methodology

## Design Principles

YEOI (Youth Economic Opportunity Index) adopts a **transparent weighted linear model**, using data **credibility thresholds** rather than an "official vs. unofficial" binary to determine whether indicators enter the main ranking.

- Undergraduate economics applications value interpretability
- Weights have clear economic meaning (oriented toward young people's city choices)
- Third-party data (job postings, rent, enterprise directories) can enter the main index as long as caliber is fixed and collection is reproducible
- Results can be independently verified

## Index Formula

```text
YEOI = 0.20 x JobOpportunity
     + 0.20 x StartingIncome
     + 0.20 x LivingCostAffordability
     + 0.20 x EnterpriseOpportunity
     + 0.10 x GrowthPotential
     + 0.10 x HumanCapitalCityBase
```

Each component is a **0-100 standardized score** computed within the same year's city cross-section; the living cost dimension is inverse-normalized on `rent_burden` or `housing_burden`, so higher scores indicate lower pressure.

## Weight Description

| Dimension | Weight | Economic Meaning |
|-----------|--------|-------------------|
| Job Opportunity | 0.20 | Whether young people can find jobs (job postings or employment capacity proxy) |
| Starting Income | 0.20 | Starting salary or disposable income return |
| Living Cost Affordability | 0.20 | Rent / housing price relative to income as living cost pressure |
| Enterprise Opportunity | 0.20 | Career opportunities from large enterprises, listed companies, and high-tech firms |
| Growth Potential | 0.10 | Long-term opportunity from population inflow and innovation activity |
| Human Capital / City Base | 0.10 | University resources and city economic base (down-weighted to avoid macro ranking dominance) |

## Dimension Indicators and Fallback

The main index uses a "primary indicator + quality threshold + fallback" mechanism (see `src/yei/data_quality.py`):

| Dimension | Primary Indicator | Fallback |
|-----------|-------------------|----------|
| Job Opportunity | `job_posting_count` | mean of `innovation_index` + `population_growth` |
| Starting Income | `entry_salary` | `disposable_income` |
| Living Cost | `rent_burden` | `housing_burden` |
| Enterprise Opportunity | `listed_company_count` + `high_tech_company_count` (composite) | `listed_company_count` only |

`EnterpriseOpportunity` uses **composite scoring**: both `listed_company_count` and `high_tech_company_count` are independently min-max normalized and then averaged. If only one metric is available, that single metric is used. This captures both traditional large enterprises and innovation-driven high-tech firms.

`GrowthPotential` = mean of standardized(`population_growth`, `innovation_index`).
`HumanCapitalCityBase` = mean of standardized(`weighted_university_score`, `gdp_per_capita`).

`tertiary_ratio` has been demoted to a supplementary field and no longer enters the main formula (high missing rate, indirect link to youth opportunity).

## Data Credibility Tiers

| Tier | Example | Eligible for Main Index? |
|------|---------|--------------------------|
| A | Statistical yearbooks, communiques, NBS | Yes |
| B | Listed company domiciles, enterprise directories | Yes (requires source record) |
| C | Recruitment platforms, Numbeo rent | Yes (requires >=80% city coverage + fixed collection rules) |
| D | Media screenshots, unverifiable rankings | No |

Main index admission threshold (`CORE_METRIC_COVERAGE_THRESHOLD = 0.80`): if non-missing ratio of sample cities in a year cross-section is < 80%, the dimension falls back.

## Standardization Method

### Min-Max Normalization

For positive indicators:

```text
Score_i = (x_i - min(x)) / (max(x) - min(x)) x 100
```

For living cost burden (lower is better):

```text
Score_i = (max(x) - x_i) / (max(x) - min(x)) x 100
```

Normalization is performed **independently within each year cross-section**.

### Edge Cases

When all cities have the same value for an indicator in a given year (`max = min`), the score is set to 50.

## Derived Indicators

### Housing Burden

```text
HousingBurden = HousePrice / DisposableIncome
```

### Rent Burden

```text
RentBurden = RentMonthly x 12 / DisposableIncome
```

### Population Growth

```text
PopulationGrowth_t = (Population_t - Population_{t-1}) / Population_{t-1}
```

## Ranking Rules

- Rank by `yeoi_score` descending
- Tied cities share the same rank (`method='min'`)
- Rankings are only valid within the same `{year}` cross-section

## Sensitivity Analysis

Run:

```bash
uv run python -c "from yei.sensitivity import run_sensitivity_report; print(run_sensitivity_report('data/processed/sensitivity_report.csv'))"
```

Tests the impact of +/- 0.05 weight shifts on Top-5 rankings, confirming that third-party data does not singly dominate conclusions.

## Implementation Entry Point

```bash
uv run yeoi-build
```

Configuration and weights are in `src/yei/config.py`; quality thresholds are in `src/yei/data_quality.py`.
