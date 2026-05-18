from __future__ import annotations

import json
from pathlib import Path

from brief.scanner.conf_parser import ConfParser
from brief.scanner.models import (
    AppScanReport,
    FileCoverage,
    ObjectSignals,
    ObjectType,
)
from brief.scanner.signals import signal_for
from brief.scanner.xml_parser import extract_dashboard_searches

__all__ = ["scan_app"]


_CONF_TO_OBJECT_TYPE: dict[str, ObjectType] = {
    "savedsearches.conf": "savedsearch",
    "macros.conf": "macro",
    "eventtypes.conf": "eventtype",
    "tags.conf": "tag",
    "transforms.conf": "transform",
    "commands.conf": "command",
}


def scan_app(app_path: Path) -> AppScanReport:
    app_path = Path(app_path).resolve()
    app_name, app_version, app_description = _read_app_identity(app_path)

    objects: list[ObjectSignals] = []
    file_coverage: list[FileCoverage] = []
    for conf_name, object_type in _CONF_TO_OBJECT_TYPE.items():
        default_path = app_path / "default" / conf_name
        local_path = app_path / "local" / conf_name
        merged = ConfParser.parse_layered(default_path, local_path)
        file_objects: list[ObjectSignals] = []
        for stanza_name, kvs in merged.items():
            if stanza_name == "default":
                continue
            file_objects.append(signal_for(stanza_name, object_type, kvs, conf_name))
        objects.extend(file_objects)
        if file_objects:
            file_coverage.append(_coverage(conf_name, file_objects))

    views_dir = app_path / "default" / "data" / "ui" / "views"
    embedded = extract_dashboard_searches(views_dir)

    return AppScanReport(
        app_name=app_name,
        app_version=app_version,
        app_description=app_description,
        objects=objects,
        file_coverage=file_coverage,
        embedded_dashboard_searches=embedded,
    )


def _read_app_identity(app_path: Path) -> tuple[str, str | None, str | None]:
    name = app_path.name
    version: str | None = None
    description: str | None = None

    manifest_path = app_path / "app.manifest"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            info = data.get("info", {})
            ident = info.get("id") or {}
            name = info.get("title") or ident.get("name") or name
            version = ident.get("version")
            description = info.get("description")
        except json.JSONDecodeError:
            pass

    app_conf = app_path / "default" / "app.conf"
    if app_conf.exists():
        merged = ConfParser.parse_file(app_conf)
        launcher = merged.get("launcher", {})
        version = version or launcher.get("version")
        description = description or launcher.get("description")
        ui = merged.get("ui", {})
        if not name or name == app_path.name:
            name = ui.get("label") or name

    return name, version, description


def _coverage(file_name: str, file_objects: list[ObjectSignals]) -> FileCoverage:
    total = len(file_objects)
    described = sum(1 for o in file_objects if o.description_present)
    pct = (described / total * 100.0) if total else 0.0
    return FileCoverage(
        file_name=file_name,
        total_objects=total,
        described_count=described,
        coverage_pct=round(pct, 2),
    )
