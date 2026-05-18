from __future__ import annotations

import re

_MACRO_CALL = re.compile(r"`([a-zA-Z_][\w]*)(?:\(([^`]*)\))?`")
_MAX_DEPTH = 10


class MacroExpansionError(Exception):
    pass


class MacroExpander:
    @staticmethod
    def expand(spl: str, macros: dict[str, dict[str, str]]) -> str:
        return _expand_recursive(spl, macros, depth=0)


def _expand_recursive(spl: str, macros: dict[str, dict[str, str]], depth: int) -> str:
    if depth >= _MAX_DEPTH:
        raise MacroExpansionError(
            f"macro recursion exceeded depth {_MAX_DEPTH}; likely a self-referential macro"
        )
    if "`" not in spl:
        return spl

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        args_blob = match.group(2)
        call_args = _split_args(args_blob) if args_blob is not None else []
        stanza = _lookup_macro(macros, name, len(call_args))
        if stanza is None:
            return match.group(0)
        body = stanza.get("definition", "")
        formal = _split_args(stanza.get("args", "")) if call_args else []
        for formal_name, value in zip(formal, call_args):
            body = body.replace(f"${formal_name}$", value)
        return body

    expanded = _MACRO_CALL.sub(replace, spl)
    if expanded == spl:
        return expanded
    return _expand_recursive(expanded, macros, depth + 1)


def _lookup_macro(
    macros: dict[str, dict[str, str]], name: str, arity: int
) -> dict[str, str] | None:
    arity_key = f"{name}({arity})"
    if arity_key in macros:
        return macros[arity_key]
    if arity == 0 and name in macros:
        return macros[name]
    return None


def _split_args(args_blob: str) -> list[str]:
    if not args_blob.strip():
        return []
    return [a.strip() for a in args_blob.split(",")]
