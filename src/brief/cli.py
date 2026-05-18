from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from brief.scanner import scan_app
from brief.scanner.models import AppScanReport

app = typer.Typer(help="Audit Splunk apps for AI-agent-readiness.")


@app.command(help="Run the full audit pipeline against a Splunk app directory.")
def audit(
    app_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    output: Path = typer.Option(Path("./brief-out"), help="Output directory for artifacts."),
    offline: bool = typer.Option(False, help="Use Ollama fallback instead of Splunk Hosted Models."),
) -> None:
    raise NotImplementedError("Pipeline implementation pending — see docs/brief-spec.html §03.")


@app.command(help="Scan a Splunk app and print a readable summary (no LLM calls).")
def scan(
    app_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    output: Path | None = typer.Option(None, help="Write the scan report JSON to this path."),
) -> None:
    report = scan_app(app_path)
    _print_summary(report)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        typer.echo(f"\nReport written to {output}")


def _print_summary(report: AppScanReport) -> None:
    console = Console()
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
    any_findings = False
    for o in report.objects:
        if o.safety.violations or o.safety.warnings:
            any_findings = True
            findings.add_row(
                o.name,
                "\n".join(o.safety.violations) or "—",
                "\n".join(o.safety.warnings) or "—",
            )
    if any_findings:
        console.print(findings)
    else:
        console.print("[green]No safety violations or warnings.[/green]")

    console.print(
        f"\n[bold]{len(report.embedded_dashboard_searches)}[/bold] embedded dashboard searches"
    )


if __name__ == "__main__":
    app()
