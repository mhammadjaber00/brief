---
name: brief
description: Project context, tech-stack pins, and critical pitfalls for Brief — the AI agent that audits Splunk apps for AI-agent-readiness. Use this whenever the user works on the Brief project, scaffolds or edits anything under `brief/`, writes code that imports `splunklib.ai`, integrates with the Splunk MCP Server (Splunkbase app 7931), generates descriptions for Splunk saved searches, calls `saia_explain_spl`, uses Foundation-Sec-1.1-8B-Instruct or gpt-oss-20b, builds the MCP manifest YAML, or asks about the hackathon deadline. Also trigger when the user mentions "Splunk app readiness", "splunk audit", "saved-search descriptions", "MCP manifest for Splunk", "savedsearches.conf", or any of the pinned versions/PRs listed in this skill (#743, #753, #759, #724). Use it even when the user does not explicitly say "Brief" — Splunk + AI agent context is enough.
---

# Brief — Splunk App Auditing Agent

Brief audits Splunk apps for AI-agent-readiness. It scans `.conf` metadata, uses the Splunk AI Assistant for SPL to understand each saved search, generates rich semantic descriptions with Foundation-Sec or gpt-oss-20b, and emits three artifacts:

1. Agent-readiness score (per saved search, per app)
2. Unified-diff PR proposing description improvements
3. MCP manifest declaring which searches are safe for agents to call

This is a hackathon submission. **Track: Platform & Developer Experience.** **Submit by EOD 2026-06-14** (deadline is 2026-06-15 09:00 PDT — don't trust the portal on deadline day). Stackable bonus prizes: Best Use of Developer Tools, MCP Server, Hosted Models.

The canonical spec lives at [docs/brief-spec.html](docs/brief-spec.html). Read §03 (pipeline) and §06 (Splunk AI stack) before writing any agent code. Step-by-step playbooks are at `docs/step-1.html` through `docs/step-9.html`.

## Pinned versions

| Component | Version | Notes |
|---|---|---|
| Python | 3.13 | Required by splunk-sdk 3.0.0 |
| splunk-sdk | 3.0.0 | Install as `splunk-sdk[ai]==3.0.0` — `[ai]` extras pulls in `mcp`, `langchain`, `pydantic`, `httpx`. **PyPI name is `splunk-sdk`** (the GitHub repo is `splunk-sdk-python`, hence the PR numbers below). |
| Splunk MCP Server | 1.1.2 | Splunkbase app 7931 |
| Splunk AI Assistant for SPL | ≥1.4.0 | Exposes `saia_explain_spl` as MCP tool |
| Hosted Models | Foundation-Sec-1.1-8B-Instruct (security apps), gpt-oss-20b (general apps) | Reachable via Splunk Cloud-Connected SAIA (paid tier) OR via local Ollama using the open-weight versions (Foundation-Sec at `fdtn-ai/Foundation-Sec-1.1-8B-Instruct` on HF, gpt-oss-20b at `ollama.com/library/gpt-oss:20b`). |
| AppInspect | latest | Safety validation |
| Local Ollama models | `gpt-oss:20b` (default for both classes; in Ollama library), `foundation-sec:8b` (security preferred; created via `scripts/install-foundation-sec.sh` from the public HF safetensors) | Auto-routed by `brief.generator.local._model_for(app_class)`. Override via `BRIEF_MODEL_SECURITY` / `BRIEF_MODEL_GENERAL`. |

Choose Foundation-Sec when the app's CIM data models or sourcetypes indicate security telemetry (auth, endpoint, network traffic, threat intel). Default to gpt-oss-20b otherwise. The scanner emits an `app_category` signal — use it to route.

## Critical SDK pitfalls — these fail silently

The splunk-sdk-python v3.0.0 release renamed/moved several things from older tutorials. If agent loops break in confusing ways, re-check these first.

1. **Agent state is `Agent.messages`, not `Agent.response`.** Renamed in splunk-sdk-python#743. Older tutorials show `.response` — those are wrong for v3.0.0 and reading from `.response` returns `None` rather than raising.
2. **Token/step/timeout middleware lives in `splunklib.ai.limits`, not `splunklib.ai.hooks`.** Moved in splunk-sdk-python#759. Importing from `.hooks` raises ImportError at agent-startup time, which can look like an unrelated failure further down the trace.
3. **`id` is required (non-nullable) on tool, subagent, and output calls.** Enforced by splunk-sdk-python#724. Generate UUIDs explicitly — the SDK will not auto-generate.
4. **Default `AgentLimits`**: `max_tokens=200000`, `max_steps=100`, `timeout=600s`. Brief's audit sessions can outrun these for large apps — override at agent construction.
5. **Structured output via `Agent.respond(response_model=…)` auto-retries on schema failure.** Don't wrap it in a try/except that catches `ValidationError` and gives up; let the SDK retry. Only bail after the SDK's own retry exhaustion.
6. **SDK tool API is `splunklib.ai.registry.ToolRegistry`** with `@registry.tool(name=..., description=...)` as a decorator (not `registry.add()` — older drafts of the spec are wrong about that). Pass tools to the Agent via `ToolSettings(local=LocalToolSettings(allowlist=ToolAllowlist(names=[...])), remote=None)` — the Agent looks up by name through the allowlist, not by a registry handoff. `Agent` also requires `service: splunklib.client.Service` and a concrete model (`AnthropicModel` / `OpenAIModel` / `GoogleModel`). Hosted Models are reached as `PredefinedModel` subtypes only when running inside Splunk Cloud.

## Critical Splunk pitfalls

1. **Generate MCP bearer tokens from inside the MCP Server app.** The Settings → Tokens path was deprecated in MCP Server v1.0.0 — tokens from there are silently rejected.
2. **Do NOT use OAuth 2.1.** It's a closed Cloud-only preview, requires Twix 10.3.2512.X, and needs ~1 week of Splunk Identity Service team coordination. Static encrypted bearer tokens are the supported hackathon path.
3. **MCP guardrails for `splunk_run_query`**: ≤60s runtime, ≤1000 events, no destructive SPL (no `| delete`, no `| outputlookup` to destructive paths). Brief's safety analyzer enforces this statically before flagging a search as agent-callable. If a saved search violates a guardrail, mark `suitable_for_agent=False` and explain why in the report.
4. **Roles**: `mcp_user` with `mcp_tool_execute` is the minimum runtime role. Brief itself, doing cross-app enumeration in the Splunk app deployment shape, needs `sc_admin` with `mcp_tool_admin`.
5. **Agent must NOT run as the system user.** splunk-sdk-python#753 forbids it. Create a dedicated user (e.g., `brief_agent`) before deploying.
6. **Splunk Hosted Models are Cloud-only.** They cannot be reached from offline development. Use the Ollama adapter for CLI and GitHub Action modes; Hosted Models are reached only when Brief runs as a Splunk app inside Splunk Cloud.
7. **Splunk on macOS Apple Silicon is a dev dead-end for the Splunk-app shape.** Splunk runs through Rosetta as x86_64 Python with hardened-runtime + library validation enabled. Vendored native extensions (`pydantic_core`, `lxml`, `cryptography`, etc.) get rejected at `dlopen` with "Team ID mismatch" — even after ad-hoc signing — because Splunk's Python has a real Team ID and macOS won't load no-Team-ID libraries into it. Workarounds modify Splunk's binary and break on updates. **For local Mac dev, use the CLI shape.** Splunk-app shape targets `--vendor=linux` (Splunk Cloud, on-prem Linux Splunk).

## File structure

```
brief/
├── pyproject.toml
├── src/brief/
│   ├── __init__.py
│   ├── agent.py                  # The splunklib.ai Agent
│   ├── scanner/                  # Stage 1: metadata + safety
│   │   ├── conf_parser.py
│   │   ├── xml_parser.py
│   │   ├── safety.py
│   │   └── signals.py
│   ├── spl/                      # Stage 2: SPL understanding
│   │   ├── macro_expander.py
│   │   └── explainer.py          # saia_explain_spl wrapper
│   ├── generator/                # Stage 3: description generation
│   │   ├── schema.py             # Pydantic GeneratedDescription
│   │   ├── hosted.py             # Splunk Hosted Models adapter
│   │   └── local.py              # Ollama fallback
│   ├── scoring/
│   │   └── score.py
│   ├── emit/                     # Stage 4: artifacts
│   │   ├── diff.py
│   │   ├── manifest.py
│   │   └── report.py
│   ├── cli.py                    # Entry point (typer)
│   └── app_splunk/               # Splunk app deployment shape
├── action.yml                    # GitHub Action manifest
├── Dockerfile                    # For Action container
├── tests/fixtures/               # Sample Splunk apps
├── docs/                         # brief-spec.html + step-*.html
└── architecture_diagram.png      # Required by hackathon rules
```

Prefer many small files over one large module — readers (humans and agents) orient faster.

## The generation contract — Pydantic schema

```python
from typing import Literal
from pydantic import BaseModel, Field

class GeneratedDescription(BaseModel):
    description: str = Field(min_length=80, max_length=240)
    primary_use_case: str = Field(max_length=120)
    output_fields: list[str]
    mitre_techniques: list[str] | None = None  # security apps only
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
```

`GeneratedDescription` is the new-description contract; `QualityRubric` scores existing descriptions. Hosted Models route through `splunklib.ai`'s structured output (auto-retries bad schemas — don't catch). The Ollama adapter passes `format=Schema.model_json_schema()` to `AsyncClient.chat` and retries up to 3× on `ValidationError`.

## Description quality rules

Foundation-Sec / gpt-oss-20b should produce descriptions that:

- **Lead with a verb** — "Returns…", "Counts…", "Detects…", not "This search…"
- **Name specifics** — event IDs, sourcetypes, indexes that actually appear in the SPL
- **State the canonical use case** — "Use for credential stuffing investigations"
- **Put MITRE technique IDs in `mitre_techniques`**, never in prose
- **Avoid hedging** — no "might", "possibly", "could be useful for"

Why: agents calling these searches need crisp, factual handles. Hedging makes descriptions useless as routing signals.

## MCP manifest schema

```yaml
app: TA_security_monitoring
tools:
  - name: get_failed_auth_24h
    saved_search: get_failed_auth_24h
    description: |
      Returns count of failed Linux SSH logins (event 4625) by user
      and source IP in the last 24h. Use for credential stuffing.
    output_fields: [user, src_ip, count]
    mitre_techniques: [T1110.001, T1078]
    rbac_role: mcp_user
    estimated_runtime: fast
```

Only emit a tool entry when `suitable_for_agent` is true AND the safety analyzer passed.

## Code conventions

- **Type hints everywhere.** Python 3.13 native syntax: `list[str]`, `dict[K, V]`, `X | Y`. No `typing.List`, no `Optional[X]`.
- **Pydantic** for cross-module data models; **dataclasses** for internal-only state.
- **`pathlib.Path` always** — never `os.path` string concatenation.
- **Logging via `structlog`** — never `print()`.
- **`async`** for: agent calls, MCP calls, parallel SPL explanation in batch mode. Synchronous code is fine for parsers and local I/O.
- **Module size**: prefer many small files over one large module.
- **Docstrings** on every public function. Include an example when behavior isn't obvious from the signature.

## Testing

- `pytest` for everything.
- 2–3 sample Splunk apps committed to `tests/fixtures/`.
- Mock Splunk Hosted Models with the local Ollama adapter — tests run offline.
- **Snapshot test the diff PR outputs.** Generation changes are then reviewable in git.
- Integration test: end-to-end CLI run on a fixture app, assert score > 80%.

## Output conventions

- All artifacts go to a configurable `--output` directory.
- Default file names: `report.html`, `score.json`, `descriptions.diff`, `mcp_manifest.yaml`.
- **Never modify input files in place.** Brief proposes via diff; humans approve via PR merge.

## Hackathon-required artifacts

- Public GitHub repo with detectable OSI license — **Apache 2.0** chosen.
- README with setup + dependency list.
- Demo video < 3 minutes, public on YouTube or Vimeo.
- File at repo root named exactly `architecture_diagram.png` (or `.md` or `.pdf`).

## Timeline checkpoints

- 28 days total: 2026-05-18 → 2026-06-15.
- **Submit by EOD 2026-06-14.** Never trust the portal on deadline day.
- Step 09 (demo + submission) reserves Week 4 — protect that buffer.
- Splunk Enterprise trial expires 2026-07-17 (winners' day); Developer License extends to 6 months — **apply within the first 7 days**.
- Splunk Cloud trial provisioning takes 24–48h; **apply Day 1**.

## When in doubt

`docs/brief-spec.html` is canonical. If this skill and the spec disagree, the spec wins and this skill should be updated.
