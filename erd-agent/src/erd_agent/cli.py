from __future__ import annotations
import typer
from rich.console import Console
from .agent import run_agent

app = typer.Typer(help="Generate Mermaid ERD markdown from a Git repository using LangGraph.")
console = Console()

@app.command()
def run(
    repo_url: str = typer.Argument(..., help="Git repository URL, e.g. https://github.com/user/repo.git"),
    output: str = typer.Option("erd.md", "--output", "-o", help="Output markdown file path"),
    workdir: str | None = typer.Option(None, "--workdir", help="Optional working directory"),
):
    """Clone a Git repository, analyze entities, and write Mermaid ERD markdown."""
    result = run_agent(repo_url=repo_url, output=output, workdir=workdir)
    console.print(f"[green]Generated:[/green] {result['output']}")

if __name__ == "__main__":
    app()
