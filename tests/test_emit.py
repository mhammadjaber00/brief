from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import yaml

from brief.agent import audit_app
from brief.emit import emit_all
from brief.emit.diff import generate_diff
from brief.emit.manifest import build_manifest, emit_manifest
from brief.generator.schema import GeneratedDescription
from brief.scanner.models import (
    AppScanReport,
    ObjectSignals,
    SafetyReport,
)
from brief.scoring.score import score_app

SAMPLE = Path(__file__).parent / "fixtures" / "sample-ta-1"


def _stub_description(name: str = "fls") -> GeneratedDescription:
    return GeneratedDescription(
        description=(
            "Returns count of failed SSH login attempts by user and source IP in the "
            "last 24 hours. Use for credential stuffing investigations."
        ),
        primary_use_case="credential stuffing investigation",
        output_fields=["user", "src_ip", "count"],
        mitre_techniques=["T1110.001"],
        estimated_runtime="fast",
        suitable_for_agent=True,
        reasoning="bounded aggregation, no destructive commands, common security pattern",
    )


def _stub_unsafe_description() -> GeneratedDescription:
    return GeneratedDescription(
        description=(
            "Deletes outdated indicators from the ioc_lookup table older than 30 days. "
            "Operational maintenance only — not safe for agent dispatch."
        ),
        primary_use_case="lookup table maintenance",
        output_fields=[],
        estimated_runtime="fast",
        suitable_for_agent=False,
        reasoning="modifies state via outputlookup; not appropriate for agent calls",
    )


def test_manifest_yaml_round_trips(tmp_path: Path) -> None:
    obj = ObjectSignals(
        name="failed_login_count_24h",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(safe=True, violations=[], warnings=[]),
        raw_definition="index=linux_secure | stats count by user, src_ip",
        file_origin="savedsearches.conf",
    )
    report = AppScanReport(
        app_name="TA-test",
        app_version="1.0.0",
        app_description=None,
        objects=[obj],
        file_coverage=[],
        embedded_dashboard_searches=[],
    )
    descriptions = {"failed_login_count_24h": _stub_description()}

    out = tmp_path / "manifest.yaml"
    emit_manifest(report, descriptions, out)

    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert loaded["app"] == "TA-test"
    assert loaded["version"] == "1.0.0"
    assert loaded["generated_by"].startswith("brief v")
    assert loaded["tools"] and len(loaded["tools"]) == 1
    tool = loaded["tools"][0]
    assert tool["name"] == "failed_login_count_24h"
    assert tool["suitable_for_agent"] is True
    assert tool["mitre_techniques"] == ["T1110.001"]
    assert tool["rbac_role"] == "mcp_user"


def test_manifest_excludes_unsuitable_and_unsafe_tools() -> None:
    safe_obj = ObjectSignals(
        name="safe_one",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(safe=True, violations=[], warnings=[]),
        raw_definition="index=main | stats count",
        file_origin="savedsearches.conf",
    )
    unsafe_obj = ObjectSignals(
        name="unsafe_one",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(
            safe=False, violations=["destructive command: `| delete`"], warnings=[]
        ),
        raw_definition="index=main | delete",
        file_origin="savedsearches.conf",
    )
    not_for_agent_obj = ObjectSignals(
        name="lookup_writer",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(safe=True, violations=[], warnings=["uses `| outputlookup`"]),
        raw_definition="| inputlookup x | outputlookup x",
        file_origin="savedsearches.conf",
    )
    report = AppScanReport(
        app_name="TA-mix",
        app_version="0.1",
        app_description=None,
        objects=[safe_obj, unsafe_obj, not_for_agent_obj],
        file_coverage=[],
        embedded_dashboard_searches=[],
    )
    descriptions = {
        "safe_one": _stub_description(),
        "unsafe_one": _stub_description(),
        "lookup_writer": _stub_unsafe_description(),
    }
    manifest = build_manifest(report, descriptions)
    tool_names = [t["name"] for t in manifest["tools"]]
    assert tool_names == ["safe_one"]


def test_diff_inserts_descriptions_under_correct_stanzas() -> None:
    obj = ObjectSignals(
        name="orphaned_processes",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(safe=True, violations=[], warnings=[]),
        raw_definition="index=endpoint | stats count by Image",
        file_origin="savedsearches.conf",
    )
    report = AppScanReport(
        app_name="sample-ta-1",
        app_version=None,
        app_description=None,
        objects=[obj],
        file_coverage=[],
        embedded_dashboard_searches=[],
    )
    descriptions = {"orphaned_processes": _stub_description()}
    diff_text = generate_diff(report, descriptions, SAMPLE)

    assert "--- a/default/savedsearches.conf" in diff_text
    assert "+++ b/default/savedsearches.conf" in diff_text
    assert "+description = Returns count of failed SSH" in diff_text
    assert "[orphaned_processes]" in diff_text


def test_diff_applies_cleanly_to_fixture_copy(tmp_path: Path) -> None:
    target = tmp_path / "sample-ta-1"
    shutil.copytree(SAMPLE, target)

    obj = ObjectSignals(
        name="orphaned_processes",
        object_type="savedsearch",
        description_present=False,
        description_text=None,
        safety=SafetyReport(safe=True, violations=[], warnings=[]),
        raw_definition="index=endpoint | stats count by Image",
        file_origin="savedsearches.conf",
    )
    report = AppScanReport(
        app_name="sample-ta-1",
        app_version=None,
        app_description=None,
        objects=[obj],
        file_coverage=[],
        embedded_dashboard_searches=[],
    )
    descriptions = {"orphaned_processes": _stub_description()}
    diff_text = generate_diff(report, descriptions, target)
    diff_path = tmp_path / "descriptions.diff"
    diff_path.write_text(diff_text, encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
        cwd=target,
        check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=target,
        check=True,
    )
    result = subprocess.run(
        ["git", "apply", "--check", str(diff_path)],
        cwd=target,
        capture_output=True,
    )
    assert result.returncode == 0, f"git apply --check failed: {result.stderr.decode()}"


def test_emit_all_produces_four_files(tmp_path: Path) -> None:
    async def run() -> tuple:
        return await audit_app(SAMPLE, mode="offline")

    report, descriptions, rubrics = asyncio.run(run())
    score = score_app(report, descriptions, rubrics)
    out_dir = tmp_path / "brief-out"
    paths = emit_all(report, score, descriptions, rubrics, SAMPLE, out_dir)

    assert paths["score"].name == "score.json"
    assert paths["diff"].name == "descriptions.diff"
    assert paths["manifest"].name == "mcp_manifest.yaml"
    assert paths["report"].name == "report.html"
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0

    html_text = paths["report"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_text
    assert report.app_name in html_text

    loaded = yaml.safe_load(paths["manifest"].read_text(encoding="utf-8"))
    assert loaded["app"] == report.app_name

    score_text = paths["score"].read_text(encoding="utf-8")
    assert f'"overall_score": {score.overall_score}' in score_text
