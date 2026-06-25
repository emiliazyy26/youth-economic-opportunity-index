"""Download and integrate project raw data."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

from yei.city_names import CITY_NAME_EN, CITY_NAME_ZH, CITY_REGCODE
from yei.communique_fetch import fetch_communique_panel
from yei.config import (
    ALL_CITIES,
    HIGH_TECH_COMPANIES_FILE,
    HOUSING_ANNUAL_FILE,
    INTERIM_DATA_DIR,
    LISTED_COMPANIES_FILE,
    MISSING_DATA_REPORT_FILE,
    RAW_DATA_DIR,
    SOURCE_DOCUMENTS_FILE,
    SOURCE_OBSERVATION_COLUMNS,
    SOURCE_OBSERVATIONS_FILE,
    SUPPLEMENTARY_TARGET_METRICS,
    TARGET_METRICS,
    YEARS,
    YOUTH_PLATFORM_FILE,
)
from yei.data_quality import classify_missing_metric, metric_tier
from yei.house_price_yuan import (
    build_house_price_yuan_sqm,
    load_house_price_yuan_sqm,
    save_house_price_yuan_sqm,
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

# Common metric keywords in China City Statistical Yearbook Excel files
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
    "house_price": "yuan/sqm",
    "weighted_university_score": "quality_score",
    "rd_expenditure": "100 million yuan",
    "science_technology_expenditure": "100 million yuan",
    "housing_sales_area": "10000 sqm",
    "housing_sales_value": "100 million yuan",
    "tertiary_value": "100 million yuan",
    "tertiary_ratio": "percent",
    "listed_company_count": "count",
    "high_tech_company_count": "count",
    "job_posting_count": "count",
    "entry_salary": "yuan/person/year",
    "rent_monthly": "yuan/month",
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
    """Aggregate 70-city monthly housing price index into annual values."""
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


def ensure_house_price_yuan_sqm() -> pd.DataFrame:
    """Load or fetch yuan/sqm new home average prices (unified caliber for 20 cities)."""
    housing = load_house_price_yuan_sqm()
    expected_rows = len(ALL_CITIES) * len(YEARS)
    if len(housing) >= expected_rows:
        return housing

    print("Fetching house_price (yuan/sqm) from gotohui ...")
    fetched = build_house_price_yuan_sqm()
    if fetched.empty:
        return housing
    save_house_price_yuan_sqm(fetched)
    return fetched


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
    """Parse a single yearbook Excel file and extract sample city metrics."""
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
    """Attempt to fetch city annual series from NBS easyquery API."""
    try:
        from cnstats.stats import stats
    except ImportError as exc:
        raise RuntimeError("cn-stats not installed") from exc

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
    """Supplement with official data from NBS API when available."""
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


def load_listed_company_counts() -> pd.DataFrame:
    """Load A-share listed company domicile counts (Tier B institutional data, treated as stable within a year)."""
    if not LISTED_COMPANIES_FILE.exists():
        return pd.DataFrame(columns=["city", "year", "listed_company_count"])

    raw = pd.read_csv(LISTED_COMPANIES_FILE)
    rows = []
    for city in ALL_CITIES:
        match = raw[raw["city"] == city]
        if match.empty:
            continue
        count = float(match.iloc[0]["listed_company_count"])
        for year in YEARS:
            rows.append({"city": city, "year": year, "listed_company_count": count})
    return pd.DataFrame(rows)


def load_high_tech_company_observations() -> pd.DataFrame:
    """Convert high-tech company counts to source observations (year-specific)."""
    if not HIGH_TECH_COMPANIES_FILE.exists():
        return pd.DataFrame(columns=SOURCE_OBSERVATION_COLUMNS)

    raw = pd.read_csv(HIGH_TECH_COMPANIES_FILE)
    records = []
    for _, row in raw.iterrows():
        city = row["city"]
        if city not in ALL_CITIES:
            continue
        records.append(
            {
                "city": city,
                "year": int(row["year"]),
                "metric": "high_tech_company_count",
                "value": float(row["high_tech_company_count"]),
                "unit": METRIC_UNITS["high_tech_company_count"],
                "source_type": "science_bureau",
                "source_name": row.get("source_name", "Torch Center / science bureau"),
                "source_url": row.get("source_url", ""),
                "source_file": str(HIGH_TECH_COMPANIES_FILE),
                "extraction_method": "manual_csv",
                "is_official_source": False,
                "notes": row.get("notes", ""),
            }
        )
    return pd.DataFrame(records, columns=SOURCE_OBSERVATION_COLUMNS)


def load_youth_platform_observations() -> pd.DataFrame:
    """Load platform samples for recruitment/entry salary/rent (Tier C), convert to source observations.

    If the CSV contains a 'year' column with year-specific rows, use them directly
    for job_posting_count and entry_salary. For rent_monthly (which lacks year
    variation), apply the snapshot across all years.
    """
    if not YOUTH_PLATFORM_FILE.exists():
        return pd.DataFrame(columns=SOURCE_OBSERVATION_COLUMNS)

    raw = pd.read_csv(YOUTH_PLATFORM_FILE)
    records = []
    year_specific_metrics = {"job_posting_count", "entry_salary"}
    snapshot_metrics = {"rent_monthly"}

    has_year_col = "year" in raw.columns

    for _, row in raw.iterrows():
        city = row["city"]
        row_year = int(row["year"]) if has_year_col and not pd.isna(row.get("year")) else None

        for metric in year_specific_metrics | snapshot_metrics:
            value = row.get(metric)
            if pd.isna(value) or value == "":
                continue

            if metric in year_specific_metrics and has_year_col and row_year is not None:
                # Use year-specific value directly
                records.append(
                    {
                        "city": city,
                        "year": row_year,
                        "metric": metric,
                        "value": float(value),
                        "unit": METRIC_UNITS.get(metric, ""),
                        "source_type": "platform_sample",
                        "source_name": row.get("source_name", "platform_sample"),
                        "source_url": row.get("source_url", ""),
                        "source_file": str(YOUTH_PLATFORM_FILE),
                        "extraction_method": "manual_csv",
                        "is_official_source": False,
                        "notes": row.get("notes", ""),
                    }
                )
            elif metric in snapshot_metrics:
                # Apply snapshot across all years
                for year in YEARS:
                    records.append(
                        {
                            "city": city,
                            "year": year,
                            "metric": metric,
                            "value": float(value),
                            "unit": METRIC_UNITS.get(metric, ""),
                            "source_type": "platform_sample",
                            "source_name": row.get("source_name", "platform_sample"),
                            "source_url": row.get("source_url", ""),
                            "source_file": str(YOUTH_PLATFORM_FILE),
                            "extraction_method": "manual_csv",
                            "is_official_source": False,
                            "notes": (
                                f"{row.get('notes', '')}; snapshot_year={row_year or 'unknown'}"
                            ).strip("; "),
                        }
                    )
    return pd.DataFrame(records, columns=SOURCE_OBSERVATION_COLUMNS)


def load_listed_company_observations() -> pd.DataFrame:
    """Convert listed company counts to source observations."""
    if not LISTED_COMPANIES_FILE.exists():
        return pd.DataFrame(columns=SOURCE_OBSERVATION_COLUMNS)

    raw = pd.read_csv(LISTED_COMPANIES_FILE)
    records = []
    for _, row in raw.iterrows():
        city = row["city"]
        if city not in ALL_CITIES:
            continue
        for year in YEARS:
            records.append(
                {
                    "city": city,
                    "year": year,
                    "metric": "listed_company_count",
                    "value": float(row["listed_company_count"]),
                    "unit": METRIC_UNITS["listed_company_count"],
                    "source_type": "stock_exchange",
                    "source_name": row.get("source_name", "A-share listing domicile"),
                    "source_url": row.get("source_url", ""),
                    "source_file": str(LISTED_COMPANIES_FILE),
                    "extraction_method": "manual_csv",
                    "is_official_source": False,
                    "notes": row.get("notes", ""),
                }
            )
    return pd.DataFrame(records, columns=SOURCE_OBSERVATION_COLUMNS)


def load_university_counts() -> pd.DataFrame:
    """Return quality-weighted university scores for each city (985x5 + 211x2.5 + other standard universities x0.3).

    The 985/211 lists are based on historical MOE designations; standard university counts come from the 2025 MOE university list.
    """
    # (985 count, 211 non-985 count, other standard university count)
    _uni_data: dict[str, tuple[int, int, int]] = {
        "Beijing":      (8, 18, 66),   # 92 total - 8 985 - 18 211 = 66 other
        "Shanghai":     (4,  6, 54),   # 64 total
        "Nanjing":      (2,  6, 45),   # 53 total
        "Wuhan":        (2,  5, 82),   # 89 total
        "Xi'an":        (2,  5, 56),   # 63 total (NW A&F in Yangling not counted)
        "Guangzhou":    (2,  2, 79),   # 83 total
        "Changsha":     (3,  1, 53),   # 57 total (incl. NUDT)
        "Chengdu":      (2,  2, 54),   # 58 total
        "Hangzhou":     (1,  0, 46),   # 47 total
        "Harbin":       (1,  3, 47),   # 51 total
        "Hefei":        (1,  2, 51),   # 54 total
        "Chongqing":    (1,  1, 67),   # 69 total
        "Shenyang":     (1,  1, 45),   # 47 total
        "Qingdao":      (1,  1, 22),   # 24 total
        "Xiamen":       (1,  0, 15),   # 16 total
        "Zhengzhou":    (0,  1, 64),   # 65 total
        "Suzhou":       (0,  1, 24),   # 25 total
        "Kunming":      (0,  1, 48),   # 49 total
        "Nanchang":     (0,  1, 52),   # 53 total
        "Shenzhen":     (0,  0,  8),   # 8 total
    }
    rows = []
    for city, (n985, n211, nother) in _uni_data.items():
        quality = n985 * 5.0 + n211 * 2.5 + nother * 0.3
        rows.append({"city": city, "weighted_university_score": round(quality, 1)})

    counts = pd.DataFrame(rows)
    counts["source"] = "Ministry of Education university list (quality-weighted, 2025)"
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
    """Load manually verified source observations (long format)."""
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
            source_type="third_party_index",
            extraction_method="web_annual_mean",
            is_official_source=False,
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
            metrics=["weighted_university_score"],
        )
    )

    manual = load_manual_source_observations()
    if not manual.empty:
        frames.append(manual)

    listed = load_listed_company_observations()
    if not listed.empty:
        frames.append(listed)

    high_tech = load_high_tech_company_observations()
    if not high_tech.empty:
        frames.append(high_tech)

    youth = load_youth_platform_observations()
    if not youth.empty:
        frames.append(youth)

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

    if "rent_monthly" in panel.columns and "disposable_income" in panel.columns:
        can_derive_rent = (
            panel["rent_monthly"].notna()
            & panel["disposable_income"].notna()
            & panel["disposable_income"].ne(0)
        )
        panel.loc[can_derive_rent, "rent_burden"] = (
            panel.loc[can_derive_rent, "rent_monthly"] * 12
            / panel.loc[can_derive_rent, "disposable_income"]
        )

    # Derive tertiary_ratio from tertiary_value / gdp_total for rows missing it
    if "tertiary_value" in panel.columns and "gdp_total" in panel.columns:
        can_derive_tr = (
            panel["tertiary_ratio"].isna()
            & panel["tertiary_value"].notna()
            & panel["gdp_total"].notna()
            & panel["gdp_total"].ne(0)
        )
        panel.loc[can_derive_tr, "tertiary_ratio"] = (
            panel.loc[can_derive_tr, "tertiary_value"]
            / panel.loc[can_derive_tr, "gdp_total"]
            * 100
        )

    # Linear interpolation for remaining gaps (tertiary structure changes slowly)
    if "tertiary_ratio" in panel.columns:
        panel["tertiary_ratio"] = pd.to_numeric(panel["tertiary_ratio"], errors="coerce")
        panel["tertiary_ratio"] = panel.groupby("city")["tertiary_ratio"].transform(
            lambda s: s.interpolate(method="linear", limit_direction="both")
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
        "weighted_university_score",
        "tertiary_ratio",
        "rd_expenditure",
        "innovation_index",
        "listed_company_count",
        "high_tech_company_count",
        "job_posting_count",
        "entry_salary",
        "rent_monthly",
        "rent_burden",
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

    # Derive tertiary_ratio from tertiary_value / gdp_total
    derived_tertiary_ratio = set()
    tertiary_value = observations[observations["metric"] == "tertiary_value"]
    if not tertiary_value.empty and not gdp_total.empty:
        tv_keys = set(zip(tertiary_value["city"], tertiary_value["year"].astype(int), strict=False))
        gdp_keys = set(zip(gdp_total["city"], gdp_total["year"].astype(int), strict=False))
        derived_tertiary_ratio = tv_keys & gdp_keys

    # Cities with at least one tertiary_ratio (observed or derived) can interpolate all gaps
    tertiary_ratio_cities = set()
    tr_obs = observations[observations["metric"] == "tertiary_ratio"]
    if not tr_obs.empty:
        tertiary_ratio_cities.update(tr_obs["city"].unique())
    tertiary_ratio_cities.update(c for c, _ in derived_tertiary_ratio)

    records = []
    all_targets = {**TARGET_METRICS, **SUPPLEMENTARY_TARGET_METRICS}
    for metric, years in all_targets.items():
        for city in ALL_CITIES:
            for year in years:
                if (city, year, metric) in observed:
                    continue
                if metric == "gdp_per_capita" and (city, year) in derived_gdp_per_capita:
                    continue
                if metric == "house_price" and (city, year) in derived_house_price:
                    continue
                if metric == "tertiary_ratio" and (city, year) in derived_tertiary_ratio:
                    continue
                if metric == "tertiary_ratio" and city in tertiary_ratio_cities:
                    continue
                tier = metric_tier(metric)
                category = classify_missing_metric(metric)
                status = "not_found"
                explanation = "Official source value not found in current source files"
                if metric == "house_price":
                    status = "not_applicable"
                    explanation = (
                        "Not covered by bundled yuan/sqm house price file or source unavailable"
                    )
                if metric in {"job_posting_count", "entry_salary"}:
                    explanation = (
                        "Platform sample not yet collected; dimension uses fallback metric"
                    )
                records.append(
                    {
                        "city": city,
                        "year": year,
                        "metric": metric,
                        "data_tier": tier,
                        "category": category,
                        "status": status,
                        "attempted_sources": "communique/yearbook/nbs_api/external_csv/platform",
                        "explanation": explanation,
                    }
                )
    columns = [
        "city",
        "year",
        "metric",
        "data_tier",
        "category",
        "status",
        "attempted_sources",
        "explanation",
    ]
    return pd.DataFrame(records, columns=columns)


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
        "weighted_university_score",
        "listed_company_count",
        "high_tech_company_count",
        "rent_burden",
        "job_posting_count",
        "entry_salary",
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
    housing_index = build_annual_housing_index(files["housing_70city"], files["housing_alt"])
    housing = ensure_house_price_yuan_sqm()
    if housing.empty:
        print("WARN: yuan/sqm house prices unavailable; falling back to NBS index.")
        housing = housing_index
    else:
        housing_index.to_csv(EXTERNAL_DIR / "house_price_nbs_index.csv", index=False)

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
