from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from brief import generator, spl
from brief.generator.classifier import classify_app
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.scanner import scan_app
from brief.scanner.models import AppScanReport, ObjectSignals

Mode = Literal["live", "offline"]

_logger = logging.getLogger(__name__)


async def audit_app(
    path: Path,
    mode: Mode = "offline",
) -> tuple[AppScanReport, dict[str, GeneratedDescription], dict[str, QualityRubric]]:
    report = scan_app(path)
    app_class = classify_app(report)
    _logger.info("classified %s as %s", report.app_name, app_class)

    macros = _macros_dict(report.objects)
    proposed: dict[str, GeneratedDescription] = {}
    rubrics: dict[str, QualityRubric] = {}

    for obj in report.objects:
        if obj.object_type != "savedsearch":
            continue
        if not obj.raw_definition:
            continue
        try:
            explanation = await spl.explain(obj.raw_definition, macros, mode=mode)
        except Exception as exc:
            _logger.warning("failed to explain SPL for %s: %s", obj.name, exc)
            continue

        if obj.description_present:
            try:
                rubrics[obj.name] = await generator.evaluate(
                    description=obj.description_text or "",
                    explanation=explanation,
                    mode=mode,
                    app_class=app_class,
                )
            except Exception as exc:
                _logger.warning("failed to evaluate quality for %s: %s", obj.name, exc)
        else:
            try:
                proposed[obj.name] = await generator.generate(
                    explanation=explanation,
                    raw_spl=obj.raw_definition,
                    mode=mode,
                    app_class=app_class,
                )
            except Exception as exc:
                _logger.warning("failed to generate description for %s: %s", obj.name, exc)

    return report, proposed, rubrics


def _macros_dict(objects: list[ObjectSignals]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for obj in objects:
        if obj.object_type == "macro" and obj.raw_definition:
            out[obj.name] = {"definition": obj.raw_definition}
    return out


def build_brief_agent():
    """Construct a splunklib.ai.Agent that exposes Brief's pipeline as tools.

    Wires Brief's scanner / SPL explainer / generator into a `ToolRegistry`,
    allowlists those four tool names via `ToolSettings`, and wraps the lot in
    an `Agent` connected to the local Splunk Enterprise instance.

    Requires `SPLUNK_HOST` / `SPLUNK_TOKEN` (defaults to localhost + SPLUNK_MCP_TOKEN)
    and `ANTHROPIC_API_KEY` (the Agent's model). The deterministic Stage 1-4
    pipeline runs through `audit_app()` directly; this builder is the chat /
    tool-calling surface that demonstrates `splunklib.ai` usage.

    The state field is `Agent.messages` (PR #743), limits live in
    `splunklib.ai.limits` (PR #759), and the agent runs as the dedicated
    `brief_agent` Splunk user (never as system per PR #753).
    """
    from splunklib.ai import Agent, AnthropicModel
    from splunklib.ai.limits import AgentLimits
    from splunklib.ai.registry import ToolRegistry
    from splunklib.ai.tool_settings import LocalToolSettings, ToolAllowlist, ToolSettings
    from splunklib.client import connect

    host = os.environ.get("SPLUNK_HOST", "localhost")
    port = int(os.environ.get("SPLUNK_PORT", "8089"))
    token = os.environ.get("SPLUNK_TOKEN") or os.environ.get("SPLUNK_MCP_TOKEN")
    if not token:
        raise RuntimeError("SPLUNK_TOKEN (or SPLUNK_MCP_TOKEN) must be set to build the agent")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY required for build_brief_agent. Use audit_app() for the "
            "offline deterministic pipeline."
        )

    service = connect(host=host, port=port, token=token, scheme="https", verify=False)

    registry = ToolRegistry()

    @registry.tool(
        name="scan_app",
        description="Scan a Splunk app directory for AI-agent-readiness signals. "
        "Returns a structured AppScanReport with per-object signals, file coverage, "
        "embedded dashboard searches, and static SPL safety findings.",
    )
    def _scan_app(app_path: str) -> dict:
        return scan_app(Path(app_path)).model_dump()

    @registry.tool(
        name="explain_spl",
        description="Explain a Splunk SPL search. Returns a structured SPLExplanation with "
        "indexes_queried, sourcetypes_filtered, fields_extracted, transformations, "
        "output_shape, and a plain-English summary.",
    )
    async def _explain_spl(spl_query: str, mode: str = "offline") -> dict:
        explanation = await spl.explain(spl_query, macros={}, mode=mode)  # type: ignore[arg-type]
        return explanation.model_dump()

    @registry.tool(
        name="generate_description",
        description="Generate an agent-callable description (GeneratedDescription) for an SPL "
        "search, given its structured explanation and the app classification.",
    )
    async def _generate_description(
        explanation_json: dict,
        raw_spl: str,
        app_class: str,
        mode: str = "offline",
    ) -> dict:
        explanation = spl.SPLExplanation.model_validate(explanation_json)
        description = await generator.generate(
            explanation=explanation,
            raw_spl=raw_spl,
            mode=mode,  # type: ignore[arg-type]
            app_class=app_class,
        )
        return description.model_dump()

    @registry.tool(
        name="evaluate_quality",
        description="Score an existing saved-search description with the quality rubric: "
        "is_tautology, specifies_data_source, specifies_use_case, actionable, plus a 0-10 score.",
    )
    async def _evaluate_quality(
        description: str,
        explanation_json: dict,
        app_class: str,
        mode: str = "offline",
    ) -> dict:
        explanation = spl.SPLExplanation.model_validate(explanation_json)
        rubric = await generator.evaluate(
            description=description,
            explanation=explanation,
            mode=mode,  # type: ignore[arg-type]
            app_class=app_class,
        )
        return rubric.model_dump()

    allowlist = ToolAllowlist(
        names=["scan_app", "explain_spl", "generate_description", "evaluate_quality"]
    )

    return Agent(
        model=AnthropicModel(
            model="claude-sonnet-4-6",
            api_key=anthropic_key,
            base_url="https://api.anthropic.com",
        ),
        service=service,
        system_prompt=(
            "You audit Splunk apps for AI-agent-readiness. Use the registered tools to "
            "scan apps, explain saved searches, and propose descriptions. Brief never "
            "modifies Splunk state directly — all proposals go out as unified diffs that "
            "humans review and merge."
        ),
        tool_settings=ToolSettings(
            local=LocalToolSettings(allowlist=allowlist),
            remote=None,
        ),
        limits=AgentLimits(max_tokens=200_000, max_steps=100, timeout=600.0),
        name="brief",
        description="Brief — Splunk app auditing agent.",
    )
