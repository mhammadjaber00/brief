#!/usr/bin/env bash
# One-time setup: download Foundation-Sec-1.1-8B-Instruct from HuggingFace and
# register it with Ollama as `foundation-sec:8b`.
#
# Brief routes security-classified apps to this model when present. Without it,
# Brief falls back to gpt-oss:20b (also a Splunk Hosted Model).
#
# Requirements:
#   - ollama installed and `ollama serve` reachable at $OLLAMA_HOST
#   - ~20GB free disk for the safetensors + GGUF conversion (Ollama auto-converts)
#   - git-lfs (for cloning the HF repo) OR plain HTTPS download (this script uses HTTPS)
#
# Usage:
#   scripts/install-foundation-sec.sh
#   scripts/install-foundation-sec.sh --keep-source   # don't delete the downloaded safetensors
set -euo pipefail

KEEP_SOURCE=false
if [[ "${1:-}" == "--keep-source" ]]; then
    KEEP_SOURCE=true
fi

OLLAMA_NAME="foundation-sec:8b"
HF_REPO="fdtn-ai/Foundation-Sec-1.1-8B-Instruct"
WORK_DIR="${TMPDIR:-/tmp}/brief-foundation-sec"
SOURCE_DIR="$WORK_DIR/source"

if ! command -v ollama >/dev/null; then
    echo "error: ollama not installed. Get it from https://ollama.com/download" >&2
    exit 1
fi

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -qx "$OLLAMA_NAME"; then
    echo "$OLLAMA_NAME already registered in Ollama. Nothing to do."
    exit 0
fi

mkdir -p "$SOURCE_DIR"
cd "$SOURCE_DIR"

echo "Downloading $HF_REPO from HuggingFace..."
BASE="https://huggingface.co/$HF_REPO/resolve/main"
for f in \
    config.json \
    generation_config.json \
    chat_template.jinja \
    tokenizer.json \
    tokenizer_config.json \
    special_tokens_map.json \
    model.safetensors.index.json \
    model-00001-of-00004.safetensors \
    model-00002-of-00004.safetensors \
    model-00003-of-00004.safetensors \
    model-00004-of-00004.safetensors \
; do
    if [[ -s "$f" ]]; then
        echo "  · $f (already present, skipping)"
        continue
    fi
    echo "  · $f"
    curl -fL --progress-bar -o "$f.partial" "$BASE/$f"
    mv "$f.partial" "$f"
done

cat > Modelfile <<'EOF'
FROM .
PARAMETER temperature 0.2
EOF

echo
echo "Registering with Ollama as $OLLAMA_NAME (this triggers safetensors -> GGUF conversion, can take 5-10 min)..."
ollama create "$OLLAMA_NAME" -f Modelfile

echo
echo "Verifying..."
ollama list | grep -i foundation-sec || true

if ! $KEEP_SOURCE; then
    echo "Cleaning source files at $SOURCE_DIR (~16GB)..."
    rm -rf "$SOURCE_DIR"
fi

echo
echo "Done. Brief will now route security-classified apps to $OLLAMA_NAME automatically."
echo "Override per-class via env: BRIEF_MODEL_SECURITY / BRIEF_MODEL_GENERAL."
