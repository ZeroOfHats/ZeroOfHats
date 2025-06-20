CREATE TABLE rag_chunks (
    id SERIAL PRIMARY KEY,
    chunk_content TEXT NOT NULL,
    source_file TEXT,
    chunk_index INTEGER,
    metadata JSONB,
    embedding NUMERIC[] -- Using NUMERIC[] as a placeholder for VECTOR
);

CREATE TABLE level_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    structure JSONB NOT NULL, -- e.g., { "size": "10x10", "tile_map": [...], "entry_points": [...] }
    default_entities JSONB -- e.g., { "monsters": [{"type_id": 1, "count": 5}], "items": [...] }
);

CREATE TABLE entity_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL, -- e.g., 'monster', 'item', 'player_character', 'trap'
    default_properties JSONB NOT NULL, -- e.g., { "stats": {"hp": 10, "atk": 3}, "sprite": "goblin.png", "abilities": [] }
    description TEXT
);

CREATE TABLE game_instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    level_template_id INTEGER REFERENCES level_templates(id) ON DELETE SET NULL,
    current_state JSONB NOT NULL, -- e.g., { "player_location": {"x":1, "y":2}, "active_entities": [...], "discovered_areas": [] }
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
