# Labyrinth2D - Design Document

## Phase 1: Game & System Design

### 1. Game Concept Refinement & Display

*   **Perspective & Grid:** The game will feature a 2D top-down perspective on a 50x50 character grid. This maintains the low-bit aesthetic of labyrinth1D while expanding the playable area significantly.

*   **Rendering Approach:**
    *   **Chosen Method:** HTML Canvas with JavaScript.
    *   **Justification:**
        *   **Performance:** For a 50x50 grid that might require frequent updates (player movement, entity animations, environmental changes), directly manipulating pixels or drawing characters on a canvas will be significantly more performant than updating the `innerHTML` of 50x50 individual DOM elements or a large `<pre>` tag.
        *   **Flexibility:** Canvas allows for finer control over rendering. We can easily define character sprites, colors, and potentially even simple animations (e.g., a blinking cursor for the player, or a shimmer effect on a special tile) without being constrained by standard text rendering.
        *   **Future-Proofing:** If we decide to add subtle graphical flairs beyond simple characters (e.g., slightly rounded corners for walls, different font styles for different elements), Canvas provides the necessary drawing primitives.
        *   **Interaction:** Canvas can handle mouse events for potential future features like clicking on tiles or entities for information.

*   **Player Movement:**
    *   **Method:** 4-directional movement (Up, Down, Left, Right).
    *   **Justification:**
        *   **Simplicity:** 4-directional movement is simpler to implement and control, especially with keyboard input.
        *   **Clarity:** It aligns well with a grid-based environment, making it clear which tile the player will move to.
        *   **Consistency:** Many classic top-down grid-based games use 4-directional movement. 8-directional movement can sometimes feel ambiguous on a strict grid if not handled carefully with diagonal sprites or movement rules. For character-based rendering, 4-directional is cleaner.

### 2. "Scrap Code" Integration, Harvesting, & "Machine Building"

The economy and evolution of player creations in Labyrinth2D revolve around "code" as a primary resource. This code can be found as curated "Scrap Code" snippets or actively harvested from the environment and other "machines".

*   **Types of Code Resources:**
    *   **"Scrap Code" Snippets:**
        *   **Structure:** These are pre-defined, curated Python function strings or self-contained code blocks, often with metadata (name, description, type). They represent well-understood, functional pieces of logic.
        *   **Acquisition:** Found in the dungeon, awarded for quest completion, or provided by the RAG system.
        *   **Example (as before):**
            ```python
            # Scrap: Basic Random Walk
            def random_walk(start_x, start_y, length, tile_char):
                # ... implementation ...
            ```
    *   **"Harvested Code" Fragments:**
        *   **Structure:** Raw strings of characters, potentially lines of Python code, or even non-executable symbolic data obtained by disassembling structures or environmental features. This code might be incomplete, obfuscated, or specific to the machine it came from.
        *   **Acquisition:** Actively mined or cannibalized from any unprotected tile, entity, or structure on the grid by a player's or AI sprite.
        *   **Representation:** Could be a simple string, or a dictionary if it has multiple parts e.g. `{"block_type": "wall_basic", "code_fragment": "self.hp = 10", "material_yield": {"stone": 1}}`.
        *   **Educational Aspect:** A key gameplay loop is for players to learn how to analyze, debug, modify, and integrate these harvested fragments into functional code.

*   **Harvesting and Cannibalization Mechanics:**
    *   **Universal Harvesting Principle:** Any tile, entity (that isn't actively defending itself or owned by the harvesting sprite's faction and protected), or structure on the grid can be targeted for harvesting by a sprite.
    *   **Mining/Disassembly Process:**
        *   A sprite (player's or AI) must typically be adjacent to the target tile/structure.
        *   The sprite executes a script action (e.g., `game.harvest_tile(x, y, self_id)` or `game.disassemble_structure(target_id, self_id)`).
        *   This action may take multiple turns ("ticks") depending on the complexity or resilience of the target.
        *   Harvesting might change the target tile (e.g., a '#' wall becomes a '.' floor, or a machine entity loses 'health' or components).
    *   **Defense:** Structures or tiles can be defended by nearby sprites of the same faction. An attempt to harvest a defended structure might fail or trigger a response from defending sprites.
    *   **Yield:** Successful harvesting yields "Harvested Code" fragments and/or basic resources (e.g., 'circuits', 'data_core', 'alphanumeric_shards'). The quality and type of code/resources depend on the source.
    *   **"Alphanumeric Graveyard":** Certain rooms or areas might be rich in unique, ancient, or powerful code fragments, representing remnants of forgotten machines.

*   **"Machine Building" & Code Evolution:**
    *   **Mechanism:** "Machine building" is the process of players writing Python scripts (for room generation or entity behaviors) by:
        1.  Integrating pre-defined "Scrap Code" snippets.
        2.  Analyzing, cleaning, and integrating "Harvested Code" fragments.
        3.  Writing their own original code.
    *   **Player Goal:** To create increasingly complex and effective "machines" – which can be dungeon rooms, automated entities (sprites), interactive systems, or even systems that manage other systems.
    *   **Example:** A player harvests a code fragment `target_faction = "red"` from a destroyed enemy spawner. They might then integrate this into their own spawner's targeting logic, or modify it to `target_faction = "blue"` for a new purpose.

*   **Sprite Spawners & Factions:**
    *   **Sprite Spawners:** A fundamental type of "machine" that players can build or encounter.
        *   **Function:** Procedurally generate and deploy new sprite entities onto the grid.
        *   **Scripting:** The spawner's script would define the type of sprite, its initial properties (including faction, code/scripts it runs), and spawn conditions (e.g., rate, resource cost).
    *   **Factions:**
        *   Sprites (player and AI) can belong to factions (e.g., "blue_team", "red_team", "player_faction", "neutral_fauna").
        *   Faction affiliation dictates allegiances: sprites typically won't harvest from their own faction's undefended structures (unless specifically scripted to do so, e.g., for recycling) and may defend them.
        *   Faction status will be a key property for entities and influence AI behavior and game mode objectives.
        *   The player typically starts with their own faction.

*   **Initial Focus for Implementation:**
    *   Represent "Scrap Code" as Python function strings.
    *   Represent basic "Harvested Code" as simple strings.
    *   Implement a basic harvesting action via a game API call.
    *   Allow manual copy-paste for both scrap and harvested code into the player's script editor.
    *   Introduce a 'faction' property for entities.

### 3. Game API (Python) - Generation & Runtime

The Game API is crucial for player interaction with Labyrinth2D. It's split into two main contexts:
1.  **Procedural Generation API:** Used by player scripts (`generate_room`) to define the static layout of a room, including initial tile placements and entity setups.
2.  **Runtime Entity API:** Used by scripts assigned to entities, enabling them to react to the game world, interact with other entities, and perform actions like moving, harvesting, or defending.

We will assume constants like `GRID_WIDTH` (50) and `GRID_HEIGHT` (50) are available, possibly via `game.GRID_WIDTH`. An instance of a relevant `GameAPI` class will be injected into the player's script scope as `game`.

#### 3.1 Core Room Generation Function Signature

Player-created scripts for room generation must define a function with the following signature:
```python
def generate_room(seed: int, room_params: dict) -> None:
    '''
    Generates a 50x50 room layout by calling game API functions.
    Args:
        seed: An integer seed for random number generation.
        room_params: A dictionary of parameters to influence generation
                     (e.g., {'room_type': 'cavern', 'difficulty': 'easy', 'default_faction': 'neutral'}).
    Returns:
        None. The room data is built up by calls to the game API.
    '''
    # Player's generation logic here, using game.set_tile, game.place_entity etc.
    # The game engine will internally retrieve the grid and entity list post-execution.
```

#### 3.2 Procedural Generation API Functions (`game.*`)

These functions are available within the `generate_room` script.

*   `game.set_tile(x: int, y: int, char: str, properties: dict = None)`:
    *   Sets the character for a specific tile.
    *   `properties`: Optional dict for tile-specific data, e.g., `{'harvestable': True, 'code_fragment': '...', 'faction_owner': 'red_team'}`.

*   `game.get_tile(x: int, y: int) -> str`: (Remains as is)
*   `game.draw_line(x1: int, y1: int, x2: int, y2: int, char: str, properties: dict = None)`: (Can now also take `properties` for the tiles)
*   `game.fill_rect(x: int, y: int, width: int, height: int, char: str, properties: dict = None)`: (Can now also take `properties` for the tiles)

*   `game.place_entity(entity_id: str, type: str, x: int, y: int, sprite_char: str, properties: dict = None)`:
    *   Places an entity. `properties` is crucial and now standardly includes:
        *   `script_name`: Name of the Python script governing this entity's runtime behavior.
        *   `faction_id`: String identifying the entity's faction (e.g., "player_1", "goblins", "neutral_traders").
        *   `health`: Integer, if applicable.
        *   `defense_value`: Integer, representing inherent toughness against harvesting/attacks.
        *   `is_spawner`: Boolean, if this entity can spawn other entities.
        *   `can_harvest`: Boolean, if this entity is capable of harvesting.
        *   Other custom properties as needed by its script or type.

*   `game.get_random_int(min_val: int, max_val: int) -> int`: (Remains as is)
*   `game.get_random_coord() -> tuple[int, int]`: (Remains as is)
*   `game.display_generation_message(message: str)`: (Remains as is)
*   `game.GRID_WIDTH: int = 50` (read-only property)
*   `game.GRID_HEIGHT: int = 50` (read-only property)

#### 3.3 Runtime Entity API Functions (`game.*`)

These functions are available to scripts assigned to entities during active gameplay. The `game` object here provides methods relevant to an active, dynamic environment.

*   **Movement & Position:**
    *   `game.move_self(dx: int, dy: int) -> bool`: Moves the entity executing the script. Returns `True` if successful.
    *   `game.get_self_id() -> str`: Gets ID of the current entity.
    *   `game.get_self_position() -> tuple[int, int]`: Gets current (x,y) of the entity.
    *   `game.get_player_position() -> Optional[tuple[int, int]]`: Gets player's current (x,y), if present.

*   **Entity Interaction & Properties:**
    *   `game.get_entity_property(entity_id: str, property_name: str) -> any`: Retrieves a shared/public property.
    *   `game.set_entity_property(entity_id: str, property_name: str, value: any)`: Modifies a shared/public property (e.g. 'target_mode'; internal properties like 'health' might be modified by specific actions like `game.attack`).
    *   `game.get_self_property(property_name: str) -> any`: Gets a property from the current entity.
    *   `game.set_self_property(property_name: str, value: any)`: Sets a property on the current entity.
    *   `game.get_entities_at(x: int, y: int) -> list[str]`: Returns IDs of entities at a location.
    *   `game.get_entities_in_radius(x: int, y: int, radius: int, include_self=False) -> list[str]`: Returns IDs of entities within a given radius.
    *   `game.get_distance_to(target_x: int, target_y: int) -> float`: Calculates distance from self to target coordinates.

*   **Combat & Defense (Basic):**
    *   `game.attack_target(target_entity_id: str, damage_amount: int) -> bool`: Perform an attack. Returns true if target was hit/affected.
    *   `game.is_hostile(target_entity_id: str) -> bool`: Checks if target is hostile based on faction.

*   **Harvesting & Environment Interaction:**
    *   `game.analyze_tile_code(x: int, y: int) -> Optional[dict]`:
        *   Inspects a tile for harvestable code/resources.
        *   Returns a dictionary like `{'code_fragment': "...", 'resource_type': "...", 'value': ...}` or `None`.
    *   `game.harvest_tile(x: int, y: int, time_to_harvest: int = 1) -> Optional[dict]`:
        *   Attempts to harvest the tile at `(x,y)`. This action might require multiple turns (ticks), specified by `time_to_harvest`. The game engine would manage the multi-turn action, and the script would re-check status or be called back.
        *   Returns the harvested data (similar to `analyze_tile_code`) on final successful tick, or `None` if failed (e.g., defended, depleted, wrong tool).
        *   Modifies the tile if successful (e.g., '#' to '.', or removes a 'machine' part).
    *   `game.get_tile_info(x: int, y: int) -> dict`: Returns char and properties of a tile e.g. `{'char': '#', 'harvestable': True, 'faction_owner': 'red'}`.

*   **Faction Mechanics:**
    *   `game.get_self_faction() -> str`: Returns the faction ID of the current entity.
    *   `game.get_entity_faction(entity_id: str) -> Optional[str]`: Returns the faction ID of another entity.
    *   `game.get_tile_faction_owner(x: int, y: int) -> Optional[str]`: Gets faction owning the tile/structure at (x,y).
    *   `game.broadcast_message(message: any, radius: Optional[int] = None, target_faction: Optional[str] = None)`:
        *   Sends a `message` (can be a string or dict) to other entities.
        *   `radius`: If specified, only entities within this radius receive it.
        *   `target_faction`: If specified, only entities of this faction receive it.
        *   Entities receive messages via a predefined callback function in their script (e.g., `on_message_received(sender_id, message)`).

*   **Spawning (for Spawner-type entities):**
    *   `game.spawn_entity(type: str, x: int, y: int, sprite_char: str, properties: dict) -> Optional[str]`:
        *   Allows an entity with `is_spawner=True` and appropriate script logic to create new entities.
        *   Returns the new entity's ID or `None` if spawning failed (e.g., location blocked, resource cost not met).
        *   `properties` must include `faction_id` for the new entity.

*   **Communication & Control:**
    *   `game.display_message(message: str)`: Displays a message in the main game log (runtime).
    *   `game.log_message(message: str)`: For entity's own script debugging, less visible than `display_message`.

*   **Note on API Evolution:** The distinction between generation and runtime APIs is key. Generation API sets up the "level", Runtime API lets entities "live" in it. Functions like `game.destroy_entity(entity_id)` and `game.create_entity(...)` (from original Labyrinth1D) are essentially covered by `game.harvest_tile` (which might destroy an entity by depleting it) and `game.spawn_entity`. We'll refine this as we implement.
### 4. Level Creator & Room Chaining Mechanism

*   **Data Structure for Labyrinth:**
    *   **Representation:** A graph-like structure will be used. The overall labyrinth can be represented as a Python dictionary or a custom `LabyrinthMap` object.
    *   **`LabyrinthMap` Object:**
        ```python
        class LabyrinthMap:
            def __init__(self, name="MyLabyrinth"):
                self.name = name
                self.rooms = {}  # Key: room_id (str), Value: RoomNode object
                self.start_room_id = None # ID of the room where the player begins

            def add_room(self, room_node):
                self.rooms[room_node.id] = room_node
                if not self.start_room_id:
                    self.start_room_id = room_node.id

            def get_room(self, room_id):
                return self.rooms.get(room_id)

            def connect_rooms(self, from_room_id, from_coords, to_room_id, to_coords, connection_id=None, bidirectional=True):
                # Details in RoomNode and Connection object
                from_room = self.get_room(from_room_id)
                to_room = self.get_room(to_room_id)
                if not from_room or not to_room:
                    print(f"Error: Cannot connect rooms. One or both not found: {from_room_id}, {to_room_id}")
                    return

                if not connection_id:
                    connection_id = f"conn_{from_room_id}_to_{to_room_id}"

                conn_outgoing = Connection(
                    id=connection_id + "_out",
                    target_room_id=to_room_id,
                    target_entry_coords=to_coords, # Player appears here in the new room
                    source_exit_coords=from_coords # Coordinates of the 'door' or 'portal' in the source room
                )
                from_room.add_connection(conn_outgoing)

                if bidirectional:
                    conn_incoming = Connection(
                        id=connection_id + "_in",
                        target_room_id=from_room_id,
                        target_entry_coords=from_coords,
                        source_exit_coords=to_coords
                    )
                    to_room.add_connection(conn_incoming)
        ```
    *   **`RoomNode` Object:**
        ```python
        class RoomNode:
            def __init__(self, room_id, display_name, generator_script_name, room_params=None):
                self.id = room_id # Unique ID for this room instance, e.g., "room_001", "boss_chamber"
                self.display_name = display_name # User-friendly name, e.g., "Goblin Barracks"
                self.generator_script_name = generator_script_name # Name/ID of the Python script used to generate this room
                self.room_params = room_params if room_params else {} # Specific params for this room's generation
                self.connections = {} # Key: connection_id, Value: Connection object
                # The actual 50x50 grid (list[list[str]]) will be generated on demand or cached.

            def add_connection(self, connection):
                # A room's connection defines an exit point leading to another room.
                # The connection object stores where this exit leads.
                self.connections[connection.id] = connection
        ```
    *   **`Connection` Object:**
        ```python
        class Connection:
            def __init__(self, id, target_room_id, target_entry_coords, source_exit_coords):
                self.id = id # e.g., "portal_north_exit"
                self.target_room_id = target_room_id # ID of the RoomNode this connection leads to
                self.target_entry_coords = target_entry_coords # (x,y) where player appears in the target room
                self.source_exit_coords = source_exit_coords # (x,y) of the 'door' or 'portal' tile in the source room.
                                                          # Player interaction with this tile triggers transition.
        ```
    *   **Serialization:** This structure (LabyrinthMap, RoomNodes, Connections) will need to be serializable (e.g., to JSON or Pickle) for saving and loading labyrinth designs. JSON is preferable for readability and interoperability.

*   **Room Connection & Player Transition:**
    *   **Mechanism:** Connections are defined by "portals" or "doors" at specific coordinates in a room. These will be special tiles (e.g., 'D' for Door, 'O' for Portal).
    *   **Player Interaction:** When the player moves onto a tile that is marked as an exit point of a `Connection` in the current `RoomNode`:
        1.  The game identifies the `Connection` object associated with `source_exit_coords`.
        2.  It retrieves `target_room_id` and `target_entry_coords` from the `Connection`.
        3.  The game loads/generates the grid for `target_room_id` (using its `generator_script_name` and `room_params`).
        4.  The player's position is updated to `target_entry_coords` within the new room's grid.
        5.  The UI re-renders with the new room's grid and player position.
    *   **Visual Cue:** The procedural generation script for a room will be responsible for placing the actual 'door' or 'portal' characters at the `source_exit_coords` defined in its connections. The Level Creator UI ensures these definitions are consistent.

*   **Conceptual UI for Level Creator:**
    *   **View:** A bird's-eye, abstract graphical view or a structured text-based representation.
        *   **Graphical (Ideal):** A canvas where each room is a draggable box. Connections are lines drawn between boxes. Clicking a box shows its properties (ID, script name, etc.). Clicking a line shows connection properties.
        *   **Text/Table-based (Simpler Initial):**
            *   A list of all rooms in the labyrinth. Each entry shows Room ID, Display Name, Generator Script.
            *   A separate view/table for connections, where each row defines: `From Room ID`, `From Coords (X,Y)`, `To Room ID`, `To Coords (X,Y)`, `Bidirectional?`.
    *   **Functionality:**
        1.  **Create New Room:**
            *   Prompt for a unique Room ID (e.g., `room_001`).
            *   Prompt for a Display Name.
            *   Allow selection of a `generator_script_name` from available player-saved or default scripts.
            *   Allow input of `room_params` (as a JSON string or key-value pairs).
        2.  **Define Connections:**
            *   Select a "From Room" and a "To Room."
            *   Specify `source_exit_coords` (e.g., `(49, 25)` for an exit on the right edge of "From Room").
            *   Specify `target_entry_coords` (e.g., `(0, 25)` for an entry on the left edge of "To Room").
            *   Option for bidirectional connection (creates the reverse automatically).
        3.  **Set Start Room:** Designate one room as the player's starting point.
        4.  **Save/Load Labyrinth:** Serialize the `LabyrinthMap` object to a file (e.g., JSON) and allow loading it back.
        5.  **Visualization:** (Even if text-based) Some way to quickly see which rooms are connected. For example, selecting a room could highlight its direct connections.
    *   **Layout Support:** This data structure inherently supports forks, turns, loops, and dead ends by the nature of graph connections.

### 5. Experiential Education & RAG Strategy

The educational core of Labyrinth2D is learning Python for procedural generation, entity scripting, and systems interaction through direct gameplay, heavily supported by the integrated RAG system. The new mechanics of code harvesting and faction play will be central to this educational process.

*   **RAG's Role in Teaching & Gameplay:**
    1.  **Comprehensive API Documentation:**
        *   Contextual help for all Game API functions (generation and runtime), including new ones like `game.analyze_tile_code()`, `game.harvest_tile()`, `game.get_self_faction()`, etc.
        *   Provides explanations, signatures, examples, and expected return values or side effects.
    2.  **Conceptual Guidance for Core Mechanics:**
        *   Explains procedural generation algorithms.
        *   Explains entity scripting for behaviors (movement, decision making).
        *   **NEW:** Explains how to identify promising structures/tiles for code harvesting.
        *   **NEW:** Guides on interpreting and modifying potentially incomplete or obfuscated "Harvested Code."
        *   **NEW:** Teaches basic principles of scripting defensive behaviors for entities and structures.
        *   **NEW:** Explains faction dynamics and how to script faction-aware behaviors (e.g., identifying friend/foe, reacting to broadcasts).
    3.  **Snippet Management & Integration:**
        *   Suggests relevant "Scrap Code" snippets.
        *   **NEW:** Assists in analyzing "Harvested Code" fragments, suggesting how they might be cleaned up, completed, or integrated with existing code or scrap snippets. (e.g., "This fragment `if self.x > target.x:` looks like part of a movement logic. You could combine it with a `game.move_self(-1, 0)` call.")
    4.  **Error Explanation & Debugging:**
        *   Provides clearer explanations for Python errors, especially those common in game scripting (e.g., `NoneType` errors when an entity is destroyed, issues with coordinates).
        *   Helps debug issues related to harvesting (e.g., "Harvest failed, maybe the tile is defended or has no code? Try `game.get_tile_info()`.") or faction logic.
    5.  **Progressive Learning via "Scripting Quests":** The RAG delivers quests that build skills incrementally.

*   **Prompt Structure for RAG:** (Largely as before, but with new examples)
    *   User-initiated:
        *   "How do I check if a wall '#' has code I can harvest?" (RAG: "Use `game.analyze_tile_code(x,y)`. If it returns data, you can try `game.harvest_tile(x,y)`.")
        *   "This harvested code `data = self.mem[0]` doesn't work. What could be wrong?" (RAG: "It seems to access `self.mem[0]`. Does your entity's script initialize `self.mem` as a list or dictionary? Perhaps the structure it came from had a different setup.")
        *   "How do I make my sprite attack nearby 'red_team' sprites?"
        *   "What's the best way to defend my spawner?"
    *   System-initiated (contextual):
        *   "Your sprite seems to be idle. You could script it to explore, or if it has `can_harvest=True`, look for harvestable tiles. Want some ideas?"
        *   "You just harvested `{'code_fragment': 'health += 5'}`. This could be part of a repair script. Would you like help integrating it?"

*   **Revised & New "Scripting Quests" (Guided by RAG):**
    1.  **Quest: "The First Room"** (As before)
    2.  **Quest: "Place Three Treasures"** (As before)
    3.  **Quest: "Resourceful Digger"**
        *   **Objective:** Locate a specific type of tile (e.g., a cracked wall 'C') and successfully harvest a basic resource or a simple code fragment from it using `game.harvest_tile()`.
        *   **RAG Guidance:** How to use `game.analyze_tile_code()` to check if 'C' is harvestable, then `game.harvest_tile()`. Explain that harvesting might change 'C' to '.'.
    4.  **Quest: "Deconstruct & Reconstruct"**
        *   **Objective:** Harvest a specific, slightly more complex code fragment (e.g., a simple movement pattern like `if game.get_player_position()[0] < self.x: self.move(-1,0)`) from a predefined "decaying machine" entity. Then, integrate this code into a new, simple entity script for one of the player's own sprites.
        *   **RAG Guidance:** Help analyzing the harvested fragment, identifying its purpose, and showing how to embed it into a standard entity script structure (e.g., an `on_tick()` function).
    5.  **Quest: "My First Sentry"**
        *   **Objective:** Create a stationary sprite that, if it detects a sprite from an enemy faction within a small radius (e.g., 3 tiles), broadcasts a warning message.
        *   **RAG Guidance:** Using `game.get_entities_in_radius()`, `game.get_entity_faction()`, `game.get_self_faction()`, and `game.broadcast_message()`.
    6.  **Quest: "The Automated Miner"**
        *   **Objective:** Script a sprite to find specific harvestable tiles (e.g., marked with '$'), move to them, and harvest them. The sprite should then perhaps return the harvested resources to a "drop-off" point.
        *   **RAG Guidance:** Pathfinding concepts (simple versions), state management for the sprite (e.g., `state='searching'`, `state='harvesting'`, `state='returning'`), using `game.harvest_tile()` effectively.
    7.  **Quest: "Claim and Defend"**
        *   **Objective:** Create a room, place a "faction flag" (a special tile or entity), and assign a sprite to "guard" it. If an enemy sprite approaches the flag, the guard should attempt to attack it.
        *   **RAG Guidance:** Combining detection (`game.get_entities_in_radius`), faction checking (`game.is_hostile`), and combat (`game.attack_target`). Introduction to simple defensive AI logic.
    8.  **Quest: "Build a Spawner"**
        *   **Objective:** Script an entity to act as a 'Sprite Spawner', creating new sprites of a specific type and faction at regular intervals or when conditions are met, using `game.spawn_entity()`.
        *   **RAG Guidance:** How to use `game.spawn_entity()`, managing spawn timers or resource costs, setting properties for spawned entities (especially their faction and script).

*   **Teaching Code Modification:**
    *   The RAG will play a crucial role in helping players understand that harvested code isn't always plug-and-play.
    *   It will offer advice on:
        *   Identifying variables and how they might need to be renamed or re-scoped.
        *   Understanding control flow in fragments and how to complete it.
        *   Recognizing common patterns (e.g., "This looks like it's trying to iterate through nearby tiles...").
        *   Safely testing modified code.

This revised strategy aims to make the "experiential education" process deeply intertwined with the core gameplay loops of exploration, harvesting, building, and faction interaction.

### 6. Technology Stack & Docker

*   **Web Framework (Python):**
    *   **Choice:** FastAPI.
    *   **Justification:**
        *   **Performance:** FastAPI is known for its high performance, which will be beneficial for handling game state updates, RAG queries, and script executions.
        *   **Asynchronous Support:** Its native `async` support is excellent for I/O-bound operations like handling multiple user connections (if we ever scale to that), RAG API calls, and potentially long-running script executions without blocking the main thread.
        *   **Data Validation:** Uses Pydantic for data validation, which is great for ensuring API requests (e.g., script submissions, RAG queries) are correctly formatted.
        *   **Automatic Docs:** Generates OpenAPI documentation automatically, which is useful for API development and testing.
        *   **Modern & Growing:** It's a modern framework with a growing community and good support.
        *   **Alternative (Flask):** Flask is also a solid choice and simpler for smaller projects. However, for the potential complexity and desired performance, FastAPI offers a better foundation. Streamlit is more geared towards data science apps and might be restrictive for a full-fledged game UI.

*   **Frontend Technologies:**
    *   **HTML, CSS, JavaScript:** Standard web technologies.
    *   **Grid Rendering:** As decided in Section 1, **HTML Canvas + JavaScript** will be used for rendering the 50x50 character grid. This provides the necessary performance and flexibility for drawing characters, potential small animations, and handling interactions.
    *   **JavaScript Framework (Optional):** For managing the UI components (code editor, RAG display, game controls), a lightweight framework like Vue.js or Svelte could be considered in later phases if complexity grows. For the initial phases, vanilla JavaScript or a simpler library like HTMX might suffice to keep things lightweight and focused. *Initial implementation will use vanilla JavaScript to minimize dependencies.*
    *   **Code Editor:** A browser-based code editor component (e.g., CodeMirror, Monaco Editor - though Monaco might be too heavy) will be embedded for players to write their Python scripts. *A simpler `<textarea>` with basic enhancements might be used initially, with CodeMirror as a stretch goal for Phase 2/3.*

*   **Python Sandboxing:**
    *   **Strategy:** Building upon the `labyrinth1D` approach. Player-written Python scripts (for procedural generation and entity behaviors) will be executed using `exec()`.
    *   **Security Measures:**
        1.  **Restricted `globals` and `locals`:** The `exec()` function will be called with carefully curated dictionaries for global and local scopes.
        2.  **Limited API Exposure:** Only the specific `GameAPI` object (tailored for generation or runtime) will be injected. No direct access to filesystem, network, or dangerous built-in modules (e.g., `os`, `subprocess`, `sys` beyond what's essential and safe).
        3.  **Resource Limits (Future Enhancement):** For long-running scripts or complex procedural generation, consider ways to impose resource limits (CPU time, memory). This can be complex. Initial versions might rely on timeouts or script complexity analysis.
        4.  **Separate Process/Thread (Future Enhancement):** For more robust sandboxing, consider running player scripts in separate processes or heavily restricted threads. Docker itself provides a layer of isolation for the entire application.
    *   **Focus:** The primary goal is to prevent scripts from damaging the server environment or accessing unauthorized data.

*   **RAG System:**
    *   Leveraging ZeroExMachina's RAGs as specified. The exact integration mechanism (API calls to a RAG service) will be defined during implementation. Assume it's an HTTP API endpoint.

*   **Persistence:**
    *   **Player Scripts:** Initially, these can be stored on the server's filesystem (e.g., in a dedicated directory, perhaps as `.py` files or in a simple database like SQLite).
    *   **Labyrinth Maps:** Saved labyrinth structures (from the Level Creator) will likely be stored as JSON files on the server.
    *   **Scrap Code Inventory:** Player's collected scrap code could be part of their user session or persisted alongside their scripts.
    *   *A simple file-based approach will be used for Phase 2/3, with potential to move to SQLite if needed.*

*   **Docker Compose (`docker-compose.yml` Outline):**
    ```yaml
    version: '3.8'

    services:
      labyrinth2d_web:
        build:
          context: .  # Assuming Dockerfile is in the root
          dockerfile: Dockerfile
        ports:
          - "8000:8000" # Expose FastAPI app (adjust port as needed)
        volumes:
          - ./player_data:/app/player_data # Persistent storage for scripts, maps
          # - ./game_code:/app/game_code # If code is mounted for development
        environment:
          # - RAG_API_URL=http://rag_service:port # If RAG is a separate container
          - PYTHONUNBUFFERED=1 # For seeing print statements from Python immediately
        # depends_on:
        #   - rag_service # If RAG is a local Docker service

      # rag_service: # Optional: If running a RAG system as a separate container
      #   image: your_rag_image_here # Or build from a Dockerfile
      #   # environment:
      #   #   - MODEL_PATH=/models
      #   # volumes:
      #   #   - ./rag_models:/models
      #   ports:
      #     - "8080:8080" # Example port for RAG service

    volumes:
      player_data: # Define the named volume for persistence
    ```
    *   **Dockerfile Contents (Conceptual):**
        *   Base image: `python:3.10-slim` (or similar).
        *   Set up working directory.
        *   Install Python dependencies from `requirements.txt` (FastAPI, Uvicorn, etc.).
        *   Copy application code into the image.
        *   Expose the port Uvicorn will run on.
        *   `CMD` to run the FastAPI application using Uvicorn.
    *   **Note:** If the RAG system is a Python library integrated directly into the FastAPI app, a separate `rag_service` in Docker Compose might not be needed. If it's an external or standalone service, it would be included. The prompt mentions "integrated RAG system," which could mean a library, but also "RAGs (leveraging ZeroExMachina's RAGs)," suggesting it might be a distinct component. The `docker-compose.yml` provides flexibility. *For initial phases, the RAG might be called via an external HTTP API, or if it's a library, it's part of the `labyrinth2d_web` service.*

### 7. Game Modes & Win Conditions

Labyrinth2D is designed to be flexible, supporting emergent gameplay through its scripting and harvesting mechanics. To provide structure and varied challenges, several game modes can be introduced, each with unique objectives and win conditions. The game will also feature a default "sandbox" mode.

*   **Default Mode: Sandbox / Creative Exploration**
    *   **Objective:** Open-ended exploration, machine building, code harvesting, and interaction with the environment and any naturally spawning or player-created entities/factions.
    *   **Win Conditions:** None explicitly defined by the system. Players set their own goals (e.g., "build a self-sustaining base," "map out the entire labyrinth," "master a complex code harvesting technique").
    *   **Player Experience:** Focus on learning, experimentation, and creation in a persistent or semi-persistent world (defined by the Labyrinth Map).

*   **Game Mode: Attrition / Last Faction Standing**
    *   **Setup:**
        *   Can be played on a single complex room or a small Labyrinth Map of interconnected rooms.
        *   Two or more factions are defined (e.g., "Player Faction" vs. "Red Faction" vs. "Blue Faction").
        *   Each faction might start with one or more "Sprite Spawners" and a small number of initial sprites.
    *   **Objective:** Be the last faction with active sprites or operational spawners on the map.
    *   **Win Conditions:**
        *   All sprites and spawners belonging to other factions are destroyed or disabled.
        *   A faction is considered defeated if it has no means of producing new sprites and no active sprites remaining.
    *   **Player Experience:** Strategic scripting of offensive and defensive sprites, resource management (harvesting code/energy to build and maintain forces), and tactical positioning.

*   **Game Mode: Capture the Flag (Conceptual)**
    *   **Setup:**
        *   A Labyrinth Map with at least two designated "base" rooms, one for each primary faction.
        *   A "flag" entity is placed in each faction's base.
    *   **Objective:**
        *   Retrieve the enemy faction's flag and return it to your own base while your flag is still secure.
        *   Alternatively, a central "flag" or multiple "control points" that need to be captured and held for a certain duration.
    *   **Win Conditions:**
        *   Successfully capturing the enemy flag and bringing it to your base.
        *   (For control points) Holding designated points for a cumulative time limit.
    *   **Player Experience:** Focus on scripting diverse sprite roles: fast "runners" to grab flags, "defenders" to protect your flag/base, "escorts," and "attackers" to disrupt enemy operations. Requires coordination (possibly via `game.broadcast_message`) and map awareness.

*   **Game Mode: Code Dominion**
    *   **Setup:**
        *   A map with various "Code Repositories" (special structures or tiles rich in valuable, unique scrap/harvestable code).
    *   **Objective:** Harvest and "control" a certain percentage of the total available unique code fragments or achieve a certain "code complexity" score by building sophisticated machines.
    *   **Win Conditions:**
        *   Be the first faction to accumulate X points worth of unique code fragments.
        *   Successfully build and maintain a "Master Machine" that requires diverse and complex code components harvested from different sources.
    *   **Player Experience:** Emphasizes exploration, strategic harvesting (some code might be better defended), and the core loop of understanding and repurposing harvested code.

*   **Implementing Game Modes:**
    *   **Game State Management:** The main game loop will need to track game mode-specific states (e.g., flag locations, faction scores, active spawners per faction).
    *   **Room Parameters:** `room_params` in the `generate_room` function could include game mode specific flags (e.g., `{'game_mode': 'attrition', 'faction_setup': {...}}`).
    *   **UI:** The game UI will need to display objectives and current status relevant to the active game mode.
    *   **API Support:** The Game API might need minor extensions for game mode interactions (e.g., `game.get_flag_status(faction_id)`, `game.get_capture_point_owner(point_id)`).

This section provides a starting point for structured play, complementing the open-ended nature of the core Labyrinth2D experience. The "Level Creator" could eventually allow players to set up these game modes for their own custom Labyrinths.
```
