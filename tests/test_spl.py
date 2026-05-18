from __future__ import annotations

from pathlib import Path

import pytest

import brief.spl as spl_pkg
from brief.scanner import scan_app
from brief.spl import cache_size, clear_cache, explain
from brief.spl.models import SPLExplanation


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield
    clear_cache()


async def test_offline_caches_repeated_calls() -> None:
    spl = "index=main | stats count by host"
    first = await explain(spl, macros={}, mode="offline")
    assert isinstance(first, SPLExplanation)
    assert first.source == "ollama"
    assert cache_size() == 1
    second = await explain(spl, macros={}, mode="offline")
    assert second is first


async def test_live_falls_back_to_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(_: str) -> SPLExplanation:
        raise spl_pkg.SaiaExplanationError("no tenant configured")

    monkeypatch.setattr(spl_pkg, "explain_via_saia", fail)

    result = await explain("index=main | stats count", macros={}, mode="live")
    assert result.source == "ollama"


async def test_live_uses_saia_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = SPLExplanation(
        indexes_queried=["main"],
        sourcetypes_filtered=[],
        fields_extracted=["host"],
        transformations=["counts events"],
        output_shape="count by host",
        summary="Counts events grouped by host in the main index.",
        source="saia",
    )

    async def fake_saia(_: str) -> SPLExplanation:
        return stub

    monkeypatch.setattr(spl_pkg, "explain_via_saia", fake_saia)

    result = await explain("index=main | stats count by host", macros={}, mode="live")
    assert result.source == "saia"
    assert result.indexes_queried == ["main"]


async def test_macros_inlined_before_explanation(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    async def capture(spl: str) -> SPLExplanation:
        captured.append(spl)
        return SPLExplanation(output_shape="", summary="", source="ollama")

    monkeypatch.setattr(spl_pkg, "explain_via_ollama", capture)

    macros = {"my_index": {"definition": "index=security"}}
    await explain("`my_index` | stats count", macros, mode="offline")
    assert captured == ["index=security | stats count"]


async def test_real_ollama_extracts_indexes_from_sample_ta() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample-ta-1"
    report = scan_app(fixture)
    test_searches = [
        o
        for o in report.objects
        if o.object_type == "savedsearch"
        and o.raw_definition
        and "index=" in o.raw_definition
    ][:3]
    assert len(test_searches) >= 3, f"need 3 indexed searches, got {len(test_searches)}"

    for s in test_searches:
        explanation = await explain(s.raw_definition, macros={}, mode="offline")
        assert isinstance(explanation, SPLExplanation)
        assert explanation.source == "ollama"
