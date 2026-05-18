from pathlib import Path

import typer

app = typer.Typer(help="Audit Splunk apps for AI-agent-readiness.")


@app.command(help="Run the full audit pipeline against a Splunk app directory.")
def audit(
    app_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    output: Path = typer.Option(Path("./brief-out"), help="Output directory for artifacts."),
    offline: bool = typer.Option(False, help="Use Ollama fallback instead of Splunk Hosted Models."),
) -> None:
    raise NotImplementedError("Pipeline implementation pending — see docs/brief-spec.html §03.")


if __name__ == "__main__":
    app()
