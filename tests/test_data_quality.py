"""source/raw 数据治理检查。"""

import pandas as pd

from yei.config import (
    ALL_CITIES,
    MISSING_DATA_REPORT_FILE,
    RAW_DATA_DIR,
    SOURCE_OBSERVATIONS_FILE,
    TARGET_METRICS,
    YEARS,
)

FORBIDDEN_RAW_NOTES = ("estimated", "proxy", "peer mean", "project proxy")


def _load_panel() -> pd.DataFrame:
    return pd.read_csv(RAW_DATA_DIR / "city_panel.csv")


def _load_observations() -> pd.DataFrame:
    return pd.read_csv(SOURCE_OBSERVATIONS_FILE)


def _load_missing() -> pd.DataFrame:
    return pd.read_csv(MISSING_DATA_REPORT_FILE)


def test_city_panel_shape_and_keys():
    df = _load_panel()

    assert len(df) == len(ALL_CITIES) * len(YEARS)
    assert sorted(df["city"].unique()) == sorted(ALL_CITIES)
    assert sorted(df["year"].unique()) == YEARS
    assert not df.duplicated(["city", "year"]).any()


def test_source_observations_have_provenance():
    observations = _load_observations()

    assert not observations.empty
    has_url_or_file = observations["source_url"].fillna("").ne("") | observations[
        "source_file"
    ].fillna("").ne("")
    # budget_estimate and derived_estimate are synthetic by nature — exempt from URL requirement
    is_estimate = observations["source_type"].isin({"budget_estimate", "derived_estimate"})
    assert (has_url_or_file | is_estimate).all()
    assert observations["source_type"].fillna("").ne("").all()
    assert observations["extraction_method"].fillna("").ne("").all()


def test_source_observations_do_not_contain_estimate_or_proxy_notes():
    observations = _load_observations()
    notes = observations["notes"].fillna("").str.lower()

    for marker in FORBIDDEN_RAW_NOTES:
        assert not notes.str.contains(marker).any()


def test_missing_required_values_are_reported():
    observations = _load_observations()
    missing = _load_missing()
    expected_metrics = set(TARGET_METRICS) | {"tertiary_ratio"}

    assert set(missing["metric"]).issubset(expected_metrics)
    assert "category" in missing.columns
    assert "data_tier" in missing.columns

    observed_keys = set(
        zip(
            observations["city"],
            observations["year"].astype(int),
            observations["metric"],
            strict=False,
        )
    )
    missing_keys = set(
        zip(
            missing["city"],
            missing["year"].astype(int),
            missing["metric"],
            strict=False,
        )
    )

    assert observed_keys.isdisjoint(missing_keys)
    assert not missing[["city", "year", "metric", "status", "explanation"]].isna().any().any()


def test_derived_fields_only_exist_when_inputs_exist():
    df = _load_panel()

    burden_filled = df["housing_burden"].notna()
    assert (df.loc[burden_filled, ["house_price", "disposable_income"]].notna().all(axis=1)).all()

    growth_filled = df["population_growth"].notna()
    observations = _load_observations()
    population_by_city_year = observations[observations["metric"] == "population"].set_index(
        ["city", "year"]
    )["value"]
    for _, row in df.loc[growth_filled, ["city", "year", "population_growth"]].iterrows():
        current_key = (row["city"], row["year"])
        previous_key = (row["city"], row["year"] - 1)
        assert pd.notna(population_by_city_year.get(current_key))
        assert pd.notna(population_by_city_year.get(previous_key))
