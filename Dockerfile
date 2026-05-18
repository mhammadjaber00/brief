FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_HOST=http://127.0.0.1:11434 \
    OLLAMA_MODELS=/root/.ollama/models \
    OLLAMA_MODEL=gpt-oss:20b

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git jq zstd procps && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /brief/
COPY src /brief/src/
WORKDIR /brief/

RUN pip install --no-cache-dir -e .

RUN mkdir -p "$OLLAMA_MODELS" && \
    (ollama serve > /tmp/build-ollama.log 2>&1 &) && \
    for i in $(seq 1 30); do \
        curl -sf http://127.0.0.1:11434/api/tags > /dev/null && break; \
        sleep 1; \
    done && \
    ollama pull gpt-oss:20b && \
    echo "=== ollama list after pull ===" && \
    ollama list && \
    pkill -f "ollama serve" || true

COPY scripts/action-entrypoint.sh /brief/scripts/action-entrypoint.sh
COPY scripts/open_pr.py /brief/scripts/open_pr.py
RUN chmod +x /brief/scripts/action-entrypoint.sh

ENTRYPOINT ["/brief/scripts/action-entrypoint.sh"]
