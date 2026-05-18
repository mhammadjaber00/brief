from __future__ import annotations

import re

from brief.scanner.models import SafetyReport

_TERMINAL_AGGREGATIONS = re.compile(
    r"\|\s*(stats|chart|timechart|top|rare|tstats)\b", re.IGNORECASE
)
_HEAD_LIMIT = re.compile(r"\|\s*head\s+\d+", re.IGNORECASE)

_VIOLATIONS: dict[str, re.Pattern[str]] = {
    "| delete": re.compile(r"\|\s*delete\b", re.IGNORECASE),
    "| sendalert": re.compile(r"\|\s*sendalert\b", re.IGNORECASE),
    "| script": re.compile(r"\|\s*script\b", re.IGNORECASE),
    "| outputtext": re.compile(r"\|\s*outputtext\b", re.IGNORECASE),
}

_OUTPUTLOOKUP = re.compile(r"\|\s*outputlookup\b", re.IGNORECASE)
_JOIN = re.compile(r"\|\s*join\b", re.IGNORECASE)
_APPEND = re.compile(r"\|\s*append\b", re.IGNORECASE)
_EARLIEST_DAYS = re.compile(r"earliest\s*=\s*-(\d+)d", re.IGNORECASE)
_INDEX_WILDCARD = re.compile(r"\bindex\s*=\s*\*", re.IGNORECASE)


def analyze_spl(spl: str) -> SafetyReport:
    violations: list[str] = []
    warnings: list[str] = []

    for label, pattern in _VIOLATIONS.items():
        if pattern.search(spl):
            violations.append(f"destructive command: `{label}`")

    if _OUTPUTLOOKUP.search(spl):
        warnings.append("uses `| outputlookup` — verify target lookup is safe")

    has_head = bool(_HEAD_LIMIT.search(spl))

    if _JOIN.search(spl) and not has_head:
        warnings.append("`| join` without `| head N` — likely exceeds 60s runtime")
    if _APPEND.search(spl) and not has_head:
        warnings.append("`| append` without `| head N` — likely exceeds 60s runtime")

    m = _EARLIEST_DAYS.search(spl)
    if m and int(m.group(1)) >= 30 and not has_head:
        warnings.append(
            f"earliest=-{m.group(1)}d without `| head N` — likely exceeds 60s runtime"
        )

    if _INDEX_WILDCARD.search(spl):
        warnings.append("`index=*` without further filtering — wide index breadth")

    has_aggregation = bool(_TERMINAL_AGGREGATIONS.search(spl))
    if not has_aggregation and not has_head:
        warnings.append(
            "no terminal aggregation and no `| head N` — likely exceeds 1000 events"
        )

    return SafetyReport(
        safe=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )
