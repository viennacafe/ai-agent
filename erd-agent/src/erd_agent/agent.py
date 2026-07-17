from __future__ import annotations
import os
import shutil
import tempfile
from pathlib import Path
from git import Repo
from langgraph.graph import StateGraph, END

from .models import AgentState
from .parser import read_source_files, parse_java_entities, parse_sql_tables, build_mermaid


def clone_repo(state: AgentState) -> AgentState:
    repo_url = state["repo_url"]
    workdir = state.get("workdir") or tempfile.mkdtemp(prefix="erd-agent-")
    repo_path = str(Path(workdir) / "repo")
    if Path(repo_path).exists():
        shutil.rmtree(repo_path)
    Repo.clone_from(repo_url, repo_path, depth=1)
    return {**state, "workdir": workdir, "repo_path": repo_path}


def scan_source(state: AgentState) -> AgentState:
    source_files = read_source_files(state["repo_path"])
    return {**state, "source_files": source_files}


def extract_schema(state: AgentState) -> AgentState:
    source_files = state.get("source_files", {})
    java_entities, java_rels = parse_java_entities(source_files)
    sql_entities, sql_rels = parse_sql_tables(source_files)
    entities = java_entities or sql_entities
    relationships = java_rels or sql_rels
    return {**state, "entities": entities, "relationships": relationships}


def generate_mermaid(state: AgentState) -> AgentState:
    mermaid = build_mermaid(state.get("entities", []), state.get("relationships", []))
    return {**state, "mermaid_code": mermaid}


def generate_markdown(state: AgentState) -> AgentState:
    repo_url = state["repo_url"]
    entities = state.get("entities", [])
    entity_summary = "\n".join([f"- `{e.name}`: {len(e.fields)} fields" for e in entities]) or "- Entity를 찾지 못했습니다."
    markdown = f"""# Repository

{repo_url}

## Entity Summary

{entity_summary}

## Mermaid ERD
```mermaid
{state.get('mermaid_code', 'erDiagram')}
```
"""
    return {**state, "markdown": markdown}


def write_output(state: AgentState) -> AgentState:
    output = state.get("output") or "erd.md"
    Path(output).write_text(state.get("markdown", ""), encoding="utf-8")
    return {**state, "output": output}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("clone_repo", clone_repo)
    graph.add_node("scan_source", scan_source)
    graph.add_node("extract_schema", extract_schema)
    graph.add_node("generate_mermaid", generate_mermaid)
    graph.add_node("generate_markdown", generate_markdown)
    graph.add_node("write_output", write_output)

    graph.set_entry_point("clone_repo")
    graph.add_edge("clone_repo", "scan_source")
    graph.add_edge("scan_source", "extract_schema")
    graph.add_edge("extract_schema", "generate_mermaid")
    graph.add_edge("generate_mermaid", "generate_markdown")
    graph.add_edge("generate_markdown", "write_output")
    graph.add_edge("write_output", END)
    return graph.compile()


def run_agent(repo_url: str, output: str = "erd.md", workdir: str | None = None) -> AgentState:
    app = build_graph()
    initial: AgentState = {"repo_url": repo_url, "output": output}
    if workdir:
        initial["workdir"] = workdir
    return app.invoke(initial)
