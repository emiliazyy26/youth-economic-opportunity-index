"""主指数数据质量门槛与维度指标选择。"""

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
    """样本城市在该截面内的非缺失比例。"""
    if series.empty:
        return 0.0
    return float(series.notna().sum()) / len(series)


def passes_core_threshold(series: pd.Series) -> bool:
    return coverage_ratio(series) >= CORE_METRIC_COVERAGE_THRESHOLD


def select_dimension_metric(
    group: pd.DataFrame,
    dimension: str,
) -> tuple[str, pd.Series, str]:
    """为某年截面选择维度输入列，返回 (列名, 序列, 来源标签)。"""
    spec = DIMENSION_SPEC[dimension]
    primary = spec["primary"]
    if primary in group.columns and passes_core_threshold(group[primary]):
        return primary, group[primary], primary

    fallbacks = spec["fallback_metrics"]
    if not fallbacks:
        if primary in group.columns:
            return primary, group[primary], f"{primary}_partial"
        raise ValueError(f"No metric available for dimension {dimension}")

    available = [m for m in fallbacks if m in group.columns and group[m].notna().any()]
    if not available:
        raise ValueError(f"No fallback metrics for dimension {dimension}")

    if len(available) == 1:
        metric = available[0]
        return metric, group[metric], f"{metric}_fallback"

    composite = group[available].mean(axis=1)
    label = "+".join(available) + "_fallback"
    return label, composite, label


def classify_missing_metric(metric: str) -> str:
    """缺失报告分类：core / supplementary / excluded."""
    if metric in DATA_TIER_D:
        return "excluded"
    if metric in SUPPLEMENTARY_TARGET_METRICS:
        return "supplementary"
    if metric in TARGET_METRICS or metric in {spec["primary"] for spec in DIMENSION_SPEC.values()}:
        return "core"
    return "core"
