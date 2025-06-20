# Labyrinth2D Game API Reference

This document details the Python Game API available to player scripts in Labyrinth2D.
The `game` object provided to your scripts will be an instance of either `GenerationGameAPI` (for room generation scripts) or `RuntimeGameAPI` (for entity behavior scripts).

## I. GenerationGameAPI (`game.*` in `generate_room` scripts)

Used when your `generate_room(seed, room_params)` function is called.

### Tile Manipulation
*   `game.set_tile(x: int, y: int, char: str, properties: dict = None)`: Sets the character and optional properties for a tile at (x,y).
*   `game.get_tile(x: int, y: int) -> str`: Returns the character of the tile at (x,y).
*   `game.draw_line(x1: int, y1: int, x2: int, y2: int, char: str, properties: dict = None)`: Draws a horizontal or vertical line.
*   `game.fill_rect(x: int, y: int, width: int, height: int, char: str, properties: dict = None)`: Fills a rectangle with a character.

### Entity Placement
*   `game.place_entity(entity_id: str, type: str, x: int, y: int, sprite_char: str, properties: dict = None)`: Places an entity. `properties` should include `script_name`, `faction_id`, `health`, etc.

### Utilities
*   `game.get_random_int(min_val: int, max_val: int) -> int`: Returns a seeded random integer.
*   `game.get_random_coord() -> tuple[int, int]`: Returns seeded random (x,y) coordinates within grid boundaries.
*   `game.display_generation_message(message: str)`: Logs a message to the script action log (visible after script execution).
*   `game.GRID_WIDTH: int` (read-only): Grid width (50).
*   `game.GRID_HEIGHT: int` (read-only): Grid height (50).

### External System Hooks (Placeholders)
*   `game.call_fractal_bloom(params: dict) -> dict`:
    *   **Future Purpose:** Interface with an external "FractalBloom" system to get complex geometric patterns for level design.
    *   **Current Behavior:** Logs the call. Returns a hardcoded dummy dictionary representing a simple pattern (e.g., `{"pattern_type": "simple_line_set", "lines": [...]}`).
    *   **Example:** `pattern = game.call_fractal_bloom({"type": "crystal_growth", "size": 10})`
*   `game.get_gateway_info(gateway_id: str) -> dict`:
    *   **Future Purpose:** Query information about an inter-dimensional "GateWay" (e.g., its destination, status).
    *   **Current Behavior:** Logs the call. Returns a hardcoded dummy dictionary with info like `{"id": gateway_id, "status": "conceptual", "target_realm_type": "lava_world"}`.
    *   **Example:** `gw_data = game.get_gateway_info("main_exit")`

## II. RuntimeGameAPI (`game.*` in entity `on_tick` scripts)

Used by scripts assigned to entities during active gameplay.

### Self Information & Properties
*   `game.get_self_id() -> str`: Returns the ID of the entity executing the script.
*   `game.get_self_properties() -> dict`: Returns a copy of the current entity's properties.
*   `game.get_self_property(property_name: str) -> any`: Retrieves a specific property of the current entity.
*   `game.set_self_property(property_name: str, value: any)`: Sets a property on the current entity.

### Movement & Position
*   `game.move_self(dx: int, dy: int) -> bool`: Moves the entity by (dx, dy). Returns `True` on success, `False` if blocked.
*   `game.get_player_position() -> tuple[int, int] | None`: Returns player's (x,y) or `None`.

### World Interaction & Sensing
*   `game.get_tile_info(x: int, y: int) -> dict`: Returns info about a tile, e.g., `{'char': '#', 'is_wall': True}`.
*   `game.get_entity_properties(target_entity_id: str) -> dict | None`: Get properties of another entity.
*   `game.get_entities_in_radius(radius: int, target_type: str = None, target_faction: str = None) -> list[dict]`: Finds entities within a radius, with optional filters.
*   `game.analyze_tile_code(x: int, y: int) -> Optional[dict]`: (Not fully detailed here, relates to harvesting)
*   `game.harvest_tile(x: int, y: int, time_to_harvest: int = 1) -> Optional[dict]`: (Not fully detailed here, relates to harvesting)

### Faction Mechanics
*   `game.get_entity_faction(entity_id: str) -> Optional[str]`: (Mistake in design, should be `get_self_property('faction_id')` or `get_entity_properties(id).get('faction_id')`. This specific function might not exist as a top-level call for *any* entity, usually it's for self or a specific target whose properties you fetch.)
    *   *Correction:* Use `game.get_self_property('faction_id')` for own faction. For others: `props = game.get_entity_properties('other_id'); faction = props.get('faction_id') if props else None`.
*   `game.get_tile_faction_owner(x: int, y: int) -> Optional[str]`: (Not fully detailed here, assumes tiles can have faction ownership properties)
*   `game.broadcast_message(message: any, radius: Optional[int] = None, target_faction: Optional[str] = None)`: Send a message to other entities.

### Spawning (for Spawner-type entities)
*   `game.spawn_entity(type: str, x: int, y: int, sprite_char: str, properties: dict) -> Optional[str]`: Allows an entity (if capable) to spawn new entities. Returns new entity's ID or `None`.

### Communication & Logging
*   `game.log_message(message: str)`: Logs a message to the entity's script action log (visible in main game log, prefixed by entity ID).

### External System Hooks (Placeholders)
*   `game.call_procast_engine(task_type: str, params: dict) -> dict`:
    *   **Future Purpose:** Interface with an external "ProcastEngine" for procedural tasks, events, or narrative elements.
    *   **Current Behavior:** Logs the call. Returns a dummy dictionary like `{"task_id": "proc_...", "status": "pending_conceptual_execution", ...}`.
    *   **Example:** `event_data = game.call_procast_engine("spawn_anomaly", {"intensity": 0.8})`
*   `game.get_zero_gears_state(component_id: str) -> dict`:
    *   **Future Purpose:** Query the state of complex "ZeroGears" machinery or systems.
    *   **Current Behavior:** Logs the call. Returns a dummy dictionary like `{"component_id": component_id, "status": "nominal_placeholder", "energy_level": 0.75, ...}`.
    *   **Example:** `gear_status = game.get_zero_gears_state("main_reactor_core")`

---
*Note: This API is subject to change and expansion as Labyrinth2D evolves.*
