from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BriefConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    splunk_mcp_url: str | None = None
    splunk_mcp_token: SecretStr | None = None

    splunk_cloud_host: str | None = None
    splunk_cloud_token: SecretStr | None = None

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    output_dir: Path = Path("./brief-out")


def load_config(env_file: Path | None = None) -> BriefConfig:
    if env_file is not None:
        return BriefConfig(_env_file=str(env_file))
    return BriefConfig()
