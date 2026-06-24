# Youth Economic Opportunity Index (YEOI)

A transparent, data-driven analysis of urban economic opportunity for young professionals in China — covering jobs, starting income, living cost and city attractiveness.

## Research Question

> For young people, which Chinese cities provide the best balance between job opportunity, starting income and living cost?

The project builds a transparent and interpretable Urban Economic Opportunity Index (YEOI) for young professionals and early-career workers — not a housing price forecast or black-box machine learning model.

## Quick Start

```bash
uv sync
uv run yeoi-download   # Optional: refresh raw data
uv run yeoi-build      # Build YEOI
uv run streamlit run app/streamlit_app.py
```

## Index Formula

```text
YEOI = 0.25 x JobOpportunity + 0.20 x StartingIncome
     + 0.20 x LivingCost + 0.15 x BigCompany
     + 0.10 x GrowthPotential + 0.10 x CityBase
```

Third-party data (job postings, rent) enters the main ranking only after passing a credibility threshold; see [docs/methodology.md](docs/methodology.md).

## Key Outputs

| File | Description |
|------|-------------|
| `data/processed/city_economic_opportunity.csv` | City x year panel |
| `data/processed/yeoi_scores.csv` | YEOI sub-scores and rankings |
| `data/processed/sensitivity_report.csv` | Weight sensitivity analysis |
| `app/streamlit_app.py` | Interactive dashboard |

## Documentation

- [Project Design](docs/project-design.md)
- [Data Design](docs/data-design.md)
- [Methodology](docs/methodology.md)
- [Data Dictionary](data/data_dictionary.md)
- [Architecture](docs/architecture.md)
- [Data Improvement Log](docs/data_improvement_log.md)

## Tech Stack

Python 3.12+ · uv · pandas · streamlit · pytest · ruff

## License

MIT
