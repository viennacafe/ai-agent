from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .service import generate_diagrams

app = typer.Typer(no_args_is_help=True, help="Generate Mermaid diagrams from a Git repository.")
console = Console()


@app.command()
def generate(
    repo_url: Annotated[str, typer.Argument(help="Git repository URL")],
    diagram: Annotated[
        str, typer.Option("--diagram", "-d", help="all, erd, or sequence")
    ] = "all",
    output_dir: Annotated[
        str, typer.Option("--output-dir", "-o")
    ] = "outputs",
    max_files: Annotated[int, typer.Option(help="Maximum source files included")] = 120,
    max_chars_per_file: Annotated[
        int, typer.Option(help="Maximum characters read from each file")
    ] = 10_000,
    max_total_chars: Annotated[
        int, typer.Option(help="Maximum repository context characters")
    ] = 240_000,
) -> None:
    """Clone a repository and generate ERD/sequence diagrams."""
    try:
        files = generate_diagrams(
            repo_url,
            diagram=diagram,
            output_dir=output_dir,
            max_files=max_files,
            max_chars_per_file=max_chars_per_file,
            max_total_chars=max_total_chars,
        )
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Generated files")
    table.add_column("Type")
    table.add_column("Path")
    for kind, path in files.items():
        table.add_row(kind, path)
    console.print(table)


if __name__ == "__main__":
    app()
