"""Pydantic schema for generator output — the cross-module contract.

Pass this as ``response_model=GeneratedDescription`` to ``Agent.respond()``.
The splunk-sdk-python v3.0.0 SDK enforces the schema and auto-retries on
validation failure — do not catch ValidationError as a terminal failure.
"""

from typing import Literal

from pydantic import BaseModel, Field


class GeneratedDescription(BaseModel):
    description: str = Field(min_length=80, max_length=240)
    primary_use_case: str
    output_fields: list[str]
    mitre_techniques: list[str] | None = None
    estimated_runtime: Literal["fast", "medium", "slow"]
    suitable_for_agent: bool
