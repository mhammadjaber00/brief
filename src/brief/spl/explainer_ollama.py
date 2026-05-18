from __future__ import annotations

import json
import os

from ollama import AsyncClient

from brief.spl.models import SPLExplanation
from brief.spl.prompts import OLLAMA_SYSTEM_PROMPT

_DEFAULT_MODEL = "llama3.1:8b"
_DEFAULT_HOST = "http://localhost:11434"


class OllamaExplanationError(Exception):
    pass


async def explain_via_ollama(spl: str) -> SPLExplanation:
    model = os.environ.get("OLLAMA_MODEL", _DEFAULT_MODEL)
    host = os.environ.get("OLLAMA_HOST", _DEFAULT_HOST)
    client = AsyncClient(host=host)

    response = await client.chat(
        model=model,
        messages=[
            {"role": "system", "content": OLLAMA_SYSTEM_PROMPT},
            {"role": "user", "content": f"Explain this SPL:\n\n{spl}"},
        ],
        format="json",
        options={"temperature": 0.1},
    )
    content = response["message"]["content"]

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OllamaExplanationError(f"model returned non-JSON: {content[:200]}") from exc

    payload.setdefault("indexes_queried", [])
    payload.setdefault("sourcetypes_filtered", [])
    payload.setdefault("fields_extracted", [])
    payload.setdefault("transformations", [])
    payload.setdefault("output_shape", "")
    payload.setdefault("summary", "")
    payload["source"] = "ollama"

    return SPLExplanation.model_validate(payload)
