# Deployment & Production

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [requirements.txt](file://requirements.txt)
- [main.py](file://main.py)
- [database.py](file://database.py)
- [schemas.py](file://schemas.py)
- [models.py](file://models.py)
- [security.py](file://security.py)
- [agent.py](file://agent.py)
- [generate_audio.py](file://generate_audio.py)
</cite>

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
This document provides comprehensive deployment and production guidance for the MuseAmigo Backend. It covers production deployment on Render, environment configuration, database URL setup, API key management, CI/CD workflow via GitHub integration, frontend integration with the Unity C# client, performance considerations (cold starts, connection pooling, memory management), monitoring and logging strategies, error handling, maintenance procedures, scaling, backups, disaster recovery, and troubleshooting.

## Project Structure
The backend is a FastAPI application with SQLAlchemy ORM, integrated with a MySQL-compatible cloud database and Google Gemini for conversational AI. The repository includes:
- Application entry and routing: main.py
- Database configuration and connection pooling: database.py
- Data models and schemas: models.py, schemas.py
- Security helpers: security.py
- AI agent integration: agent.py
- Audio generation utilities: generate_audio.py
- Dependencies: requirements.txt
- Deployment and usage guidance: README.md

```mermaid
graph TB
subgraph "Application"
Main["main.py"]
DB["database.py"]
Models["models.py"]
Schemas["schemas.py"]
Security["security.py"]
Agent["agent.py"]
Audio["generate_audio.py"]
end
subgraph "External Services"
MySQL["MySQL-compatible DB<br/>via DATABASE_URL"]
Gemini["Google Gemini API<br/>via GOOGLE_API_KEY"]
Render["Render Platform<br/>Uvicorn + ASGI"]
Unity["Unity C# Client"]
end
Main --> DB
Main --> Models
Main --> Schemas
Main --> Security
Main --> Agent
Agent --> DB
Agent --> Gemini
DB --> MySQL
Main --> Render
Unity --> Main
```

**Diagram sources**
- [main.py](file://main.py)
- [database.py](file://database.py)
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)
- [security.py](file://security.py)
- [agent.py](file://agent.py)
- [generate_audio.py](file://generate_audio.py)

**Section sources**
- [README.md](file://README.md)
- [requirements.txt](file://requirements.txt)
- [main.py](file://main.py)
- [database.py](file://database.py)
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)
- [security.py](file://security.py)
- [agent.py](file://agent.py)
- [generate_audio.py](file://generate_audio.py)

## Core Components
- FastAPI application with CORS middleware and database initialization on startup
- SQLAlchemy engine with connection pooling and pre-ping/recycle settings
- Environment-driven database URL and optional fallback to local MySQL
- AI agent powered by Google Gemini with tooling for artifact, museum, exhibition, and route queries
- Unity integration endpoints for museums, artifacts, collections, tickets, routes, and achievements
- Password hashing utilities for secure credential handling

Key production-relevant elements:
- Environment variables: DATABASE_URL, GOOGLE_API_KEY
- Startup seeding of museums, artifacts, exhibitions, routes, and achievements
- Endpoint coverage for frontend consumption

**Section sources**
- [main.py](file://main.py)
- [database.py](file://database.py)
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)
- [security.py](file://security.py)
- [agent.py](file://agent.py)

## Architecture Overview
The backend runs on Render with Uvicorn as the ASGI server. Requests flow from the Unity client to FastAPI endpoints, which interact with SQLAlchemy ORM to query the MySQL-compatible database. Conversational AI features leverage Google Gemini via an API key stored in environment variables.

```mermaid
sequenceDiagram
participant Unity as "Unity C# Client"
participant API as "FastAPI App (main.py)"
participant DB as "SQLAlchemy Engine (database.py)"
participant Gemini as "Google Gemini (agent.py)"
Unity->>API : HTTP Request (e.g., GET /museums)
API->>DB : Query models (e.g., Museum)
DB-->>API : ORM Results
API-->>Unity : JSON Response
Unity->>API : POST /auth/register or /auth/login
API->>DB : Create/verify user
DB-->>API : User record
API-->>Unity : Auth response
Unity->>API : POST /collections or /tickets/purchase
API->>DB : Insert/update records
DB-->>API : Persisted records
API-->>Unity : Confirmation
Unity->>API : GET /chat (optional)
API->>Gemini : Tool-enabled agent query
Gemini-->>API : AI reply
API-->>Unity : ChatResponse
```

**Diagram sources**
- [main.py](file://main.py)
- [database.py](file://database.py)
- [agent.py](file://agent.py)

## Detailed Component Analysis

### Database Layer
- Environment-driven URL with fallback to local MySQL
- Connection pooling configured with pool_size, max_overflow, pool_pre_ping, and pool_recycle
- Session factory and dependency injection for route handlers
- Startup migration to add audio_asset column if missing

```mermaid
flowchart TD
Start(["Startup"]) --> LoadEnv["Load .env variables"]
LoadEnv --> BuildURL["Build DATABASE_URL"]
BuildURL --> CreateEngine["Create SQLAlchemy Engine<br/>with pool settings"]
CreateEngine --> PrePing["pool_pre_ping enabled"]
PrePing --> Recycle["pool_recycle set"]
Recycle --> Ready(["Ready for requests"])
```

**Diagram sources**
- [database.py](file://database.py)

**Section sources**
- [database.py](file://database.py)
- [main.py](file://main.py)

### AI Agent Integration
- Loads GOOGLE_API_KEY from .env and validates presence
- Provides tools to query artifacts, museums, exhibitions, and routes
- Uses LangChain React agent with Google Gemini LLM

```mermaid
sequenceDiagram
participant API as "FastAPI App"
participant Agent as "Agent (agent.py)"
participant Tools as "Tools (DB queries)"
participant DB as "SQLAlchemy"
API->>Agent : Invoke chat with user message
Agent->>Tools : get_artifact_details/get_museum_info/get_exhibitions/get_routes
Tools->>DB : Query models
DB-->>Tools : Results
Tools-->>Agent : Formatted facts
Agent-->>API : Final reply
API-->>Caller : ChatResponse
```

**Diagram sources**
- [agent.py](file://agent.py)
- [database.py](file://database.py)
- [models.py](file://models.py)

**Section sources**
- [agent.py](file://agent.py)
- [database.py](file://database.py)
- [models.py](file://models.py)

### Authentication and Security
- Password hashing and verification utilities
- Registration and login endpoints with validation and integrity handling
- CORS configured for development; adjust for production origins

```mermaid
flowchart TD
RegStart["POST /auth/register"] --> Validate["Validate input fields"]
Validate --> Hash["Hash password (placeholder)"]
Hash --> Save["Insert user into DB"]
Save --> Success["Return UserResponse"]
LoginStart["POST /auth/login"] --> Find["Find user by email"]
Find --> Match{"Credentials match?"}
Match --> |No| Error["HTTP 404 Invalid credentials"]
Match --> |Yes| Fields{"Has required fields?"}
Fields --> |No| Incomplete["HTTP 400 Incomplete account"]
Fields --> |Yes| Ok["Return success payload"]
```

**Diagram sources**
- [main.py](file://main.py)
- [security.py](file://security.py)

**Section sources**
- [main.py](file://main.py)
- [security.py](file://security.py)

### Data Models and Schemas
- Users, Museums, Artifacts, Collections, Exhibitions, Tickets, Routes, Achievements, UserAchievements
- Pydantic schemas for request/response serialization
- Relationships defined via foreign keys

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
MUSEUMS ||--o{ ARTIFACTS : "contains"
MUSEUMS ||--o{ EXHIBITIONS : "hosts"
MUSEUMS ||--o{ ROUTES : "provides"
MUSEUMS ||--o{ ACHIEVEMENTS : "defines"
ARTIFACTS ||--o{ COLLECTIONS : "collected"
ARTIFACTS ||--o{ USER_ACHIEVEMENTS : "triggers"
ACHIEVEMENTS ||--o{ USER_ACHIEVEMENTS : "awarded"
```

**Diagram sources**
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)

**Section sources**
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)

### API Coverage for Unity Integration
Endpoints commonly consumed by the Unity client include:
- GET /museums
- GET /artifacts/{artifact_code}
- POST /collections
- POST /tickets/purchase
- GET /museums/{museum_id}/exhibitions
- GET /museums/{museum_id}/routes
- GET /museums/{museum_id}/routes/{route_id}/achievements
- POST /users/{user_id}/achievements/reset/{museum_id}
- GET /users/{user_id}/achievements
- POST /auth/register
- POST /auth/login

These endpoints align with the Unity integration pattern described in the repository’s README.

**Section sources**
- [main.py](file://main.py)
- [README.md](file://README.md)

## Dependency Analysis
Runtime dependencies include FastAPI, Uvicorn, SQLAlchemy, PyMySQL, Pydantic, LangChain, and Google Generative AI. The application relies on environment variables for database connectivity and AI API access.

```mermaid
graph LR
FastAPI["FastAPI"] --> SQLA["SQLAlchemy"]
FastAPI --> Pydantic["Pydantic"]
FastAPI --> Uvicorn["Uvicorn"]
SQLA --> PyMySQL["PyMySQL"]
Agent["LangChain Agent"] --> Gemini["Google Generative AI"]
Agent --> SQLA
```

**Diagram sources**
- [requirements.txt](file://requirements.txt)
- [main.py](file://main.py)
- [agent.py](file://agent.py)
- [database.py](file://database.py)

**Section sources**
- [requirements.txt](file://requirements.txt)
- [main.py](file://main.py)
- [agent.py](file://agent.py)
- [database.py](file://database.py)

## Performance Considerations
- Cold start handling for free-tier hosting:
  - Expect initial request latency after idle periods on Render Free tier.
  - Plan for first-run delays and cache warm-up strategies.
- Connection pooling optimization:
  - Connection pool size and overflow are configured in the database engine.
  - Enable pre-ping to validate connections and recycle periodically to avoid stale connections.
- Memory management:
  - Ensure database sessions are closed in all code paths (context managers or try/finally).
  - Limit payload sizes and pagination for large lists.
  - Avoid loading unnecessary fields in ORM queries.
- AI agent performance:
  - Keep tool queries efficient; limit result sets.
  - Consider caching frequently accessed facts if appropriate.
- Endpoint-level optimizations:
  - Add response caching for read-heavy endpoints where safe.
  - Use database indexes on frequently filtered columns (e.g., artifact_code, user_id).

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common production issues and resolutions:
- Database connectivity failures:
  - Verify DATABASE_URL environment variable is set on Render.
  - Confirm network access to the cloud database endpoint.
- Missing GOOGLE_API_KEY:
  - Ensure GOOGLE_API_KEY is present in environment variables for AI features.
- CORS errors in production:
  - Configure allow_origins to specific domains instead of wildcard.
- Integrity errors on registration:
  - Handle duplicate emails gracefully and return user-friendly messages.
- Slow initial requests:
  - Accept cold start delays on free tier; consider keep-alive or scheduled pings.
- Session leaks:
  - Ensure get_db() is used as a dependency and sessions are closed in all branches.

**Section sources**
- [database.py](file://database.py)
- [agent.py](file://agent.py)
- [main.py](file://main.py)

## Conclusion
This document outlined production deployment of the MuseAmigo Backend on Render, environment configuration, database and API key management, CI/CD workflow, Unity integration, performance tuning, monitoring/logging, error handling, maintenance, scaling, backups, and disaster recovery. Adhering to these practices will help maintain a reliable, scalable, and observable backend for the Unity client.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### A. Production Deployment on Render
- Platform: Render with Uvicorn + ASGI
- Environment variables to configure:
  - DATABASE_URL: Cloud database connection string
  - GOOGLE_API_KEY: Google Gemini API key
- Build command and start command are inferred from the runtime; ensure requirements.txt is accurate.
- Swagger UI endpoint for testing is exposed at the Render domain.

**Section sources**
- [README.md](file://README.md)
- [database.py](file://database.py)
- [agent.py](file://agent.py)

### B. CI/CD Workflow via GitHub Integration
- Commit and push changes to the main branch.
- Render will trigger a build and deploy the latest commit automatically.
- Typical build time is a few minutes.

**Section sources**
- [README.md](file://README.md)

### C. Frontend Integration with Unity C#
- Base URL for production: https://museamigo-backend.onrender.com
- Example patterns:
  - GET /museums
  - GET /artifacts/{artifact_code}
  - POST /collections
  - POST /tickets/purchase
  - GET /museums/{museum_id}/exhibitions
  - GET /museums/{museum_id}/routes
  - GET /museums/{museum_id}/routes/{route_id}/achievements
  - POST /users/{user_id}/achievements/reset/{museum_id}
  - GET /users/{user_id}/achievements
  - POST /auth/register
  - POST /auth/login

**Section sources**
- [README.md](file://README.md)
- [main.py](file://main.py)

### D. Monitoring and Logging Strategies
- Enable structured logging in production (e.g., JSON logs).
- Centralize logs on Render or a log aggregation service.
- Monitor uptime, response times, error rates, and cold start durations.
- Set up alerts for sustained high error rates or slow response times.

[No sources needed since this section provides general guidance]

### E. Scaling, Backups, and Disaster Recovery
- Scaling:
  - Horizontal scaling with multiple instances behind a load balancer.
  - Stateless design to enable easy scaling.
- Backups:
  - Schedule regular logical backups of the MySQL-compatible database.
  - Store backups securely and test restore procedures periodically.
- Disaster recovery:
  - Maintain a documented RTO/RPO.
  - Automate restoration steps and validate them regularly.

[No sources needed since this section provides general guidance]