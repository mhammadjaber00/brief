from __future__ import annotations

import re
from typing import Literal

from brief.scanner.models import AppScanReport

AppClass = Literal["security", "general"]

_SECURITY_DESCRIPTION_KEYWORDS = re.compile(
    r"\b(security|threat|soc|siem|compliance|attack|intrusion|malware|breach|"
    r"detection|forensic|incident|vulnerability|exploit|phishing)\b",
    re.IGNORECASE,
)

_SECURITY_INDEX_KEYWORDS = re.compile(
    r"\b(wineventlog|linux_secure|netflow|firewall|proxy|dns_query|audit|"
    r"sysmon|suricata|zeek|bro|endpoint|edr|ids|ips|threat_intel|ioc)\b",
    re.IGNORECASE,
)

_SECURITY_EVENTTYPE_KEYWORDS = re.compile(
    r"\b(attack|breach|intrusion|alert|threat|suspicious|malware|phishing|"
    r"unauthorized|failed_login|brute_force)\b",
    re.IGNORECASE,
)


def classify_app(report: AppScanReport) -> AppClass:
    if report.app_description and _SECURITY_DESCRIPTION_KEYWORDS.search(report.app_description):
        return "security"

    for obj in report.objects:
        if obj.object_type == "savedsearch" and _SECURITY_INDEX_KEYWORDS.search(obj.raw_definition):
            return "security"
        if obj.object_type == "eventtype":
            if _SECURITY_EVENTTYPE_KEYWORDS.search(obj.name):
                return "security"
            if obj.description_text and _SECURITY_EVENTTYPE_KEYWORDS.search(obj.description_text):
                return "security"

    return "general"
