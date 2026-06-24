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

# 分析样本：20 城 × 5 年
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

# 数据可信等级：A 官方 / B 机构公开 / C 平台样本 / D 不可复核
DATA_TIER_A = {
    "gdp_per_capita",
    "disposable_income",
    "population",
    "population_growth",
    "house_price",
    "housing_burden",
    "rd_expenditure",
    "innovation_index",
    "university_quality",
}
DATA_TIER_B = {"listed_company_count", "average_wage"}
DATA_TIER_C = {"job_posting_count", "entry_salary", "rent_monthly", "rent_burden"}
DATA_TIER_D = {"youth_unemployment_proxy"}

# 主指数维度权重（living_cost / rent_burden 在 build_index 中反向标准化）
YEOI_WEIGHTS = {
    "job_opportunity_score": 0.25,
    "starting_income_score": 0.20,
    "living_cost_score": 0.20,
    "big_company_score": 0.15,
    "growth_potential_score": 0.10,
    "city_base_score": 0.10,
}

# 主指数准入：城市覆盖率阈值
CORE_METRIC_COVERAGE_THRESHOLD = 0.80

# 维度主指标与 fallback（fallback 在覆盖率不足时启用）
DIMENSION_SPEC = {
    "job_opportunity": {
        "primary": "job_posting_count",
        "fallback_metrics": ["innovation_index", "population_growth"],
        "invert": False,
    },
    "starting_income": {
        "primary": "entry_salary",
        "fallback_metrics": ["disposable_income"],
        "invert": False,
    },
    "living_cost": {
        "primary": "rent_burden",
        "fallback_metrics": ["housing_burden"],
        "invert": True,
    },
    "big_company": {
        "primary": "listed_company_count",
        "fallback_metrics": [],
        "invert": False,
    },
}

GROWTH_POTENTIAL_METRICS = ["population_growth", "innovation_index"]
CITY_BASE_METRICS = ["university_quality", "gdp_per_capita"]

# 主指数 raw 字段；tertiary_ratio 降为补充字段
RAW_COLUMNS = [
    "city",
    "year",
    "gdp_per_capita",
    "disposable_income",
    "house_price",
    "housing_burden",
    "population_growth",
    "university_quality",
    "innovation_index",
    "listed_company_count",
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
    "big_company_score",
    "growth_potential_score",
    "city_base_score",
    "yeoi_score",
    "rank",
    "job_opportunity_source",
    "starting_income_source",
    "living_cost_source",
]

# 下载流水线目标指标（含青年维度）
TARGET_METRICS = {
    "gdp_per_capita": YEARS,
    "disposable_income": YEARS,
    "population": [2020, *YEARS],
    "house_price": YEARS,
    "rd_expenditure": YEARS,
    "university_quality": YEARS,
    "listed_company_count": YEARS,
    "job_posting_count": YEARS,
    "entry_salary": YEARS,
    "rent_monthly": YEARS,
}

SUPPLEMENTARY_TARGET_METRICS = {
    "tertiary_ratio": YEARS,
}
