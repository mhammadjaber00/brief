from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from brief.cli import app

SAMPLE = Path(__file__).parent / "fixtures" / "sample-ta-1"
OSQUERY = Path(__file__).parent / "fixtures" / "ta-osquery"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help_shows_two_commands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout
    assert "audit" in result.stdout


def test_scan_help_documents_flags(runner: CliRunner) -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.stdout
    assert "--output" in result.stdout


def test_audit_help_documents_flags(runner: CliRunner) -> None:
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.stdout
    assert "--app-class" in result.stdout
    assert "--model" in result.stdout
    assert "--verbose" in result.stdout


def test_scan_table_format_on_fixture(runner: CliRunner) -> None:
    result = runner.invoke(app, ["scan", str(SAMPLE)])
    assert result.exit_code == 0
    assert "Sample TA 1" in result.stdout
    assert "savedsearches.conf" in result.stdout


def test_scan_json_format_emits_valid_json(runner: CliRunner) -> None:
    result = runner.invoke(app, ["scan", str(SAMPLE), "-f", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["app_name"] == "Sample TA 1"
    assert any(o["object_type"] == "savedsearch" for o in payload["objects"])


def test_scan_handles_ta_osquery(runner: CliRunner) -> None:
    result = runner.invoke(app, ["scan", str(OSQUERY)])
    assert result.exit_code == 0
    assert "TA-Osquery" in result.stdout or "osquery" in result.stdout.lower()


def test_audit_rejects_bad_mode(runner: CliRunner) -> None:
    result = runner.invoke(app, ["audit", str(SAMPLE), "--mode", "garbage"])
    assert result.exit_code == 2
    assert "mode" in result.stdout.lower() or "mode" in str(result.exception or "").lower()


def test_audit_rejects_bad_app_class(runner: CliRunner) -> None:
    result = runner.invoke(app, ["audit", str(SAMPLE), "--app-class", "weird"])
    assert result.exit_code == 2


def test_scan_rejects_non_app_directory(runner: CliRunner, tmp_path: Path) -> None:
    not_an_app = tmp_path / "empty"
    not_an_app.mkdir()
    result = runner.invoke(app, ["scan", str(not_an_app)])
    assert result.exit_code == 2
