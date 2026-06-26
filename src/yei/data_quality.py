"""Main index data quality thresholds and dimension metric selection."""

from __future__ import annotations

import pandas as pd

from yei.config import (
    CORE_METRIC_COVERAGE_THRESHOLD,
    DATA_TIER_A,
    DATA_TIER_B,
    DATA_TIER_C,
    DATA_TIER_D,
    DIMENSION_SPEC,
    SUPPLEMENTARY_TARGET_METRICS,
    TARGET_METRICS,
)


def metric_tier(metric: str) -> str:
    if metric in DATA_TIER_A:
        return "A"
    if metric in DATA_TIER_B:
        return "B"
    if metric in DATA_TIER_C:
        return "C"
    if metric in DATA_TIER_D:
        return "D"
    return "unknown"


def coverage_ratio(series: pd.Series) -> float:
    """Non-missing ratio of sample cities within the cross-section."""
    if series.empty:
        return 0.0
    return float(series.notna().sum()) / len(series)


def passes_core_threshold(series: pd.Series) -> bool:
    return coverage_ratio(series) >= CORE_METRIC_COVERAGE_THRESHOLD


def select_dimension_metric(
    group: pd.DataFrame,
    dimension: str,
) -> tuple[str, pd.Series, str]:
    """Select dimension input column for a year cross-section, return (column_name, series, source_label)."""
    spec = DIMENSION_SPEC[dimension]
    primary = spec["primary"]
    if primary in group.columns and passes_core_threshold(group[primary]):
        return primary, group[primary], primary
    if primary in group.columns:
        return primary, group[primary], f"{primary}_partial"
    raise ValueError(f"No metric available for dimension {dimension}")


def classify_missing_metric(metric: str) -> str:
    """Missing report classification: core / supplementary / excluded."""
    if metric in DATA_TIER_D:
        return "excluded"
    if metric in SUPPLEMENTARY_TARGET_METRICS:
        return "supplementary"
    if metric in TARGET_METRICS or metric in {spec["primary"] for spec in DIMENSION_SPEC.values()}:
        return "core"
    return "core"
