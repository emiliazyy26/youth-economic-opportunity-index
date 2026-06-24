"""Standardize city house_price to yuan/sqm (China Index Academy 100-city / gotohui new home average price)."""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests

from yei.config import ALL_CITIES, RAW_DATA_DIR, YEARS

HOUSE_PRICE_YUAN_FILE = RAW_DATA_DIR / "external" / "house_price_yuan_sqm.csv"
GOTOHUI_BASE = "https://fangjia.gotohui.com/years"

# gotohui city IDs (new home yuan/sqm, consistent with Suzhou's existing caliber)
GOTOHUI_CITY_IDS: dict[str, int] = {
    "Beijing": 1,
    "Shanghai": 3,
    "Guangzhou": 3770,
    "Shenzhen": 49,
    "Hangzhou": 3759,
    "Nanjing": 78,
    "Suzhou": 81,
    "Chengdu": 300,
    "Wuhan": 168,
    "Xi'an": 274,
    "Chongqing": 6,
    "Hefei": 91,
    "Changsha": 181,
    "Qingdao": 247,
    "Xiamen": 3792,
    "Zhengzhou": 3849,
    "Harbin": 156,
    "Shenyang": 215,
    "Kunming": 284,
    "Nanchang": 204,
}

SOURCE_NAME = "China Index Academy 100-city new home price (gotohui annual mean, yuan/sqm)"
SOURCE_URL = "https://fangjia.gotohui.com/"


def _parse_year_page(html: str) -> list[float]:
    """Parse monthly new home average prices (yuan/sqm) from the annual page."""
    rows = re.findall(r"<tr><td>(\d+月)</td>(.*?)</tr>", html, flags=re.DOTALL)
    values: list[float] = []
    for _, cells in rows:
        prices = re.findall(r"<td>([\d,]+)<span[^>]*>元/㎡</span></td>", cells)
        if len(prices) >= 2:
            values.append(float(prices[1].replace(",", "")))
        elif len(prices) == 1:
            values.append(float(prices[0].replace(",", "")))

    if values:
        return values

    markdown_rows = re.findall(
        r"\|\s*\d+月\s*\|\s*[\d,]+元/㎡\s*\|\s*([\d,]+)元/㎡",
        html,
    )
    return [float(v.replace(",", "")) for v in markdown_rows]


def fetch_city_year_new_home_price(
    city_id: int, year: int, *, session: requests.Session
) -> float | None:
    url = f"{GOTOHUI_BASE}/{city_id}/{year}/"
    response = session.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    monthly = _parse_year_page(response.text)
    if not monthly:
        return None
    return sum(monthly) / len(monthly)


def build_house_price_yuan_sqm(
    years: list[int] | None = None,
    *,
    sleep_seconds: float = 0.3,
) -> pd.DataFrame:
    """Fetch annual new home average prices (yuan/sqm) for each city and year."""
    target_years = years or YEARS
    session = requests.Session()
    records: list[dict] = []

    for city in ALL_CITIES:
        city_id = GOTOHUI_CITY_IDS[city]
        for year in target_years:
            price = fetch_city_year_new_home_price(city_id, year, session=session)
            if price is None:
                continue
            records.append(
                {
                    "city": city,
                    "year": year,
                    "house_price": price,
                    "source": SOURCE_NAME,
                    "source_url": f"{GOTOHUI_BASE}/{city_id}/{year}/",
                    "source_file": str(HOUSE_PRICE_YUAN_FILE),
                }
            )
            if sleep_seconds:
                time.sleep(sleep_seconds)

    return pd.DataFrame(records)


def load_house_price_yuan_sqm(path: Path | None = None) -> pd.DataFrame:
    csv_path = path or HOUSE_PRICE_YUAN_FILE
    if not csv_path.exists():
        return pd.DataFrame(
            columns=["city", "year", "house_price", "source", "source_url", "source_file"]
        )
    return pd.read_csv(csv_path)


def save_house_price_yuan_sqm(df: pd.DataFrame, path: Path | None = None) -> Path:
    csv_path = path or HOUSE_PRICE_YUAN_FILE
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return csv_path
