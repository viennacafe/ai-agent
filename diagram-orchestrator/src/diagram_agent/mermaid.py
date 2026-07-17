from __future__ import annotations

import re

_VALID_ID = r"[A-Za-z_][A-Za-z0-9_]*"
_MESSAGE_RE = re.compile(
    rf"^\s*({_VALID_ID})\s*(-->>|->>|-->|->|--x|-x|--\)|-\)|--)\s*({_VALID_ID})\s*:\s*(.+?)\s*$"
)
_PARTICIPANT_RE = re.compile(
    rf'^\s*(?:participant|actor)\s+({_VALID_ID})(?:\s+as\s+"[^"]*")?\s*$'
)
_ACTIVATION_RE = re.compile(rf"^\s*(activate|deactivate)\s+({_VALID_ID})\s*$")
_BLOCK_START_RE = re.compile(r"^\s*(alt|opt|loop|par|critical|break|rect)\b", re.IGNORECASE)
_BRANCH_RE = re.compile(r"^\s*(else|and|option)\b", re.IGNORECASE)
_NOTE_RE = re.compile(
    rf"^\s*Note\s+(?:left of|right of|over)\s+{_VALID_ID}(?:\s*,\s*{_VALID_ID})?\s*:\s*.+$",
    re.IGNORECASE,
)
_ARROW_RE = r"-->>|->>|-->|->|--x|-x|--\)|-\)|--"


def strip_fence(text: str) -> str:
    """Extract only the Mermaid body from a fenced or prose-wrapped response."""
    value = str(text or "").strip()
    fenced = re.search(r"```(?:mermaid)?\s*(.*?)```", value, re.IGNORECASE | re.DOTALL)
    if fenced:
        value = fenced.group(1).strip()
    lines = value.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() in {"sequenceDiagram", "erDiagram"}), 0)
    return "\n".join(lines[start:]).strip()


def _safe_participant_id(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    value = re.sub(r"[^A-Za-z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "Participant"
    if value[0].isdigit():
        value = f"P_{value}"
    return value


def _participant_display_name(raw_identifier: str, explicit_label: str | None) -> str:
    if explicit_label:
        label = explicit_label.strip().strip('"').strip("'")
    else:
        label = raw_identifier.strip().strip('"').strip("'")
        if "." in label:
            label = label.rsplit(".", 1)[0]
        label = re.sub(r"\(.*\)$", "", label).strip()
    label = re.sub(r"[\r\n]+", " ", label).replace('"', "'").strip()
    return label or "Participant"


def _build_participant_aliases(lines: list[str]) -> tuple[dict[str, str], list[str], set[str]]:
    aliases: dict[str, str] = {}
    used: set[str] = set()
    declared: set[str] = set()
    normalized: list[str] = []
    declaration_re = re.compile(
        r'^\s*(participant|actor)\s+(.+?)(?:\s+as\s+(".*?"|\S.*))?\s*$',
        re.IGNORECASE,
    )

    for raw in lines:
        match = declaration_re.match(raw)
        if not match:
            normalized.append(raw)
            continue
        kind, raw_identifier, explicit_label = match.groups()
        raw_identifier = raw_identifier.strip().strip('"').strip("'")
        base = _safe_participant_id(raw_identifier)
        alias = base
        suffix = 2
        while alias in used and aliases.get(raw_identifier) != alias:
            alias = f"{base}_{suffix}"
            suffix += 1
        used.add(alias)
        declared.add(alias)
        aliases[raw_identifier] = alias
        aliases[alias] = alias
        display = _participant_display_name(raw_identifier, explicit_label)
        normalized.append(
            f"{kind.lower()} {alias}" if display == alias else f'{kind.lower()} {alias} as "{display}"'
        )
    return aliases, normalized, declared


def _replace_participant_reference(token: str, aliases: dict[str, str]) -> str:
    raw = token.strip().strip('"').strip("'")
    return aliases.get(raw, _safe_participant_id(raw))


def _default_message_label(arrow: str) -> str:
    return "completed" if arrow.startswith("--") else "call"


def normalize_sequence_diagram(text: str) -> str:
    """Return a conservative, parser-safe Mermaid sequence diagram.

    The normalizer fixes model output deterministically instead of relying only
    on a repair prompt: unsafe participant IDs, missing message labels,
    undeclared participants, unmatched activations and unclosed control blocks.
    """
    value = strip_fence(text)
    raw_lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    if not raw_lines or raw_lines[0].strip() != "sequenceDiagram":
        raw_lines.insert(0, "sequenceDiagram")

    source_lines: list[str] = []
    for raw in raw_lines:
        line = raw.replace("→", "->>").replace("–>>", "-->>").replace("—>>", "-->>")
        line = re.sub(r"(->>|-->>|->|-->)[+-](?=[^\s:]+)", r"\1", line)
        source_lines.append(line)

    aliases, declaration_normalized, declared = _build_participant_aliases(source_lines)
    body: list[str] = []
    referenced_order: list[str] = []

    # Allows an absent colon, an empty label, or whitespace-only label.
    permissive_message_re = re.compile(
        rf"^(\s*)([^\s]+?)\s*({_ARROW_RE})\s*([^\s:]+)\s*(?::\s*(.*))?$"
    )
    activation_re = re.compile(r"^(\s*)(activate|deactivate)\s+(.+?)\s*$", re.IGNORECASE)
    note_re = re.compile(r"^(\s*Note\s+(?:left of|right of|over)\s+)([^:]+)(?::\s*(.*))?$", re.IGNORECASE)

    for original, normalized_decl in zip(source_lines, declaration_normalized):
        stripped = original.strip()
        if stripped == "sequenceDiagram":
            continue
        if re.match(r"^\s*(participant|actor)\s+", original, re.IGNORECASE):
            body.append(normalized_decl)
            continue

        message = permissive_message_re.match(original)
        if message:
            indent, sender, arrow, receiver, label = message.groups()
            sender_alias = _replace_participant_reference(sender, aliases)
            receiver_alias = _replace_participant_reference(receiver, aliases)
            for name in (sender_alias, receiver_alias):
                if name not in referenced_order:
                    referenced_order.append(name)
            safe_label = re.sub(r"[\r\n]+", " ", (label or "")).strip()
            if not safe_label:
                safe_label = _default_message_label(arrow)
            body.append(f"{indent}{sender_alias}{arrow}{receiver_alias}: {safe_label}")
            continue

        activation = activation_re.match(original)
        if activation:
            indent, action, target = activation.groups()
            target_alias = _replace_participant_reference(target, aliases)
            if target_alias not in referenced_order:
                referenced_order.append(target_alias)
            body.append(f"{indent}{action.lower()} {target_alias}")
            continue

        note = note_re.match(original)
        if note:
            prefix, participants, label = note.groups()
            refs = [_replace_participant_reference(part, aliases) for part in participants.split(",")]
            for name in refs:
                if name not in referenced_order:
                    referenced_order.append(name)
            safe_label = re.sub(r"[\r\n]+", " ", (label or "note")).strip() or "note"
            body.append(f"{prefix}{','.join(refs)}: {safe_label}")
            continue

        # Preserve known Mermaid directives and comments; discard prose/unknown syntax.
        if (
            stripped.startswith("%%")
            or stripped == "autonumber"
            or stripped.startswith("title ")
            or _BLOCK_START_RE.match(stripped)
            or _BRANCH_RE.match(stripped)
            or stripped == "end"
        ):
            body.append(original)

    # Insert declarations for any participant referenced by messages/activation/note.
    undeclared = [name for name in referenced_order if name not in declared]
    declarations_end = 0
    while declarations_end < len(body) and re.match(r"^\s*(participant|actor)\s+", body[declarations_end], re.IGNORECASE):
        declarations_end += 1
    body[declarations_end:declarations_end] = [f"participant {name}" for name in undeclared]
    declared.update(undeclared)

    # Deterministically repair activation and control-block balance.
    repaired: list[str] = []
    active: list[str] = []
    block_depth = 0
    for line in body:
        stripped = line.strip()
        act = _ACTIVATION_RE.match(line)
        if act:
            action, name = act.groups()
            if action == "activate":
                active.append(name)
                repaired.append(line)
            elif name in active:
                # Close the most recent matching activation.
                idx = len(active) - 1 - active[::-1].index(name)
                active.pop(idx)
                repaired.append(line)
            # unmatched deactivate is discarded
            continue
        if _BLOCK_START_RE.match(stripped):
            block_depth += 1
            repaired.append(line)
            continue
        if stripped == "end":
            if block_depth > 0:
                block_depth -= 1
                repaired.append(line)
            continue
        if _BRANCH_RE.match(stripped) and block_depth == 0:
            continue
        repaired.append(line)

    # Close activations before closing control blocks. Reverse order is safest.
    repaired.extend(f"deactivate {name}" for name in reversed(active))
    repaired.extend("end" for _ in range(block_depth))
    return "\n".join(["sequenceDiagram", *repaired]).strip()


def sequence_syntax_issues(text: str) -> list[str]:
    value = normalize_sequence_diagram(text)
    lines = value.splitlines()
    issues: list[str] = []
    if not lines or lines[0].strip() != "sequenceDiagram":
        return ["The first non-empty line must be exactly 'sequenceDiagram'."]

    declared: set[str] = set()
    active: list[str] = []
    block_depth = 0
    for number, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%") or stripped == "autonumber" or stripped.startswith("title "):
            continue
        participant = _PARTICIPANT_RE.match(line)
        if participant:
            declared.add(participant.group(1))
            continue
        activation = _ACTIVATION_RE.match(line)
        if activation:
            action, name = activation.groups()
            if name not in declared:
                issues.append(f"Line {number}: activation target '{name}' is not declared.")
            if action == "activate":
                active.append(name)
            elif name not in active:
                issues.append(f"Line {number}: '{name}' is deactivated without a matching activation.")
            else:
                idx = len(active) - 1 - active[::-1].index(name)
                active.pop(idx)
            continue
        if _BLOCK_START_RE.match(line):
            block_depth += 1
            continue
        if _BRANCH_RE.match(line):
            if block_depth == 0:
                issues.append(f"Line {number}: branch keyword appears outside a block.")
            continue
        if stripped == "end":
            if block_depth == 0:
                issues.append(f"Line {number}: unmatched 'end'.")
            else:
                block_depth -= 1
            continue
        if _NOTE_RE.match(line):
            continue
        message = _MESSAGE_RE.match(line)
        if message:
            sender, _, receiver, label = message.groups()
            for name in (sender, receiver):
                if name not in declared:
                    issues.append(f"Line {number}: participant '{name}' is used before declaration.")
            if not label.strip():
                issues.append(f"Line {number}: message label is empty.")
            continue
        issues.append(f"Line {number}: unsupported or malformed Mermaid sequence syntax: {stripped}")

    if block_depth:
        issues.append(f"There are {block_depth} unclosed Mermaid control block(s).")
    if active:
        issues.append("Unclosed activations: " + ", ".join(active))
    return issues


_ER_RELATIONSHIP_RE = re.compile(
    r'^(\s*[A-Za-z_][\w]*\s+(?:\|\||o\||}\||\|o|oo|\|\{|o\{|}o)--(?:\|\||o\||}\||\|o|oo|\|\{|o\{|}o)\s+[A-Za-z_][\w]*)\s*(?::\s*.*)?$'
)


def normalize_erd_relationship_labels(text: str) -> str:
    value = strip_fence(text)
    output: list[str] = []
    for raw in value.splitlines():
        line = raw.rstrip()
        match = _ER_RELATIONSHIP_RE.match(line)
        if match:
            line = f'{match.group(1)} : ""'
        output.append(line)
    return "\n".join(output).strip()
