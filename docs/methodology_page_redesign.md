# Methodology Page Redesign Plan

## Goal

Improve `_page_methodology` so that users can quickly understand:

1. What the six YEOI dimensions measure
2. How the final score is calculated
3. Whether the ranking is robust
4. How reliable the data is

This is an undergraduate application project, so the page should prioritize clarity over technical detail.

## Recommended Page Structure

### 1. How YEOI Is Constructed

Add a short introduction and a simple table covering the six dimensions:

| Dimension | Weight | What It Measures | Main Indicators |
|---|---:|---|---|
| Job Opportunity | 20% | Availability of jobs | Job postings |
| Starting Income | 20% | Early-career earning potential | Entry salary |
| Living Cost | 20% | Affordability of living | Rent burden |
| Business Ecosystem | 20% | Enterprise and career environment | Listed and high-tech companies |
| Growth Potential | 10% | Future development opportunities | Population growth, innovation |
| City Base | 10% | Human capital and economic foundation | University score, GDP per capita |

The table shows primary indicators only. Fallback logic is documented in `docs/methodology.md`.

The table is the main new feature. It directly addresses the current page's biggest weakness: the six dimensions are not currently explained.

### 2. Scoring Rules

Add a short explanation using plain language:

- Each dimension is standardized to a 0–100 score within each year.
- Lower rent or housing burden produces a higher Living Cost score.
- Composite dimensions average the standardized scores of their indicators.
- The final YEOI score is the weighted sum of the six dimension scores.

Display the formula as text:

```text
YEOI = 20% × Job Opportunity
     + 20% × Starting Income
     + 20% × Living Cost
     + 20% × Business Ecosystem
     + 10% × Growth Potential
     + 10% × City Base
```

A separate pie chart is unnecessary because the table and formula already show the weight structure clearly.

### 3. Weight Sensitivity Analysis

Keep the current chart and conclusion logic.

Add one plain-language explanation:

> Each dimension's weight is adjusted by ±5 percentage points. We then check how many cities in the Top 5 change rank. Smaller changes indicate a more robust conclusion.

### 4. Data Credibility

Replace the current detailed Tier table with a concise version:

- **Tier A:** Official statistics
- **Tier B:** Institutional public data
- **Tier C:** Platform sample data
- **Tier D:** Proxy or unverifiable data

Add a note that Tier D indicators are not currently used in the main YEOI calculation.

### 5. Data Gaps

Keep the current data-gap display at the bottom of the page. It supports transparency but should not dominate the page.

## Implementation Scope

Only modify `_render_sensitivity()` in `app/streamlit_app.py`:

- Add the six-dimension overview table
- Add the scoring rules and formula
- Keep the existing sensitivity analysis
- Simplify the explanatory text for data credibility
- Keep the existing data-gap logic

Do not modify:

- `src/yei/config.py`
- `src/yei/build_index.py`
- `src/yei/sensitivity.py`
- Other dashboard pages

## Implementation Principle

Use the existing configuration and scoring logic where convenient, but do not introduce a complex metadata framework just for this display page. A small, readable table is preferable to additional abstraction.

## Expected Result

The revised page should communicate the following story:

> YEOI combines six understandable dimensions, gives the greatest weight to immediate economic conditions, tests whether the ranking changes under reasonable alternative weights, and clearly reports data limitations.

This keeps the methodology credible and transparent without making the project appear over-engineered.
