from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from brief import __version__ as BRIEF_VERSION
from brief.generator.schema import GeneratedDescription
from brief.scanner.models import AppScanReport


def build_manifest(
    report: AppScanReport,
    descriptions: dict[str, GeneratedDescription],
) -> dict:
    tools: list[dict] = []
    for obj in report.objects:
        if obj.object_type != "savedsearch":
            continue
        if obj.name not in descriptions:
            continue
        if obj.safety.violations:
            continue
        d = descriptions[obj.name]
        if not d.suitable_for_agent:
            continue
        entry: dict = {
            "name": obj.name,
            "saved_search": obj.name,
            "description": d.description,
            "output_fields": d.output_fields,
            "rbac_role": "mcp_user",
            "estimated_runtime": d.estimated_runtime,
            "suitable_for_agent": True,
        }
        if d.mitre_techniques:
            entry["mitre_techniques"] = d.mitre_techniques
        tools.append(entry)

    return {
        "app": report.app_name,
        "version": report.app_version or "",
        "generated_by": f"brief v{BRIEF_VERSION}",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools": tools,
    }


def emit_manifest(
    report: AppScanReport,
    descriptions: dict[str, GeneratedDescription],
    output_path: Path,
) -> Path:
    manifest = build_manifest(report, descriptions)
    yaml_text = yaml.safe_dump(manifest, default_flow_style=False, sort_keys=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml_text, encoding="utf-8")
    return output_path
