"""下载并整合项目原始数据。"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

from uei.city_names import CITY_NAME_EN, CITY_NAME_ZH, CITY_REGCODE
from uei.communique_fetch import fetch_communique_panel
from uei.config import (
    ALL_CITIES,
    HOUSING_ANNUAL_FILE,
    INTERIM_DATA_DIR,
    MISSING_DATA_REPORT_FILE,
    RAW_DATA_DIR,
    SOURCE_DOCUMENTS_FILE,
    SOURCE_OBSERVATION_COLUMNS,
    SOURCE_OBSERVATIONS_FILE,
    YEARS,
)

EXTERNAL_DIR = RAW_DATA_DIR / "external"
YEARBOOK_DIR = RAW_DATA_DIR / "yearbooks"
PANEL_FILE = RAW_DATA_DIR / "city_panel.csv"
SOURCES_FILE = RAW_DATA_DIR / "data_sources.csv"
MANUAL_SOURCE_OBSERVATIONS_FILE = RAW_DATA_DIR / "manual_source_observations.csv"

HOUSING_URL = "https://raw.githubusercontent.com/hugohe3/70cityprice/main/70cityprice.csv"
HOUSING_ALT_URL = (
    "https://raw.githubusercontent.com/changao1/"
    "70-China-cities-housing-index-data-by-national-bureau-of-statistics/"
    "main/merged_housing_data_eng.csv"
)

# 常见指标在《中国城市统计年鉴》Excel 中的关键词
YEARBOOK_KEYWORDS = {
    "gdp_per_capita": ["人均地区生产总值", "人均GDP", "人均生产总值"],
    "disposable_income": ["居民人均可支配收入", "全体居民人均可支配收入"],
    "population": ["常住人口", "年末常住人口"],
    "rd_expenditure": ["研究与试验发展", "R&D经费", "R&D"],
    "science_technology_expenditure": ["科学技术支出"],
    "housing_sales_area": ["商品房销售面积", "商品房屋销售面积"],
    "housing_sales_value": ["商品房销售额", "商品房屋销售额"],
}

METRIC_UNITS = {
    "gdp_per_capita": "yuan/person",
    "gdp_total": "100 million yuan",
    "disposable_income": "yuan/person",
    "population": "person",
    "house_price": "index",
    "university_resource": "count",
    "rd_expenditure": "100 million yuan",
    "science_technology_expenditure": "100 million yuan",
    "housing_sales_area": "10000 sqm",
    "housing_sales_value": "100 million yuan",
}

TARGET_METRICS = {
    "gdp_per_capita": YEARS,
    "disposable_income": YEARS,
    "population": [2020, *YEARS],
    "house_price": YEARS,
    "rd_expenditure": YEARS,
    "university_resource": YEARS,
}

SOURCE_COLUMNS = {"city", "year", "source", "source_url", "source_file"}


def _download(url: str, dest: Path, timeout: int = 120) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def download_external_files() -> dict[str, Path]:
    files = {
        "housing_70city": _download(HOUSING_URL, EXTERNAL_DIR / "70cityprice.csv"),
        "housing_alt": _download(HOUSING_ALT_URL, EXTERNAL_DIR / "housing_index.csv"),
    }
    return files


def build_annual_housing_index(primary_csv: Path, fallback_csv: Path) -> pd.DataFrame:
    """从 70 城月度指数汇总为年度住房价格指数。"""
    alt = pd.read_csv(fallback_csv)
    alt = alt[alt["city"].isin(ALL_CITIES) & alt["year"].isin(YEARS + [2020])]
    annual = (
        alt.groupby(["city", "year"], as_index=False)["new_home_price_index"]
        .mean()
        .rename(columns={"new_home_price_index": "house_price"})
    )
    annual["source"] = (
        "NBS 70-city new home price index (GitHub mirror: "
        "changao1/70-China-cities-housing-index-data)"
    )
    annual["source_url"] = HOUSING_ALT_URL
    annual["source_file"] = str(fallback_csv)

    raw = pd.read_csv(primary_csv, encoding="utf-8-sig")
    raw["year"] = pd.to_datetime(raw["DATE"]).dt.year
    target_cities = set(CITY_NAME_ZH.values())
    subset = raw[
        raw["CITY"].isin(target_cities)
        & (raw["FixedBase"] == "定基比")
        & raw["CommodityHouseIDX"].notna()
    ].copy()
    if subset.empty:
        subset = raw[
            raw["CITY"].isin(target_cities)
            & (raw["FixedBase"] == "同比")
            & raw["CommodityHouseIDX"].notna()
        ].copy()

    fallback = (
        subset.groupby(["CITY", "year"], as_index=False)["CommodityHouseIDX"]
        .mean()
        .rename(columns={"CITY": "city_zh", "CommodityHouseIDX": "house_price"})
    )
    fallback["city"] = fallback["city_zh"].map(CITY_NAME_EN)
    fallback = fallback[fallback["city"].notna() & fallback["year"].isin(YEARS + [2020])]
    fallback["source"] = (
        "NBS 70-city commodity housing price index "
        "(GitHub mirror: hugohe3/70cityprice)"
    )
    fallback["source_url"] = HOUSING_URL
    fallback["source_file"] = str(primary_csv)

    combined = pd.concat([annual, fallback], ignore_index=True)
    return combined.sort_values(["city", "year"]).drop_duplicates(
        ["city", "year"], keep="first"
    )


def _find_city_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        col_text = str(col)
        if any(key in col_text for key in ("城市", "地区", "City")):
            return col
    return None


def _extract_city_metric(table: pd.DataFrame, city_col: str, city_zh: str) -> float | None:
    city_rows = table[table[city_col].astype(str).str.contains(city_zh, na=False)]
    if city_rows.empty:
        return None

    row = city_rows.iloc[0]
    for value in row.iloc[1:]:
        if pd.isna(value) or str(value).strip() in {"", "-", "…"}:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def parse_yearbook_excel(path: Path, data_year: int) -> pd.DataFrame:
    """解析单本年鉴 Excel，提取样本城市指标。"""
    records: dict[tuple[str, int], dict] = {}
    xls = pd.ExcelFile(path)

    for sheet in xls.sheet_names:
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        if raw.empty:
            continue

        sheet_text = str(sheet)
        matched_metrics = [
            metric
            for metric, keywords in YEARBOOK_KEYWORDS.items()
            if any(keyword in sheet_text for keyword in keywords)
        ]
        if not matched_metrics:
            joined = raw.head(5).astype(str).apply(lambda col: "".join(col), axis=0).str.cat(sep="")
            matched_metrics = [
                metric
                for metric, keywords in YEARBOOK_KEYWORDS.items()
                if any(keyword in joined for keyword in keywords)
            ]
        if not matched_metrics:
            continue

        header_row = None
        for idx in range(min(10, len(raw))):
            row = raw.iloc[idx].astype(str)
            if row.str.contains("城市|地区", na=False).any():
                header_row = idx
                break
        if header_row is None:
            continue

        table = pd.read_excel(path, sheet_name=sheet, header=header_row)
        city_col = _find_city_column(table)
        if city_col is None:
            continue

        for city_en, city_zh in CITY_NAME_ZH.items():
            key = (city_en, data_year)
            record = records.setdefault(
                key,
                {
                    "city": city_en,
                    "year": data_year,
                    "source": path.name,
                    "source_url": "",
                    "source_file": str(path),
                },
            )
            for metric in matched_metrics:
                value = _extract_city_metric(table, city_col, city_zh)
                if value is not None:
                    record[metric] = value

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records.values())


def infer_data_year_from_filename(path: Path) -> int | None:
    match = re.search(r"(20\d{2})", path.stem)
    if not match:
        return None
    yearbook_edition = int(match.group(1))
    return yearbook_edition - 1


def load_yearbook_panel() -> pd.DataFrame:
    if not YEARBOOK_DIR.exists():
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for path in sorted(YEARBOOK_DIR.glob("*.xls*")):
        data_year = infer_data_year_from_filename(path)
        if data_year is None:
            continue
        parsed = parse_yearbook_excel(path, data_year)
        if not parsed.empty:
            frames.append(parsed)

    if not frames:
        return pd.DataFrame()
    panel = pd.concat(frames, ignore_index=True)
    return panel.sort_values(["city", "year"]).drop_duplicates(["city", "year"], keep="last")


def fetch_nbs_city_series(zbcode: str, city_en: str, years: list[int]) -> pd.DataFrame:
    """尝试从国家统计局 easyquery 获取城市年度序列。"""
    try:
        from cnstats.stats import stats
    except ImportError as exc:
        raise RuntimeError("cn-stats 未安装") from exc

    regcode = CITY_REGCODE[city_en]
    rows = []
    for year in years:
        try:
            result = stats(zbcode=zbcode, datestr=str(year), regcode=regcode, dbcode="csnd")
        except Exception:
            continue
        if result is None or result.empty:
            continue
        value = pd.to_numeric(result.iloc[0, -1], errors="coerce")
        if pd.notna(value):
            rows.append({"city": city_en, "year": year, "value": float(value)})
    return pd.DataFrame(rows)


def try_fetch_nbs_panel() -> pd.DataFrame:
    """在国家统计局接口可用时补充官方数据。"""
    metric_codes = {
        "gdp_per_capita": "A020102",
        "disposable_income": "A0A0101",
        "population": "A030101",
    }
    frames = []
    for city in ALL_CITIES:
        for metric, zbcode in metric_codes.items():
            try:
                series = fetch_nbs_city_series(zbcode, city, YEARS + [2020])
            except Exception:
                return pd.DataFrame()
            if series.empty:
                continue
            series = series.rename(columns={"value": metric})
            frames.append(series)

    if not frames:
        return pd.DataFrame()

    panel = frames[0]
    for frame in frames[1:]:
        panel = panel.merge(frame, on=["city", "year"], how="outer")
    panel["source"] = "National Bureau of Statistics easyquery (csnd)"
    panel["source_url"] = "https://data.stats.gov.cn/easyquery.htm"
    panel["source_file"] = ""
    return panel


def load_university_counts() -> pd.DataFrame:
    """使用项目内置高校数量表；后续可替换为教育部名单自动统计。"""
    counts = pd.DataFrame(
        [
            {"city": "Beijing", "university_resource": 92},
            {"city": "Shanghai", "university_resource": 64},
            {"city": "Guangzhou", "university_resource": 83},
            {"city": "Wuhan", "university_resource": 89},
            {"city": "Nanjing", "university_resource": 53},
            {"city": "Xi'an", "university_resource": 63},
            {"city": "Chengdu", "university_resource": 58},
            {"city": "Chongqing", "university_resource": 69},
            {"city": "Hangzhou", "university_resource": 47},
            {"city": "Changsha", "university_resource": 57},
            {"city": "Harbin", "university_resource": 51},
            {"city": "Shenyang", "university_resource": 47},
            {"city": "Qingdao", "university_resource": 24},
            {"city": "Zhengzhou", "university_resource": 65},
            {"city": "Kunming", "university_resource": 49},
            {"city": "Nanchang", "university_resource": 53},
            {"city": "Hefei", "university_resource": 54},
            {"city": "Shenzhen", "university_resource": 8},
            {"city": "Suzhou", "university_resource": 25},
            {"city": "Xiamen", "university_resource": 16},
        ]
    )
    counts["source"] = "Ministry of Education university list (manual count, 2025)"
    counts["source_url"] = "https://www.moe.gov.cn/"
    counts["source_file"] = ""
    return counts


def _is_official_url(url: str) -> bool:
    if not url:
        return True
    unofficial_markers = ("hongheiku.com", "tjnj.net", "githubusercontent.com")
    return not any(marker in url for marker in unofficial_markers)


def _frame_to_observations(
    frame: pd.DataFrame,
    *,
    source_type: str,
    extraction_method: str,
    is_official_source: bool,
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=SOURCE_OBSERVATION_COLUMNS)

    metric_columns = metrics or [
        col for col in frame.columns if col not in SOURCE_COLUMNS and col not in {"city_zh"}
    ]
    records = []
    for _, row in frame.iterrows():
        for metric in metric_columns:
            if metric not in frame.columns or pd.isna(row.get(metric)):
                continue
            source_url = row.get("source_url", "")
            official = bool(is_official_source) and _is_official_url(str(source_url))
            records.append(
                {
                    "city": row["city"],
                    "year": int(row["year"]),
                    "metric": metric,
                    "value": float(row[metric]),
                    "unit": METRIC_UNITS.get(metric, ""),
                    "source_type": source_type,
                    "source_name": row.get("source", source_type),
                    "source_url": source_url,
                    "source_file": row.get("source_file", ""),
                    "extraction_method": extraction_method,
                    "is_official_source": official,
                    "notes": (
                        "" if official else "third-party mirror; verify against official source"
                    ),
                }
            )
    return pd.DataFrame(records, columns=SOURCE_OBSERVATION_COLUMNS)


def load_manual_source_observations() -> pd.DataFrame:
    """读取人工核验后的来源观测长表。"""
    if not MANUAL_SOURCE_OBSERVATIONS_FILE.exists():
        return pd.DataFrame(columns=SOURCE_OBSERVATION_COLUMNS)
    observations = pd.read_csv(MANUAL_SOURCE_OBSERVATIONS_FILE)
    for column in SOURCE_OBSERVATION_COLUMNS:
        if column not in observations.columns:
            observations[column] = ""
    return observations[SOURCE_OBSERVATION_COLUMNS]


def build_source_observations(
    yearbook: pd.DataFrame,
    nbs: pd.DataFrame,
    communiques: pd.DataFrame,
    housing: pd.DataFrame,
    universities: pd.DataFrame,
) -> pd.DataFrame:
    frames = [
        _frame_to_observations(
            yearbook,
            source_type="yearbook",
            extraction_method="excel",
            is_official_source=True,
        ),
        _frame_to_observations(
            nbs,
            source_type="nbs_api",
            extraction_method="api",
            is_official_source=True,
        ),
        _frame_to_observations(
            communiques,
            source_type="communique",
            extraction_method="regex_or_ocr",
            is_official_source=True,
        ),
        _frame_to_observations(
            housing,
            source_type="nbs_housing_index",
            extraction_method="csv_annual_mean",
            is_official_source=True,
            metrics=["house_price"],
        ),
    ]

    university_frames = []
    for year in YEARS:
        frame = universities.copy()
        frame["year"] = year
        university_frames.append(frame)
    university_panel = pd.concat(university_frames, ignore_index=True)
    frames.append(
        _frame_to_observations(
            university_panel,
            source_type="moe_list",
            extraction_method="manual_count",
            is_official_source=True,
            metrics=["university_resource"],
        )
    )

    manual = load_manual_source_observations()
    if not manual.empty:
        frames.append(manual)

    observations = pd.concat(frames, ignore_index=True)
    if observations.empty:
        return observations
    observations["_manual_priority"] = observations["extraction_method"].eq("manual_web")
    observations = observations.sort_values(
        ["city", "year", "metric", "is_official_source", "_manual_priority"],
        ascending=[True, True, True, False, False],
    )
    observations = observations.drop_duplicates(["city", "year", "metric"], keep="first")
    return observations.drop(columns="_manual_priority")


def build_source_documents(*frames: pd.DataFrame) -> pd.DataFrame:
    records = []
    seen = set()
    for frame in frames:
        if frame.empty:
            continue
        for _, row in frame.iterrows():
            key = (
                row.get("source", ""),
                row.get("source_url", ""),
                row.get("source_file", ""),
                row.get("city", ""),
                row.get("year", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "source_id": f"src_{len(records) + 1:04d}",
                    "source_type": "document",
                    "city": row.get("city", ""),
                    "year": row.get("year", ""),
                    "url": row.get("source_url", ""),
                    "local_path": row.get("source_file", ""),
                    "is_official_source": True,
                    "fetch_status": "available",
                    "notes": row.get("source", ""),
                }
            )
    return pd.DataFrame(records)


def build_wide_panel(observations: pd.DataFrame) -> pd.DataFrame:
    rows = [(city, year) for city in ALL_CITIES for year in YEARS]
    panel = pd.DataFrame(rows, columns=["city", "year"])
    if observations.empty:
        return panel

    wide = observations.pivot_table(
        index=["city", "year"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    panel = panel.merge(wide, on=["city", "year"], how="left")

    if "gdp_total" in panel.columns and "population" in panel.columns:
        can_derive_gdp_pc = (
            panel["gdp_per_capita"].isna()
            & panel["gdp_total"].notna()
            & panel["population"].notna()
            & panel["population"].ne(0)
        )
        panel.loc[can_derive_gdp_pc, "gdp_per_capita"] = (
            panel.loc[can_derive_gdp_pc, "gdp_total"] * 100000000
        ) / panel.loc[can_derive_gdp_pc, "population"]

    if "housing_sales_area" in panel.columns and "housing_sales_value" in panel.columns:
        can_derive_hp = (
            panel["house_price"].isna()
            & panel["housing_sales_area"].notna()
            & panel["housing_sales_value"].notna()
            & panel["housing_sales_area"].ne(0)
        )
        panel.loc[can_derive_hp, "house_price"] = (
            panel.loc[can_derive_hp, "housing_sales_value"] * 10000
        ) / panel.loc[can_derive_hp, "housing_sales_area"]

    if "rd_expenditure" in panel.columns:
        panel["innovation_index"] = panel["rd_expenditure"]
    else:
        panel["innovation_index"] = pd.NA

    population = observations[observations["metric"] == "population"].copy()
    if not population.empty:
        pop = population.pivot_table(
            index="city",
            columns="year",
            values="value",
            aggfunc="first",
        )
        for idx, row in panel.iterrows():
            city = row["city"]
            year = row["year"]
            if city in pop.index and year in pop.columns and (year - 1) in pop.columns:
                current = pop.loc[city, year]
                previous = pop.loc[city, year - 1]
                if pd.notna(current) and pd.notna(previous) and previous != 0:
                    panel.loc[idx, "population_growth"] = current / previous - 1

    if "house_price" in panel.columns and "disposable_income" in panel.columns:
        can_derive = panel["house_price"].notna() & panel["disposable_income"].notna()
        panel.loc[can_derive, "housing_burden"] = (
            panel.loc[can_derive, "house_price"] / panel.loc[can_derive, "disposable_income"]
        )

    expected_columns = [
        "city",
        "year",
        "gdp_per_capita",
        "gdp_total",
        "disposable_income",
        "population",
        "house_price",
        "housing_burden",
        "housing_sales_area",
        "housing_sales_value",
        "population_growth",
        "university_resource",
        "innovation_index",
    ]
    for column in expected_columns:
        if column not in panel.columns:
            panel[column] = pd.NA
    return panel[expected_columns]


def build_missing_data_report(observations: pd.DataFrame) -> pd.DataFrame:
    observed = set(
        zip(
            observations["city"],
            observations["year"].astype(int),
            observations["metric"],
            strict=False,
        )
    )
    derived_gdp_per_capita = set()
    gdp_total = observations[observations["metric"] == "gdp_total"]
    population = observations[observations["metric"] == "population"]
    if not gdp_total.empty and not population.empty:
        gdp_keys = set(zip(gdp_total["city"], gdp_total["year"].astype(int), strict=False))
        pop_keys = set(zip(population["city"], population["year"].astype(int), strict=False))
        derived_gdp_per_capita = gdp_keys & pop_keys

    derived_house_price = set()
    hsa = observations[observations["metric"] == "housing_sales_area"]
    hsv = observations[observations["metric"] == "housing_sales_value"]
    if not hsa.empty and not hsv.empty:
        hsa_keys = set(zip(hsa["city"], hsa["year"].astype(int), strict=False))
        hsv_keys = set(zip(hsv["city"], hsv["year"].astype(int), strict=False))
        derived_house_price = hsa_keys & hsv_keys
    records = []
    for metric, years in TARGET_METRICS.items():
        for city in ALL_CITIES:
            for year in years:
                if (city, year, metric) in observed:
                    continue
                if metric == "gdp_per_capita" and (city, year) in derived_gdp_per_capita:
                    continue
                if metric == "house_price" and (city, year) in derived_house_price:
                    continue
                status = "not_found"
                explanation = "Official source value not found in current source files"
                if metric == "house_price":
                    status = "not_applicable"
                    explanation = (
                        "Not covered by bundled NBS 70-city housing index or source unavailable"
                    )
                records.append(
                    {
                        "city": city,
                        "year": year,
                        "metric": metric,
                        "status": status,
                        "attempted_sources": "communique/yearbook/nbs_api/external_csv",
                        "explanation": explanation,
                    }
                )
    return pd.DataFrame(records)


def write_outputs(
    panel: pd.DataFrame,
    housing: pd.DataFrame,
    observations: pd.DataFrame,
    documents: pd.DataFrame,
    missing: pd.DataFrame,
) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    observations.to_csv(SOURCE_OBSERVATIONS_FILE, index=False)
    documents.to_csv(SOURCE_DOCUMENTS_FILE, index=False)
    missing.to_csv(MISSING_DATA_REPORT_FILE, index=False)
    panel.to_csv(PANEL_FILE, index=False)

    sources = observations[
        ["city", "year", "metric", "source_name", "source_url", "source_file", "notes"]
    ].drop_duplicates()
    sources.to_csv(SOURCES_FILE, index=False)
    housing.to_csv(HOUSING_ANNUAL_FILE, index=False)


def print_status(panel: pd.DataFrame, observations: pd.DataFrame, missing: pd.DataFrame) -> None:
    total = len(panel)
    metrics = [
        "gdp_per_capita",
        "disposable_income",
        "house_price",
        "population_growth",
        "innovation_index",
        "university_resource",
    ]
    print(f"Saved: {PANEL_FILE}")
    print(f"Rows: {total}")
    for metric in metrics:
        if metric not in panel.columns:
            print(f"- {metric}: 0/{total}")
            continue
        filled = panel[metric].notna().sum()
        print(f"- {metric}: {filled}/{total}")

    print(f"Source observations: {len(observations)}")
    print(f"Missing report rows: {len(missing)}")
    if not missing.empty:
        print(missing.groupby("metric").size())


def main() -> None:
    print("Downloading external datasets...")
    files = download_external_files()
    housing = build_annual_housing_index(files["housing_70city"], files["housing_alt"])

    print("Loading yearbook files from data/raw/yearbooks/ ...")
    yearbook = load_yearbook_panel()
    if yearbook.empty:
        print("No yearbook Excel found. Place files in data/raw/yearbooks/ and rerun.")

    print("Trying National Bureau of Statistics API...")
    nbs = try_fetch_nbs_panel()
    if nbs.empty:
        print("NBS API unavailable from current network. Skipping official online fetch.")

    print("Fetching city statistical communiques...")
    communiques = fetch_communique_panel()
    if communiques.empty:
        print("No communique data fetched.")
    else:
        communiques.to_csv(RAW_DATA_DIR / "communique_panel.csv", index=False)
        print(f"Communique rows fetched: {len(communiques)}")

    universities = load_university_counts()
    observations = build_source_observations(yearbook, nbs, communiques, housing, universities)
    documents = build_source_documents(yearbook, nbs, communiques, housing, universities)
    panel = build_wide_panel(observations)
    missing = build_missing_data_report(observations)
    write_outputs(panel, housing, observations, documents, missing)
    print_status(panel, observations, missing)


if __name__ == "__main__":
    main()
