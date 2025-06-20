# Phase 1 Design: Dockerized Web UI for RAG-Guided PostgreSQL State Management

## 1. Introduction

This document outlines the initial design decisions (Phase 1) for the project aimed at creating a Dockerized web application. This application will serve as a User Interface (UI) for managing data within a PostgreSQL database. A key feature is the planned integration of a Retrieval Augmented Generation (RAG) system to guide and potentially automate database state modifications based on natural language instructions embedded within retrieved text chunks.

This document covers:
- The PostgreSQL Docker setup.
- The initial database schema design.
- The strategy for interpreting "RAG-Guided Instructions".
- The recommended technology stack for the web UI and backend.

## 2. PostgreSQL Docker Setup Plan

The PostgreSQL database will be containerized using Docker for consistent development and deployment environments.

### 2.1. `docker/postgres/Dockerfile`

The Dockerfile for the PostgreSQL service will use an official base image and allow for custom initialization scripts.

```dockerfile
# Use the official postgres:15-alpine image as the base
FROM postgres:15-alpine

# Allow for a custom initialization script
COPY ./initdb.d/*.sh /docker-entrypoint-initdb.d/
COPY ./initdb.d/*.sql /docker-entrypoint-initdb.d/
```
An empty placeholder file `docker/postgres/initdb.d/init.sh` will be created to ensure the directory and copy instruction in the Dockerfile work:
```bash
#!/bin/sh
# This is an empty placeholder file for custom initialization scripts.
# You can add your .sh or .sql files in this directory (initdb.d)
# and they will be executed when the PostgreSQL container starts for the first time.
echo "Running custom initialization script..."
```

### 2.2. `docker-compose.yml`

The `docker-compose.yml` file at the root of the project will define the services, networks, and volumes.

```yaml
version: '3.8'

services:
  postgres:
    build: ./docker/postgres
    environment:
      POSTGRES_USER: user        # Placeholder - change in .env or secrets
      POSTGRES_PASSWORD: password  # Placeholder - change in .env or secrets
      POSTGRES_DB: appdb         # Placeholder - change in .env or secrets
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: ./src  # Assuming a Dockerfile will be in src for the web app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/appdb # Placeholder
      # Other necessary environment variables for the web app

volumes:
  postgres_data:
```

## 3. Database Schema Design

The following SQL `CREATE TABLE` statements define the initial schema for the core tables.

```sql
CREATE TABLE rag_chunks (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL, -- Identifier for the source document
    chunk_index INTEGER NOT NULL, -- Order of the chunk within the document
    text_content TEXT NOT NULL, -- The actual text content of the chunk
    embedding VECTOR(1536), -- Assuming OpenAI's text-embedding-ada-002, adjust size as needed
    metadata JSONB, -- Store other relevant information like source URL, document title, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, chunk_index)
);

COMMENT ON COLUMN rag_chunks.metadata IS 'Stores other relevant information like source URL, document title, page number, etc.';

CREATE TABLE level_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL, -- Unique name for the level template (e.g., "Desert Oasis Puzzle")
    description TEXT, -- A brief description of the level template
    structure JSONB NOT NULL, -- Defines the static layout, objects, and initial conditions of the level
    scripting_api_version VARCHAR(50) DEFAULT '1.0', -- Version of the scripting API this template uses
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN level_templates.structure IS 'Defines static layout, objects, initial interactable states, win/loss conditions, entry/exit points etc. Example: {"layout": [[1,1,0],[1,0,1]], "objects": [{"id": "key", "position": [1,2]}]}';

CREATE TABLE entity_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL, -- Unique name for the entity type (e.g., "Player", "Goblin", "HealthPotion")
    type VARCHAR(100) NOT NULL, -- Broad category like "NPC", "Item", "EnvironmentElement"
    default_properties JSONB, -- Default attributes and behaviors (e.g., health, damage, sprite, interaction scripts)
    scripting_api_version VARCHAR(50) DEFAULT '1.0', -- Version of the scripting API this entity uses
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN entity_definitions.default_properties IS 'Default attributes like health, damage, speed, inventory capacity, visual representation, interaction scripts, AI behavior tree references, etc. Example: {"health": 100, "sprite": "goblin.png", "can_attack": true}';

CREATE TABLE game_instances (
    id SERIAL PRIMARY KEY,
    level_template_id INTEGER NOT NULL REFERENCES level_templates(id),
    player_id VARCHAR(255), -- Could be a foreign key to a users table if players are registered
    session_id VARCHAR(255) UNIQUE NOT NULL, -- Unique identifier for a game session
    current_state JSONB NOT NULL, -- Stores the dynamic state of all entities and the environment in the game instance
    game_status VARCHAR(50) DEFAULT 'pending', -- e.g., pending, active, completed_success, completed_failure, paused
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON COLUMN game_instances.current_state IS 'Stores the dynamic state of all entities (positions, health, inventory) and the environment (e.g., opened doors, triggered traps) within this specific game. This is a snapshot that can be used to load/save games. Example: {"player_pos": [2,3], "entities": [{"id": "goblin1", "health": 50, "pos": [5,5]}]}';
COMMENT ON COLUMN game_instances.game_status IS 'Possible values: pending, active, completed_success, completed_failure, paused, aborted';

-- Optional: Indexes for frequently queried columns
CREATE INDEX idx_rag_chunks_embedding ON rag_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100); -- Example for pgvector
CREATE INDEX idx_game_instances_player_id ON game_instances(player_id);
CREATE INDEX idx_game_instances_status ON game_instances(game_status);
```

### Design Choices Explanation:

*   **`rag_chunks` Table:** Designed for storing text fragments and their vector embeddings for similarity search in RAG. `metadata` (JSONB) offers flexibility for storing diverse source information.
*   **`level_templates` Table:** `structure` (JSONB) is key for defining varied and complex level layouts, initial object placements, and conditions without a rigid schema.
*   **`entity_definitions` Table:** `default_properties` (JSONB) allows for defining a wide array of attributes (stats, visuals, behaviors) for different entity types.
*   **`game_instances` Table:** `current_state` (JSONB) captures the dynamic state of a game session, enabling features like save/load. JSONB provides flexibility for complex game states.
*   **General JSONB Usage:** Chosen for its ability to handle semi-structured and evolving data common in game development, reducing the need for frequent schema migrations and offering efficient querying with proper indexing.

## 4. "RAG-Guided Instructions" Interpretation Strategy

This strategy allows embedding actionable instructions within RAG chunk text, enabling the system to react to retrieved information.

### 4.1. Structured Format for Embedded Instructions

Instructions are delimited and use a key-value format, with an option for a JSON payload.

```text
%%% BEGIN_INSTRUCTION %%%
TYPE: <InstructionType>
PARAM_NAME_1: <Value1>
PARAM_NAME_2: <Value2>
DATA_JSON: <JSON_Payload_if_needed>
%%% END_INSTRUCTION %%%
```

**Example:**

```text
The ancient scroll describes a hidden chamber. To reveal it, the prophecy states:
"When the twin orbs are placed upon the pedestals of dawn, the way shall open."
It also mentions a guardian that can be pacified with a specific lullaby.

%%% BEGIN_INSTRUCTION %%%
TYPE: CREATE_ENTITY
NAME: Guardian Golem
TEMPLATE_ID: entity_golem_01
POSITION_X: 15
POSITION_Y: 22
ZONE_ID: hidden_chamber_A
HEALTH_MULTIPLIER: 1.2
DATA_JSON: {
  "loot_table": "golem_rare_gems",
  "abilities": ["stone_smash", "self_repair"],
  "on_defeat_trigger": "EVENT_OPEN_SECRET_DOOR_B"
}
%%% END_INSTRUCTION %%%

Further writings on the scroll detail the lullaby's notes...
```

### 4.2. Python Backend Parsing Logic Outline

1.  **Identify Instruction Blocks:** Scan retrieved text for `%%% BEGIN_INSTRUCTION %%%` and `%%% END_INSTRUCTION %%%` delimiters (e.g., using regex `re.compile(r"%%% BEGIN_INSTRUCTION %%%(.*?)%%% END_INSTRUCTION %%%", re.DOTALL)`).
2.  **Parse Key-Value Pairs:** Split the block content by lines. For each line, split by the first `':'` to get key and value. Store in a dictionary.
3.  **Handle Complex Data (JSON):** If a key is `DATA_JSON` (or similar), parse its string value using `json.loads()`.
4.  **Determine Action via `TYPE`:** Use the value of the `TYPE` field to dispatch the parsed instruction to the appropriate handler function or logic (e.g., `CREATE_ENTITY` handler would use other parameters like `NAME`, `TEMPLATE_ID` to interact with the database).
5.  **Error Handling:** Implement robust error handling for malformed blocks, missing `TYPE`, invalid JSON, etc.

## 5. Technology Stack for Web UI & Backend

### 5.1. Python Web Framework

*   **Recommendation:** **FastAPI**
*   **Justification:**
    *   **Performance & Async Support:** High performance and native `async/await` for I/O-bound tasks like DB queries.
    *   **Ease of Development:** Modern Python features, type hints for data validation (Pydantic).
    *   **Automatic API Docs:** Built-in Swagger UI/ReDoc for API testing and documentation.
    *   **Data Validation:** Pydantic integration for robust request/response validation.
    *   **Dependency Injection:** Simplifies managing dependencies like database sessions.

### 5.2. Database ORM/Connector

*   **Recommendation:** **SQLAlchemy 2.x (Core and ORM) with `asyncpg`**
*   **Justification:**
    *   **Powerful ORM & SQL Expression Language:** Offers both high-level ORM and fine-grained SQL control via Core.
    *   **Asynchronous Support:** `asyncpg` driver for non-blocking database operations, fitting FastAPI's async model.
    *   **Schema Management:** Integrates well with Alembic for database migrations.
    *   **Flexibility & Compatibility:** Mature, well-tested, and excellent PostgreSQL support.

### 5.3. Frontend (HTML/CSS/JS)

*   **Initial Approach:** **Server-Rendered HTML with Jinja2 Templating.**
    *   Style with a CSS framework (e.g., Tailwind CSS or Bootstrap) for rapid UI development.
    *   FastAPI integrates well with Jinja2.
    *   Suitable for data management UIs (forms, tables).
*   **Progressive Enhancement with JavaScript:**
    *   Use Vanilla JS or lightweight libraries (e.g., Alpine.js, HTMX) for client-side validation, dynamic content updates (AJAX), and richer UI components where needed.
    *   Avoids the initial complexity of a full SPA framework.

This stack provides a modern, performant, and developer-friendly foundation for the project.
