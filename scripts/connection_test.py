from __future__ import annotations

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def insecure_client_factory(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, verify=False)


async def main() -> int:
    load_dotenv()
    url = os.environ.get("SPLUNK_MCP_URL")
    token = os.environ.get("SPLUNK_MCP_TOKEN")
    if not url or not token:
        print("ERROR: set SPLUNK_MCP_URL and SPLUNK_MCP_TOKEN (see .env.example)", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(
        url, headers=headers, httpx_client_factory=insecure_client_factory
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"connected — {len(tools.tools)} tools exposed")
            for tool in tools.tools:
                print(f"  · {tool.name}")
            result = await session.call_tool("splunk_get_info", arguments={})
            print("\nsplunk_get_info →")
            for block in result.content:
                print(getattr(block, "text", block))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
