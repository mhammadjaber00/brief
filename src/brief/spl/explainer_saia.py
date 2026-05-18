from __future__ import annotations

import json
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from brief.spl.explainer_ollama import explain_via_ollama
from brief.spl.models import SPLExplanation


class SaiaExplanationError(Exception):
    pass


def _insecure_client_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, verify=False)


async def explain_via_saia(spl: str) -> SPLExplanation:
    url = os.environ.get("SPLUNK_MCP_URL")
    token = os.environ.get("SPLUNK_MCP_TOKEN")
    if not url or not token:
        raise SaiaExplanationError("SPLUNK_MCP_URL or SPLUNK_MCP_TOKEN not set")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with streamablehttp_client(
            url, headers=headers, httpx_client_factory=_insecure_client_factory
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "saia_explain_spl", arguments={"spl": spl}
                )
    except Exception as exc:
        raise SaiaExplanationError(f"MCP call failed: {exc}") from exc

    if result.isError:
        raise SaiaExplanationError(f"saia_explain_spl returned an error: {result.content}")

    prose = "".join(getattr(block, "text", "") for block in result.content).strip()
    if not prose:
        raise SaiaExplanationError("saia_explain_spl returned empty content")

    try:
        payload = json.loads(prose)
        payload["source"] = "saia"
        return SPLExplanation.model_validate(payload)
    except (json.JSONDecodeError, ValueError):
        structured = await explain_via_ollama(
            f"The Splunk AI Assistant produced this prose explanation of an SPL search:\n\n"
            f"{prose}\n\nConvert it into the JSON schema."
        )
        return structured.model_copy(update={"source": "saia"})
