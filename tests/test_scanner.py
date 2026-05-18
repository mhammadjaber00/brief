from pathlib import Path

import pytest

from brief.scanner import scan_app
from brief.scanner.models import AppScanReport

FIXTURE = Path(__file__).parent / "fixtures" / "sample-ta-1"


@pytest.fixture(scope="module")
def report() -> AppScanReport:
    return scan_app(FIXTURE)


def test_scan_returns_report(report: AppScanReport) -> None:
    assert isinstance(report, AppScanReport)


def test_savedsearch_count_matches_conf(report: AppScanReport) -> None:
    savedsearches = [o for o in report.objects if o.object_type == "savedsearch"]
    assert len(savedsearches) == 6


def test_missing_description_detected(report: AppScanReport) -> None:
    missing = [
        o
        for o in report.objects
        if o.object_type == "savedsearch" and not o.description_present
    ]
    assert len(missing) >= 1


def test_at_least_one_safety_warning(report: AppScanReport) -> None:
    savedsearches = [o for o in report.objects if o.object_type == "savedsearch"]
    total_warnings = sum(len(o.safety.warnings) for o in savedsearches)
    assert total_warnings >= 1


def test_coverage_pct_in_range(report: AppScanReport) -> None:
    for fc in report.file_coverage:
        assert 0 <= fc.coverage_pct <= 100
