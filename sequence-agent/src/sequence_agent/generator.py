from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

from .state import SourceFile

load_dotenv()

SYSTEM_PROMPT = """You are a senior software architect and Mermaid.js sequence diagram expert.
Analyze the provided repository files and generate ONLY valid Mermaid.js sequenceDiagram code.
Rules:
- Start directly with sequenceDiagram.
- Include autonumber.
- Use actor/participant names that reflect the actual code.
- Include activate/deactivate.
- Focus on the main request lifecycle from client to controller/service/repository/database/external APIs.
- Do not wrap in markdown fences.
"""


def _build_context(files: List[SourceFile], architecture_summary: str) -> str:
    chunks = [architecture_summary, "\nRepository files:"]
    for file in files:
        chunks.append(f"\n--- FILE: {file['path']} ---\n{file['content']}")
    return "\n".join(chunks)


def generate_mermaid_with_llm(files: List[SourceFile], architecture_summary: str) -> str:
    from langchain_openai import ChatOpenAI

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)
    context = _build_context(files, architecture_summary)
    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"Create a Mermaid sequence diagram for this repository.\n\n{context}"),
    ])
    return str(response.content).strip().replace("```mermaid", "").replace("```", "").strip()


def generate_mermaid_fallback(architecture_summary: str) -> str:
    return f"""sequenceDiagram
    autonumber
    actor Client
    participant Controller
    participant Service
    participant Repository
    participant DB

    Client->>Controller: HTTP Request
    activate Controller
    Controller->>Service: execute business logic
    activate Service
    Service->>Repository: query or persist data
    activate Repository
    Repository->>DB: SQL / ORM operation
    activate DB
    DB-->>Repository: result
    deactivate DB
    Repository-->>Service: data
    deactivate Repository
    Service-->>Controller: response data
    deactivate Service
    Controller-->>Client: HTTP Response
    deactivate Controller

%% {architecture_summary.replace(chr(10), chr(10) + '%% ')}
""".strip()


def generate_mermaid(files: List[SourceFile], architecture_summary: str) -> str:
    if os.getenv("OPENAI_API_KEY"):
        return generate_mermaid_with_llm(files, architecture_summary)
    return generate_mermaid_fallback(architecture_summary)


def build_markdown(git_url: str, architecture_summary: str, mermaid_code: str) -> str:
    return f"""# Git Repository Sequence Diagram

## Repository

{git_url}

## Architecture Summary

```text
{architecture_summary}
```

## Sequence Diagram

```mermaid
{mermaid_code}
```
"""
