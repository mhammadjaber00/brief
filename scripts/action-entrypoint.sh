#!/usr/bin/env bash
set -euo pipefail

_input() {
    local val
    val="$(printenv "INPUT_$1" 2>/dev/null || true)"
    echo "${val:-$2}"
}

TARGET_PATH="$(_input TARGET-PATH '.')"
MODE="$(_input MODE 'offline')"
APP_CLASS="$(_input APP-CLASS 'auto')"
OUTPUT_DIR="$(_input OUTPUT-DIR 'brief-output')"
OPEN_PR="$(_input OPEN-PR 'true')"
FAIL_BELOW_SCORE="$(_input FAIL-BELOW-SCORE '70')"
SPLUNK_MCP_URL_INPUT="$(_input SPLUNK-MCP-URL '')"
SPLUNK_MCP_TOKEN_INPUT="$(_input SPLUNK-MCP-TOKEN '')"

WORKSPACE="${GITHUB_WORKSPACE:-/github/workspace}"
ABS_TARGET="${WORKSPACE}/${TARGET_PATH#./}"
ABS_OUTPUT="${WORKSPACE}/${OUTPUT_DIR#./}"

echo "Brief — Splunk Agent-Readiness Audit"
echo "  target:  $ABS_TARGET"
echo "  mode:    $MODE"
echo "  output:  $ABS_OUTPUT"

if [[ "$MODE" == "offline" ]] || [[ "$MODE" == "live" ]]; then
    echo "Starting Ollama daemon..."
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    for i in {1..30}; do
        if curl -s --connect-timeout 1 http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
            echo "  ollama up (pid $OLLAMA_PID)"
            break
        fi
        sleep 1
    done
    echo "  models available:"
    ollama list 2>&1 | sed 's/^/    /'
fi

if [[ -n "$SPLUNK_MCP_URL_INPUT" ]]; then
    export SPLUNK_MCP_URL="$SPLUNK_MCP_URL_INPUT"
fi
if [[ -n "$SPLUNK_MCP_TOKEN_INPUT" ]]; then
    export SPLUNK_MCP_TOKEN="$SPLUNK_MCP_TOKEN_INPUT"
fi

set +e
brief audit "$ABS_TARGET" \
    --output "$ABS_OUTPUT" \
    --mode "$MODE" \
    --app-class "$APP_CLASS"
AUDIT_EXIT=$?
set -e

if [[ ! -f "$ABS_OUTPUT/score.json" ]]; then
    echo "::error::brief audit did not produce $ABS_OUTPUT/score.json (exit $AUDIT_EXIT)"
    exit 2
fi

SCORE=$(jq -r '.overall_score' "$ABS_OUTPUT/score.json")
REPORT_PATH="$ABS_OUTPUT/report.html"
echo "score=$SCORE" >> "${GITHUB_OUTPUT:-/dev/stderr}"
echo "report-path=$REPORT_PATH" >> "${GITHUB_OUTPUT:-/dev/stderr}"
echo "Overall readiness: $SCORE/100"

DIFF_FILE="$ABS_OUTPUT/descriptions.diff"
PR_NUMBER=""
if [[ "$OPEN_PR" == "true" ]] && [[ -s "$DIFF_FILE" ]] && [[ -n "${GITHUB_TOKEN:-}" ]]; then
    echo "Opening follow-up PR with proposed description changes..."
    PR_NUMBER=$(python /brief/scripts/open_pr.py \
        --diff "$DIFF_FILE" \
        --score "$SCORE" \
        --report "$REPORT_PATH" \
        --workspace "$WORKSPACE" \
        || echo "")
elif [[ "$OPEN_PR" == "true" ]] && [[ ! -s "$DIFF_FILE" ]]; then
    echo "No description changes proposed — skipping follow-up PR."
fi
echo "pr-number=$PR_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stderr}"

if [[ "$FAIL_BELOW_SCORE" != "0" ]] && (( SCORE < FAIL_BELOW_SCORE )); then
    echo "::error::Agent-readiness score $SCORE is below the configured threshold $FAIL_BELOW_SCORE."
    exit 1
fi

exit 0
