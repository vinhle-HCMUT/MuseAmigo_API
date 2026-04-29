# Artifact Discovery Endpoints

<cite>
**Referenced Files in This Document**
- [main.py](file://main.py)
- [schemas.py](file://schemas.py)
- [models.py](file://models.py)
- [database.py](file://database.py)
- [README.md](file://README.md)
- [generate_audio.py](file://generate_audio.py)
- [agent.py](file://agent.py)
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
This document provides comprehensive API documentation for the artifact discovery endpoints, focusing on the GET `/artifacts/{artifact_code}` endpoint that enables QR code scanning workflows. The endpoint retrieves artifact details with support for case-insensitive matching and flexible space handling for artifact codes. It integrates seamlessly with the Unity frontend's artifact display system and includes audio asset generation capabilities.

The MuseAmigo project is a museum interaction platform built with FastAPI, MySQL, and integrated with Google Gemini AI for contextual assistance. The artifact discovery system serves as the core mechanism for visitors to explore museum collections through QR code interactions.

## Project Structure
The backend follows a modular FastAPI architecture with clear separation of concerns:

```mermaid
graph TB
subgraph "FastAPI Application"
APP[main.py]
SCHEMAS[schemas.py]
MODELS[models.py]
DATABASE[database.py]
end
subgraph "Audio Generation"
AUDIO[generate_audio.py]
end
subgraph "AI Integration"
AGENT[agent.py]
end
subgraph "External Services"
UNITY[Unity Frontend]
GOOGLE[Google Gemini API]
end
APP --> SCHEMAS
APP --> MODELS
APP --> DATABASE
AUDIO --> APP
AGENT --> GOOGLE
APP --> UNITY
AGENT --> APP
```

**Diagram sources**
- [main.py:15-23](file://main.py#L15-L23)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [models.py:1-105](file://models.py#L1-L105)
- [database.py:1-38](file://database.py#L1-L38)

**Section sources**
- [main.py:15-23](file://main.py#L15-L23)
- [schemas.py:1-137](file://schemas.py#L1-L137)
- [models.py:1-105](file://models.py#L1-L105)
- [database.py:1-38](file://database.py#L1-L38)

## Core Components

### ArtifactResponse Schema
The artifact response schema defines the standardized data structure returned by the discovery endpoint:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | integer | Unique identifier for the artifact | Yes |
| artifact_code | string | QR code identifier (case-insensitive) | Yes |
| title | string | Artifact name/title | Yes |
| year | string | Historical period/year | Yes |
| description | string | Detailed artifact description | Yes |
| is_3d_available | boolean | 3D model availability flag | Yes |
| museum_id | integer | Associated museum identifier | Yes |
| unity_prefab_name | string | Unity prefab reference for 3D models | Conditional |
| audio_asset | string | Audio asset path for narration | Optional |

**Section sources**
- [schemas.py:36-48](file://schemas.py#L36-L48)
- [models.py:27-42](file://models.py#L27-L42)

### Database Model Integration
The artifact model maintains a direct relationship with the database schema, supporting both the discovery endpoint and Unity integration:

```mermaid
erDiagram
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
MUSEUMS {
int id PK
string name
string operating_hours
int base_ticket_price
float latitude
float longitude
}
ARTIFACTS ||--|| MUSEUMS : "belongs_to"
```

**Diagram sources**
- [models.py:27-42](file://models.py#L27-L42)
- [models.py:16-26](file://models.py#L16-L26)

**Section sources**
- [models.py:27-42](file://models.py#L27-L42)
- [models.py:16-26](file://models.py#L16-L26)

## Architecture Overview

### Artifact Discovery Workflow
The artifact discovery system implements a robust lookup mechanism supporting multiple input formats:

```mermaid
sequenceDiagram
participant Client as "Unity Client"
participant API as "FastAPI Server"
participant DB as "MySQL Database"
participant Audio as "Audio Generator"
Client->>API : GET /artifacts/{artifact_code}
API->>API : Clean and normalize input
API->>API : Try exact case-insensitive match
API->>DB : Query by artifact_code (UPPER)
DB-->>API : Match found or null
alt Exact match found
API->>DB : Retrieve full artifact record
DB-->>API : Artifact data
API->>Audio : Generate audio asset if needed
Audio-->>API : Audio file path
API-->>Client : ArtifactResponse
else No exact match
API->>API : Try space-normalized match
API->>DB : Query with spaces removed
DB-->>API : Match found or null
alt Space-normalized match found
API->>DB : Retrieve artifact record
DB-->>API : Artifact data
API-->>Client : ArtifactResponse
else No match found
API-->>Client : 404 Not Found
end
end
```

**Diagram sources**
- [main.py:609-632](file://main.py#L609-L632)
- [schemas.py:36-48](file://schemas.py#L36-L48)

### Audio Asset Generation Pipeline
The system includes automated audio asset generation for artifact descriptions:

```mermaid
flowchart TD
Start([Artifact Request]) --> CheckAudio["Check audio_asset field"]
CheckAudio --> HasAudio{"Audio asset exists?"}
HasAudio --> |Yes| ReturnExisting["Return existing audio path"]
HasAudio --> |No| GenerateAudio["Generate new audio file"]
GenerateAudio --> CreateTone["Create sine wave tone"]
CreateTone --> SaveFile["Save WAV file"]
SaveFile --> UpdateDB["Update database record"]
UpdateDB --> ReturnNew["Return new audio path"]
ReturnExisting --> End([Response])
ReturnNew --> End
```

**Diagram sources**
- [generate_audio.py:12-38](file://generate_audio.py#L12-L38)
- [generate_audio.py:41-77](file://generate_audio.py#L41-L77)

**Section sources**
- [main.py:609-632](file://main.py#L609-L632)
- [generate_audio.py:12-38](file://generate_audio.py#L12-L38)

## Detailed Component Analysis

### GET /artifacts/{artifact_code} Endpoint

#### Implementation Details
The artifact discovery endpoint implements sophisticated matching logic to handle various QR code input formats:

```mermaid
flowchart TD
Input[artifact_code Parameter] --> Clean["Trim whitespace<br/>Convert to uppercase"]
Clean --> ExactMatch["Exact case-insensitive match"]
ExactMatch --> ExactFound{"Exact match found?"}
ExactFound --> |Yes| ReturnArtifact["Return artifact data"]
ExactFound --> |No| RemoveSpaces["Remove all spaces from input"]
RemoveSpaces --> SpaceMatch["Space-normalized match"]
SpaceMatch --> SpaceFound{"Space-normalized match found?"}
SpaceFound --> |Yes| ReturnArtifact
SpaceFound --> |No| NotFound["Raise 404 error"]
ReturnArtifact --> End([Success Response])
NotFound --> End
```

**Diagram sources**
- [main.py:611-632](file://main.py#L611-L632)

#### Response Schema Validation
The endpoint validates responses against the ArtifactResponse schema, ensuring consistent data delivery to Unity clients:

| Property | Validation | Purpose |
|----------|------------|---------|
| artifact_code | Case-insensitive match | QR code identification |
| title | String validation | Display name |
| year | String validation | Historical context |
| description | String validation | Detailed information |
| is_3d_available | Boolean validation | 3D model availability |
| unity_prefab_name | String validation | Unity prefab reference |
| audio_asset | String validation | Audio narration path |

**Section sources**
- [main.py:609-632](file://main.py#L609-L632)
- [schemas.py:36-48](file://schemas.py#L36-L48)

### Unity Frontend Integration

#### 3D Model Integration Patterns
The Unity frontend receives structured data enabling seamless 3D model loading:

```mermaid
classDiagram
class ArtifactResponse {
+int id
+string artifact_code
+string title
+string year
+string description
+bool is_3d_available
+int museum_id
+string unity_prefab_name
+string audio_asset
}
class UnityPrefabLoader {
+LoadPrefab(prefabName) GameObject
+Setup3DModel(modelData) void
+HandleDisplayMode() void
}
class AudioAssetManager {
+LoadAudio(assetPath) AudioClip
+PlayNarration() void
+StopNarration() void
}
ArtifactResponse --> UnityPrefabLoader : "provides data for"
ArtifactResponse --> AudioAssetManager : "provides audio path for"
UnityPrefabLoader --> AudioAssetManager : "coordinates with"
```

**Diagram sources**
- [schemas.py:36-48](file://schemas.py#L36-L48)
- [models.py:37-40](file://models.py#L37-L40)

#### Audio Asset Generation
The system generates placeholder audio files for artifact descriptions:

| Audio File | Frequency | Duration | Purpose |
|------------|-----------|----------|---------|
| artifact_001.wav | 330 Hz (E note) | 3 seconds | Historical narration |
| artifact_002.wav | 494 Hz (B note) | 3 seconds | Museum guide voice |

**Section sources**
- [generate_audio.py:41-77](file://generate_audio.py#L41-L77)
- [models.py:39-40](file://models.py#L39-L40)

### Error Handling and Validation

#### Error Scenarios
The system implements comprehensive error handling for artifact lookup failures:

```mermaid
flowchart TD
Request[Artifact Lookup Request] --> Validate["Validate input format"]
Validate --> ValidInput{"Valid input?"}
ValidInput --> |No| InvalidFormat["Return 400 Bad Request"]
ValidInput --> |Yes| SearchDB["Search database"]
SearchDB --> Found{"Artifact found?"}
Found --> |Yes| Success["Return ArtifactResponse"]
Found --> |No| NotFound["Return 404 Not Found"]
Success --> End([Response])
NotFound --> End
InvalidFormat --> End
```

**Diagram sources**
- [main.py:626-630](file://main.py#L626-L630)

#### Practical Examples

##### QR Code Scanning Workflow
1. **Visitor scans QR code** at museum exhibit
2. **Unity client sends request** to `/artifacts/{artifact_code}`
3. **Server processes input** with case-insensitive matching
4. **Database query executes** with normalized artifact code
5. **Response returned** with complete artifact details
6. **Unity displays 3D model** if available
7. **Audio narration plays** for enhanced experience

##### Artifact Data Structure Examples
**Complete Artifact Record:**
```json
{
  "id": 1,
  "artifact_code": "IP-001",
  "title": "Presidential Desk",
  "year": "1960s",
  "description": "The original presidential desk used by President Nguyễn Văn Thiệu...",
  "is_3d_available": true,
  "museum_id": 1,
  "unity_prefab_name": "Model_Presidential_Desk",
  "audio_asset": "assets/audio/artifact_001.wav"
}
```

**Minimal Artifact Record:**
```json
{
  "id": 2,
  "artifact_code": "WRM-001",
  "title": "Guillotine",
  "year": "Early 1900s",
  "description": "A guillotine used during the French colonial period...",
  "is_3d_available": false,
  "museum_id": 2,
  "unity_prefab_name": "Model_Guillotine",
  "audio_asset": ""
}
```

**Section sources**
- [main.py:75-170](file://main.py#L75-L170)
- [schemas.py:36-48](file://schemas.py#L36-L48)

## Dependency Analysis

### Component Dependencies
The artifact discovery system relies on several interconnected components:

```mermaid
graph LR
subgraph "Core Dependencies"
FASTAPI[FastAPI Framework]
SQLALCHEMY[SQLAlchemy ORM]
PYDANTIC[Pydantic Validation]
end
subgraph "Application Layer"
MAIN[main.py]
SCHEMAS[schemas.py]
MODELS[models.py]
end
subgraph "Infrastructure"
DATABASE[database.py]
AUDIO[generate_audio.py]
AGENT[agent.py]
end
subgraph "External Integration"
UNITY[Unity Frontend]
GOOGLE[Google Gemini API]
end
FASTAPI --> MAIN
SQLALCHEMY --> MODELS
PYDANTIC --> SCHEMAS
MAIN --> SCHEMAS
MAIN --> MODELS
MAIN --> DATABASE
AUDIO --> MAIN
AGENT --> GOOGLE
MAIN --> UNITY
AGENT --> MAIN
```

**Diagram sources**
- [main.py:1-10](file://main.py#L1-L10)
- [schemas.py:1-17](file://schemas.py#L1-L17)
- [models.py:1-2](file://models.py#L1-L2)
- [database.py:1-38](file://database.py#L1-L38)

### Database Relationship Management
The system maintains referential integrity through foreign key relationships:

```mermaid
erDiagram
USERS {
int id PK
string full_name
string email UK
string hashed_password
}
ARTIFACTS {
int id PK
string artifact_code UK
int museum_id FK
}
COLLECTIONS {
int id PK
int user_id FK
int artifact_id FK
}
USERS ||--o{ COLLECTIONS : "owns"
ARTIFACTS ||--o{ COLLECTIONS : "collected_by"
```

**Diagram sources**
- [models.py:4-15](file://models.py#L4-L15)
- [models.py:43-51](file://models.py#L43-L51)

**Section sources**
- [models.py:4-15](file://models.py#L4-L15)
- [models.py:43-51](file://models.py#L43-L51)

## Performance Considerations

### Database Optimization
The artifact lookup implements efficient indexing strategies:

- **artifact_code**: Unique index for O(log n) lookups
- **artifact_code_upper**: Case-insensitive comparison using UPPER function
- **space-normalized**: Handles QR codes with embedded spaces

### Connection Pool Management
The database connection pool configuration ensures optimal performance:

| Parameter | Value | Purpose |
|-----------|--------|---------|
| pool_size | 10 | Concurrent connections |
| max_overflow | 20 | Additional connections when pool is full |
| pool_pre_ping | True | Validate connections before use |
| pool_recycle | 3600 | Recycle connections hourly |

### Caching Strategies
Consider implementing Redis caching for frequently accessed artifacts to reduce database load and improve response times for popular museum items.

## Troubleshooting Guide

### Common Issues and Solutions

#### 404 Not Found Errors
**Symptoms:** Artifact code not found despite correct input
**Causes:**
- Incorrect artifact code format
- Case sensitivity issues
- Spaces in QR code not handled
- Database synchronization delays

**Solutions:**
1. Verify artifact code format matches database entries
2. Ensure case-insensitive matching is working
3. Check for space-normalization functionality
4. Confirm database seeding completed successfully

#### Audio Asset Generation Failures
**Symptoms:** Missing audio assets or generation errors
**Causes:**
- File path permissions
- Directory creation failures
- Audio file corruption

**Solutions:**
1. Verify audio asset directory exists and is writable
2. Check file permissions for audio generation
3. Validate audio file integrity
4. Review generate_audio.py error handling

#### Unity Integration Issues
**Symptoms:** 3D models not displaying or audio not playing
**Causes:**
- Incorrect prefab names
- Missing audio asset paths
- Network connectivity issues
- CORS configuration problems

**Solutions:**
1. Validate unity_prefab_name matches Unity asset names
2. Check audio_asset paths are accessible
3. Verify network connectivity to API endpoints
4. Configure CORS middleware appropriately

**Section sources**
- [main.py:626-630](file://main.py#L626-L630)
- [generate_audio.py:40-77](file://generate_audio.py#L40-L77)
- [database.py:17-24](file://database.py#L17-L24)

## Conclusion

The artifact discovery endpoint provides a robust foundation for museum interaction through QR code scanning. Its sophisticated matching logic accommodates various QR code formats while maintaining data consistency through Pydantic validation. The integration with Unity enables immersive 3D experiences with synchronized audio narration.

Key strengths of the implementation include:
- Flexible artifact code matching (case-insensitive, space-handling)
- Comprehensive response schema validation
- Automated audio asset generation
- Seamless Unity frontend integration
- Scalable database design with proper indexing

Future enhancements could include caching mechanisms for improved performance, enhanced error logging for debugging, and expanded AI integration for contextual artifact information.