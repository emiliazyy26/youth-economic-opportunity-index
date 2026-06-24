"""Integration tests for the data quality validation script."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

from yei.config import RAW_DATA_DIR

# The validation script lives in scripts/, not in the package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
validate_path = PROJECT_ROOT / "scripts" / "validate_observations.py"
spec = importlib.util.spec_from_file_location("validate_observations", validate_path)
validate = importlib.util.module_from_spec(spec)
sys.modules["validate_observations"] = validate
spec.loader.exec_module(validate)


def test_data_fixes_are_present() -> None:
    """Two known disposable_income errors were corrected."""
    panel = pd.read_csv(RAW_DATA_DIR / "city_panel.csv")
    harbin_2023 = panel[(panel["city"] == "Harbin") & (panel["year"] == 2023)]
    kunming_2024 = panel[(panel["city"] == "Kunming") & (panel["year"] == 2024)]

    assert len(harbin_2023) == 1
    assert harbin_2023.iloc[0]["disposable_income"] == pytest.approx(45784.0)

    assert len(kunming_2024) == 1
    assert kunming_2024.iloc[0]["disposable_income"] == pytest.approx(47301.0)


def test_validation_produces_no_critical_warnings() -> None:
    """After calibration, the validation script should not emit CRITICAL warnings."""
    panel, obs = validate.load_data()
    scores = validate.load_yeoi_scores()
    warnings = validate.run_all_checks(panel, obs, scores)
    report = validate.build_report_dataframe(warnings, obs)

    critical = report[report["status"] == "CRITICAL"]
    assert len(critical) == 0, f"Unexpected CRITICAL warnings: {critical.to_dict('records')}"


def test_validation_exits_cleanly(capsys) -> None:
    """The validation script main() should return exit code 0."""
    import sys as test_sys

    original_argv = test_sys.argv
    try:
        test_sys.argv = [
            "validate_observations.py",
            "--report-csv",
            str(RAW_DATA_DIR / "data_quality_report.csv"),
        ]
        validate.main()
    finally:
        test_sys.argv = original_argv

    captured = capsys.readouterr()
    assert "CRITICAL=0" in captured.err or "CRITICAL=0" in captured.out
