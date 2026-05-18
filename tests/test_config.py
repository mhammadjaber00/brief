from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from brief.config import BriefConfig, load_config


@pytest.fixture(autouse=True)
def isolated_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    for var in (
        "SPLUNK_MCP_URL",
        "SPLUNK_MCP_TOKEN",
        "SPLUNK_CLOUD_HOST",
        "SPLUNK_CLOUD_TOKEN",
        "OLLAMA_HOST",
        "OLLAMA_MODEL",
        "OUTPUT_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


def test_defaults_when_no_env() -> None:
    config = load_config()
    assert config.ollama_host == "http://localhost:11434"
    assert config.ollama_model == "llama3.1:8b"
    assert config.splunk_mcp_url is None
    assert config.splunk_mcp_token is None


def test_reads_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SPLUNK_MCP_URL=https://example.com/mcp\n"
        "SPLUNK_MCP_TOKEN=secret-token\n"
        "OLLAMA_MODEL=custom-model\n",
        encoding="utf-8",
    )
    config = load_config(env_file)
    assert config.splunk_mcp_url == "https://example.com/mcp"
    assert isinstance(config.splunk_mcp_token, SecretStr)
    assert config.splunk_mcp_token.get_secret_value() == "secret-token"
    assert config.ollama_model == "custom-model"


def test_env_vars_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "from-env")
    monkeypatch.setenv("SPLUNK_MCP_URL", "https://from-env.example.com")
    config = load_config()
    assert config.ollama_model == "from-env"
    assert config.splunk_mcp_url == "https://from-env.example.com"


def test_explicit_env_file_overrides_process_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "from-process-env")
    env_file = tmp_path / "custom.env"
    env_file.write_text("OLLAMA_MODEL=from-env-file\n", encoding="utf-8")
    config = load_config(env_file)
    assert config.ollama_model == "from-process-env"


def test_secret_str_does_not_leak_in_repr() -> None:
    config = BriefConfig(splunk_mcp_token="hunter2")
    assert "hunter2" not in repr(config)
    assert "hunter2" not in str(config.splunk_mcp_token)
    assert config.splunk_mcp_token.get_secret_value() == "hunter2"
