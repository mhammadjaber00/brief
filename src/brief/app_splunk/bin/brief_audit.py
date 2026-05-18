from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_BIN_DIR = Path(__file__).resolve().parent
_LIB_DIR = _BIN_DIR / "lib"
if _LIB_DIR.exists():
    sys.path.insert(0, str(_LIB_DIR))

from splunklib.searchcommands import (  # type: ignore[import-not-found]
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)


@Configuration()
class BriefAuditCommand(GeneratingCommand):
    mode = Option(
        doc="Generation backend: offline (Ollama) | live (Splunk Hosted Models, falls back to Ollama).",
        require=False,
        default="live",
        validate=validators.Set("offline", "live"),
    )
    apps_path = Option(
        doc="Path to the apps directory to scan (default: $SPLUNK_HOME/etc/apps).",
        require=False,
        default=None,
    )
    limit = Option(
        doc="Maximum number of apps to audit in this run (default: all).",
        require=False,
        default=0,
        validate=validators.Integer(minimum=0),
    )

    def generate(self):
        try:
            from brief.agent import audit_app
            from brief.scoring.score import score_app
        except ImportError as exc:
            yield self._error_row(
                f"Brief package not importable from bin/lib/: {exc}. "
                "Run scripts/package-app.sh to bundle dependencies."
            )
            return

        apps_root = Path(
            self.apps_path or os.environ.get("SPLUNK_HOME", "/opt/splunk") + "/etc/apps"
        )
        if not apps_root.is_dir():
            yield self._error_row(f"apps directory not found: {apps_root}")
            return

        audited = 0
        for app_dir in sorted(p for p in apps_root.iterdir() if p.is_dir()):
            if app_dir.name == "brief":
                continue
            if self.limit and audited >= self.limit:
                break
            if not (app_dir / "default").is_dir() and not (app_dir / "local").is_dir():
                continue
            try:
                report, descriptions, rubrics = asyncio.run(
                    audit_app(app_dir, mode=self.mode)
                )
                score = score_app(report, descriptions, rubrics)
            except Exception as exc:
                yield self._row(
                    app_name=app_dir.name,
                    status="error",
                    error=str(exc)[:240],
                )
                continue

            yield self._row(
                app_name=report.app_name,
                app_path=str(app_dir),
                status="ok",
                overall_score=score.overall_score,
                presence_pct=score.presence_pct,
                quality_avg=score.quality_avg,
                coverage_pct=score.coverage_pct,
                safety_pct=score.safety_pct,
                described_count=sum(f.described_count for f in report.file_coverage),
                total_objects=sum(f.total_objects for f in report.file_coverage),
                proposed_count=len(descriptions),
                rubric_count=len(rubrics),
            )
            audited += 1

    def _row(self, **fields):
        row = {
            "_time": datetime.now(timezone.utc).timestamp(),
            "source": "brief",
            "sourcetype": "brief:audit",
            "index": "brief_scores",
        }
        row.update(fields)
        return row

    def _error_row(self, message: str):
        return self._row(app_name="<setup>", status="error", error=message)


dispatch(BriefAuditCommand, sys.argv, sys.stdin, sys.stdout, __name__)
