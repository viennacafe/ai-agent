from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterable, List

from git import Repo

from .state import SourceFile

SOURCE_EXTENSIONS = {
    ".java", ".kt", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".cs", ".php", ".rb", ".yml", ".yaml",
    ".properties", ".xml", ".gradle", ".md",
}

EXCLUDE_DIRS = {
    ".git", "build", "target", "node_modules", ".gradle", ".idea",
    "dist", "out", "coverage", "__pycache__", ".venv", "venv",
}


def clone_repository(git_url: str) -> str:
    base_dir = Path(tempfile.mkdtemp(prefix="git-sequence-agent-"))
    repo_dir = base_dir / "repo"
    try:
        Repo.clone_from(git_url, repo_dir, depth=1)
    except Exception:
        shutil.rmtree(base_dir, ignore_errors=True)
        raise
    return str(repo_dir)


def _iter_source_paths(repo_dir: Path) -> Iterable[Path]:
    for path in repo_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SOURCE_EXTENSIONS:
            yield path


def collect_source_files(repo_dir: str, max_files: int = 80, max_chars_per_file: int = 8000) -> List[SourceFile]:
    root = Path(repo_dir)
    files: List[SourceFile] = []
    for path in sorted(_iter_source_paths(root))[:max_files]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:max_chars_per_file]
        except Exception:
            continue
        files.append({"path": str(path.relative_to(root)), "content": content})
    return files
