from diagram_agent.mermaid import normalize_sequence_diagram, sequence_syntax_issues


def test_normalize_removes_arrow_activation_markers():
    source = """sequenceDiagram
participant Client
participant Service
Client->>+Service: call
activate Service
Service-->>-Client: result
deactivate Service
"""
    normalized = normalize_sequence_diagram(source)
    assert "->>+" not in normalized
    assert "-->>-" not in normalized
    assert sequence_syntax_issues(normalized) == []


def test_repairs_unclosed_activation():
    source = """sequenceDiagram
participant Client
participant Service
Client->>Service: call
activate Service
"""
    normalized = normalize_sequence_diagram(source)
    assert normalized.rstrip().endswith("deactivate Service")
    assert sequence_syntax_issues(normalized) == []


def test_repairs_undeclared_participant():
    source = """sequenceDiagram
participant Client
Client->>Service: call
"""
    normalized = normalize_sequence_diagram(source)
    assert "participant Service" in normalized
    assert sequence_syntax_issues(normalized) == []


def test_repairs_unclosed_alt_block():
    source = """sequenceDiagram
participant A
participant B
alt success
A->>B: call
"""
    normalized = normalize_sequence_diagram(source)
    assert normalized.rstrip().endswith("end")
    assert sequence_syntax_issues(normalized) == []

from diagram_agent.mermaid import normalize_erd_relationship_labels


def test_erd_relationship_labels_are_blank():
    source = '''erDiagram
    USER ||--o{ POST : writes
    POST }o--|| USER : "belongs to"
'''
    normalized = normalize_erd_relationship_labels(source)
    assert ': writes' not in normalized
    assert 'belongs to' not in normalized
    assert normalized.count(': ""') == 2


def test_posts_api_controller_delete_is_sanitized():
    source = '''sequenceDiagram
participant Client
participant PostsApiController.delete
participant PostsService.delete
Client->>PostsApiController.delete: DELETE /posts/{id}
activate PostsApiController.delete
PostsApiController.delete->>PostsService.delete: delete(id)
PostsService.delete-->>PostsApiController.delete: deleted
PostsApiController.delete-->>Client: 204 No Content
deactivate PostsApiController.delete
'''
    normalized = normalize_sequence_diagram(source)
    assert 'participant PostsApiController_delete as "PostsApiController"' in normalized
    assert 'participant PostsService_delete as "PostsService"' in normalized
    assert 'Client->>PostsApiController_delete: DELETE /posts/{id}' in normalized
    assert 'activate PostsApiController_delete' in normalized
    assert 'PostsApiController.delete' not in normalized
    assert sequence_syntax_issues(normalized) == []


def test_invalid_participant_alias_with_parentheses_is_sanitized():
    source = '''sequenceDiagram
participant Client
participant Controller.delete()
Client->>Controller.delete(): call
Controller.delete()-->>Client: ok
'''
    normalized = normalize_sequence_diagram(source)
    assert 'participant Controller_delete as "Controller"' in normalized
    assert 'Client->>Controller_delete: call' in normalized
    assert sequence_syntax_issues(normalized) == []


def test_empty_return_message_gets_default_label():
    source = '''sequenceDiagram
participant PostsRepository
participant PostsService
PostsRepository-->>PostsService
'''
    normalized = normalize_sequence_diagram(source)
    assert 'PostsRepository-->>PostsService: completed' in normalized
    assert sequence_syntax_issues(normalized) == []


def test_colon_with_empty_message_gets_default_label():
    source = '''sequenceDiagram
participant CommentRepository
participant CommentService
CommentRepository-->>CommentService:
'''
    normalized = normalize_sequence_diagram(source)
    assert 'CommentRepository-->>CommentService: completed' in normalized
    assert sequence_syntax_issues(normalized) == []


def test_undeclared_participants_are_inserted():
    source = '''sequenceDiagram
Client->>Controller: call
Controller-->>Client: ok
'''
    normalized = normalize_sequence_diagram(source)
    assert 'participant Client' in normalized
    assert 'participant Controller' in normalized
    assert sequence_syntax_issues(normalized) == []


def test_activation_balance_is_repaired():
    source = '''sequenceDiagram
participant Client
participant Service
Client->>Service: call
activate Service
Service-->>Client: ok
'''
    normalized = normalize_sequence_diagram(source)
    assert normalized.rstrip().endswith('deactivate Service')
    assert sequence_syntax_issues(normalized) == []


def test_user_reported_delete_sequences_are_valid():
    source = '''sequenceDiagram
participant Client
participant PostsApiController
participant PostsService
participant PostsRepository
Client->>PostsApiController: DELETE /api/posts/{id}
activate PostsApiController
PostsApiController->>PostsService: delete(id)
activate PostsService
PostsService->>PostsRepository: delete(posts)
activate PostsRepository
PostsRepository-->>PostsService
 deactivate PostsRepository
PostsService-->>PostsApiController
 deactivate PostsService
PostsApiController-->>Client: 200 OK
 deactivate PostsApiController
'''
    normalized = normalize_sequence_diagram(source)
    assert 'PostsRepository-->>PostsService: completed' in normalized
    assert 'PostsService-->>PostsApiController: completed' in normalized
    assert sequence_syntax_issues(normalized) == []
