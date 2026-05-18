from __future__ import annotations

import logging
from typing import Literal

from brief.generator.hosted import (
    HostedModelsUnavailable,
    evaluate_quality_hosted,
    generate_description_hosted,
)
from brief.generator.local import (
    LocalGenerationError,
    evaluate_quality_local,
    generate_description_local,
)
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.spl.models import SPLExplanation

__all__ = [
    "GeneratedDescription",
    "QualityRubric",
    "generate",
    "evaluate",
]

Mode = Literal["live", "offline"]

_logger = logging.getLogger(__name__)


async def generate(
    explanation: SPLExplanation,
    raw_spl: str,
    mode: Mode,
    app_class: str,
) -> GeneratedDescription:
    if mode == "live":
        try:
            return await generate_description_hosted(explanation, raw_spl, app_class)
        except HostedModelsUnavailable as exc:
            _logger.warning("hosted models unavailable (%s); falling back to Ollama", exc)
    return await generate_description_local(explanation, raw_spl, app_class)


async def evaluate(
    description: str,
    explanation: SPLExplanation,
    mode: Mode,
    app_class: str,
) -> QualityRubric:
    if mode == "live":
        try:
            return await evaluate_quality_hosted(description, explanation, app_class)
        except HostedModelsUnavailable as exc:
            _logger.warning("hosted models unavailable (%s); falling back to Ollama", exc)
    return await evaluate_quality_local(description, explanation, app_class)
