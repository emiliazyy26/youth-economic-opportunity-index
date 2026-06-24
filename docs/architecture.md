# Architecture and Development Guide

## Directory Structure

```text
youth-economic-opportunity-index/
├── app/
│   └── streamlit_app.py       # Dashboard entry point
├── data/
│   ├── raw/                   # Manually collected raw CSV files
│   ├── processed/             # Cleaned results and index outputs
│   └── data_dictionary.md     # Field, unit, caliber and source documentation
├── docs/                      # Project documentation
├── notebooks/                 # Jupyter research process display
│   ├── 01_data_sources.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_exploratory_analysis.ipynb
│   ├── 04_index_calculation.ipynb
│   └── 05_explanatory_model.ipynb
├── reports/                   # Research report outputs for portfolio use
├── src/
│   └── yei/                   # Core Python package
│       ├── config.py          # Paths, cities, weight constants
│       ├── clean_data.py      # Cleaning and field derivation
│       ├── build_index.py     # YEOI computation pipeline
│       └── visualize.py       # Static charts
├── tests/
├── pyproject.toml
└── README.md
```

## Data Flow

```text
data/raw/city_panel.csv
        |
        v  clean_data.py
data/processed/city_economic_opportunity.csv
        |
        v  build_index.py
data/processed/yeoi_scores.csv
        |
        ├──> visualize.py  →  figures/
        └──> streamlit_app.py
```

`src/yei/` is the authoritative, reproducible data production pipeline; `notebooks/` serves to display the research process, exploratory analysis, and economic interpretation. Notebooks may call functions from `src/yei/` but should not duplicate independent cleaning or index computation logic.

## Notebook Design

| Notebook | Purpose |
|----------|---------|
| `01_data_sources.ipynb` | Explain sample cities, data sources, field calibers and source verifiability |
| `02_data_cleaning.ipynb` | Show missing value checks, unit unification, field naming and housing burden derivation |
| `03_exploratory_analysis.ipynb` | Analyze relationships among income, GDP, housing pressure, population growth and innovation |
| `04_index_calculation.ipynb` | Explain normalization, weights, YEOI rankings and sensitivity analysis |
| `05_explanatory_model.ipynb` | Optional explanatory regression or correlation analysis, not a predictive model |

Notebooks serve as research narrative for admissions officers to showcase analytical thinking; the command-line entry `uv run yeoi-build` remains the authoritative computation entry point.

## Environment Management

This project uses [uv](https://docs.astral.sh/uv/) to manage Python version and dependencies.

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev
```

The virtual environment is located in `.venv/` and can be used via `uv run` without manual activation.

## Common Commands

```bash
# Build index
uv run yeoi-build

# Run tests
uv run pytest

# Code linting
uv run ruff check src tests

# Start dashboard
uv run streamlit run app/streamlit_app.py
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `config.py` | Centralized paths, sample cities, YEOI weights |
| `clean_data.py` | Read raw data, derive housing_burden, write processed table |
| `build_index.py` | Min-Max normalization, weighted summation, ranking |
| `visualize.py` | matplotlib static charts for report use |
| `app/streamlit_app.py` | Interactive city queries and ranking display |
| `notebooks/` | Research process display and exploratory analysis |

## Development Conventions

1. **Column naming** uses lowercase snake_case
2. **Configuration centralized** — city lists and weights only change in `config.py`
3. **Raw and processed separation** — raw data is never modified in place
4. **Per-year cross-section normalization** — do not mix min/max across years
5. **Notebooks do not duplicate production logic** — import from `src/yei/` when reuse is needed
6. **Data before product** — complete CSV, notebook and charts (Day 1-6) before dashboard

## Extension Points

| Need | Suggested Location |
|------|-------------------|
| Add new data source | `data/raw/` + `clean_data.py` |
| Adjust weights | `config.py` → `YEOI_WEIGHTS` |
| Add new chart | `visualize.py` |
| Sensitivity analysis | `notebooks/` or new `src/yei/sensitivity.py` |
| Report charts | `visualize.py` → `reports/` |
