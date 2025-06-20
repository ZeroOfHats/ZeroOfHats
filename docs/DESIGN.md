# Game Design Document

## 1. Game Concept & Display Mechanics

*   **Core Game Concept:** The game will be a dungeon scroller where the game world, characters, and objects are represented by alphanumeric characters.
*   **Grid Rendering:** The game will be rendered on a 10x10 grid within an HTML `<pre>` tag to maintain monospace formatting.
*   **Movement and Level Wrapping:**
    *   Player movement will primarily be along the X-axis.
    *   When the player reaches the edge of the map on the Y-axis, the view will wrap around to the other side of the map.
*   **Map Storage and Update:**
    *   The server will store the complete, large game map.
    *   The client will only receive and display a 10x10 portion of the map, representing the player's current view. This view will be updated as the player moves.

## 2. Technology Stack Selection

*   **Web Framework: Flask**
    *   **Justification:** Flask is a lightweight and flexible Python web framework, suitable for rapid prototyping and development. Its simplicity allows for easy integration of the game logic and API endpoints.
*   **Game Frontend: HTML/CSS/Vanilla JavaScript**
    *   **Graphics Rendering:** The game grid and its contents (player, entities, environment) will be rendered by dynamically updating the content of the `<pre>` tag using JavaScript. CSS will be used for basic styling, ensuring a monospace font and retro feel.
    *   **Input Capture:** Player input (movement commands, script execution triggers) will be captured using JavaScript event listeners on keyboard events and UI button clicks.
*   **In-Game Scripting Environment: `exec()` with Sandboxing**
    *   **Execution:** User-provided Python scripts will be executed using the `exec()` function.
    *   **Sandboxing:** To mitigate security risks, `exec()` will be used in conjunction with a sandboxing mechanism like `RestrictedPython`. This will limit the script's access to the underlying system and Python's more dangerous built-in functions.
    *   **Security:** The sandbox will prevent scripts from performing malicious operations such as file system access, network requests, or importing arbitrary modules.
    *   **Resource Management:** While `RestrictedPython` offers some control, further considerations for resource management (e.g., execution time limits, memory limits) might be necessary if scripts become complex, though this is a stretch goal for a prototype.

## 3. RAG Integration

*   **RAG Models/Embeddings Availability in Docker:**
    *   **Recommendation:** For the prototype, RAG models and pre-computed embeddings for game documentation will be **baked into the Docker image**. This simplifies deployment and ensures consistency across environments. Volume mounts could be considered for larger, more dynamic datasets in a production setting.
*   **API Endpoints for RAG Interaction:**
    *   **Endpoint:** `/rag_query` (POST request)
    *   **Request Structure (JSON):**
        ```json
        {
          "query_text": "How do I move the player?"
        }
        ```
    *   **Response Structure (JSON):**
        ```json
        {
          "suggestions": [
            {
              "document_fragment": "To move the player, use the `game.move_player(direction)` function...",
              "source": "game_api.md",
              "score": 0.85
            },
            {
              "document_fragment": "The player can move 'north', 'south', 'east', or 'west'.",
              "source": "movement_rules.md",
              "score": 0.72
            }
          ],
          "raw_query_response": "..." // Optional: for debugging or more advanced use cases
        }
        ```
*   **Feeding Game-Specific Documentation to RAG:**
    *   **Format:** Documentation will be provided as Markdown files (`.md`).
    *   **Preprocessing:** A script (e.g., `build_rag_kb.py`) will parse these Markdown files, potentially chunk them, and generate embeddings.
    *   **Augmenting Knowledge Base:** The preprocessed documents and their embeddings will form the knowledge base for the RAG system. This process will occur during the Docker image build.

## 4. Core Game API & Scripting Hooks (Python)

The following `game.*` functions will be exposed to the in-game scripting environment:

*   `game.get_player_position() -> dict`: Returns the player's current coordinates (e.g., `{'x': 5, 'y': 2}`).
*   `game.move_player(direction: str)`: Moves the player one step in the specified direction (`'north'`, `'south'`, `'east'`, `'west'`).
*   `game.add_entity(entity_id: str, type: str, x: int, y: int, sprite_char: str, properties: dict = {})`: Adds a new entity to the game world.
    *   `entity_id`: A unique identifier for the entity.
    *   `type`: A category for the entity (e.g., `'monster'`, `'item'`, `'npc'`).
    *   `x`, `y`: Coordinates for the entity.
    *   `sprite_char`: The character used to represent the entity on the grid.
    *   `properties`: An optional dictionary for custom data associated with the entity.
*   `game.remove_entity(entity_id: str)`: Removes an entity from the game world.
*   `game.set_entity_script(entity_id: str, script_code_string: str)`: Associates a Python script with an entity. This script will define the entity's behavior.
*   `game.get_entity_property(entity_id: str, property_name: str) -> any`: Retrieves a specific property value for an entity.
*   `game.set_entity_property(entity_id: str, property_name: str, value: any)`: Sets or updates a property for an entity.
*   `game.get_grid_cell(x: int, y: int) -> dict | None`: Returns information about the cell at the given coordinates (e.g., `{'type': 'wall', 'char': '#'}` or `{'type': 'empty', 'char': '.'}` or `None` if out of bounds of the current view).
*   `game.display_message(message_string: str)`: Displays a message to the player in the game's message/console area.

**Entity Update Cycle:**
The game will likely operate on a **turn-based or event-driven** model. When the player acts (e.g., moves or runs a script), entity scripts associated with entities in the vicinity or relevant to the action might be triggered.

## 5. Docker Strategy

*   **`Dockerfile` Structure:**
    ```dockerfile
    # Base Image
    FROM python:3.10-slim

    # Set working directory
    WORKDIR /app

    # Install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy application code
    COPY . .

    # Pre-build RAG knowledge base (if applicable)
    # This might involve running a Python script
    # RUN python scripts/build_rag_kb.py

    # Expose port
    EXPOSE 5000

    # Command to run the application
    CMD ["python", "app.py"]
    # Or using a run script: CMD ["./run.sh"]
    ```
*   **Helper Scripts:**
    *   `build_rag_kb.py` (Potential): A Python script to process documentation files (Markdown) and generate the RAG knowledge base (embeddings). This would be run during the Docker build process.
    *   `run.sh` (Potential): A shell script to start the Flask application, possibly setting environment variables or running other prerequisite tasks.
*   **Considerations:**
    *   **Base Image:** `python:3.10-slim` is chosen for its small size while providing a full Python environment.
    *   **Efficient Dependencies:** `pip install --no-cache-dir` reduces image size.
    *   **Sandboxing Setup:** If `RestrictedPython` or other sandboxing libraries have system dependencies, they must be installed in the Dockerfile.
    *   **Port:** The Flask app will run on port `5000` by default, which is exposed.
    *   **Volumes:** For development, volumes can be used to mount the application code for live reloading. For RAG assets, baking them in is preferred for the prototype, but volumes could be an option for larger, more dynamic knowledge bases later.

## 6. User Interface (UI) Sketch (Conceptual)

*   **Layout Description:**
    The UI will be divided into a few key areas, likely using simple HTML `div` elements styled with CSS.

    ```
    +-----------------------------------------------------+
    | Game Title / Info Bar                               |
    +-----------------------------------------------------+
    | Game Display (10x10 <pre> grid) | Player Info       |
    |                                 | (Health, Score)   |
    |                                 |                   |
    |                                 +-------------------+
    |                                 | RAG Suggestions   |
    |                                 | (Scrollable list) |
    +-----------------------------------------------------+
    | Code Editor (<textarea>)        | Script Output     |
    |                                 | (<pre> Console)   |
    | +-----------------------------+ |                   |
    | | Run Script Button           | |                   |
    +-----------------------------------------------------+
    | RAG Query Input (<input type="text">)               |
    +-----------------------------------------------------+
    ```

*   **Essential UI Elements:**
    *   **Game Display:** A 10x10 grid rendered in a `<pre>` tag showing the player's current view of the game world.
    *   **Player Info:** A small section displaying key player stats (e.g., health, score, inventory items - simplified for prototype).
    *   **Code Editor:** A `<textarea>` element where users can write and edit Python scripts for entities or general game interaction.
    *   **"Run Script" Button:** A button to trigger the execution of the script currently in the Code Editor.
    *   **Script Output/Console:** A `<pre>` or `<div>` area to display messages from `game.display_message()` and any output or errors from executed scripts.
    *   **RAG Query Input:** A text input field for users to type queries for the RAG system.
    *   **RAG Suggestions Display:** An area (possibly a scrollable list) to show suggestions, code snippets, or documentation fragments returned by the RAG system.

*   **Overall Aesthetic:**
    *   **Monospace Fonts:** Primarily use monospace fonts (e.g., Courier New, Consolas) for the game display, code editor, and console to enhance the retro, terminal-like feel.
    *   **Limited Colors:** A simple color palette, perhaps reminiscent of old terminals (e.g., green or amber text on a black background).
    *   **Retro Feel:** The overall design should evoke a sense of classic text-based adventure games or early computing interfaces.
```
