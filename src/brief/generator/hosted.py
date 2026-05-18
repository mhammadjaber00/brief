from __future__ import annotations

from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.spl.models import SPLExplanation


class HostedModelsUnavailable(Exception):
    pass


SECURITY_MODEL_ID = "Foundation-Sec-1.1-8B-Instruct"
GENERAL_MODEL_ID = "gpt-oss-20b"


def model_id_for(app_class: str) -> str:
    return SECURITY_MODEL_ID if app_class == "security" else GENERAL_MODEL_ID


async def generate_description_hosted(
    explanation: SPLExplanation,
    raw_spl: str,
    app_class: str,
) -> GeneratedDescription:
    raise HostedModelsUnavailable(
        f"Splunk Hosted Models ({model_id_for(app_class)}) require a Splunk Cloud tenant; "
        "not provisioned yet. Caller should fall back to the Ollama adapter."
    )


async def evaluate_quality_hosted(
    description: str,
    explanation: SPLExplanation,
    app_class: str,
) -> QualityRubric:
    raise HostedModelsUnavailable(
        f"Splunk Hosted Models ({model_id_for(app_class)}) require a Splunk Cloud tenant; "
        "not provisioned yet. Caller should fall back to the Ollama adapter."
    )
