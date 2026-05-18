from typing import Literal

from pydantic import BaseModel, Field


class GeneratedDescription(BaseModel):
    description: str = Field(min_length=80, max_length=240)
    primary_use_case: str = Field(max_length=120)
    output_fields: list[str]
    mitre_techniques: list[str] | None = None
    estimated_runtime: Literal["fast", "medium", "slow"]
    suitable_for_agent: bool
    reasoning: str = Field(max_length=300)


class QualityRubric(BaseModel):
    quality_score: int = Field(ge=0, le=10)
    is_tautology: bool
    specifies_data_source: bool
    specifies_use_case: bool
    actionable: bool
    reasoning: str
