from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .graph import build_graph
from .repository import load_repository


def generate_diagrams(
    repo_url: str,
    *,
    diagram: str = "all",
    output_dir: str = "outputs",
    work_dir: str = ".work",
    max_files: int = 120,
    max_chars_per_file: int = 10_000,
    max_total_chars: int = 240_000,
) -> dict[str, str]:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    if diagram not in {"all", "erd", "sequence"}:
        raise ValueError("diagram은 all, erd, sequence 중 하나여야 합니다.")

    snapshot = load_repository(
        repo_url,
        Path(work_dir),
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
    )

    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1")
    graph = build_graph(model_name)
    result = graph.invoke({
        "repo_url": repo_url,
        "repo_name": snapshot.repo_name,
        "diagram_request": diagram,
        "repository_context": snapshot.context,
        "output_dir": output_dir,
        "completed": [],
    })
    return result["output_files"]
