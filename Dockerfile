FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_HOST=http://127.0.0.1:11434

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git jq && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /brief/
COPY src /brief/src/
WORKDIR /brief/

RUN pip install --no-cache-dir -e .

RUN ollama serve & \
    sleep 3 && \
    ollama pull llama3.1:8b && \
    pkill -f "ollama serve" || true

COPY scripts/action-entrypoint.sh /brief/scripts/action-entrypoint.sh
COPY scripts/open_pr.py /brief/scripts/open_pr.py
RUN chmod +x /brief/scripts/action-entrypoint.sh

ENTRYPOINT ["/brief/scripts/action-entrypoint.sh"]
