from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from splunklib.ai.messages import HumanMessage

from brief.agent import build_brief_agent

load_dotenv()
console = Console()


async def main() -> int:
    provider = sys.argv[1] if len(sys.argv) > 1 else "google"
    target = sys.argv[2] if len(sys.argv) > 2 else "tests/fixtures/sample-ta-1"

    console.print(Rule("[bold]Brief — splunklib.ai Agent demo[/bold]"))
    console.print(f"Provider: [cyan]{provider}[/cyan]")

    agent = build_brief_agent(provider=provider)

    console.print(f"Constructed: [green]{type(agent).__module__}.{type(agent).__name__}[/green]")
    console.print(f"  name:        [bold]{agent.name}[/bold]")
    console.print(f"  description: {agent.description}")
    console.print(f"  model:       {type(agent.model).__name__}")
    console.print(f"  limits:      max_steps={agent.limits.max_steps}, timeout={agent.limits.timeout}s")
    console.print(f"  tools:       {list(agent.tool_settings.local.allowlist.names)}")

    prompt = (
        f"Use the scan_app tool on the path {target!r} and report:\n"
        "1. The app name and version\n"
        "2. How many saved searches it has\n"
        "3. Which saved searches are missing descriptions\n"
        "4. The most concerning safety finding\n"
        "Be concise — one paragraph per point."
    )
    console.print(Rule("[dim]User prompt[/dim]"))
    console.print(prompt)

    console.print(Rule("[dim]Agent run[/dim]"))
    async with agent:
        with console.status("[bold]Agent running (tool calls + LLM turns)…[/bold]"):
            response = await agent.invoke([HumanMessage(content=prompt)])

    console.print(Rule("[dim]Final response[/dim]"))
    final = response.final_message.content if hasattr(response.final_message, "content") else str(response.final_message)
    console.print(Panel(str(final), border_style="green"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
