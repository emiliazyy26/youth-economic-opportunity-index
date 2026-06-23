from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

CITY_DATA_FILE = PROCESSED_DATA_DIR / "city_economic_opportunity.csv"
UEOI_SCORES_FILE = PROCESSED_DATA_DIR / "ueoi_scores.csv"
SOURCE_OBSERVATIONS_FILE = RAW_DATA_DIR / "source_observations.csv"
SOURCE_DOCUMENTS_FILE = RAW_DATA_DIR / "source_documents.csv"
MISSING_DATA_REPORT_FILE = RAW_DATA_DIR / "missing_data_report.csv"
HOUSING_ANNUAL_FILE = INTERIM_DATA_DIR / "housing_annual.csv"

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

# UEOI 权重（housing_burden_score 已反向标准化，分数越高表示住房压力越低）
UEOI_WEIGHTS = {
    "income_score": 0.25,
    "gdp_score": 0.20,
    "talent_capital_score": 0.15,
    "population_growth_score": 0.12,
    "innovation_score": 0.12,
    "industry_structure_score": 0.10,
    "housing_burden_score": 0.06,
}

# source-backed 宽表基础字段；允许值缺失，但不允许估算或 proxy 补值。
RAW_COLUMNS = [
    "city",
    "year",
    "gdp_per_capita",
    "disposable_income",
    "house_price",
    "housing_burden",
    "population_growth",
    "university_quality",
    "tertiary_ratio",
    "innovation_index",
]

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

# 指数输出字段
SCORE_COLUMNS = [
    "city",
    "year",
    "income_score",
    "gdp_score",
    "talent_capital_score",
    "population_growth_score",
    "innovation_score",
    "industry_structure_score",
    "housing_burden_score",
    "ueoi_score",
    "rank",
]
