from __future__ import annotations

from pydantic import BaseModel

from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.scanner.models import AppScanReport


class ObjectScore(BaseModel):
    object_name: str
    presence: float
    quality: float
    safety: float
    composite: float


class FileScore(BaseModel):
    file_name: str
    coverage: float
    avg_quality: float
    composite: float


class AppScore(BaseModel):
    app_name: str
    overall_score: int
    presence_pct: int
    quality_avg: int
    coverage_pct: int
    safety_pct: int
    objects: list[ObjectScore]
    files: list[FileScore]


def _object_safety(violations: list[str], warnings: list[str]) -> float:
    if violations:
        return 0.0
    if warnings:
        return 0.5
    return 1.0


def _object_quality(
    description_present: bool,
    obj_name: str,
    quality_rubrics: dict[str, QualityRubric],
) -> float:
    if not description_present:
        return 0.0
    rubric = quality_rubrics.get(obj_name)
    if rubric is None:
        return 0.5
    return rubric.quality_score / 10.0


def score_app(
    report: AppScanReport,
    descriptions: dict[str, GeneratedDescription],
    quality_rubrics: dict[str, QualityRubric],
) -> AppScore:
    del descriptions

    objects: list[ObjectScore] = []
    file_origin_by_name: dict[str, str] = {}

    for obj in report.objects:
        if obj.object_type != "savedsearch":
            continue
        file_origin_by_name[obj.name] = obj.file_origin
        presence = 1.0 if obj.description_present else 0.0
        quality = _object_quality(obj.description_present, obj.name, quality_rubrics)
        safety = _object_safety(obj.safety.violations, obj.safety.warnings)
        composite = 0.4 * presence + 0.3 * quality + 0.3 * safety
        objects.append(
            ObjectScore(
                object_name=obj.name,
                presence=presence,
                quality=quality,
                safety=safety,
                composite=composite,
            )
        )

    by_file: dict[str, list[ObjectScore]] = {}
    for os_ in objects:
        by_file.setdefault(file_origin_by_name[os_.object_name], []).append(os_)

    files: list[FileScore] = []
    for file_name, file_objects in by_file.items():
        n = len(file_objects)
        files.append(
            FileScore(
                file_name=file_name,
                coverage=sum(o.presence for o in file_objects) / n,
                avg_quality=sum(o.quality for o in file_objects) / n,
                composite=sum(o.composite for o in file_objects) / n,
            )
        )

    if not objects:
        return AppScore(
            app_name=report.app_name,
            overall_score=0,
            presence_pct=0,
            quality_avg=0,
            coverage_pct=0,
            safety_pct=0,
            objects=[],
            files=[],
        )

    n = len(objects)
    presence_pct = round(sum(o.presence for o in objects) / n * 100)
    quality_avg = round(sum(o.quality for o in objects) / n * 100)
    coverage_pct = (
        round(sum(f.coverage for f in files) / len(files) * 100) if files else 0
    )
    safety_pct = round(sum(o.safety for o in objects) / n * 100)
    overall_score = round(
        0.4 * presence_pct + 0.3 * quality_avg + 0.2 * coverage_pct + 0.1 * safety_pct
    )

    return AppScore(
        app_name=report.app_name,
        overall_score=overall_score,
        presence_pct=presence_pct,
        quality_avg=quality_avg,
        coverage_pct=coverage_pct,
        safety_pct=safety_pct,
        objects=objects,
        files=files,
    )
