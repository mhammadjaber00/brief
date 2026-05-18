from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from brief import generator as generator_pkg
from brief.agent import audit_app
from brief.generator.classifier import classify_app
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.scanner import scan_app
from brief.spl import clear_cache
from brief.spl.models import SPLExplanation

SAMPLE = Path(__file__).parent / "fixtures" / "sample-ta-1"
OSQUERY = Path(__file__).parent / "fixtures" / "ta-osquery"


@pytest.fixture(autouse=True)
def reset_spl_cache():
    clear_cache()
    yield
    clear_cache()


def test_generated_description_schema_enforces_min_length() -> None:
    with pytest.raises(ValidationError):
        GeneratedDescription(
            description="too short",
            primary_use_case="x",
            output_fields=[],
            estimated_runtime="fast",
            suitable_for_agent=True,
            reasoning="r",
        )


def test_quality_rubric_score_bounded() -> None:
    with pytest.raises(ValidationError):
        QualityRubric(
            quality_score=11,
            is_tautology=False,
            specifies_data_source=True,
            specifies_use_case=True,
            actionable=True,
            reasoning="r",
        )


def test_classifier_tags_sample_ta_as_security() -> None:
    report = scan_app(SAMPLE)
    assert classify_app(report) == "security"


def test_classifier_tags_osquery_as_security() -> None:
    report = scan_app(OSQUERY)
    assert classify_app(report) == "security"


def test_audit_app_generates_descriptions_for_undescribed_searches() -> None:
    import asyncio

    async def run() -> tuple:
        return await audit_app(SAMPLE, mode="offline")

    report, proposed = asyncio.run(run())

    undescribed_savedsearches = [
        o for o in report.objects
        if o.object_type == "savedsearch" and not o.description_present
    ]
    assert len(undescribed_savedsearches) >= 1
    assert len(proposed) >= 1
    for name, description in proposed.items():
        assert isinstance(description, GeneratedDescription)
        assert len(description.description) >= 80
        assert any(c.isalpha() for c in description.description)


def test_quality_rubric_detects_tautology() -> None:
    import asyncio

    async def run() -> QualityRubric:
        explanation = SPLExplanation(
            indexes_queried=["linux_secure"],
            sourcetypes_filtered=["linux_secure"],
            fields_extracted=["user", "src_ip", "count"],
            transformations=["groups by user and src_ip", "counts events"],
            output_shape="user, src_ip, count",
            summary="Returns count of failed Linux SSH logins by user and source IP in last 24h.",
            source="ollama",
        )
        return await generator_pkg.evaluate(
            description="auth search",
            explanation=explanation,
            mode="offline",
            app_class="security",
        )

    rubric = asyncio.run(run())
    assert rubric.is_tautology is True
    assert rubric.quality_score < 4
