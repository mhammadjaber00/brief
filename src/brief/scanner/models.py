from typing import Literal

from pydantic import BaseModel, Field

ObjectType = Literal["savedsearch", "macro", "eventtype", "tag", "transform", "command"]


class SafetyReport(BaseModel):
    safe: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ObjectSignals(BaseModel):
    name: str
    object_type: ObjectType
    description_present: bool
    description_text: str | None
    quality_score: float | None = None
    safety: SafetyReport
    raw_definition: str
    file_origin: str


class FileCoverage(BaseModel):
    file_name: str
    total_objects: int
    described_count: int
    coverage_pct: float


class EmbeddedSearch(BaseModel):
    dashboard: str
    panel: str | None
    query: str


class AppScanReport(BaseModel):
    app_name: str
    app_version: str | None
    app_description: str | None
    objects: list[ObjectSignals]
    file_coverage: list[FileCoverage]
    embedded_dashboard_searches: list[EmbeddedSearch]
