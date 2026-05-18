from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from brief.scanner.models import EmbeddedSearch


def extract_dashboard_searches(views_dir: Path) -> list[EmbeddedSearch]:
    if not views_dir.exists():
        return []
    out: list[EmbeddedSearch] = []
    for xml_file in sorted(views_dir.glob("*.xml")):
        out.extend(_extract_from_file(xml_file))
    return out


def _extract_from_file(path: Path) -> list[EmbeddedSearch]:
    dashboard = path.stem
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError:
        return []
    root = tree.getroot()
    if root.get("version") == "2.0":
        return _extract_studio(root, dashboard)
    return _extract_simple_xml(root, dashboard)


def _extract_simple_xml(root: etree._Element, dashboard: str) -> list[EmbeddedSearch]:
    out: list[EmbeddedSearch] = []
    for panel in root.iter("panel"):
        title_el = panel.find("title")
        panel_title = (title_el.text or "").strip() if title_el is not None else None
        for query_el in panel.iter("query"):
            query = (query_el.text or "").strip()
            if query:
                out.append(EmbeddedSearch(dashboard=dashboard, panel=panel_title, query=query))
    return out


def _extract_studio(root: etree._Element, dashboard: str) -> list[EmbeddedSearch]:
    definition = root.find("definition")
    if definition is None or definition.text is None:
        return []
    try:
        spec = json.loads(definition.text)
    except json.JSONDecodeError:
        return []
    out: list[EmbeddedSearch] = []
    for ds_name, ds in (spec.get("dataSources") or {}).items():
        if ds.get("type") != "ds.search":
            continue
        query = ((ds.get("options") or {}).get("query") or "").strip()
        if query:
            out.append(EmbeddedSearch(dashboard=dashboard, panel=ds_name, query=query))
    return out
