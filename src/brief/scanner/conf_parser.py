from __future__ import annotations

import re
from configparser import RawConfigParser
from pathlib import Path

_CONTINUATION = re.compile(r"\\\s*\n[ \t]*")


def _splice_continuations(text: str) -> str:
    return _CONTINUATION.sub(" ", text)


class ConfParser:
    @staticmethod
    def parse_file(path: Path) -> dict[str, dict[str, str]]:
        raw = path.read_text(encoding="utf-8")
        spliced = _splice_continuations(raw)
        parser = RawConfigParser(default_section="default", strict=False, interpolation=None)
        parser.read_string(spliced)
        defaults = dict(parser.defaults())
        out: dict[str, dict[str, str]] = {}
        for section in parser.sections():
            items = dict(parser.items(section, raw=True))
            for key in defaults:
                items.pop(key, None)
            out[section] = items
        if defaults:
            out["default"] = defaults
        return out

    @staticmethod
    def parse_layered(default_path: Path | None, local_path: Path | None) -> dict[str, dict[str, str]]:
        merged: dict[str, dict[str, str]] = {}
        if default_path and default_path.exists():
            merged = ConfParser.parse_file(default_path)
        if local_path and local_path.exists():
            local = ConfParser.parse_file(local_path)
            for stanza, kvs in local.items():
                merged.setdefault(stanza, {}).update(kvs)
        return merged
