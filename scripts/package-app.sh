#!/usr/bin/env bash
# Build brief-app-0.1.0.spl at repo root.
#
# Usage:
#   scripts/package-app.sh                  # structure only (8K, requires post-install pip in Splunk)
#   scripts/package-app.sh --vendor=macos   # vendor macOS x86_64 wheels (local Splunk Enterprise on Mac, runs under Rosetta)
#   scripts/package-app.sh --vendor=linux   # vendor manylinux x86_64 wheels (Splunk Cloud, Linux Splunk hosts)
#   scripts/package-app.sh --vendor         # vendor host-native (rarely what you want — only works if Splunk runs your host's arch)
set -euo pipefail

REPO=$(git rev-parse --show-toplevel)
APP_DIR="$REPO/src/brief/app_splunk"
STAGING=$(mktemp -d)
STAGING_APP="$STAGING/brief"

cp -R "$APP_DIR" "$STAGING_APP"

VENDOR_ARG="${1:-}"
VENDOR_PLATFORM=""
case "$VENDOR_ARG" in
  "")
    ;;
  --vendor)
    ;;
  --vendor=macos)
    VENDOR_PLATFORM="macosx_11_0_x86_64"
    ;;
  --vendor=linux)
    VENDOR_PLATFORM="manylinux2014_x86_64"
    ;;
  *)
    echo "error: unknown option '$VENDOR_ARG' (use --vendor, --vendor=macos, --vendor=linux, or no flag)" >&2
    exit 1
    ;;
esac

if [[ -n "$VENDOR_ARG" ]]; then
  if [[ ! -x "$REPO/.venv/bin/pip" ]]; then
    echo "error: $REPO/.venv/bin/pip not found — create the venv first" >&2
    exit 1
  fi
  PIP_ARGS=(install --quiet --target "$STAGING_APP/bin/lib" --no-compile)
  if [[ -n "$VENDOR_PLATFORM" ]]; then
    echo "Vendoring brief + deps for platform=$VENDOR_PLATFORM (this can take a minute) ..."
    PIP_ARGS+=(--platform "$VENDOR_PLATFORM" --python-version 3.13 --only-binary=:all:)
  else
    echo "Vendoring brief + deps for host platform (warning: native binaries won't run on a different-arch Splunk) ..."
  fi
  "$REPO/.venv/bin/pip" "${PIP_ARGS[@]}" "$REPO"
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
echo "Install on Splunk Enterprise:"
echo "  Apps → Manage Apps → Install app from file → upload $OUTPUT"
