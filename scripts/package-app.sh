#!/usr/bin/env bash
# Build brief-app-0.1.0.spl at repo root.
#
# Usage:
#   scripts/package-app.sh             # structure only (small, requires `splunk cmd python -m pip install brief` post-install)
#   scripts/package-app.sh --vendor    # also bundle deps into bin/lib/ (large, self-contained)
set -euo pipefail

REPO=$(git rev-parse --show-toplevel)
APP_DIR="$REPO/src/brief/app_splunk"
STAGING=$(mktemp -d)
STAGING_APP="$STAGING/brief"

cp -R "$APP_DIR" "$STAGING_APP"

if [[ "${1:-}" == "--vendor" ]]; then
  echo "Vendoring brief + dependencies into bin/lib/ (this can take a minute and produces a large .spl) ..."
  if [[ ! -x "$REPO/.venv/bin/pip" ]]; then
    echo "error: $REPO/.venv/bin/pip not found — create the venv first with 'python3.13 -m venv .venv && .venv/bin/pip install -e .'" >&2
    exit 1
  fi
  "$REPO/.venv/bin/pip" install --quiet --target "$STAGING_APP/bin/lib" --no-compile "$REPO"
fi

find "$STAGING_APP" \( -name "__pycache__" -o -name ".DS_Store" -o -name "*.pyc" -o -name "*.pyo" \) \
  -exec rm -rf {} + 2>/dev/null || true

if [[ -x "$REPO/.venv/bin/splunk-appinspect" ]]; then
  echo "Running splunk-appinspect on staging dir..."
  if ! "$REPO/.venv/bin/splunk-appinspect" inspect "$STAGING_APP" 2>&1 | tail -10; then
    echo "warning: appinspect returned non-zero — see output above" >&2
  fi
fi

OUTPUT="$REPO/brief-app-0.1.0.spl"
tar -czf "$OUTPUT" -C "$STAGING" brief

rm -rf "$STAGING"

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "Packaged: $OUTPUT ($SIZE)"
echo
echo "Verify contents:"
echo "  tar -tzf $OUTPUT | head -20"
echo
echo "Install on Splunk Enterprise:"
echo "  Apps → Manage Apps → Install app from file → upload $OUTPUT"
