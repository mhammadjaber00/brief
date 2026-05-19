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

### Hosted Models via Cloud-Connected SAIA endpoint
- **Status:** `src/brief/generator/hosted.py` stubs raise `HostedModelsUnavailable`. The Cloud-Connected SAIA endpoint is **paid-tier gated** on Splunk Cloud — Cloud Free Trial cannot provision a Cloud-Connected tenant (confirmed via the "Tenant code cannot be generated, This operation is not supported in cloud stack" error on the setup form).
- **What works instead:** the same Hosted Models are reachable via **local Ollama** using their open-weight versions: `gpt-oss:20b` (from Ollama Library) and `foundation-sec:8b` (created via `scripts/install-foundation-sec.sh` from the public `fdtn-ai/Foundation-Sec-1.1-8B-Instruct` HF safetensors). `brief.generator.local._model_for(app_class)` routes accordingly.
- **What's still deferred:** the Cloud-Connected endpoint adapter itself. Wire-up is straightforward when a paid Cloud tenant is available.
- **Unblocks:** Splunk Cloud paid tier with Cloud-Connected enabled, then implement the `splunklib.ai`-based hosted call in `generator/hosted.py`.

### SAIA `saia_explain_spl` for Stage 2
- **Status:** MCP wire-up confirmed (server identifies as `Splunk_MCP_Server v1.1.2`, token auth works, tool registers). Runtime call returns "Service not initialized, please contact support."
- **Why deferred:** same paid-tier gate — `saia_explain_spl` is backed by the Cloud-Connected service.
- **Fallback in place:** `brief.spl.explain(mode="live")` catches `SaiaExplanationError` and falls back to Ollama. Pipeline runs end-to-end either way.

### splunklib.ai.Agent end-to-end runtime verification
- **Status:** `build_brief_agent(provider="google"|"anthropic")` constructs the real Agent with the correct SDK shape — `ToolRegistry` with `@registry.tool` decorator, `ToolAllowlist`, `ToolSettings`, `GoogleModel`/`AnthropicModel`, `AgentLimits`, `splunklib.client.connect` for the `service`. Live runtime demoable via `scripts/demo-agent.py`.
- **Unblock:** `export GEMINI_API_KEY=...` (free at https://aistudio.google.com/apikey) then run `scripts/demo-agent.py`. Output captures the Agent run trace including tool calls — that's the `Agent.messages` state surface PR #743 introduced.
- **What the spec wanted:** "Agent state is correctly tracked via `.messages` — verify by inspecting the agent run trace." Demo script makes this trivial to record for the submission video.

## Step 07 — Splunk app deployment shape

### Splunk-app runtime verification on Splunk Cloud
- **Status:** `brief-app-0.1.0.spl` packages cleanly with `scripts/package-app.sh --vendor=linux` (24MB, manylinux2014_x86_64 wheels). AppInspect: 0 errors, 0 failures, 0 future-failures, 3 warnings, 108 successes against the staging dir. Dashboard XML, saved searches, and the `| briefaudit | collect index=brief_scores` flow are all wired.
- **Why deferred:** Splunk Cloud trial provisioning is still pending (see top of this file). Live runtime verification (install → trigger audit → confirm dashboard populates) waits for the Cloud tenant.
- **Unblocks:** Cloud trial activates → upload `brief-app-0.1.0.spl` via Cloud's app manager → grant `brief_agent` the `sc_admin` + `mcp_tool_admin` capability → run `| briefaudit mode=live limit=3 | collect index=brief_scores marker="brief_audit"` once → open the Readiness dashboard.

### Won't-do: local Splunk Enterprise on Apple Silicon
- **Status:** confirmed incompatible. Splunk on macOS arm64 runs under Rosetta as x86_64 Python with hardened-runtime + library validation. Vendored native extensions (`pydantic_core`, `lxml`, `cryptography`, etc.) get rejected at `dlopen` with "Team ID mismatch" — even after ad-hoc signing — because the Splunk Python binary has a real Team ID and macOS refuses to load no-Team-ID libraries into it.
- **Why won't-do:** the only workarounds modify Splunk's Python binary (`codesign -fs - /Applications/Splunk/bin/python3`) and risk breaking on Splunk's auto-update. Not worth pursuing for a hackathon when Splunk Cloud (the real target) has no such restriction.
- **For local Brief demo on Mac:** use the CLI (`brief audit tests/fixtures/sample-ta-1`). It produces identical artifacts to what the Splunk-app shape would emit. Same HTML report, same MCP manifest, same diff.

## Step 08 — GitHub Action shape

### Action runtime verification on GitHub Actions runners
- **Status:** action files committed (action.yml, Dockerfile, .dockerignore, entrypoint script, open_pr.py, self-test workflow). Local docker build skipped because Docker daemon wasn't running.
- **Why deferred:** verification needs either a PR to this repo (which triggers `test-action.yml` on `ubuntu-latest`) or manual `workflow_dispatch`. Both are easy but require a human click.
- **Unblocks:** GitHub Actions → "Self-test the Brief action" → "Run workflow" (workflow_dispatch). Confirm: Docker image builds, Brief audits `tests/fixtures/sample-ta-1/`, `brief-output/` artifact uploads with all four files.

### Marketplace listing
- **Status:** action.yml has `name`, `description`, `author`, `branding` — Marketplace-ready metadata.
- **Why deferred:** publishing to the Marketplace requires tagging a release (`v1`), opting in via GitHub's repository settings, and providing a logo. Logo and Step 09 demo screenshots come together.
- **Unblocks:** create a release tag (`git tag -a v1.0.0 -m "Initial release"; git push --tags`), then in Repository → Releases → "Publish this Action to the GitHub Marketplace". Logo image needed.

## Step 09 — submission

### architecture_diagram.png
- **Status:** `architecture_diagram.md` placeholder satisfies the hackathon rule (accepts `.png` / `.md` / `.pdf` at repo root).
- **Why deferred:** finalize in Step 09 with the actual diagram.
- **Unblocks:** Steps 05–08 complete.

### Demo video (<3 min, public on YouTube/Vimeo)
- **Status:** not started.
- **Why deferred:** Step 09 task; needs the working pipeline to demo.
- **Unblocks:** code complete through Step 08.
