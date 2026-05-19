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
| `OLLAMA_MODEL` | Override the model for both classes (rarely set; prefer per-class envs below) |
| `BRIEF_MODEL_SECURITY` | Ollama model tag for security-classified apps (default `gpt-oss:20b`; recommended `foundation-sec:8b`) |
| `BRIEF_MODEL_GENERAL` | Ollama model tag for general apps (default `gpt-oss:20b`) |

Tokens are wrapped in Pydantic's `SecretStr` and never appear in logs or `repr()`.

## Splunk Hosted Models

Brief routes saved searches to one of the two Splunk Hosted Models depending on the app classifier's verdict:

| App class | Model | Source |
|---|---|---|
| security | **Foundation-Sec-1.1-8B-Instruct** | [`fdtn-ai/Foundation-Sec-1.1-8B-Instruct`](https://huggingface.co/fdtn-ai/Foundation-Sec-1.1-8B-Instruct) |
| general | **gpt-oss-20b** | Ollama Library (`gpt-oss:20b`) |

Both are reached two ways: via **Splunk Cloud-Connected SAIA** when the tenant tier allows, or via **local Ollama** with the open-weight models. Brief tries Cloud-Connected first in `--mode live`, falls back to local Ollama, and falls back again to `gpt-oss:20b` if Foundation-Sec isn't installed.

### Live demo of the `splunklib.ai.Agent` (free)

`scripts/demo-agent.py` constructs Brief's real `splunklib.ai.Agent`, registers the pipeline as `ToolRegistry` tools, and invokes it on a fixture app. Default provider is **Gemini 2.5 Flash** via Google AI Studio's free tier.

```bash
# Get a free key at https://aistudio.google.com/apikey, then:
export GEMINI_API_KEY=your-key-here
.venv/bin/python scripts/demo-agent.py

# Or against a different fixture / use Anthropic Claude:
.venv/bin/python scripts/demo-agent.py google tests/fixtures/ta-osquery
.venv/bin/python scripts/demo-agent.py anthropic   # needs ANTHROPIC_API_KEY
```

Shows the Agent name, tool allowlist, AgentLimits, then runs an end-to-end audit query and prints the agent's final answer.

### Set up Foundation-Sec locally (optional)

The Foundation-Sec weights aren't on Ollama's default library yet. One-time setup downloads the safetensors from HuggingFace and registers them with Ollama:

```bash
scripts/install-foundation-sec.sh
```

~16GB download + ~5GB conversion. After this, `BRIEF_MODEL_SECURITY` automatically resolves to `foundation-sec:8b` and Brief uses it for any app the classifier tags as security.

Without this step, Brief uses `gpt-oss:20b` for both classes — still a Splunk Hosted Model, just not the security-fine-tuned one.

## Project layout

See [docs/brief-spec.html](docs/brief-spec.html) for the canonical spec (§03 covers the pipeline, §06 covers the Splunk AI stack). Step-by-step playbooks: `docs/step-1.html` through `docs/step-9.html`.

## Use as a GitHub Action

Drop this into `.github/workflows/audit.yml` in any Splunk-app repository:

```yaml
on:
  pull_request:
    paths: ['**.conf', '**/views/*.xml']

permissions:
  contents: write
  pull-requests: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: mhammadjaber00/brief@v1
        with:
          target-path: '.'
          mode: 'offline'
          fail-below-score: '70'
          open-pr: 'true'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

What it does on every PR that touches `.conf` or dashboard XML:

1. Scans the app, explains every saved search, generates descriptions for the undescribed ones (Ollama, fully offline by default — no network calls beyond the GitHub API).
2. Posts a comment on the PR with the readiness score.
3. Opens a follow-up PR with the proposed `description = …` inserts as a unified diff. Reviewers merge it (or not) — Brief never modifies the original PR's files.
4. Fails the workflow if the score is below `fail-below-score`.

For live mode (Splunk Hosted Models): pass `SPLUNK_MCP_URL` / `SPLUNK_MCP_TOKEN` as workflow secrets.

## Architecture

See `architecture_diagram.md` (placeholder, finalized in Step 09).

## Hackathon admin (deferred)

- **W-8BEN form** — required for non-US prize recipients. Blank IRS form is at `forms/w8ben.pdf` (gitignored). Fill on award.
- **Prize payout** — Payoneer (not Wise).

## License

Apache-2.0. Full text in `LICENSE`.
