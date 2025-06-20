# Web UI User Guide

Welcome to the RAG-Guided PostgreSQL State Management Web UI. This guide explains how to use the interface to manage RAG chunks and game state data.

## Table of Contents
- [Accessing the Application](#accessing-the-application)
- [Navigation](#navigation)
- [Managing RAG Chunks](#managing-rag-chunks)
    - [Viewing RAG Chunks](#viewing-rag-chunks)
    - [Adding a New RAG Chunk](#adding-a-new-rag-chunk)
    - [Editing a RAG Chunk](#editing-a-rag-chunk)
    - [Deleting a RAG Chunk](#deleting-a-rag-chunk)
- [Managing Game State](#managing-game-state)
    - [Game Instances](#game-instances)
        - [Viewing Game Instances](#viewing-game-instances)
        - [Adding a New Game Instance](#adding-a-new-game-instance)
        - [Editing a Game Instance](#editing-a-game-instance)
        - [Deleting a Game Instance](#deleting-a-game-instance)
    - [Entity Definitions](#entity-definitions)
        - [Viewing Entity Definitions](#viewing-entity-definitions)
    - [Level Templates](#level-templates)
        - [Viewing Level Templates](#viewing-level-templates)
- [RAG-Guided Instructions](#rag-guided-instructions)
    - [Overview](#overview)
    - [Formatting Instructions](#formatting-instructions)
    - [Processing Instructions](#processing-instructions)
    - [Example Workflow](#example-workflow)
    - [Troubleshooting Processing](#troubleshooting-processing)

## Accessing the Application
Once the application is running (see `README.md` for setup instructions), the Web UI is accessible at [http://localhost:8000](http://localhost:8000).

## Navigation
The main navigation bar at the top of the page provides links to different sections:
- **Home**: The main landing page, showing counts of various data types.
- **Add RAG Chunk**: Form to create a new RAG chunk.
- **View RAG Chunks**: Lists all stored RAG chunks.
- **Add Game Instance**: Form to create a new game instance.
- **View Game Instances**: Lists all stored game instances.
- **View Entity Definitions**: Lists all entity definitions (primarily created via RAG instructions).
- **View Level Templates**: Lists all level templates (primarily created via RAG instructions). (Assuming a view page for level templates will be added if not already present)

## Managing RAG Chunks

### Viewing RAG Chunks
Navigate to "View RAG Chunks". This page displays a table of all RAG chunks with their ID, a snippet of their content, source file, index, metadata, and available actions.

### Adding a New RAG Chunk
1.  Navigate to "Add RAG Chunk".
2.  Fill in the form:
    - **Chunk Content** (Required): The raw text content of the RAG chunk. This is where you can embed RAG Instructions.
    - **Source File** (Optional): The original file name or source identifier.
    - **Chunk Index** (Optional): The numerical index of the chunk within its source.
    - **Metadata (JSON format, optional)**: Any additional structured data about the chunk, entered as a valid JSON string (e.g., `{"author": "Jules", "category": "lore"}`).
3.  Click "Add Chunk". You will be redirected to the RAG Chunks list.

### Editing a RAG Chunk
1.  On the "View RAG Chunks" page, find the chunk you wish to edit.
2.  Click the "Edit" button in the "Actions" column for that chunk.
3.  The edit form will appear, pre-filled with the chunk's current data.
4.  Modify the fields as needed. If editing metadata, ensure it remains valid JSON.
5.  Click "Save Changes".

### Deleting a RAG Chunk
1.  On the "View RAG Chunks" page, find the chunk you wish to delete.
2.  Click the "Delete" button in the "Actions" column.
3.  A confirmation dialog will appear. Click "OK" to confirm deletion.

## Managing Game State

### Game Instances

#### Viewing Game Instances
Navigate to "View Game Instances". This page displays a table of game instances, including their ID, name, linked Level Template ID (if any), a pretty-printed version of their `current_state` JSONB data, and creation/update timestamps.

#### Adding a New Game Instance
1.  Navigate to "Add Game Instance".
2.  Fill in the form:
    - **Instance Name** (Required): A descriptive name for this game instance.
    - **Current State (JSON format)** (Required): The full JSONB data representing the game state (e.g., `{"player_location": {"x":1, "y":2}, "inventory": []}`). Must be valid JSON.
    - **Level Template ID** (Optional): If this game instance is based on a `LevelTemplate`, enter its ID here.
3.  Click "Add Game Instance". If the JSON is invalid, the form will be redisplayed with an error message.

#### Editing a Game Instance
1.  On the "View Game Instances" page, click "Edit" for the desired instance.
2.  Modify the name, current state JSON, or Level Template ID.
3.  If the "Current State" JSON is invalid, an error will be shown on the form when you try to save. Correct it and resubmit.
4.  Click "Save Changes".

#### Deleting a Game Instance
1.  On the "View Game Instances" page, click "Delete" for the desired instance.
2.  Confirm the deletion when prompted.

### Entity Definitions

#### Viewing Entity Definitions
Navigate to "View Entity Definitions". This page lists all entity definitions created in the system, primarily through the RAG-Guided Instructions feature. It shows their ID, name, type, and a pretty-printed version of their `default_properties` JSONB. Currently, Entity Definitions are added via RAG Instruction processing.

### Level Templates

#### Viewing Level Templates
(Assuming a "View Level Templates" page exists or will be added, similar to "View Entity Definitions". Navigation link should also exist.)
This page would list all level templates created, primarily through RAG-Guided Instructions. It would show ID, name, description, and pretty-printed `structure` and `default_entities` JSONB.

## RAG-Guided Instructions

### Overview
This powerful feature allows the system to automatically create game data (like Entity Definitions and Level Templates) by parsing specially formatted instructions embedded within the text of your RAG Chunks.

### Formatting Instructions
Instructions must follow a specific format to be recognized and processed correctly. For complete details, syntax rules, and examples of supported instruction types (`CREATE_ENTITY`, `CREATE_LEVEL_TEMPLATE`), please refer to the separate **[RAG Instruction Format Document](rag_instruction_format.md)**.

A brief example for creating an entity:
```
%%% BEGIN_INSTRUCTION %%%
TYPE: CREATE_ENTITY
DATA_JSON: {
    "name": "Goblin Archer",
    "type": "monster",
    "default_properties": {"hp": 8, "atk": 4, "weapon": "shortbow"}
}
%%% END_INSTRUCTION %%%
```

### Processing Instructions
1.  **Embed Instructions**: Write or ensure your RAG chunk text contains one or more instruction blocks, correctly formatted as per the [RAG Instruction Format Document](rag_instruction_format.md).
2.  **Add/Edit RAG Chunk**: Use the UI to "Add" this new RAG chunk or "Edit" an existing one to include these instructions in its "Chunk Content" field.
3.  **Trigger Processing**:
    - Navigate to "View RAG Chunks".
    - Locate the RAG chunk containing the instructions.
    - Click the "Process Instructions" button in the "Actions" column for that chunk.
4.  **Review Results**:
    - You will be taken to a "RAG Instruction Processing Results" page.
    - This page displays a log detailing the outcome of each attempted instruction. Success messages will indicate created data (e.g., "Success: Created EntityDefinition 'Goblin Archer' (ID: 42)."). Error messages will indicate issues with parsing or execution.

### Example Workflow
1.  **Prepare RAG Chunk Content**: Create text that includes a definition for a new game monster, formatted as a `CREATE_ENTITY` instruction. For example:
    ```text
    The ancient texts describe a fearsome beast known as the "Gorgon".
    It is said to have a petrifying gaze and tough, stony hide.

    %%% BEGIN_INSTRUCTION %%%
    TYPE: CREATE_ENTITY
    DATA_JSON: {
        "name": "Gorgon",
        "type": "beast",
        "default_properties": {
            "hp": 75,
            "armor_class": 15,
            "abilities": ["petrifying_gaze", "stone_hide"]
        },
        "description": "A monstrous beast with a gaze that turns flesh to stone."
    }
    %%% END_INSTRUCTION %%%

    Only the bravest heroes should attempt to face it.
    ```
2.  **Add RAG Chunk**: Go to "Add RAG Chunk", paste the content above into the "Chunk Content" field, and save.
3.  **Process**: Find the new chunk in the "View RAG Chunks" list and click "Process Instructions".
4.  **Verify**:
    - Check the "Processing Results" page for a success message related to "Gorgon".
    - Navigate to "View Entity Definitions". You should see "Gorgon" listed as a new entity.

### Troubleshooting Processing
- **"No valid RAG instructions parsed..."**:
    - Ensure your instruction blocks start with `%%% BEGIN_INSTRUCTION %%%` and end with `%%% END_INSTRUCTION %%%`.
    - Check that each instruction has a `TYPE:` line.
    - Verify that there's content between the begin and end markers.
- **"Parser Error: Malformed JSON..."**:
    - The content provided for a `DATA_JSON:` field is not valid JSON. Carefully check for missing commas, unquoted keys/strings, or mismatched brackets/braces. Use a JSON validator tool if needed.
- **"Error: Missing required fields..."**:
    - The `DATA_JSON` for a specific `TYPE` (e.g., `CREATE_ENTITY`) is missing mandatory fields (e.g., `name` or `type` for `CREATE_ENTITY`). Refer to the [RAG Instruction Format Document](rag_instruction_format.md) for required fields for each type.
- **"Error: Could not create ... The name already exists..."**:
    - You are trying to create an entity or level template with a name that is already in use. Names must be unique.
```
