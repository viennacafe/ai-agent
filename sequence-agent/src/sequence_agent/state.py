from __future__ import annotations

from typing import List, Optional, TypedDict


class SourceFile(TypedDict):
    path: str
    content: str


class AgentState(TypedDict, total=False):
    git_url: str
    repo_dir: str
    source_files: List[SourceFile]
    architecture_summary: str
    mermaid_code: str
    markdown: str
    output_path: str
    errors: List[str]
