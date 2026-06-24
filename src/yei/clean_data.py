"""Data cleaning and field derivation."""

from pathlib import Path

import pandas as pd

from yei.config import CITY_DATA_FILE, RAW_COLUMNS, RAW_DATA_DIR


def load_raw_data(path: Path | None = None) -> pd.DataFrame:
    """Load the main data table from the raw directory."""
    data_path = path or RAW_DATA_DIR / "city_panel.csv"
    if not data_path.exists():
        raise FileNotFoundError(
            f"Raw data not found: {data_path}\n"
            "Please save collected data as data/raw/city_panel.csv first"
        )

    df = pd.read_csv(data_path)
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")

    return df


def derive_housing_burden(df: pd.DataFrame) -> pd.DataFrame:
    """Housing burden = house_price / disposable_income (fill missing values row-wise)."""
    result = df.copy()
    can_derive = (
        result["housing_burden"].isna()
        & result["house_price"].notna()
        & result["disposable_income"].notna()
    )
    result.loc[can_derive, "housing_burden"] = (
        result.loc[can_derive, "house_price"] / result.loc[can_derive, "disposable_income"]
    )
    return result


def derive_rent_burden(df: pd.DataFrame) -> pd.DataFrame:
    """Rent burden = monthly_rent x 12 / annual disposable income."""
    result = df.copy()
    if "rent_monthly" not in result.columns:
        return result
    can_derive = (
        result["rent_burden"].isna()
        & result["rent_monthly"].notna()
        & result["disposable_income"].notna()
        & result["disposable_income"].ne(0)
    )
    result.loc[can_derive, "rent_burden"] = (
        result.loc[can_derive, "rent_monthly"] * 12 / result.loc[can_derive, "disposable_income"]
    )
    return result


def clean_city_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names, sort and deduplicate."""
    result = derive_rent_burden(derive_housing_burden(df))
    result = result.sort_values(["city", "year"]).drop_duplicates(
        subset=["city", "year"], keep="last"
    )
    return result.reset_index(drop=True)


def save_processed(df: pd.DataFrame, path: Path | None = None) -> Path:
    """Write to the processed directory."""
    output_path = path or CITY_DATA_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
