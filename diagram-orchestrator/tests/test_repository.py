from diagram_agent.repository import parse_repo_name
from diagram_agent.mermaid import strip_fence, sequence_syntax_issues


def test_parse_repo_name():
    assert parse_repo_name("https://github.com/acme/sample.git") == "sample"


def test_strip_fence():
    assert strip_fence("```mermaid\nerDiagram\n```") == "erDiagram"


def test_validate_mermaid():
    value = "sequenceDiagram\nparticipant A"
    assert value.startswith("sequenceDiagram")
    assert sequence_syntax_issues(value) == []
