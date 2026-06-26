from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = RAW_DATA_DIR / "external"

CITY_DATA_FILE = PROCESSED_DATA_DIR / "city_economic_opportunity.csv"
YEOI_SCORES_FILE = PROCESSED_DATA_DIR / "yeoi_scores.csv"
SOURCE_OBSERVATIONS_FILE = RAW_DATA_DIR / "source_observations.csv"
SOURCE_DOCUMENTS_FILE = RAW_DATA_DIR / "source_documents.csv"
MISSING_DATA_REPORT_FILE = RAW_DATA_DIR / "missing_data_report.csv"
HOUSING_ANNUAL_FILE = INTERIM_DATA_DIR / "housing_annual.csv"
YOUTH_PLATFORM_FILE = EXTERNAL_DATA_DIR / "youth_platform_indicators.csv"
LISTED_COMPANIES_FILE = EXTERNAL_DATA_DIR / "listed_companies_by_city.csv"
HIGH_TECH_COMPANIES_FILE = EXTERNAL_DATA_DIR / "high_tech_companies_by_city.csv"

# Analysis sample: 20 cities x 5 years
YEARS = list(range(2021, 2026))

CITIES: dict[str, list[str]] = {
    "megacity": ["Beijing", "Shanghai", "Shenzhen", "Guangzhou"],
    "strong_second_tier": [
        "Hangzhou",
        "Nanjing",
        "Suzhou",
        "Chengdu",
        "Wuhan",
        "Xi'an",
    ],
    "transition": [
        "Hefei",
        "Changsha",
        "Qingdao",
        "Xiamen",
        "Zhengzhou",
        "Chongqing",
    ],
    "control": ["Harbin", "Shenyang", "Kunming", "Nanchang"],
}

ALL_CITIES = [city for group in CITIES.values() for city in group]

# Data credibility tiers: A official / B institutional public / C platform sample / D unverifiable
DATA_TIER_A = {
    "gdp_per_capita",
    "disposable_income",
    "population",
    "population_growth",
    "house_price",
    "housing_burden",
    "rd_expenditure",
    "innovation_index",
    "weighted_university_score",
}
DATA_TIER_B = {"listed_company_count", "high_tech_company_count", "average_wage"}
DATA_TIER_C = {"job_posting_count", "entry_salary", "rent_monthly", "rent_burden"}
DATA_TIER_D = {"youth_unemployment_proxy"}

# Main index dimension weights (living_cost / rent_burden are inverted in build_index)
YEOI_WEIGHTS = {
    "job_opportunity_score": 0.20,
    "starting_income_score": 0.20,
    "living_cost_score": 0.20,
    "enterprise_opportunity_score": 0.20,
    "growth_potential_score": 0.10,
    "city_base_score": 0.10,
}

# Main index admission: city coverage threshold
CORE_METRIC_COVERAGE_THRESHOLD = 0.80

# Dimension primary metrics (used directly; no fallback)
DIMENSION_SPEC = {
    "job_opportunity": {
        "primary": "job_posting_count",
        "invert": False,
    },
    "starting_income": {
        "primary": "entry_salary",
        "invert": False,
    },
    "living_cost": {
        "primary": "rent_burden",
        "invert": True,
    },
    "enterprise_opportunity": {
        "primary": "listed_company_count",
        "invert": False,
    },
}

GROWTH_POTENTIAL_METRICS = ["population_growth", "innovation_index"]
CITY_BASE_METRICS = ["weighted_university_score", "gdp_per_capita"]

# Main index raw fields; tertiary_ratio demoted to supplementary field
RAW_COLUMNS = [
    "city",
    "year",
    "gdp_per_capita",
    "disposable_income",
    "house_price",
    "housing_burden",
    "population_growth",
    "weighted_university_score",
    "innovation_index",
    "listed_company_count",
    "high_tech_company_count",
    "job_posting_count",
    "entry_salary",
    "rent_monthly",
    "rent_burden",
    "tertiary_ratio",
]

SUPPLEMENTARY_COLUMNS = ["tertiary_ratio"]

SOURCE_OBSERVATION_COLUMNS = [
    "city",
    "year",
    "metric",
    "value",
    "unit",
    "source_type",
    "source_name",
    "source_url",
    "source_file",
    "extraction_method",
    "is_official_source",
    "notes",
]

SCORE_COLUMNS = [
    "city",
    "year",
    "job_opportunity_score",
    "starting_income_score",
    "living_cost_score",
    "enterprise_opportunity_score",
    "growth_potential_score",
    "city_base_score",
    "yeoi_score",
    "rank",
    "job_opportunity_source",
    "starting_income_source",
    "living_cost_source",
]

# Download pipeline target metrics (including youth dimensions)
TARGET_METRICS = {
    "gdp_per_capita": YEARS,
    "disposable_income": YEARS,
    "population": [2020, *YEARS],
    "house_price": YEARS,
    "rd_expenditure": YEARS,
    "weighted_university_score": YEARS,
    "listed_company_count": YEARS,
    "high_tech_company_count": YEARS,
    "job_posting_count": YEARS,
    "entry_salary": YEARS,
    "rent_monthly": YEARS,
}

SUPPLEMENTARY_TARGET_METRICS = {
    "tertiary_ratio": YEARS,
}
