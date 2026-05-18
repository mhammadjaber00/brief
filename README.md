# Brief

Audit Splunk apps for AI-agent-readiness. Brief scans `.conf` metadata, uses the Splunk AI Assistant for SPL to understand each saved search, generates rich semantic descriptions, and emits three artifacts:

1. **Agent-readiness score** — per saved search and per app
2. **Unified-diff PR** — proposing description improvements (input files are never modified in place)
3. **MCP manifest** — declaring which searches are safe for agents to call

## Requirements

- Python **3.13**
- [splunk-sdk-python](https://github.com/splunk/splunk-sdk-python) **3.0.0**
- Splunk MCP Server **1.1.2** (Splunkbase app 7931)
- Splunk AI Assistant for SPL **≥1.4.0**
- Optional (offline mode): [Ollama](https://ollama.com) with `llama3.1:8b-instruct`

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
brief audit path/to/splunk-app --output ./brief-out
```

Add `--offline` to use the local Ollama fallback (useful for CI and dev). Without it, Brief talks to Splunk Hosted Models (Cloud-only).

## Project layout

See [docs/brief-spec.html](docs/brief-spec.html) for the canonical spec (§03 covers the pipeline, §06 covers the Splunk AI stack). Step-by-step playbooks: `docs/step-1.html` through `docs/step-9.html`.

## Architecture

See `architecture_diagram.md` (placeholder, finalized in Step 09).

## Hackathon admin (deferred)

- **W-8BEN form** — required for non-US prize recipients. Blank IRS form is at `forms/w8ben.pdf` (gitignored). Fill on award.
- **Prize payout** — Payoneer (not Wise).

## License

Apache-2.0. Full text in `LICENSE`.
