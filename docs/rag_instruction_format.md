# RAG Instruction Format

This document details the precise format for embedding structured instructions within RAG (Retrieval Augmented Generation) chunk text. These instructions allow the system to automatically parse and act upon data definitions found in the chunks.

## General Structure

Each instruction block must be enclosed by specific delimiters:

```
%%% BEGIN_INSTRUCTION %%%
TYPE: <INSTRUCTION_TYPE>
KEY_1: VALUE_1
KEY_2: VALUE_2
...
DATA_JSON: { ... valid JSON object ... }
%%% END_INSTRUCTION %%%
```

**Key Points:**
- Delimiters: `%%% BEGIN_INSTRUCTION %%%` and `%%% END_INSTRUCTION %%%` mark the start and end of an instruction block.
- Key-Value Pairs: Inside the block, instructions are defined as key-value pairs, separated by a colon (`:`).
    - Keys are case-insensitive during parsing (e.g., `TYPE`, `type`, `Type` are treated the same) and are normalized to uppercase internally.
    - Values are taken as strings, with leading/trailing whitespace stripped.
- `TYPE`: This is a mandatory key that defines the action to be performed (e.g., `CREATE_ENTITY`, `CREATE_LEVEL_TEMPLATE`). If `TYPE` is missing, the instruction block is skipped.
- `DATA_JSON`: This is a special key. Its value **must** be a valid JSON object string. This JSON object contains the detailed data for the instruction. The structure of this JSON object depends on the `TYPE`. If `DATA_JSON` is present but contains malformed JSON, a parsing error will occur for that instruction.

## Supported Instruction Types and `DATA_JSON` Structures

### 1. `TYPE: CREATE_ENTITY`

Creates a new entity definition in the `entity_definitions` table.

**Required Keys in `DATA_JSON`**:
- `name` (String): The unique name of the entity. Must be a non-empty string.
- `type` (String): The category or type of the entity (e.g., "monster", "item", "npc"). Must be a non-empty string.
- `default_properties` (JSON Object): A JSON object defining the base attributes, stats, or other properties of the entity. The structure of this object is flexible but it must be a valid JSON object (e.g., `{}`).

**Optional Keys in `DATA_JSON`**:
- `description` (String): A textual description of the entity.

**Example:**
```
%%% BEGIN_INSTRUCTION %%%
TYPE: CREATE_ENTITY
DATA_JSON: {
    "name": "Shadow Wraith",
    "type": "monster",
    "default_properties": {
        "hp": 20,
        "atk": 5,
        "speed": 2,
        "immunities": ["cold", "necrotic"],
        "abilities": ["invisibility", "drain_life"]
    },
    "description": "A spectral entity that phases through walls and drains life force."
}
%%% END_INSTRUCTION %%%
```

### 2. `TYPE: CREATE_LEVEL_TEMPLATE`

Creates a new level template in the `level_templates` table.

**Required Keys in `DATA_JSON`**:
- `name` (String): The unique name of the level template. Must be a non-empty string.
- `structure` (JSON Object): A JSON object defining the layout, size, tile map, or other structural aspects of the level. The content is flexible but it must be a valid JSON object (e.g., `{}`).

**Optional Keys in `DATA_JSON`**:
- `description` (String): A textual description of the level template.
- `default_entities` (JSON Object): A JSON object that might define default entities, spawn points, or other gameplay elements for this template. Must be a valid JSON object if provided.

**Example:**
```
%%% BEGIN_INSTRUCTION %%%
TYPE: CREATE_LEVEL_TEMPLATE
DATA_JSON: {
    "name": "Ancient Crypt - Floor 1",
    "description": "The dusty first floor of an ancient burial site, filled with traps and undead.",
    "structure": {
        "size": "15x15",
        "layout_type": "corridors_and_rooms",
        "tile_set": "crypt_tiles",
        "features": ["sarcophagi", "hidden_passages", "pressure_plates"]
    },
    "default_entities": {
        "monsters": [
            {"type_name": "Skeleton Warrior", "count_range": [3, 6]},
            {"type_name": "Zombie", "count_range": [5, 10]}
        ],
        "traps": ["spike_trap", "arrow_slit"]
    }
}
%%% END_INSTRUCTION %%%
```

*(More instruction types can be added here as the system evolves.)*
```

## Parsing Notes
- The parser (`src/rag_parser.py`) processes the content between the delimiters.
- It splits content by lines and then each line by the first colon to get key-value pairs.
- If `DATA_JSON` is present, its entire string value is passed to a JSON loader. Ensure the JSON content is properly escaped if necessary within the RAG chunk, though typically it's a direct JSON string.
- If an instruction block does not have a `TYPE` key, it will be skipped.
- If `DATA_JSON` is present but its content is not valid JSON, a `RAGInstructionError` will be raised during parsing for that instruction block, and it will not be processed further by the executor.
- Other key-value pairs are stored as simple strings.
