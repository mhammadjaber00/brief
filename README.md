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

Two commands:

```bash
# Stage 1 only — fast structural audit, no LLM calls
brief scan path/to/splunk-app

# Full pipeline — scan, explain, generate, score, emit four artifacts
brief audit path/to/splunk-app --output ./brief-out
```

### `brief audit` flags
- `--mode offline|live` — generation backend. `offline` uses Ollama; `live` tries Splunk Hosted Models and falls back to Ollama. Default: `offline`.
- `--app-class auto|security|general` — override the classifier. Default: `auto`.
- `--model NAME` — override the Ollama model name (default: `llama3.1:8b`).
- `--verbose / -v` — show per-stage trace output.
- `--output / -o DIR` — output directory for artifacts (default: `./brief-out`).

Exit codes: `0` clean, `1` partial (some descriptions couldn't be generated), `2` setup error (bad path, bad flag value, scan failure).

### `brief scan` flags
- `--format table|json` — output format. Default: `table`.
- `--output / -o PATH` — also write the JSON report to this path.

## Configuration

Brief reads configuration from environment variables (and a local `.env` file if present). Copy `.env.example` to `.env` and fill in the values.

| Variable | Purpose |
|---|---|
| `SPLUNK_MCP_URL` | Splunk MCP Server endpoint (e.g. `https://localhost:8089/services/mcp`) |
| `SPLUNK_MCP_TOKEN` | Bearer token generated **from inside the MCP Server app** (never from Settings → Tokens) |
| `SPLUNK_CLOUD_HOST` | Splunk Cloud host for Hosted Models (live mode) — leave blank for offline |
| `SPLUNK_CLOUD_TOKEN` | Splunk Cloud token for Hosted Models |
| `OLLAMA_HOST` | Ollama daemon URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama model tag (default `llama3.1:8b`) |

Tokens are wrapped in Pydantic's `SecretStr` and never appear in logs or `repr()`.

## Project layout

See [docs/brief-spec.html](docs/brief-spec.html) for the canonical spec (§03 covers the pipeline, §06 covers the Splunk AI stack). Step-by-step playbooks: `docs/step-1.html` through `docs/step-9.html`.

## Architecture

See `architecture_diagram.md` (placeholder, finalized in Step 09).

## Hackathon admin (deferred)

- **W-8BEN form** — required for non-US prize recipients. Blank IRS form is at `forms/w8ben.pdf` (gitignored). Fill on award.
- **Prize payout** — Payoneer (not Wise).

## License

Apache-2.0. Full text in `LICENSE`.
