from __future__ import annotations

import difflib
from pathlib import Path

from brief.generator.schema import GeneratedDescription
from brief.scanner.models import AppScanReport


def generate_diff(
    report: AppScanReport,
    descriptions: dict[str, GeneratedDescription],
    source_path: Path,
) -> str:
    by_file: dict[str, dict[str, GeneratedDescription]] = {}
    for obj in report.objects:
        if obj.name in descriptions:
            by_file.setdefault(obj.file_origin, {})[obj.name] = descriptions[obj.name]

    parts: list[str] = []
    for conf_name, file_descs in by_file.items():
        conf_path = source_path / "default" / conf_name
        if not conf_path.exists():
            continue
        original_text = conf_path.read_text(encoding="utf-8")
        original_lines = original_text.splitlines()
        modified_lines = _insert_descriptions(original_lines, file_descs)
        if modified_lines == original_lines:
            continue
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/default/{conf_name}",
            tofile=f"b/default/{conf_name}",
            lineterm="",
        )
        parts.extend(diff)
        parts.append("")

    return "\n".join(parts).rstrip("\n") + ("\n" if parts else "")


def _insert_descriptions(
    lines: list[str],
    descriptions: dict[str, GeneratedDescription],
) -> list[str]:
    out: list[str] = []
    rewriting_stanza: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stanza_name = stripped[1:-1]
            out.append(line)
            if stanza_name in descriptions:
                rewriting_stanza = stanza_name
                text = descriptions[stanza_name].description.replace("\n", " ").strip()
                out.append(f"description = {text}")
            else:
                rewriting_stanza = None
            continue
        if rewriting_stanza is not None and "=" in stripped:
            key = stripped.split("=", 1)[0].strip().lower()
            if key == "description":
                continue
        out.append(line)
    return out
