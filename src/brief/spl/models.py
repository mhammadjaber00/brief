from typing import Literal

from pydantic import BaseModel, Field

ExplanationSource = Literal["saia", "ollama"]


class SPLExplanation(BaseModel):
    indexes_queried: list[str] = Field(default_factory=list)
    sourcetypes_filtered: list[str] = Field(default_factory=list)
    fields_extracted: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)
    output_shape: str
    summary: str
    source: ExplanationSource
