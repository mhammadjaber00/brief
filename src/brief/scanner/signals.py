from __future__ import annotations

from brief.scanner.models import ObjectSignals, ObjectType, SafetyReport
from brief.scanner.safety import analyze_spl

_RAW_KEY_BY_TYPE: dict[ObjectType, str] = {
    "savedsearch": "search",
    "macro": "definition",
    "eventtype": "search",
    "tag": "",
    "transform": "REGEX",
    "command": "filename",
}

_DESCRIPTION_MIN_CHARS = 10


def signal_for(
    name: str,
    object_type: ObjectType,
    stanza: dict[str, str],
    file_origin: str,
) -> ObjectSignals:
    description_text = (stanza.get("description") or "").strip() or None
    description_present = bool(
        description_text and len(description_text) > _DESCRIPTION_MIN_CHARS
    )

    raw_key = _RAW_KEY_BY_TYPE.get(object_type, "")
    raw_definition = stanza.get(raw_key, "") if raw_key else ""

    if object_type in ("savedsearch", "eventtype") and raw_definition:
        safety = analyze_spl(raw_definition)
    else:
        safety = SafetyReport(safe=True, violations=[], warnings=[])

    return ObjectSignals(
        name=name,
        object_type=object_type,
        description_present=description_present,
        description_text=description_text,
        safety=safety,
        raw_definition=raw_definition,
        file_origin=file_origin,
    )
