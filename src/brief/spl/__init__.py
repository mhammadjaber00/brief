from __future__ import annotations

import hashlib
import logging
from typing import Literal

from brief.spl.explainer_ollama import OllamaExplanationError, explain_via_ollama
from brief.spl.explainer_saia import SaiaExplanationError, explain_via_saia
from brief.spl.macro_expander import MacroExpander
from brief.spl.models import SPLExplanation

__all__ = ["explain", "SPLExplanation", "MacroExpander"]

Mode = Literal["live", "offline"]

_logger = logging.getLogger(__name__)
_cache: dict[str, SPLExplanation] = {}


def _cache_key(expanded: str) -> str:
    return hashlib.sha256(expanded.encode("utf-8")).hexdigest()


async def explain(
    spl: str,
    macros: dict[str, dict[str, str]],
    mode: Mode = "offline",
) -> SPLExplanation:
    expanded = MacroExpander.expand(spl, macros)
    key = _cache_key(expanded)
    if key in _cache:
        return _cache[key]

    explanation: SPLExplanation
    if mode == "live":
        try:
            explanation = await explain_via_saia(expanded)
        except SaiaExplanationError as exc:
            _logger.warning("saia path failed (%s); falling back to Ollama", exc)
            explanation = await explain_via_ollama(expanded)
    else:
        explanation = await explain_via_ollama(expanded)

    _cache[key] = explanation
    return explanation


def clear_cache() -> None:
    _cache.clear()


def cache_size() -> int:
    return len(_cache)
