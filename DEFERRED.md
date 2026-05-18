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

## Step 09 — submission

### architecture_diagram.png
- **Status:** `architecture_diagram.md` placeholder satisfies the hackathon rule (accepts `.png` / `.md` / `.pdf` at repo root).
- **Why deferred:** finalize in Step 09 with the actual diagram.
- **Unblocks:** Steps 05–08 complete.

### Demo video (<3 min, public on YouTube/Vimeo)
- **Status:** not started.
- **Why deferred:** Step 09 task; needs the working pipeline to demo.
- **Unblocks:** code complete through Step 08.
