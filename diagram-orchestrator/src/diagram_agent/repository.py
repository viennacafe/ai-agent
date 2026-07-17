from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_EXTENSIONS = {
    ".java", ".kt", ".kts", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".cs", ".php", ".rb", ".scala",
    ".sql", ".graphql", ".gql", ".proto",
    ".xml", ".yml", ".yaml", ".json", ".toml", ".properties",
    ".gradle", ".md",
}

IMPORTANT_FILENAMES = {
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "settings.gradle.kts", "package.json", "pyproject.toml",
    "requirements.txt", "go.mod", "Cargo.toml", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
}

IGNORED_DIRS = {
    ".git", ".idea", ".vscode", ".gradle", ".mvn", "node_modules",
    "vendor", "dist", "build", "target", "out", "coverage",
    "__pycache__", ".venv", "venv", "bin", "obj",
}

PATH_PRIORITY_PATTERNS = (
    "entity", "model", "domain", "schema", "migration", "repository", "dao",
    "controller", "route", "api", "service", "usecase", "handler",
    "config", "application", "main", "readme",
)


@dataclass(frozen=True)
class RepositorySnapshot:
    repo_name: str
    root: Path
    context: str


def parse_repo_name(repo_url: str) -> str:
    path = urlparse(repo_url).path.rstrip("/")
    name = Path(path).name
    return name.removesuffix(".git") or "repository"


def _authenticated_url(repo_url: str) -> str:
    token = os.getenv("GIT_TOKEN", "").strip()
    if not token or not repo_url.startswith("https://github.com/"):
        return repo_url
    return repo_url.replace("https://", f"https://x-access-token:{token}@", 1)


def clone_repository(repo_url: str, work_dir: Path) -> Path:
    repo_name = parse_repo_name(repo_url)
    target = work_dir / repo_name
    if target.exists():
        shutil.rmtree(target)

    safe_url = repo_url
    auth_url = _authenticated_url(repo_url)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", auth_url, str(target)],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable을 찾을 수 없습니다.") from exc
    except subprocess.CalledProcessError as exc:
        # Avoid leaking an embedded token.
        error = (exc.stderr or exc.stdout or "git clone failed").replace(auth_url, safe_url)
        raise RuntimeError(error.strip()) from exc
    return target


def _is_candidate(path: Path) -> bool:
    if any(part in IGNORED_DIRS for part in path.parts):
        return False
    return path.name in IMPORTANT_FILENAMES or path.suffix.lower() in ALLOWED_EXTENSIONS


def _priority(path: Path) -> tuple[int, int, str]:
    lower = str(path).lower()
    score = sum(1 for keyword in PATH_PRIORITY_PATTERNS if keyword in lower)
    # Higher semantic score first, then shorter paths.
    return (-score, len(path.parts), lower)


def _safe_read(path: Path, max_chars: int) -> str | None:
    try:
        if path.stat().st_size > max_chars * 4:
            return None
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    text = text.replace("\x00", "")
    return text[:max_chars]


def build_repository_context(
    root: Path,
    *,
    max_files: int = 120,
    max_chars_per_file: int = 10_000,
    max_total_chars: int = 240_000,
) -> str:
    candidates = [p for p in root.rglob("*") if p.is_file() and _is_candidate(p.relative_to(root))]
    candidates.sort(key=lambda p: _priority(p.relative_to(root)))

    sections: list[str] = []
    total = 0
    for path in candidates[: max_files * 3]:
        if len(sections) >= max_files or total >= max_total_chars:
            break
        relative = path.relative_to(root)
        content = _safe_read(path, max_chars_per_file)
        if not content or not content.strip():
            continue
        block = f"\n===== FILE: {relative.as_posix()} =====\n{content}\n"
        if total + len(block) > max_total_chars:
            remaining = max_total_chars - total
            if remaining < 500:
                break
            block = block[:remaining]
        sections.append(block)
        total += len(block)

    if not sections:
        raise RuntimeError("분석할 수 있는 텍스트 소스 파일을 찾지 못했습니다.")

    tree = "\n".join(str(p.relative_to(root).as_posix()) for p in candidates[:300])
    return (
        "REPOSITORY FILE INDEX\n"
        "=====================\n"
        f"{tree}\n\n"
        "SELECTED SOURCE CONTENT\n"
        "=======================\n"
        + "".join(sections)
    )


def load_repository(
    repo_url: str,
    work_dir: Path,
    *,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
) -> RepositorySnapshot:
    root = clone_repository(repo_url, work_dir)
    return RepositorySnapshot(
        repo_name=parse_repo_name(repo_url),
        root=root,
        context=build_repository_context(
            root,
            max_files=max_files,
            max_chars_per_file=max_chars_per_file,
            max_total_chars=max_total_chars,
        ),
    )
