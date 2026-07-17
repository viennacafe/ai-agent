# Git Repository Sequence Diagram

## Repository

https://github.com/hojunnnnn/board.git

## Architecture Summary

```text
Detected architecture summary:
- Controllers: CommentApiController, PostsApiController, PostsApiControllerTest, PostsIndexController, UserApiController, UserController
- Services: CommentService, CustomOAuth2UserService, CustomUserDetailsService, PostsService, PostsServiceTest, UserService
- Repositories: CommentRepository, CommentRepositoryTest, PostsRepository, PostsRepositoryTest, UserRepository, UserRepositoryTest
- Entities/Models: BaseTimeEntity, Comment, Posts, User
- Config files: build.gradle, gradle/wrapper/gradle-wrapper.properties, settings.gradle, src/main/resources/application.properties
```

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant PostsApiController
    participant PostsService
    participant PostsRepository
    participant Database

    Client->>PostsApiController: POST /api/posts
    activate PostsApiController
    PostsApiController->>PostsService: save(dto, user.getNickname())
    activate PostsService
    PostsService->>PostsRepository: save(posts)
    activate PostsRepository
    PostsRepository->>Database: INSERT INTO posts (title, content, writer, user_id)
    deactivate PostsRepository
    PostsService-->>PostsApiController: return posts.getId()
    deactivate PostsService
    PostsApiController-->>Client: return postsId

    Client->>PostsApiController: GET /api/posts/{id}
    activate PostsApiController
    PostsApiController->>PostsService: findById(id)
    activate PostsService
    PostsService->>PostsRepository: findById(id)
    activate PostsRepository
    PostsRepository->>Database: SELECT * FROM posts WHERE id = {id}
    deactivate PostsRepository
    PostsService-->>PostsApiController: return PostsDto.Response(posts)
    deactivate PostsService
    PostsApiController-->>Client: return PostsDto.Response

    Client->>PostsApiController: PUT /api/posts/{id}
    activate PostsApiController
    PostsApiController->>PostsService: update(id, dto)
    activate PostsService
    PostsService->>PostsRepository: findById(id)
    activate PostsRepository
    PostsRepository->>Database: SELECT * FROM posts WHERE id = {id}
    deactivate PostsRepository
    PostsService->>PostsRepository: update(posts)
    activate PostsRepository
    PostsRepository->>Database: UPDATE posts SET title = {title}, content = {content} WHERE id = {id}
    deactivate PostsRepository
    deactivate PostsService
    PostsApiController-->>Client: return id

    Client->>PostsApiController: DELETE /api/posts/{id}
    activate PostsApiController
    PostsApiController->>PostsService: delete(id)
    activate PostsService
    PostsService->>PostsRepository: findById(id)
    activate PostsRepository
    PostsRepository->>Database: SELECT * FROM posts WHERE id = {id}
    deactivate PostsRepository
    PostsService->>PostsRepository: delete(posts)
    activate PostsRepository
    PostsRepository->>Database: DELETE FROM posts WHERE id = {id}
    deactivate PostsRepository
    deactivate PostsService
    PostsApiController-->>Client: return id
    deactivate PostsApiController
```
