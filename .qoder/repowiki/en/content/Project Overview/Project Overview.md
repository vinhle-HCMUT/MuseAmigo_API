# Project Overview

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [main.py](file://main.py)
- [models.py](file://models.py)
- [schemas.py](file://schemas.py)
- [database.py](file://database.py)
- [agent.py](file://agent.py)
- [security.py](file://security.py)
- [generate_audio.py](file://generate_audio.py)
- [requirements.txt](file://requirements.txt)
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

## Introduction

MuseAmigo is an innovative interactive museum experience platform designed to seamlessly blend physical museum visits with digital storytelling. The system creates an immersive educational journey where visitors can scan QR codes to unlock rich multimedia experiences, engage with AI-powered chat assistance, and participate in gamified exploration activities.

The platform serves as a comprehensive ecosystem that transforms traditional museum visits into dynamic, personalized adventures. Visitors can discover historical artifacts through 3D models, listen to narrated stories, navigate guided tours, collect virtual treasures, and earn achievements while exploring cultural institutions.

At its core, MuseAmigo combines cutting-edge technologies to deliver an engaging experience:
- **QR Code Integration**: Physical artifact identification through scannable codes
- **AI-Powered Assistance**: Intelligent chatbot powered by Google Gemini AI
- **Gamification System**: Achievement tracking and reward mechanisms
- **Real-time Navigation**: Interactive route planning and museum guidance
- **Multi-platform Experience**: Seamless integration between mobile apps and Unity-based applications

## Project Structure

The MuseAmigo Backend follows a modular FastAPI architecture organized around clear functional domains:

```mermaid
graph TB
subgraph "Core Application"
MAIN[main.py<br/>FastAPI Application]
DB[database.py<br/>Database Engine]
MODELS[models.py<br/>ORM Models]
SCHEMAS[schemas.py<br/>Pydantic Schemas]
end
subgraph "AI & Intelligence"
AGENT[agent.py<br/>Gemini AI Agent]
SECURITY[security.py<br/>Password Security]
end
subgraph "Audio System"
AUDIO[generate_audio.py<br/>Audio Generation]
end
subgraph "External Services"
RENDER[Render Cloud<br/>Deployment Platform]
MYSQL[MySQL Database<br/>Aiven Cloud]
GEMINI[Google Gemini AI<br/>Language Model]
end
MAIN --> DB
MAIN --> MODELS
MAIN --> SCHEMAS
MAIN --> AGENT
AGENT --> MYSQL
DB --> MYSQL
RENDER --> MAIN
GEMINI --> AGENT
```

**Diagram sources**
- [main.py:1-25](file://main.py#L1-L25)
- [database.py:1-38](file://database.py#L1-L38)
- [agent.py:1-122](file://agent.py#L1-L122)

The backend is structured around several key layers:

- **Application Layer**: FastAPI routes and business logic
- **Data Access Layer**: SQLAlchemy ORM models and database connections
- **Integration Layer**: AI agent and external service integrations
- **Presentation Layer**: Pydantic schemas for request/response validation

**Section sources**
- [main.py:12-25](file://main.py#L12-L25)
- [database.py:1-38](file://database.py#L1-L38)
- [models.py:1-105](file://models.py#L1-L105)

## Core Components

### Database Schema Architecture

The system employs a comprehensive relational database design supporting multiple museum collections and interactive features:

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
ARTIFACTS ||--o{ COLLECTIONS : "collected"
ARTIFACTS ||--o{ USER_ACHIEVEMENTS : "triggers"
MUSEUMS ||--o{ ARTIFACTS : "contains"
MUSEUMS ||--o{ EXHIBITIONS : "hosts"
MUSEUMS ||--o{ ROUTES : "provides"
MUSEUMS ||--o{ TICKETS : "issues"
ACHIEVEMENTS ||--o{ USER_ACHIEVEMENTS : "awarded"
```

**Diagram sources**
- [models.py:4-105](file://models.py#L4-L105)

### Authentication System

The backend implements a robust user authentication mechanism with password hashing and session management:

```mermaid
sequenceDiagram
participant Client as "Unity Client"
participant API as "FastAPI Backend"
participant DB as "MySQL Database"
participant Security as "Security Module"
Client->>API : POST /auth/register
API->>Security : Hash password
Security-->>API : Hashed password
API->>DB : Create user record
DB-->>API : User created
API-->>Client : UserResponse
Client->>API : POST /auth/login
API->>DB : Find user by email
DB-->>API : User found
API->>Security : Verify password
Security-->>API : Password verified
API-->>Client : Login success response
```

**Diagram sources**
- [main.py:538-601](file://main.py#L538-L601)
- [security.py:1-12](file://security.py#L1-L12)

**Section sources**
- [models.py:4-15](file://models.py#L4-L15)
- [schemas.py:4-23](file://schemas.py#L4-L23)
- [security.py:1-12](file://security.py#L1-L12)

## Architecture Overview

MuseAmigo operates as a centralized API platform serving multiple client applications and external services:

```mermaid
graph TB
subgraph "Client Applications"
UNITY[Unity Mobile App]
WEB[Web Interface]
ADMIN[Admin Dashboard]
end
subgraph "Backend Services"
FASTAPI[FastAPI Core API]
AGENT[AI Assistant Service]
AUDIO[Audio Processing]
end
subgraph "Data Layer"
MYSQL[(MySQL Database)]
REDIS[(Redis Cache)]
end
subgraph "External Integrations"
GEMINI[Google Gemini AI]
RENDER[Render Cloud]
AIVEN[Aiven Cloud]
end
UNITY --> FASTAPI
WEB --> FASTAPI
ADMIN --> FASTAPI
FASTAPI --> MYSQL
FASTAPI --> REDIS
AGENT --> GEMINI
AGENT --> MYSQL
AUDIO --> FASTAPI
RENDER --> FASTAPI
AIVEN --> MYSQL
```

**Diagram sources**
- [main.py:1-15](file://main.py#L1-L15)
- [agent.py:94-105](file://agent.py#L94-L105)
- [database.py:12-24](file://database.py#L12-L24)

The architecture emphasizes scalability and modularity:

- **Centralized API**: Single source of truth for all museum data and user interactions
- **Service-Oriented Design**: Clear separation between authentication, content delivery, and AI assistance
- **Cloud-Native Deployment**: Optimized for containerized deployment and auto-scaling
- **AI Integration**: Intelligent assistant service enhances user experience through natural language processing

**Section sources**
- [README.md:3](file://README.md#L3)
- [main.py:15-23](file://main.py#L15-L23)

## Detailed Component Analysis

### Artifact Discovery System

The artifact discovery mechanism enables seamless QR code scanning and content delivery:

```mermaid
sequenceDiagram
participant Visitor as "Visitor Device"
participant API as "Artifact API"
participant DB as "Database"
participant Unity as "Unity Client"
Visitor->>API : Scan QR Code
API->>DB : Query artifact by code
DB-->>API : Artifact details
API->>API : Process 3D availability
API->>API : Generate audio asset path
API-->>Visitor : ArtifactResponse
Visitor->>Unity : Display artifact
Unity->>Unity : Load 3D model
Unity->>Unity : Play audio narration
Unity-->>Visitor : Enhanced experience
```

**Diagram sources**
- [main.py:609-632](file://main.py#L609-L632)
- [schemas.py:36-48](file://schemas.py#L36-L48)

Key features include:
- **Flexible QR Code Matching**: Supports both exact and formatted artifact codes
- **3D Content Integration**: Automatic loading of Unity-compatible 3D models
- **Audio Narration**: Synchronized audio descriptions for enhanced storytelling
- **Museum Context**: Rich contextual information linking artifacts to their cultural origins

### Achievement Tracking System

The gamification framework provides progressive engagement through achievement milestones:

```mermaid
flowchart TD
START([User Interaction]) --> SCAN{Artifact Scanned?}
SCAN --> |Yes| CHECK[Check Achievement Requirements]
SCAN --> |No| CONTINUE[Continue Exploring]
CHECK --> GLOBAL[Global Achievements]
CHECK --> MUSEUM[Museum-Specific Achievements]
GLOBAL --> COUNT{Scan Count >= Requirement?}
MUSEUM --> MUSEUM_COUNT{Museum Scan Count >= Requirement?}
COUNT --> |Yes| GRANT_GLOBAL[Grant Global Achievement]
MUSEUM_COUNT --> |Yes| GRANT_MUSEUM[Grant Museum Achievement]
COUNT --> |No| CONTINUE
MUSEUM_COUNT --> |No| CONTINUE
GRANT_GLOBAL --> UPDATE_DB[Update User Achievements]
GRANT_MUSEUM --> UPDATE_DB
UPDATE_DB --> POINTS[Add Points to User]
POINTS --> DISPLAY[Display Achievement Notification]
DISPLAY --> CONTINUE
CONTINUE --> END([Experience Complete])
```

**Diagram sources**
- [main.py:738-800](file://main.py#L738-L800)
- [models.py:86-105](file://models.py#L86-L105)

Achievement categories include:
- **Progressive Milestones**: Scan counts across all artifacts
- **Museum Exploration**: Site-specific discovery challenges
- **Collection Completion**: Artifact acquisition targets
- **Community Recognition**: Multi-user achievement badges

### AI Assistant Integration

The integrated AI assistant provides intelligent museum guidance and information services:

```mermaid
sequenceDiagram
participant User as "Visitor"
participant Chat as "Chat Interface"
participant Agent as "AI Agent"
participant Tools as "Database Tools"
participant DB as "MySQL Database"
User->>Chat : Ask museum question
Chat->>Agent : Forward query
Agent->>Tools : Select appropriate tool
Tools->>DB : Query relevant data
DB-->>Tools : Return results
Tools-->>Agent : Structured information
Agent-->>Chat : Formatted response
Chat-->>User : Natural language answer
Note over Agent,DB : Tools include artifact search, museum info, exhibitions, routes
```

**Diagram sources**
- [agent.py:17-105](file://agent.py#L17-L105)

The AI system utilizes specialized tools for different information domains:
- **Artifact Information Retrieval**: Detailed artifact descriptions and historical context
- **Museum Operations**: Opening hours, pricing, and location details
- **Exhibition Catalog**: Current and upcoming exhibition information
- **Navigation Guidance**: Recommended routes and museum layouts

**Section sources**
- [agent.py:1-122](file://agent.py#L1-L122)
- [main.py:8-9](file://main.py#L8-L9)

### Ticket Management System

The ticketing system handles visitor admission and QR code generation:

```mermaid
flowchart TD
CUSTOMER[Customer Request] --> VALIDATE[Validate Request Data]
VALIDATE --> GENERATE[Generate Unique QR Code]
GENERATE --> CREATE_TICKET[Create Ticket Record]
CREATE_TICKET --> DATABASE[Store in Database]
DATABASE --> RESPONSE[Return Ticket Details]
RESPONSE --> CUSTOMER[Display QR Code]
CUSTOMER --> SCAN[Entrance Scan]
SCAN --> VERIFY[Verify QR Code]
VERIFY --> VALID{Valid Ticket?}
VALID --> |Yes| ACCESS[Grant Access]
VALID --> |No| ERROR[Display Error]
ACCESS --> LOG[Log Entry/Exit]
LOG --> END[Complete Transaction]
```

**Diagram sources**
- [main.py:669-694](file://main.py#L669-L694)

Key ticket features include:
- **Unique QR Code Generation**: Prevents duplication and ensures security
- **Real-time Validation**: Instant verification at museum entrances
- **User Tracking**: Comprehensive visitor analytics and access logs
- **Flexible Pricing**: Support for various ticket types and pricing structures

**Section sources**
- [main.py:669-694](file://main.py#L669-L694)
- [models.py:62-73](file://models.py#L62-L73)

## Dependency Analysis

The backend relies on a carefully selected set of dependencies optimized for performance and functionality:

```mermaid
graph LR
subgraph "Core Framework"
FASTAPI[FastAPI 0.136.0]
SQLALCHEMY[SQLAlchemy 2.0.49]
PYDANTIC[Pydantic 2.13.2]
end
subgraph "Database Layer"
PYMYSQL[PyMySQL 1.1.2]
AIVEN[Aiven Cloud MySQL]
end
subgraph "AI & Language"
LANGCHAIN[LangChain 1.2.15]
GEMINI[Google Gemini 1.73.1]
LANGGRAPH[LangGraph 1.1.8]
end
subgraph "Security & Utilities"
PASSLIB[PassLib 1.7.4]
DOTENV[python-dotenv 1.2.2]
UVICORN[Uvicorn 0.44.0]
end
subgraph "Cloud Deployment"
RENDER[Render Platform]
CORS[CORS Middleware]
end
FASTAPI --> SQLALCHEMY
FASTAPI --> PYDANTIC
SQLALCHEMY --> PYMYSQL
PYMYSQL --> AIVEN
FASTAPI --> LANGCHAIN
LANGCHAIN --> GEMINI
LANGCHAIN --> LANGGRAPH
FASTAPI --> PASSLIB
FASTAPI --> DOTENV
FASTAPI --> UVICORN
RENDER --> FASTAPI
FASTAPI --> CORS
```

**Diagram sources**
- [requirements.txt:12-59](file://requirements.txt#L12-L59)

**Section sources**
- [requirements.txt:1-59](file://requirements.txt#L1-L59)

## Performance Considerations

The MuseAmigo backend is designed with several performance optimization strategies:

### Database Optimization
- **Connection Pooling**: Configured with 10 base connections and 20 overflow capacity
- **Pre-ping Validation**: Ensures connection health before use
- **Automatic Recycling**: Connections refreshed hourly to prevent stale connections
- **Foreign Key Indexing**: Strategic indexing on frequently queried foreign keys

### API Response Optimization
- **Selective Field Loading**: Pydantic schemas limit response payload size
- **Lazy Loading**: Non-critical data loaded only when requested
- **Caching Strategy**: Redis integration planned for frequently accessed data
- **Batch Operations**: Bulk data operations for seeding and maintenance tasks

### AI Service Efficiency
- **Tool-Based Architecture**: Specialized tools reduce unnecessary database queries
- **Query Optimization**: Efficient filtering and search algorithms
- **Response Formatting**: Structured data minimizes parsing overhead

## Troubleshooting Guide

### Common Issues and Solutions

**Database Connection Problems**
- Verify DATABASE_URL environment variable is properly configured
- Check Aiven cloud connectivity and firewall settings
- Monitor connection pool exhaustion during peak usage

**AI Service Failures**
- Confirm GOOGLE_API_KEY is present in environment variables
- Validate Gemini API quota limits and billing status
- Check network connectivity to Google services

**Authentication Issues**
- Verify password hashing implementation is functioning correctly
- Check email uniqueness constraints in user registration
- Review CORS configuration for cross-origin requests

**Performance Degradation**
- Monitor database query execution times
- Check connection pool utilization metrics
- Review AI tool execution latency

**Section sources**
- [database.py:12-24](file://database.py#L12-L24)
- [agent.py:14](file://agent.py#L14)
- [main.py:538-601](file://main.py#L538-L601)

## Conclusion

MuseAmigo represents a comprehensive solution for modern museum experiences, combining traditional cultural preservation with cutting-edge digital innovation. The backend architecture demonstrates strong technical foundations with clear separation of concerns, robust data modeling, and intelligent AI integration.

The platform's strength lies in its holistic approach to museum engagement, where technology serves the enhancement of human cultural experiences rather than overshadowing them. The modular design ensures maintainability and extensibility, while the cloud-native deployment strategy provides scalability and reliability.

Future enhancements could include advanced analytics capabilities, expanded AI functionality, enhanced multimedia content delivery, and integration with augmented reality technologies. The current architecture provides an excellent foundation for these evolutionary improvements while maintaining the core mission of making cultural heritage accessible and engaging for all visitors.