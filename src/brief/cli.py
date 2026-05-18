from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from brief.cli_helpers import AppPathError, print_audit_summary, validate_app_path
from brief.config import load_config
from brief.scanner import scan_app
from brief.scanner.models import AppScanReport

app = typer.Typer(
    name="brief",
    help="Audit Splunk apps for AI-agent-readiness.",
    no_args_is_help=True,
)


@app.command(help="Stage 1 only — fast structural audit, no LLM calls.")
def scan(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, help="Path to a Splunk app folder."),
    output: Path = typer.Option(None, "--output", "-o", help="Write the scan report JSON here."),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table | json"),
) -> None:
    console = Console()
    try:
        validate_app_path(path)
    except AppPathError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2)

    report = scan_app(path)

    if format == "json":
        text = report.model_dump_json(indent=2)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            console.print(f"[dim]report → {output}[/dim]")
        else:
            typer.echo(text)
        return

    _print_scan_table(console, report)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n[dim]report → {output}[/dim]")


@app.command(help="Full audit — scan, explain, generate, score, emit.")
def audit(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, help="Path to a Splunk app folder."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory for artifacts (default: ./brief-out)."),
    mode: str = typer.Option("offline", "--mode", help="Generation backend: offline (Ollama) | live (Splunk Hosted Models with Ollama fallback)."),
    app_class: str = typer.Option("auto", "--app-class", help="Classification override: auto | security | general."),
    model: str | None = typer.Option(None, "--model", help="Override the Ollama model (default: from OLLAMA_MODEL env or llama3.1:8b)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show per-stage trace output."),
) -> None:
    console = Console()
    _configure_logging(verbose)

    try:
        validate_app_path(path)
    except AppPathError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2)

    if mode not in ("offline", "live"):
        console.print(f"[red]error:[/red] --mode must be 'offline' or 'live', got {mode!r}")
        raise typer.Exit(code=2)
    if app_class not in ("auto", "security", "general"):
        console.print(f"[red]error:[/red] --app-class must be auto | security | general, got {app_class!r}")
        raise typer.Exit(code=2)

    config = load_config()
    output_dir = output or config.output_dir

    if model:
        os.environ["OLLAMA_MODEL"] = model
    if config.ollama_host:
        os.environ.setdefault("OLLAMA_HOST", config.ollama_host)

    from brief.agent import audit_app
    from brief.emit import emit_all
    from brief.scoring.score import score_app

    try:
        with console.status(f"[bold]scanning[/bold] {path}…") as status:
            def progress_cb(msg: str) -> None:
                status.update(msg)

            report, descriptions, rubrics = asyncio.run(
                audit_app(
                    path,
                    mode=mode,
                    app_class_override=app_class,
                    progress=progress_cb,
                )
            )
    except Exception as exc:
        console.print(f"[red]error:[/red] audit failed during pipeline: {exc}")
        raise typer.Exit(code=2)

    if not report.objects:
        console.print(f"[red]error:[/red] {path} contains no scannable objects")
        raise typer.Exit(code=2)

    score = score_app(report, descriptions, rubrics)
    paths = emit_all(report, score, descriptions, rubrics, path, output_dir)

    undescribed_count = sum(
        1 for o in report.objects
        if o.object_type == "savedsearch" and o.raw_definition and not o.description_present
    )
    partial_failures = max(0, undescribed_count - len(descriptions))

    print_audit_summary(console, report, score, paths, partial_failures)

    if partial_failures > 0:
        raise typer.Exit(code=1)


def _print_scan_table(console: Console, report: AppScanReport) -> None:
    console.print(f"\n[bold]{report.app_name}[/bold] v{report.app_version or '?'}")
    if report.app_description:
        console.print(f"[dim]{report.app_description}[/dim]")

    coverage_table = Table(title="File coverage", show_lines=False)
    coverage_table.add_column("file")
    coverage_table.add_column("objects", justify="right")
    coverage_table.add_column("described", justify="right")
    coverage_table.add_column("coverage", justify="right")
    for fc in report.file_coverage:
        coverage_table.add_row(
            fc.file_name,
            str(fc.total_objects),
            str(fc.described_count),
            f"{fc.coverage_pct}%",
        )
    console.print(coverage_table)

    findings = Table(title="Safety findings", show_lines=True)
    findings.add_column("object")
    findings.add_column("violations", style="red")
    findings.add_column("warnings", style="yellow")
    has_findings = False
    for o in report.objects:
        if o.safety.violations or o.safety.warnings:
            has_findings = True
            findings.add_row(
                o.name,
                "\n".join(o.safety.violations) or "—",
                "\n".join(o.safety.warnings) or "—",
            )
    if has_findings:
        console.print(findings)
    else:
        console.print("[green]No safety findings.[/green]")

    console.print(
        f"\n[bold]{len(report.embedded_dashboard_searches)}[/bold] embedded dashboard searches"
    )


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s · %(message)s",
        stream=sys.stderr,
    )


if __name__ == "__main__":
    app()
