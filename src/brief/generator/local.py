from __future__ import annotations

import json
import os

from ollama import AsyncClient
from pydantic import ValidationError

from brief.generator.prompts import EVALUATE_QUALITY_PROMPT, GENERATE_DESCRIPTION_PROMPT
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.spl.models import SPLExplanation

_DEFAULT_MODEL_SECURITY = "gpt-oss:20b"
_DEFAULT_MODEL_GENERAL = "gpt-oss:20b"
_DEFAULT_HOST = "http://localhost:11434"
_MAX_ATTEMPTS = 3


class LocalGenerationError(Exception):
    pass


def _client() -> AsyncClient:
    return AsyncClient(host=os.environ.get("OLLAMA_HOST", _DEFAULT_HOST))


def _model_for(app_class: str) -> str:
    override = os.environ.get("OLLAMA_MODEL")
    if override:
        return override
    if app_class == "security":
        return (
            os.environ.get("BRIEF_MODEL_SECURITY")
            or _DEFAULT_MODEL_SECURITY
        )
    return (
        os.environ.get("BRIEF_MODEL_GENERAL")
        or _DEFAULT_MODEL_GENERAL
    )


def _serialize_explanation(explanation: SPLExplanation) -> str:
    return json.dumps(explanation.model_dump(exclude={"source"}), indent=2)


async def generate_description_local(
    explanation: SPLExplanation,
    raw_spl: str,
    app_class: str,
) -> GeneratedDescription:
    user_message = (
        f"App class: {app_class}\n\n"
        f"SPL explanation:\n{_serialize_explanation(explanation)}\n\n"
        f"Raw SPL:\n{raw_spl}"
    )
    return await _generate_with_retry(
        system_prompt=GENERATE_DESCRIPTION_PROMPT,
        user_message=user_message,
        schema=GeneratedDescription,
        model=_model_for(app_class),
    )


async def evaluate_quality_local(
    description: str,
    explanation: SPLExplanation,
    app_class: str,
) -> QualityRubric:
    user_message = (
        f"App class: {app_class}\n\n"
        f"Existing description:\n{description}\n\n"
        f"SPL explanation:\n{_serialize_explanation(explanation)}"
    )
    return await _generate_with_retry(
        system_prompt=EVALUATE_QUALITY_PROMPT,
        user_message=user_message,
        schema=QualityRubric,
        model=_model_for(app_class),
    )


async def _generate_with_retry(
    system_prompt: str,
    user_message: str,
    schema: type[GeneratedDescription] | type[QualityRubric],
    model: str,
):
    client = _client()
    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        response = await client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            format=schema.model_json_schema(),
            options={"temperature": 0.2 if attempt == 0 else 0.4},
        )
        content = response["message"]["content"]
        try:
            return schema.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            last_error = exc
            continue
    raise LocalGenerationError(
        f"Ollama output failed schema validation after {_MAX_ATTEMPTS} attempts: {last_error}"
    )
