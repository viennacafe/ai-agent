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
    PostsRepository->>Database: INSERT INTO posts
    deactivate PostsRepository
    PostsService-->>PostsApiController: return posts.getId()
    deactivate PostsService
    PostsApiController-->>Client: ResponseEntity.ok(postsId)
```
