from __future__ import annotations

import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .models import (
    DiagramPlan,
    DiagramResult,
    DiagramTask,
    GraphState,
    RequestMapping,
    RequestMappingCatalog,
    WorkerState,
)
from .mermaid import (
    normalize_erd_relationship_labels,
    normalize_sequence_diagram,
    sequence_syntax_issues,
    strip_fence,
)
from .prompts import (
    ERD_SYSTEM,
    PLANNER_SYSTEM,
    REQUEST_MAPPING_DISCOVERY_SYSTEM,
    SEQUENCE_REPAIR_SYSTEM,
    SEQUENCE_SYSTEM,
)


def _strip_fence(text: str) -> str:
    return strip_fence(text)


def _validate_mermaid(kind: str, mermaid: str) -> tuple[str, list[str]]:
    expected = "erDiagram" if kind == "erd" else "sequenceDiagram"
    warnings: list[str] = []
    value = (
        normalize_sequence_diagram(mermaid)
        if kind == "sequence"
        else normalize_erd_relationship_labels(mermaid)
    )
    if not value.startswith(expected):
        warnings.append(f"Expected Mermaid document to start with {expected}.")
    if kind == "sequence":
        warnings.extend(sequence_syntax_issues(value))
    return value, warnings


def _mapping_title(mapping: RequestMapping) -> str:
    return f"{mapping.http_method.upper()} {mapping.path} — {mapping.controller}.{mapping.handler}"


def _mapping_slug(mapping: RequestMapping, index: int) -> str:
    raw = f"{index:03d}-{mapping.http_method}-{mapping.path}-{mapping.controller}-{mapping.handler}"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-.").lower()
    return slug[:140] or f"{index:03d}-endpoint"


def build_graph(model_name: str):
    llm = ChatOpenAI(model=model_name, temperature=0)

    def orchestrator(state: GraphState) -> dict:
        requested = state.get("diagram_request", "all")
        allowed = ["erd", "sequence"] if requested == "all" else [requested]
        structured = llm.with_structured_output(DiagramPlan)
        plan = structured.invoke([
            ("system", PLANNER_SYSTEM),
            ("human", f"Repository: {state['repo_name']}\nRequested diagrams: {', '.join(allowed)}\nCreate exactly one task per requested diagram kind."),
        ])
        tasks_by_kind = {task.kind: task for task in plan.tasks if task.kind in allowed}
        tasks = [
            tasks_by_kind.get(kind, DiagramTask(kind=kind, objective=f"Generate an evidence-grounded {kind} Mermaid diagram.", focus=[]))
            for kind in allowed
        ]
        return {"plan": tasks}

    def dispatch_workers(state: GraphState):
        return [
            Send("diagram_worker", {
                "repo_name": state["repo_name"],
                "repository_context": state["repository_context"],
                "task": task,
            })
            for task in state["plan"]
        ]

    def _generate_sequence_for_mapping(repo_name: str, context: str, mapping: RequestMapping, index: int) -> DiagramResult:
        response = llm.invoke([
            ("system", SEQUENCE_SYSTEM),
            ("human", (
                f"Repository: {repo_name}\n"
                f"HTTP method: {mapping.http_method}\n"
                f"Resolved path: {mapping.path}\n"
                f"Controller/route module: {mapping.controller}\n"
                f"Handler: {mapping.handler}\n"
                f"Source file: {mapping.source_file}\n"
                f"Purpose: {mapping.summary}\n\n"
                f"REPOSITORY CONTEXT\n{context}"
            )),
        ])
        mermaid, warnings = _validate_mermaid("sequence", str(response.content))
        for _ in range(2):
            if not warnings:
                break
            repair = llm.invoke([
                ("system", SEQUENCE_REPAIR_SYSTEM),
                ("human", "Syntax issues to fix:\n- " + "\n- ".join(warnings) + "\n\nDiagram to repair:\n" + mermaid),
            ])
            mermaid, warnings = _validate_mermaid("sequence", str(repair.content))
        return DiagramResult(
            kind="sequence",
            title=_mapping_title(mapping),
            slug=_mapping_slug(mapping, index),
            mermaid=mermaid,
            evidence=[mapping.source_file],
            warnings=warnings,
        )

    def diagram_worker(state: WorkerState) -> dict:
        task = state["task"]
        if task.kind == "erd":
            response = llm.invoke([
                ("system", ERD_SYSTEM),
                ("human", f"Repository: {state['repo_name']}\n\n{state['repository_context']}"),
            ])
            mermaid, warnings = _validate_mermaid("erd", str(response.content))
            return {"completed": [DiagramResult(kind="erd", title="ERD", slug="erd", mermaid=mermaid, warnings=warnings)]}

        catalog_llm = llm.with_structured_output(RequestMappingCatalog)
        catalog = catalog_llm.invoke([
            ("system", REQUEST_MAPPING_DISCOVERY_SYSTEM),
            ("human", f"Repository: {state['repo_name']}\n\n{state['repository_context']}"),
        ])
        unique: dict[tuple[str, str, str, str], RequestMapping] = {}
        for mapping in catalog.mappings:
            key = (mapping.http_method.upper(), mapping.path, mapping.controller, mapping.handler)
            unique[key] = mapping
        mappings = sorted(unique.values(), key=lambda m: (m.source_file, m.controller, m.path, m.http_method, m.handler))
        if not mappings:
            return {"completed": [DiagramResult(
                kind="sequence",
                title="Request mappings",
                slug="no-request-mappings",
                mermaid="sequenceDiagram\n%% No request mappings were evidenced in the supplied repository context.",
                warnings=["No request mappings were discovered."],
            )]}
        results = [
            _generate_sequence_for_mapping(state["repo_name"], state["repository_context"], mapping, index)
            for index, mapping in enumerate(mappings, start=1)
        ]
        return {"completed": results}

    def synthesizer(state: GraphState) -> dict:
        output_dir = Path(state["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        completed = state.get("completed", [])
        files: dict[str, str] = {}
        markdown_parts = [
            f"# {state['repo_name']} diagrams", "",
            f"Source repository: `{state['repo_url']}`", "",
        ]

        erd_results = [r for r in completed if r.kind == "erd"]
        sequence_results = [r for r in completed if r.kind == "sequence"]

        for result in erd_results:
            path = output_dir / f"{state['repo_name']}-erd.mmd"
            path.write_text(result.mermaid + "\n", encoding="utf-8")
            files["erd"] = str(path)
            markdown_parts += ["## ERD", "", "```mermaid", result.mermaid, "```", ""]

        if sequence_results:
            sequence_dir = output_dir / f"{state['repo_name']}-sequences"
            sequence_dir.mkdir(parents=True, exist_ok=True)
            index_lines = [f"# {state['repo_name']} request mapping sequences", ""]
            markdown_parts += [f"## Sequence diagrams ({len(sequence_results)} request mappings)", ""]
            for i, result in enumerate(sequence_results, start=1):
                filename = f"{result.slug}.mmd"
                path = sequence_dir / filename
                path.write_text(result.mermaid + "\n", encoding="utf-8")
                index_lines.append(f"{i}. [{result.title}]({filename})")
                markdown_parts += [f"### {i}. {result.title}", ""]
                if result.evidence:
                    markdown_parts += [f"Source: `{result.evidence[0]}`", ""]
                markdown_parts += ["```mermaid", result.mermaid, "```", ""]
                if result.warnings:
                    markdown_parts += ["**Warnings**", "", *[f"- {w}" for w in result.warnings], ""]
            index_path = sequence_dir / "README.md"
            index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
            files["sequence_dir"] = str(sequence_dir)
            files["sequence_index"] = str(index_path)

        md_path = output_dir / f"{state['repo_name']}-diagrams.md"
        md_path.write_text("\n".join(markdown_parts), encoding="utf-8")
        files["markdown"] = str(md_path)
        return {"output_files": files}

    graph = StateGraph(GraphState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("diagram_worker", diagram_worker)
    graph.add_node("synthesizer", synthesizer)
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", dispatch_workers, ["diagram_worker"])
    graph.add_edge("diagram_worker", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()
