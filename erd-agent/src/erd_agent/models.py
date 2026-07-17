from __future__ import annotations
from typing import TypedDict, List, Dict, Optional
from pydantic import BaseModel, Field

class FieldInfo(BaseModel):
    name: str
    type: str = "string"
    pk: bool = False
    fk: bool = False
    nullable: bool = True

class Relationship(BaseModel):
    left: str
    right: str
    relation: str = "}o--||"
    label: str = ""

class EntityInfo(BaseModel):
    name: str
    table_name: Optional[str] = None
    fields: List[FieldInfo] = Field(default_factory=list)

class AgentState(TypedDict, total=False):
    repo_url: str
    workdir: str
    repo_path: str
    source_files: Dict[str, str]
    entities: List[EntityInfo]
    relationships: List[Relationship]
    mermaid_code: str
    markdown: str
    output: str
    errors: List[str]
