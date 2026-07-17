from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Tuple
from .models import EntityInfo, FieldInfo, Relationship

JAVA_TYPES = {
    "String": "string", "Long": "long", "Integer": "int", "int": "int", "long": "long",
    "Double": "double", "double": "double", "BigDecimal": "decimal", "Boolean": "boolean",
    "boolean": "boolean", "LocalDate": "date", "LocalDateTime": "datetime", "Date": "datetime",
    "UUID": "uuid"
}

SKIP_DIRS = {".git", "build", "target", ".gradle", "node_modules", "dist", "out"}
TEXT_EXTS = {".java", ".kt", ".sql", ".ddl", ".xml", ".yml", ".yaml", ".properties"}


def read_source_files(repo_path: str, max_files: int = 500) -> Dict[str, str]:
    base = Path(repo_path)
    files: Dict[str, str] = {}
    for p in base.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        if len(files) >= max_files:
            break
        try:
            files[str(p.relative_to(base))] = p.read_text(encoding="utf-8", errors="ignore")[:60000]
        except Exception:
            continue
    return files


def _table_name(class_body_header: str, class_name: str) -> str:
    m = re.search(r'@Table\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', class_body_header, re.S)
    return m.group(1) if m else class_name


def _column_name(annotation_block: str, field_name: str) -> str:
    m = re.search(r'@Column\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', annotation_block, re.S)
    if m:
        return m.group(1)
    m = re.search(r'@JoinColumn\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', annotation_block, re.S)
    if m:
        return m.group(1)
    return field_name


def _nullable(annotation_block: str) -> bool:
    return not re.search(r'nullable\s*=\s*false', annotation_block)


def parse_java_entities(source_files: Dict[str, str]) -> Tuple[List[EntityInfo], List[Relationship]]:
    entities: List[EntityInfo] = []
    relationships: List[Relationship] = []
    class_to_entity: Dict[str, EntityInfo] = {}

    entity_pattern = re.compile(r'((?:@[\w.]+(?:\([^)]*\))?\s*)*)\s*(?:public\s+)?class\s+(\w+)\b([^{}]*)\{', re.S)

    for _, text in source_files.items():
        for match in entity_pattern.finditer(text):
            annotations, class_name, tail = match.groups()
            if "@Entity" not in annotations and "jakarta.persistence.Entity" not in text and "javax.persistence.Entity" not in text:
                continue
            table = _table_name(annotations, class_name)
            start = match.end()
            # Simple balanced-brace extraction
            depth = 1
            i = start
            while i < len(text) and depth > 0:
                if text[i] == "{": depth += 1
                elif text[i] == "}": depth -= 1
                i += 1
            body = text[start:i-1]
            entity = EntityInfo(name=class_name, table_name=table, fields=[])
            class_to_entity[class_name] = entity

            field_pattern = re.compile(r'((?:\s*@\w+(?:\([^)]*\))?\s*)*)\s*(?:private|protected|public)\s+([\w<>?, ]+)\s+(\w+)\s*(?:=\s*[^;]+)?;', re.S)
            for fm in field_pattern.finditer(body):
                ann, java_type, field_name = fm.groups()
                if field_name in {"serialVersionUID"}:
                    continue
                simple_type = java_type.strip().split("<")[0].strip()
                is_pk = "@Id" in ann or "@EmbeddedId" in ann
                is_rel = any(a in ann for a in ["@ManyToOne", "@OneToOne", "@OneToMany", "@ManyToMany"])
                col_name = _column_name(ann, field_name)
                mermaid_type = JAVA_TYPES.get(simple_type, "string")
                if is_rel:
                    # field is a relationship, add an FK column for owning side
                    target = re.sub(r'.*<([^>]+)>.*', r'\1', java_type).strip()
                    if target == java_type.strip():
                        target = simple_type
                    rel_type = "}o--||" if "@ManyToOne" in ann else "||--o{" if "@OneToMany" in ann else "||--||"
                    relationships.append(Relationship(left=class_name, right=target, relation=rel_type, label=field_name))
                    if "@OneToMany" not in ann and "@ManyToMany" not in ann:
                        fk_name = col_name if col_name != field_name else f"{field_name}_id"
                        entity.fields.append(FieldInfo(name=fk_name, type="long", fk=True, nullable=_nullable(ann)))
                else:
                    entity.fields.append(FieldInfo(name=col_name, type=mermaid_type, pk=is_pk, nullable=_nullable(ann)))
            entities.append(entity)

    # Keep only relationships where both sides are known entities
    known = {e.name for e in entities}
    relationships = [r for r in relationships if r.left in known and r.right in known]
    return entities, relationships


def parse_sql_tables(source_files: Dict[str, str]) -> Tuple[List[EntityInfo], List[Relationship]]:
    entities: List[EntityInfo] = []
    relationships: List[Relationship] = []
    sql = "\n".join(v for k, v in source_files.items() if Path(k).suffix.lower() in {".sql", ".ddl"})
    if not sql:
        return entities, relationships
    table_re = re.compile(r'create\s+table\s+(?:if\s+not\s+exists\s+)?[`"\[]?(\w+)[`"\]]?\s*\((.*?)\);', re.I | re.S)
    for tm in table_re.finditer(sql):
        table, body = tm.groups()
        ent = EntityInfo(name=table, table_name=table, fields=[])
        for raw in body.split(','):
            line = raw.strip()
            if not line or line.lower().startswith(("primary", "foreign", "constraint", "unique", "key")):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) >= 2:
                name = parts[0].strip('`"[]')
                typ = parts[1].lower().split('(')[0]
                ent.fields.append(FieldInfo(name=name, type=typ, pk="primary key" in line.lower(), nullable="not null" not in line.lower()))
        entities.append(ent)
    return entities, relationships


def build_mermaid(entities: List[EntityInfo], relationships: List[Relationship]) -> str:
    lines = ["erDiagram"]
    if not entities:
        lines += ["    UNKNOWN {", "        string id PK", "    }"]
        return "\n".join(lines)
    for e in entities:
        lines.append(f"    {e.name} {{")
        if not e.fields:
            lines.append("        string id")
        for f in e.fields:
            tags = []
            if f.pk: tags.append("PK")
            if f.fk: tags.append("FK")
            suffix = " " + " ".join(tags) if tags else ""
            safe_name = re.sub(r'\W+', '_', f.name)
            lines.append(f"        {f.type} {safe_name}{suffix}")
        lines.append("    }")
    for r in relationships:
        label = r.label or "relates_to"
        lines.append(f"    {r.left} {r.relation} {r.right} : {label}")
    return "\n".join(lines)
