from __future__ import annotations

from brief.generator.schema import QualityRubric
from brief.scanner.models import AppScanReport, ObjectSignals, SafetyReport
from brief.scoring.score import score_app


def _obj(
    name: str,
    described: bool,
    *,
    file_origin: str = "savedsearches.conf",
    violations: list[str] | None = None,
    warnings: list[str] | None = None,
) -> ObjectSignals:
    return ObjectSignals(
        name=name,
        object_type="savedsearch",
        description_present=described,
        description_text="x" * 50 if described else None,
        safety=SafetyReport(
            safe=not (violations or []),
            violations=violations or [],
            warnings=warnings or [],
        ),
        raw_definition="index=main | stats count",
        file_origin=file_origin,
    )


def _good_rubric() -> QualityRubric:
    return QualityRubric(
        quality_score=10,
        is_tautology=False,
        specifies_data_source=True,
        specifies_use_case=True,
        actionable=True,
        reasoning="strong",
    )


def _report(objects: list[ObjectSignals]) -> AppScanReport:
    return AppScanReport(
        app_name="test",
        app_version=None,
        app_description=None,
        objects=objects,
        file_coverage=[],
        embedded_dashboard_searches=[],
    )


def test_empty_app_scores_zero() -> None:
    score = score_app(_report([]), {}, {})
    assert score.overall_score == 0
    assert score.presence_pct == 0
    assert score.quality_avg == 0
    assert score.safety_pct == 0


def test_fully_described_high_quality_safe_scores_100() -> None:
    objs = [_obj("a", True), _obj("b", True)]
    rubrics = {"a": _good_rubric(), "b": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert score.presence_pct == 100
    assert score.quality_avg == 100
    assert score.coverage_pct == 100
    assert score.safety_pct == 100
    assert score.overall_score == 100


def test_50_pct_described_yields_weighted_score() -> None:
    objs = [_obj("a", True), _obj("b", False)]
    rubrics = {"a": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert score.presence_pct == 50
    assert score.quality_avg == 50
    assert score.coverage_pct == 50
    assert score.safety_pct == 100
    assert score.overall_score == 55


def test_violations_zero_out_safety() -> None:
    objs = [_obj("a", True, violations=["destructive command: `| delete`"])]
    rubrics = {"a": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert score.safety_pct == 0


def test_warnings_only_halve_safety() -> None:
    objs = [_obj("a", True, warnings=["`index=*` without further filtering"])]
    rubrics = {"a": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert score.safety_pct == 50


def test_mixed_files_compute_per_file_coverage() -> None:
    objs = [
        _obj("a", True, file_origin="savedsearches.conf"),
        _obj("b", False, file_origin="savedsearches.conf"),
        _obj("c", True, file_origin="other.conf"),
    ]
    rubrics = {"a": _good_rubric(), "c": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert len(score.files) == 2
    by_file = {f.file_name: f for f in score.files}
    assert by_file["savedsearches.conf"].coverage == 0.5
    assert by_file["other.conf"].coverage == 1.0


def test_non_savedsearch_objects_ignored() -> None:
    objs = [
        _obj("a", True),
        ObjectSignals(
            name="mac",
            object_type="macro",
            description_present=False,
            description_text=None,
            safety=SafetyReport(safe=True, violations=[], warnings=[]),
            raw_definition="index=main",
            file_origin="macros.conf",
        ),
    ]
    rubrics = {"a": _good_rubric()}
    score = score_app(_report(objs), {}, rubrics)
    assert len(score.objects) == 1
    assert score.presence_pct == 100
