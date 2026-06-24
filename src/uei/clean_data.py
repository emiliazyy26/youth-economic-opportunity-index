"""数据清洗与字段派生。"""

from pathlib import Path

import pandas as pd

from uei.config import CITY_DATA_FILE, RAW_COLUMNS, RAW_DATA_DIR


def load_raw_data(path: Path | None = None) -> pd.DataFrame:
    """读取 raw 目录下的主数据表。"""
    data_path = path or RAW_DATA_DIR / "city_panel.csv"
    if not data_path.exists():
        raise FileNotFoundError(
            f"原始数据不存在: {data_path}\n"
            "请先将收集的数据保存为 data/raw/city_panel.csv"
        )

    df = pd.read_csv(data_path)
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"缺少字段: {sorted(missing)}")

    return df


def derive_housing_burden(df: pd.DataFrame) -> pd.DataFrame:
    """住房负担 = 房价 / 可支配收入（逐行补齐缺失值）。"""
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
    """租金负担 = 月租 × 12 / 年可支配收入。"""
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
    """标准化列名、排序并去重。"""
    result = derive_rent_burden(derive_housing_burden(df))
    result = result.sort_values(["city", "year"]).drop_duplicates(
        subset=["city", "year"], keep="last"
    )
    return result.reset_index(drop=True)


def save_processed(df: pd.DataFrame, path: Path | None = None) -> Path:
    """写入 processed 目录。"""
    output_path = path or CITY_DATA_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
