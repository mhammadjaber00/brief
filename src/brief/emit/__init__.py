from __future__ import annotations

from pathlib import Path

from brief.emit.diff import generate_diff
from brief.emit.manifest import emit_manifest
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.scanner.models import AppScanReport
from brief.scoring.score import AppScore

__all__ = ["emit_all", "generate_diff", "emit_manifest"]


def emit_all(
    report: AppScanReport,
    score: AppScore,
    descriptions: dict[str, GeneratedDescription],
    quality_rubrics: dict[str, QualityRubric],
    source_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    score_path = output_dir / "score.json"
    score_path.write_text(score.model_dump_json(indent=2), encoding="utf-8")

    diff_path = output_dir / "descriptions.diff"
    diff_path.write_text(generate_diff(report, descriptions, source_path), encoding="utf-8")

    manifest_path = output_dir / "mcp_manifest.yaml"
    emit_manifest(report, descriptions, manifest_path)

    from brief.emit.report import generate_html_report

    report_path = output_dir / "report.html"
    report_path.write_text(
        generate_html_report(report, score, descriptions, quality_rubrics),
        encoding="utf-8",
    )

    return {
        "score": score_path,
        "diff": diff_path,
        "manifest": manifest_path,
        "report": report_path,
    }
