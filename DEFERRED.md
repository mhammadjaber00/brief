# Deferred items

Items the spec calls for that are intentionally not done yet. Each entry lists what's deferred, why, what unblocks it, and what fallback (if any) is wired up in the meantime. Update as blockers clear.

## Step 01 — admin

### W-8BEN tax form
- **Status:** blank PDF at `forms/w8ben.pdf` (gitignored).
- **Why deferred:** filled on award.
- **Unblocks:** prize notification.

### Splunk Cloud trial
- **Status:** registered Day 1 (2026-05-18).
- **Why deferred:** provisioning takes 24–48h, then full activation can take longer.
- **Unblocks:** confirmed provisioned tenant.

## Step 03 — SPL comprehension

### SAIA live path (`saia_explain_spl`)
- **Status:** `src/brief/spl/explainer_saia.py` implemented and dispatches via the MCP `saia_explain_spl` tool, which is registered (confirmed by `scripts/connection_test.py` — 14 tools, including `saia_explain_spl`). Runtime calls will fail until the SAIA cloud tenant is provisioned.
- **Why deferred:** the Splunk AI Assistant "Create tenant code" setup needs an onboarding specialist (~days) — not hackathon-friendly.
- **Unblocks:** complete the form at `localhost:8000/en-US/app/Splunk_AI_Assistant_Cloud/setup` (Company name, region, work email, tenant agreement) and wait for activation.
- **Fallback in place:** `brief.spl.explain(mode="live")` catches `SaiaExplanationError` and falls back to Ollama. Tests cover this path.

## Step 04 — generation + agent

### Hosted Models adapter (Foundation-Sec-1.1-8B-Instruct, gpt-oss-20b)
- **Status:** `src/brief/generator/hosted.py` stubs raise `HostedModelsUnavailable`.
- **Why deferred:** Hosted Models are Splunk Cloud only; SAIA cloud tenant not provisioned.
- **Unblocks:** Cloud tenant active + Hosted Models endpoint reachable.
- **Fallback in place:** `brief.generator.generate(mode="live")` catches `HostedModelsUnavailable` and falls back to Ollama. Tests cover this.

### splunklib.ai.Agent end-to-end runtime verification
- **Status:** `build_brief_agent()` (in `src/brief/agent.py`) constructs the real Agent with the correct SDK shape — `ToolRegistry` with `@registry.tool` decorator, `ToolAllowlist` allowlist, `ToolSettings`, `AnthropicModel`, `AgentLimits`, `splunklib.client.connect` for the `service`. Construction not exercised at runtime.
- **Why deferred:** the chat/tool loop needs `ANTHROPIC_API_KEY` (or Cloud Hosted Models) to actually invoke the model. The deterministic Stage 1-4 pipeline runs through `audit_app()` and doesn't go through the SDK Agent.
- **Unblocks:** set `ANTHROPIC_API_KEY` and run an interactive Agent session to verify `Agent.messages` state tracking (the PR #743 surface). Or wait for Cloud Hosted Models.
- **What the spec wanted:** "Agent state is correctly tracked via `.messages` — verify by inspecting the agent run trace." Construction is correct; trace inspection waits.

## Step 07 — Splunk app deployment shape

### Install + dashboard render on local Splunk Enterprise
- **Status:** `brief-app-0.1.0.spl` packages cleanly. AppInspect: 0 errors, 0 failures, 0 future-failures, 3 warnings, 108 successes against the staging dir.
- **Why deferred:** requires running Splunk Enterprise with ≥3 other apps installed for the dashboard panels to populate. Manual step on your side.
- **Unblocks:** install the .spl on local Splunk → confirm the **Brief — Agent-Readiness** app appears under Apps → open the dashboard → trigger `| briefaudit limit=1` once to seed the `brief_scores` index.

### Vendored dependencies for self-contained .spl
- **Status:** `scripts/package-app.sh` supports `--vendor` to bundle `brief` + its dependencies into `bin/lib/` for the custom search command. Default is structure-only (small .spl, requires `splunk cmd python -m pip install brief` post-install).
- **Why deferred:** vendored deps need to target Splunk's bundled Python (Linux x86_64). Building on macOS produces native binaries that don't run on Linux Splunk. Needs a cross-platform build (manylinux wheels via `--platform`) for a portable .spl.
- **Fallback in place:** the structure-only .spl is sufficient for AppInspect validation + Splunkbase upload shape. Functional verification needs the post-install pip step or a vendored build.

## Step 09 — submission

### architecture_diagram.png
- **Status:** `architecture_diagram.md` placeholder satisfies the hackathon rule (accepts `.png` / `.md` / `.pdf` at repo root).
- **Why deferred:** finalize in Step 09 with the actual diagram.
- **Unblocks:** Steps 05–08 complete.

### Demo video (<3 min, public on YouTube/Vimeo)
- **Status:** not started.
- **Why deferred:** Step 09 task; needs the working pipeline to demo.
- **Unblocks:** code complete through Step 08.
