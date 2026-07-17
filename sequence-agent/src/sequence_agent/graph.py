from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from .analyzer import analyze_architecture
from .generator import build_markdown, generate_mermaid
from .repository import clone_repository, collect_source_files
from .state import AgentState


def clone_node(state: AgentState) -> AgentState:
    repo_dir = clone_repository(state["git_url"])
    return {"repo_dir": repo_dir}


def collect_node(state: AgentState) -> AgentState:
    files = collect_source_files(state["repo_dir"])
    return {"source_files": files}


def analyze_node(state: AgentState) -> AgentState:
    summary = analyze_architecture(state.get("source_files", []))
    return {"architecture_summary": summary}


def generate_node(state: AgentState) -> AgentState:
    mermaid = generate_mermaid(state.get("source_files", []), state.get("architecture_summary", ""))
    markdown = build_markdown(state["git_url"], state.get("architecture_summary", ""), mermaid)
    return {"mermaid_code": mermaid, "markdown": markdown}


def write_node(state: AgentState) -> AgentState:
    output_path = state.get("output_path") or "sequence-diagram.md"
    Path(output_path).write_text(state["markdown"], encoding="utf-8")
    return {"output_path": output_path}


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("clone_repository", clone_node)
    workflow.add_node("collect_source_files", collect_node)
    workflow.add_node("analyze_architecture", analyze_node)
    workflow.add_node("generate_mermaid", generate_node)
    workflow.add_node("write_markdown", write_node)

    workflow.add_edge(START, "clone_repository")
    workflow.add_edge("clone_repository", "collect_source_files")
    workflow.add_edge("collect_source_files", "analyze_architecture")
    workflow.add_edge("analyze_architecture", "generate_mermaid")
    workflow.add_edge("generate_mermaid", "write_markdown")
    workflow.add_edge("write_markdown", END)
    return workflow.compile()
