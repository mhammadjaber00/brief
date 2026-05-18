# Brief — Agent-Readiness Auditor (Splunk app)

Brief packaged as a Splunk app. Runs on Splunk Enterprise 9.0+ and Splunk Cloud Platform. Installs a weekly scheduled audit and a dashboard that scores every other app on your deployment.

## What it does

Every Sunday at 03:00 (local time), the `brief_weekly_audit` saved search runs the `| briefaudit` custom command. The command iterates `$SPLUNK_HOME/etc/apps/`, runs the Brief pipeline against each one, and writes per-app readiness scores to the `brief_scores` index.

The **Readiness** dashboard then shows:
- Overall agent-readiness across all installed apps (single value, colour-coded)
- App ranking table with drill-down to per-app detail
- Top 5 worst-performing apps
- Subscore contribution per app (presence / quality / coverage / safety)
- 90-day trend line

## Install

1. Upload the `brief-app-0.1.0.spl` file via **Apps → Manage Apps → Install app from file**.
2. Restart Splunk when prompted.
3. Configure the service account — see RBAC below.
4. Open **Apps → Brief — Agent-Readiness Auditor**. The dashboard will be empty until the first audit runs (Sundays 03:00) or you trigger it manually.

To trigger immediately:

```spl
| briefaudit mode=live
```

## Required RBAC

The service account that owns the scheduled audit needs:

- Role: **`sc_admin`** (for cross-app enumeration — `mcp_user` alone can't see other apps)
- Capability: **`mcp_tool_admin`**

**Why:** `mcp_user` + `mcp_tool_execute` is the runtime role for ordinary agent-callable tools. Brief itself is doing cross-app reads against `$SPLUNK_HOME/etc/apps/` and needs the elevated capability to enumerate apps it doesn't own.

The agent must **not** run as the system user — per [splunk-sdk-python#753](https://github.com/splunk/splunk-sdk-python/pull/753). Create a dedicated user (e.g. `brief_agent`) with the role above.

## Hosted Models token (live mode)

For `mode=live`, Brief uses **Foundation-Sec-1.1-8B-Instruct** (security apps) and **gpt-oss-20b** (general apps) via Splunk Hosted Models. This requires a Splunk Cloud tenant with the AI Assistant for SPL ≥1.4.0 app installed.

The token is **not stored in the app config**. It comes from the running Splunk instance's MCP Server integration. Generate the bearer token from inside the **MCP Server app's** token UI (NOT from Settings → Tokens — that path was deprecated in MCP Server v1.0.0 and tokens generated there are rejected).

If Hosted Models is unavailable, the Brief pipeline transparently falls back to Ollama (offline mode). To force offline mode:

```spl
| briefaudit mode=offline
```

## Verifying installation

After install, on the Splunk search head:

1. Visit **Settings → Saved Searches → brief_weekly_audit** — confirm it's enabled and scheduled.
2. Run `| metadata type=indexes index=brief_scores` — confirm the index exists.
3. Run `| briefaudit limit=1` once to confirm the command dispatches without errors.

## Constraints

- Read-only access to other apps' filesystems. Brief never writes back to audited apps; it emits a diff via the CLI shape only.
- The custom command must complete within Splunk's 5-minute interactive search timeout. For deployments with >30 apps, run it as a scheduled report (not ad-hoc).
- No tokens are committed to the app. Admins configure live-mode credentials at install time.

## License

Apache-2.0. See the top-level [LICENSE](../../../LICENSE) at the repo root.
