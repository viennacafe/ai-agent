from __future__ import annotations

import re
from typing import List

from .state import SourceFile


def _class_name(content: str, fallback_path: str) -> str:
    match = re.search(r"\b(class|interface|record)\s+(\w+)", content)
    if match:
        return match.group(2)
    return fallback_path.rsplit("/", 1)[-1].split(".", 1)[0]


def analyze_architecture(files: List[SourceFile]) -> str:
    controllers = []
    services = []
    repositories = []
    entities = []
    configs = []

    for file in files:
        path = file["path"]
        content = file["content"]
        name = _class_name(content, path)
        lowered = (path + "\n" + content[:1000]).lower()

        if "@restcontroller" in lowered or "controller" in path.lower():
            controllers.append(name)
        elif "@service" in lowered or "service" in path.lower():
            services.append(name)
        elif "jparepository" in lowered or "crudrepository" in lowered or "repository" in path.lower():
            repositories.append(name)
        elif "@entity" in lowered or "entity" in path.lower() or "model" in path.lower():
            entities.append(name)
        elif path.endswith((".properties", ".yml", ".yaml", ".xml", ".gradle")):
            configs.append(path)

    return "\n".join([
        "Detected architecture summary:",
        f"- Controllers: {', '.join(sorted(set(controllers))) or 'Not detected'}",
        f"- Services: {', '.join(sorted(set(services))) or 'Not detected'}",
        f"- Repositories: {', '.join(sorted(set(repositories))) or 'Not detected'}",
        f"- Entities/Models: {', '.join(sorted(set(entities))) or 'Not detected'}",
        f"- Config files: {', '.join(configs[:10]) or 'Not detected'}",
    ])
