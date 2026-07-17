from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field


DiagramKind = Literal["erd", "sequence"]


class DiagramTask(BaseModel):
    kind: DiagramKind
    objective: str = Field(description="Worker-specific analysis objective")
    focus: list[str] = Field(default_factory=list)


class DiagramPlan(BaseModel):
    tasks: list[DiagramTask]


class RequestMapping(BaseModel):
    http_method: str = Field(description="HTTP method such as GET, POST, PUT, PATCH, DELETE or ANY")
    path: str = Field(description="Resolved request path including class-level and method-level mappings")
    controller: str = Field(description="Controller, route handler, or endpoint module")
    handler: str = Field(description="Handler method or function name")
    source_file: str = Field(description="Repository-relative source file")
    summary: str = Field(default="", description="Short evidence-grounded purpose")


class RequestMappingCatalog(BaseModel):
    mappings: list[RequestMapping]


class DiagramResult(BaseModel):
    kind: DiagramKind
    mermaid: str
    title: str = ""
    slug: str = ""
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GraphState(TypedDict, total=False):
    repo_url: str
    repo_name: str
    diagram_request: Literal["all", "erd", "sequence"]
    repository_context: str
    plan: list[DiagramTask]
    completed: Annotated[list[DiagramResult], operator.add]
    output_dir: str
    output_files: dict[str, str]


class WorkerState(TypedDict):
    repo_name: str
    repository_context: str
    task: DiagramTask
    completed: Annotated[list[DiagramResult], operator.add]
