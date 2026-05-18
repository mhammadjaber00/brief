from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from brief.emit import emit_all
from brief.scoring.score import AppScore
from brief.scanner.models import AppScanReport


class AppPathError(ValueError):
    pass


def validate_app_path(path: Path) -> None:
    if not path.exists():
        raise AppPathError(f"path does not exist: {path}")
    if not path.is_dir():
        raise AppPathError(f"path is not a directory: {path}")
    default_dir = path / "default"
    local_dir = path / "local"
    if not default_dir.is_dir() and not local_dir.is_dir():
        raise AppPathError(
            f"{path} does not look like a Splunk app — no default/ or local/ directory"
        )
    has_conf = any(default_dir.glob("*.conf")) if default_dir.is_dir() else False
    has_conf = has_conf or (any(local_dir.glob("*.conf")) if local_dir.is_dir() else False)
    if not has_conf:
        raise AppPathError(
            f"{path}/default/ (or local/) has no .conf files — not a Splunk app shape"
        )


def print_audit_summary(
    console: Console,
    report: AppScanReport,
    score: AppScore,
    paths: dict[str, Path],
    partial_failures: int,
) -> None:
    console.print(
        f"\n[bold]{report.app_name}[/bold]"
        f" — overall readiness [bold]{score.overall_score}/100[/bold]"
    )
    sub = Table.grid(padding=(0, 2))
    sub.add_column(style="dim")
    sub.add_column()
    sub.add_row("presence", f"{score.presence_pct}")
    sub.add_row("quality", f"{score.quality_avg}")
    sub.add_row("coverage", f"{score.coverage_pct}")
    sub.add_row("safety", f"{score.safety_pct}")
    console.print(sub)

    console.print("\n[dim]artifacts[/dim]")
    for kind, path in paths.items():
        console.print(f"  · {kind:<8} {path}")

    if partial_failures:
        console.print(
            f"\n[yellow]⚠[/yellow]  {partial_failures} description(s) couldn't be "
            "generated — re-run with --verbose for details."
        )

    console.print(
        f"\n[bold]Next:[/bold] open [cyan]{paths['report']}[/cyan] to review."
    )
