# Development Guidelines

<cite>
**Referenced Files in This Document**
- [main.py](file://main.py)
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)
- [database.py](file://database.py)
- [security.py](file://security.py)
- [agent.py](file://agent.py)
- [generate_audio.py](file://generate_audio.py)
- [requirements.txt](file://requirements.txt)
- [README.md](file://README.md)
- [test_output.txt](file://test_output.txt)
</cite>

## Update Summary
**Changes Made**
- Enhanced startup logging documentation with detailed migration and seeding processes
- Improved error handling documentation for better debugging capabilities
- Added migration function documentation for database schema updates
- Updated troubleshooting guide with enhanced error handling patterns

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive development guidelines for contributors working on the MuseAmigo Backend. It explains the code organization, module structure, import patterns, FastAPI dependency injection, routing and endpoint organization, coding standards, naming conventions, architectural patterns, testing strategy, debugging/logging practices, and development workflow optimization. It also covers how to add new features, extend existing functionality, and maintain code quality in collaboration.

## Project Structure
The backend follows a modular Python structure with clear separation of concerns:
- Application entry and routing: main.py
- Data modeling: models.py
- Request/response schemas: schemas.py
- Database configuration and dependency: database.py
- Security helpers: security.py
- AI agent and tools: agent.py
- Asset generation utilities: generate_audio.py
- Dependencies: requirements.txt
- Developer documentation: README.md
- Known issue logs: test_output.txt

```mermaid
graph TB
A["main.py<br/>FastAPI app, routes, seeds"] --> B["database.py<br/>Engine, Session, get_db()"]
A --> C["models.py<br/>SQLAlchemy ORM models"]
A --> D["schemas.py<br/>Pydantic models"]
A --> E["agent.py<br/>LangGraph agent + tools"]
A --> F["security.py<br/>Hash/verify helpers"]
E --> B
E --> C
G["generate_audio.py<br/>Audio assets generator"] --> A
```

**Diagram sources**
- [main.py:1-15](file://main.py#L1-L15)
- [database.py:18-38](file://database.py#L18-L38)
- [models.py:1-105](file://models.py#L1-L105)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [agent.py:1-122](file://agent.py#L1-L122)
- [security.py:1-12](file://security.py#L1-L12)
- [generate_audio.py:1-78](file://generate_audio.py#L1-L78)

**Section sources**
- [main.py:1-15](file://main.py#L1-L15)
- [database.py:18-38](file://database.py#L18-L38)
- [models.py:1-105](file://models.py#L1-L105)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [agent.py:1-122](file://agent.py#L1-L122)
- [generate_audio.py:1-78](file://generate_audio.py#L1-L78)
- [requirements.txt:1-59](file://requirements.txt#L1-L59)

## Core Components
- FastAPI application and dependency injection
  - CORS middleware enabled for development
  - Database dependency get_db() yields a scoped Session
  - Startup event seeds initial data and migrates schema with enhanced logging
- SQLAlchemy models define domain entities and relationships
- Pydantic schemas define request/response contracts
- Security helpers for hashing and verifying passwords
- LangGraph agent with tools for artifact, museum, exhibition, and route retrieval
- Audio asset generator for artifact descriptions

Key patterns:
- Dependency injection via Depends(get_db()) in route handlers
- Response models configured with from_attributes for seamless ORM-to-JSON conversion
- Seed/migration logic runs on startup with detailed logging and graceful error handling
- Enhanced error handling with try-catch blocks and user-friendly error messages

**Section sources**
- [main.py:17-23](file://main.py#L17-L23)
- [main.py:512-526](file://main.py#L512-L526)
- [database.py:32-38](file://database.py#L32-L38)
- [schemas.py:16-17](file://schemas.py#L16-L17)
- [schemas.py:33-34](file://schemas.py#L33-L34)
- [schemas.py:47-48](file://schemas.py#L47-L48)
- [agent.py:104-105](file://agent.py#L104-L105)

## Architecture Overview
The backend uses FastAPI with SQLAlchemy for persistence and LangGraph for AI-assisted chat. The system is organized around:
- API layer: routes in main.py
- Domain models: models.py
- Data transfer objects: schemas.py
- Persistence: database.py
- Security: security.py
- AI agent: agent.py

```mermaid
graph TB
subgraph "API Layer"
R["Routes in main.py"]
end
subgraph "Domain & DTO"
M["Models in models.py"]
S["Schemas in schemas.py"]
end
subgraph "Persistence"
D["database.py<br/>Engine, Session, get_db()"]
end
subgraph "AI"
A["agent.py<br/>Agent + Tools"]
end
subgraph "Security"
SEC["security.py"]
end
R --> D
R --> M
R --> S
A --> D
A --> M
R --> SEC
```

**Diagram sources**
- [main.py:538-601](file://main.py#L538-L601)
- [models.py:1-105](file://models.py#L1-L105)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [database.py:18-38](file://database.py#L18-L38)
- [agent.py:17-105](file://agent.py#L17-L105)
- [security.py:1-12](file://security.py#L1-L12)

## Detailed Component Analysis

### FastAPI Routing and Endpoints
- Authentication: register, login, forgot password, reset password
- Museum discovery: list museums
- Artifact lookup: by code with flexible matching
- Collections: add artifact to user collection
- Exhibitions: fetch by museum
- Tickets: purchase and generate QR code
- Routes: fetch by museum
- Achievements: calculate, reset, per-route listing
- User settings: update theme/language
- AI chat: Ogima assistant powered by LangGraph with enhanced error handling

```mermaid
sequenceDiagram
participant Client as "Unity Client"
participant API as "FastAPI main.py"
participant DB as "SQLAlchemy models.py"
participant Sec as "security.py"
participant Agent as "agent.py"
Client->>API : POST /auth/register
API->>DB : Create User
API-->>Client : UserResponse
Client->>API : POST /auth/login
API->>Sec : verify password
API-->>Client : Login success
Client->>API : GET /museums
API->>DB : Query museums
API-->>Client : List[MuseumResponse]
Client->>API : GET /artifacts/{code}
API->>DB : Query artifact (exact/partial)
API-->>Client : ArtifactResponse
Client->>API : POST /collections
API->>DB : Upsert Collection
API-->>Client : CollectionResponse
Client->>API : POST /tickets/purchase
API->>DB : Create Ticket (QR)
API-->>Client : TicketResponse
Client->>API : GET /museums/{id}/exhibitions
API->>DB : Query Exhibitions
API-->>Client : List[ExhibitionResponse]
Client->>API : GET /museums/{id}/routes
API->>DB : Query Routes
API-->>Client : List[RouteResponse]
Client->>API : GET /users/{id}/achievements
API->>DB : Aggregate scans, compute progress
API-->>Client : Stats + achievements
Client->>API : POST /ai/chat
API->>Agent : agent_executor.invoke(messages)
Agent->>DB : Tool calls (artifact/museum/exhibitions/routes)
Agent-->>API : Final reply
API-->>Client : ChatResponse
```

**Diagram sources**
- [main.py:538-601](file://main.py#L538-L601)
- [main.py:604-632](file://main.py#L604-L632)
- [main.py:634-661](file://main.py#L634-L661)
- [main.py:669-694](file://main.py#L669-L694)
- [main.py:664-667](file://main.py#L664-L667)
- [main.py:697-700](file://main.py#L697-L700)
- [main.py:738-844](file://main.py#L738-L844)
- [main.py:869-897](file://main.py#L869-L897)
- [agent.py:17-105](file://agent.py#L17-L105)
- [security.py:11-12](file://security.py#L11-L12)

**Section sources**
- [main.py:538-601](file://main.py#L538-L601)
- [main.py:604-632](file://main.py#L604-L632)
- [main.py:634-661](file://main.py#L634-L661)
- [main.py:669-694](file://main.py#L669-L694)
- [main.py:664-667](file://main.py#L664-L667)
- [main.py:697-700](file://main.py#L697-L700)
- [main.py:738-844](file://main.py#L738-L844)
- [main.py:869-897](file://main.py#L869-L897)

### Data Models and Relationships
The domain model defines entities and foreign keys that reflect museum, artifact, collection, exhibition, ticket, route, achievement, and user achievement relationships.

```mermaid
erDiagram
USERS {
int id PK
string full_name
string email UK
string hashed_password
boolean is_active
string theme
string language
}
MUSEUMS {
int id PK
string name
string operating_hours
int base_ticket_price
float latitude
float longitude
}
ARTIFACTS {
int id PK
string artifact_code UK
string title
string year
string description
boolean is_3d_available
string unity_prefab_name
string audio_asset
int museum_id FK
}
COLLECTIONS {
int id PK
int user_id FK
int artifact_id FK
}
EXHIBITIONS {
int id PK
string name
string location
int museum_id FK
}
TICKETS {
int id PK
string ticket_type
string purchase_date
string qr_code UK
boolean is_used
int user_id FK
int museum_id FK
}
ROUTES {
int id PK
string name
string estimated_time
int stops_count
int museum_id FK
}
ACHIEVEMENTS {
int id PK
string name
string description
string requirement_type
int requirement_value
int points
int museum_id FK
}
USER_ACHIEVEMENTS {
int id PK
int user_id FK
int achievement_id FK
int museum_id FK
boolean is_completed
string completed_at
}
USERS ||--o{ COLLECTIONS : "owns"
USERS ||--o{ TICKETS : "purchases"
USERS ||--o{ USER_ACHIEVEMENTS : "earns"
MUSEUMS ||--o{ ARTIFACTS : "contains"
MUSEUMS ||--o{ EXHIBITIONS : "hosts"
MUSEUMS ||--o{ ROUTES : "provides"
ARTIFACTS ||--o{ COLLECTIONS : "collected_as"
ACHIEVEMENTS ||--o{ USER_ACHIEVEMENTS : "awarded_for"
```

**Diagram sources**
- [models.py:4-105](file://models.py#L4-L105)

**Section sources**
- [models.py:4-105](file://models.py#L4-L105)

### Dependency Injection and Database Sessions
- get_db() creates a SessionLocal instance and yields it to route handlers
- Session is closed in a finally block to avoid leaks
- Engine is configured with connection pooling and pre-ping/recycle

```mermaid
flowchart TD
Start(["Route handler"]) --> Inject["Depends(get_db)"]
Inject --> Yield["yield SessionLocal()"]
Yield --> UseDB["Query/commit/refresh"]
UseDB --> Close["finally: db.close()"]
Close --> End(["Return response"])
```

**Diagram sources**
- [database.py:32-38](file://database.py#L32-L38)

**Section sources**
- [database.py:18-38](file://database.py#L18-L38)
- [database.py:32-38](file://database.py#L32-L38)

### AI Agent and Tools
- Agent uses Google Gemini via LangChain and LangGraph
- Tools: artifact details, museum info, exhibitions, routes
- Agent executor is created and invoked by the chat endpoint with enhanced error handling

```mermaid
sequenceDiagram
participant Client as "Unity Client"
participant API as "FastAPI main.py"
participant Agent as "agent.py"
participant Tools as "Tools (DB queries)"
participant DB as "models.py"
Client->>API : POST /ai/chat
API->>Agent : agent_executor.invoke(messages)
Agent->>Tools : get_artifact_details/get_museum_info/...
Tools->>DB : Query Artifact/Museum/Exhibitions/Routes
DB-->>Tools : Results
Tools-->>Agent : Formatted strings
Agent-->>API : Final reply
API-->>Client : ChatResponse
```

**Diagram sources**
- [main.py:869-897](file://main.py#L869-L897)
- [agent.py:17-105](file://agent.py#L17-L105)

**Section sources**
- [agent.py:17-105](file://agent.py#L17-L105)
- [main.py:869-897](file://main.py#L869-L897)

### Enhanced Startup Logging and Migration System
The application now includes comprehensive startup logging and migration capabilities:

- **Migration Functions**: Two dedicated migration functions handle database schema updates:
  - `migrate_add_audio_asset_column()`: Adds audio_asset column to artifacts table
  - `migrate_add_user_reset_columns()`: Adds reset_token and reset_token_expires columns to users table
- **Startup Process**: Enhanced startup event with detailed logging for each operation
- **Graceful Error Handling**: Try-catch blocks with user-friendly error messages
- **Schema Migration**: Automatic schema updates during startup to ensure database consistency

```mermaid
flowchart TD
Start(["App Startup"]) --> Migrations["Run Migrations"]
Migrations --> AudioCol["Add audio_asset column"]
AudioCol --> UserCols["Add reset_token columns"]
UserCols --> Seeding["Seed Data"]
Seeding --> Museums["Seed Museums"]
Museums --> Artifacts["Seed Artifacts"]
Artifacts --> Exhibitions["Seed Exhibitions"]
Exhibitions --> Routes["Seed Routes"]
Routes --> Achievements["Seed Achievements"]
Achievements --> Cleanup["Cleanup Artifact ID 1"]
Cleanup --> Complete["Startup Complete"]
```

**Diagram sources**
- [main.py:402-452](file://main.py#L402-L452)
- [main.py:455-487](file://main.py#L455-L487)

**Section sources**
- [main.py:402-452](file://main.py#L402-L452)
- [main.py:455-487](file://main.py#L455-L487)

### Coding Standards and Naming Conventions
- Module-level imports grouped and ordered logically
- Handler functions prefixed with domain intent (e.g., get_, post_, put_)
- Response models suffixed with Response
- Database models use PascalCase
- Pydantic models use PascalCase
- Constants and configuration derived from environment variables
- Clear separation between request DTOs and response DTOs
- Enhanced error handling with descriptive exception messages

**Section sources**
- [main.py:1-11](file://main.py#L1-L11)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [models.py:1-105](file://models.py#L1-L105)

### Architectural Patterns
- Repository pattern: SQLAlchemy ORM acts as a repository for each entity
- Factory pattern: get_db() produces database sessions
- Observer pattern: Achievements computed and persisted when conditions change
- Migration pattern: Database schema updates handled through dedicated functions

```mermaid
classDiagram
class DatabaseFactory {
+get_db() Session
}
class UserRepository {
+create(user) User
+find_by_email(email) User
}
class AchievementEngine {
+calculate(user_id) Stats
+reset(user_id, museum_id)
}
class MigrationManager {
+migrate_add_audio_asset_column()
+migrate_add_user_reset_columns()
}
DatabaseFactory --> UserRepository : "provides Session"
AchievementEngine --> UserRepository : "reads collections"
MigrationManager --> DatabaseFactory : "updates schema"
```

**Diagram sources**
- [database.py:32-38](file://database.py#L32-L38)
- [models.py:4-105](file://models.py#L4-L105)
- [main.py:738-844](file://main.py#L738-L844)
- [main.py:402-452](file://main.py#L402-L452)

**Section sources**
- [database.py:32-38](file://database.py#L32-L38)
- [main.py:738-844](file://main.py#L738-L844)
- [main.py:402-452](file://main.py#L402-L452)

## Dependency Analysis
External libraries include FastAPI, SQLAlchemy, Pydantic, LangChain/LangGraph, Google Generative AI, passlib/bcrypt, and PyMySQL. The project relies on a MySQL-compatible database and environment-driven configuration.

```mermaid
graph LR
FA["FastAPI"] --> SQ["SQLAlchemy"]
FA --> PY["Pydantic"]
FA --> LG["LangGraph"]
LG --> LC["LangChain"]
LG --> GG["Google Generative AI"]
FA --> SEC["passlib/bcrypt"]
SQ --> DB["MySQL (via PyMySQL)"]
```

**Diagram sources**
- [requirements.txt:12-59](file://requirements.txt#L12-L59)

**Section sources**
- [requirements.txt:12-59](file://requirements.txt#L12-L59)

## Performance Considerations
- Connection pooling: Engine configured with pool_size, max_overflow, pre_ping, and recycle
- Minimal ORM overhead: Selective field exposure via Pydantic from_attributes
- Efficient queries: Exact/partial artifact lookup reduces unnecessary scans
- AI tool calls: Limit tool scope to essential operations
- Graceful degradation: Startup failures don't prevent application from running

## Troubleshooting Guide
Common issues and resolutions:
- Database connectivity
  - Verify DATABASE_URL in .env; fallback defaults are provided
  - Ensure MySQL service is reachable
- AI agent errors
  - GOOGLE_API_KEY must be present in .env
  - Known deprecation warning indicates import path change; adjust agent creation accordingly
- Integrity errors
  - Email uniqueness enforced; handle duplicate registration gracefully
- Cold start delays
  - Render free tier may sleep; expect slower first request
- Startup logging issues
  - Enhanced logging provides detailed migration progress
  - Migration failures are caught and logged without stopping app startup
- Error handling improvements
  - Comprehensive try-catch blocks with user-friendly error messages
  - AI chat errors return HTTP 500 with detailed error information

**Updated** Enhanced startup logging and improved error handling for better debugging experience

**Section sources**
- [database.py:12-15](file://database.py#L12-L15)
- [agent.py:14-15](file://agent.py#L14-L15)
- [test_output.txt:1-12](file://test_output.txt#L1-L12)
- [main.py:560-567](file://main.py#L560-L567)
- [main.py:455-487](file://main.py#L455-L487)
- [main.py:894-897](file://main.py#L894-L897)

## Conclusion
This backend leverages FastAPI, SQLAlchemy, and LangGraph to deliver a cohesive museum experience. Contributors should adhere to established import patterns, dependency injection, schema contracts, and architectural practices. The enhanced startup logging and improved error handling provide better debugging capabilities and development experience. Use the provided testing and debugging guidance to maintain stability and performance as new features are added.

## Appendices

### Adding New Features
- Define a new Pydantic schema in schemas.py for request/response
- Add a new SQLAlchemy model in models.py if needed
- Implement a route in main.py with proper Depends(get_db())
- Seed or migrate data if required
- Keep error handling explicit and return appropriate HTTP status codes
- Document new endpoints in Swagger UI

**Section sources**
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [models.py:1-105](file://models.py#L1-L105)
- [main.py:512-526](file://main.py#L512-L526)

### Extending Existing Functionality
- For new endpoints, reuse get_db() dependency
- For AI assistance, add a new tool in agent.py and wire it into the agent executor
- For audio assets, use generate_audio.py to produce placeholders and update artifact entries
- For database schema changes, create migration functions similar to existing ones

**Section sources**
- [database.py:32-38](file://database.py#L32-L38)
- [agent.py:17-105](file://agent.py#L17-L105)
- [generate_audio.py:41-78](file://generate_audio.py#L41-L78)
- [main.py:402-452](file://main.py#L402-L452)

### Testing Strategy
- Unit tests: Validate schemas and helper functions (e.g., password hashing)
- Integration tests: Use FastAPI TestClient to exercise routes with mocked DB sessions
- API tests: Use Swagger UI to manually validate endpoints and responses
- CI/CD: Automate tests and linting in the pipeline
- Startup testing: Verify migration functions execute successfully without errors

**Section sources**
- [README.md:24-33](file://README.md#L24-L33)

### Debugging and Logging Practices
- Use structured logging in handlers for request/response inspection
- Wrap AI tool calls with try/catch to prevent server failures
- Log exceptions with context and return user-friendly messages
- Leverage database transaction rollback on failure
- Monitor startup logs for migration progress and errors
- Utilize enhanced error messages for better debugging experience

**Updated** Enhanced logging and error handling for improved debugging capabilities

**Section sources**
- [main.py:560-567](file://main.py#L560-L567)
- [main.py:894-897](file://main.py#L894-L897)
- [main.py:455-487](file://main.py#L455-L487)

### Development Workflow Optimization
- Keep requirements.txt updated after installing new packages
- Commit and push changes; Render will auto-deploy
- Use Swagger UI for quick smoke tests
- Avoid exposing secrets; keep DATABASE_URL and GOOGLE_API_KEY in .env
- Monitor startup logs for migration progress
- Test error handling scenarios with invalid inputs

**Section sources**
- [README.md:36-48](file://README.md#L36-L48)
- [README.md:24-33](file://README.md#L24-L33)