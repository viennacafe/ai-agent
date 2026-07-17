from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .graph import build_graph

app = typer.Typer(help="Generate Mermaid sequence diagram Markdown from a Git repository URL.")
console = Console()


@app.command()
def run(
    git_url: str = typer.Argument(..., help="Git repository URL"),
    output: str = typer.Option("sequence-diagram.md", "--output", "-o", help="Markdown output path"),
):
    """Run the LangGraph agent."""
    graph = build_graph()
    result = graph.invoke({"git_url": git_url, "output_path": output})
    console.print(f"[green]Done[/green]: {Path(result['output_path']).resolve()}")
    console.print("\n[bold]Mermaid preview[/bold]\n")
    console.print(result["mermaid_code"])


if __name__ == "__main__":
    app()
