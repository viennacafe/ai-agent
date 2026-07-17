# Git Repository Sequence Diagram

## Repository

https://github.com/94-c/study_spring-boot-react-blog.git

## Architecture Summary

```text
Detected architecture summary:
- Controllers: GroupController, UserController
- Services: Not detected
- Repositories: GroupRepository, UserRepository
- Entities/Models: Event, Group, User
- Config files: .mvn/wrapper/maven-wrapper.properties, pom.xml, src/main/resources/application.yaml
```

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant GroupController
    participant GroupRepository
    participant Database

    Client->>GroupController: POST /api/group
    activate GroupController
    GroupController->>GroupRepository: save(Group)
    activate GroupRepository
    GroupRepository->>Database: INSERT Group
    activate Database
    Database-->>GroupRepository: Group saved
    deactivate Database
    GroupRepository-->>GroupController: Group object
    deactivate GroupRepository
    GroupController-->>Client: 201 Created, Group object
    deactivate GroupController

    Client->>GroupController: GET /api/groups
    activate GroupController
    GroupController->>GroupRepository: findAllByUserId(principal.getName())
    activate GroupRepository
    GroupRepository->>Database: SELECT * FROM groups WHERE user_id = ?
    activate Database
    Database-->>GroupRepository: List<Group>
    deactivate Database
    GroupRepository-->>GroupController: List<Group>
    deactivate GroupRepository
    GroupController-->>Client: 200 OK, List<Group>
    deactivate GroupController

    Client->>GroupController: GET /api/group/{id}
    activate GroupController
    GroupController->>GroupRepository: findById(id)
    activate GroupRepository
    GroupRepository->>Database: SELECT * FROM groups WHERE id = ?
    activate Database
    Database-->>GroupRepository: Group object
    deactivate Database
    GroupRepository-->>GroupController: Group object
    deactivate GroupRepository
    GroupController-->>Client: 200 OK, Group object
    deactivate GroupController

    Client->>GroupController: PUT /api/group/{id}
    activate GroupController
    GroupController->>GroupRepository: save(Group)
    activate GroupRepository
    GroupRepository->>Database: UPDATE Group
    activate Database
    Database-->>GroupRepository: Group updated
    deactivate Database
    GroupRepository-->>GroupController: Group object
    deactivate GroupRepository
    GroupController-->>Client: 200 OK, Group object
    deactivate GroupController

    Client->>GroupController: DELETE /api/group/{id}
    activate GroupController
    GroupController->>GroupRepository: deleteById(id)
    activate GroupRepository
    GroupRepository->>Database: DELETE FROM groups WHERE id = ?
    activate Database
    Database-->>GroupRepository: Group deleted
    deactivate Database
    GroupRepository-->>GroupController: void
    deactivate GroupRepository
    GroupController-->>Client: 200 OK
    deactivate GroupController
```
