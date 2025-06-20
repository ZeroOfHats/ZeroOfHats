from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Game state
base_game_map = [
    "##########",
    "#........#", # Player 'P' will be overlaid
    "#........#",
    "#..#.....#", # Added a wall for testing
    "#........#",
    "#.....#..#", # Added a wall for testing
    "#........#",
    "#........#",
    "#........#",
    "##########"
]
player_pos = {'x': 1, 'y': 1} # Player's initial position
entities = {} # To store entities: entity_id -> {type, x, y, sprite_char, properties}

def get_display_map():
    """Creates a displayable map with the player 'P' and entities overlaid."""
    display_map_list = [list(row) for row in base_game_map]

    # Overlay entities first
    for entity_id, entity in entities.items():
        if 0 <= entity['y'] < len(display_map_list) and \
           0 <= entity['x'] < len(display_map_list[0]):
            # Ensure entity does not overwrite player if at same spot, player is drawn last.
            # This simple check means player will always be on top.
            if not (entity['x'] == player_pos['x'] and entity['y'] == player_pos['y']):
                 display_map_list[entity['y']][entity['x']] = entity['sprite_char']

    # Overlay player 'P'
    if 0 <= player_pos['y'] < len(display_map_list) and \
       0 <= player_pos['x'] < len(display_map_list[0]):
        display_map_list[player_pos['y']][player_pos['x']] = 'P'

    return ["".join(row) for row in display_map_list]

@app.route('/')
def index():
    return render_template('index.html', game_map=get_display_map(), player_pos=player_pos)

@app.route('/move/<direction>', methods=['POST'])
def move(direction):
    global player_pos # We are modifying the global player_pos

    original_y, original_x = player_pos['y'], player_pos['x']

    # Update player position based on direction
    if direction == 'up': # Corresponds to 'w' or ArrowUp
        player_pos['y'] -= 1
    elif direction == 'down': # Corresponds to 's' or ArrowDown
        player_pos['y'] += 1
    elif direction == 'left': # Corresponds to 'a' or ArrowLeft
        player_pos['x'] -= 1
    elif direction == 'right': # Corresponds to 'd' or ArrowRight
        player_pos['x'] += 1

    # Boundary checks and collision detection
    map_height = len(base_game_map)
    map_width = len(base_game_map[0])

    # Y-axis wrapping
    if player_pos['y'] < 0:
        player_pos['y'] = map_height - 1
    elif player_pos['y'] >= map_height:
        player_pos['y'] = 0

    # X-axis blocking at boundaries (for now)
    if player_pos['x'] < 0:
        player_pos['x'] = 0
    elif player_pos['x'] >= map_width:
        player_pos['x'] = map_width - 1

    # Collision detection with walls ('#')
    # Check the character at the new position in the base_game_map (for walls)
    if base_game_map[player_pos['y']][player_pos['x']] == '#':
        player_pos['y'], player_pos['x'] = original_y, original_x # Revert move
        return jsonify({"game_map": get_display_map(), "player_pos": player_pos, "message": "Blocked by a wall."})

    # Check for collision with entities (simple version: cannot move onto an entity's tile)
    # More complex interactions (e.g., picking up items, talking to NPCs) would require more logic.
    for entity_id, entity in entities.items():
        if player_pos['x'] == entity['x'] and player_pos['y'] == entity['y']:
            # For now, block movement. Later, this could trigger interaction.
            player_pos['y'], player_pos['x'] = original_y, original_x # Revert move
            return jsonify({
                "game_map": get_display_map(),
                "player_pos": player_pos,
                "message": f"Cannot move onto tile occupied by {entity.get('type', 'entity')} ({entity_id})."
            })

    return jsonify({"game_map": get_display_map(), "player_pos": player_pos, "message": "Move successful."})

@app.route('/entity/add', methods=['POST'])
def add_entity():
    data = request.json
    entity_id = data.get('entity_id')
    if not entity_id:
        return jsonify({"error": "entity_id is required"}), 400
    if entity_id in entities:
        return jsonify({"error": f"Entity with ID {entity_id} already exists"}), 400

    # Basic validation for required fields
    required_fields = ['type', 'x', 'y', 'sprite_char']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        x = int(data['x'])
        y = int(data['y'])
    except ValueError:
        return jsonify({"error": "x and y must be integers"}), 400


    # Ensure entity is within map bounds and not on a wall
    map_height = len(base_game_map)
    map_width = len(base_game_map[0])
    if not (0 <= y < map_height and 0 <= x < map_width):
        return jsonify({"error": "Entity position out of map bounds"}), 400
    if base_game_map[y][x] == '#':
        return jsonify({"error": "Cannot place entity on a wall"}), 400
    # Check if player is already at this position
    if x == player_pos['x'] and y == player_pos['y']:
        return jsonify({"error": "Cannot place entity on player's current position"}), 400
    # Check if another entity is already at this position
    for existing_id, existing_entity in entities.items():
        if existing_entity['x'] == x and existing_entity['y'] == y:
            return jsonify({"error": f"Another entity ({existing_id}) already at this position"}), 400


    entities[entity_id] = {
        "type": data['type'],
        "x": x,
        "y": y,
        "sprite_char": data['sprite_char'],
        "properties": data.get('properties', {})
    }
    return jsonify({"message": f"Entity {entity_id} added successfully", "entities": entities, "game_map": get_display_map()}), 201


# Placeholder for remove_entity - to be implemented next
@app.route('/entity/remove/<entity_id>', methods=['POST']) # Using POST for consistency, could be DELETE
def remove_entity(entity_id):
    if entity_id in entities:
        del entities[entity_id]
        return jsonify({"message": f"Entity {entity_id} removed", "entities": entities, "game_map": get_display_map()})
    else:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

@app.route('/entity/property/<entity_id>/<property_name>', methods=['GET'])
def get_entity_property(entity_id, property_name):
    if entity_id not in entities:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

    entity = entities[entity_id]
    if 'properties' not in entity or property_name not in entity['properties']:
        return jsonify({"error": f"Property {property_name} not found on entity {entity_id}"}), 404

    return jsonify({
        "entity_id": entity_id,
        "property_name": property_name,
        "value": entity['properties'][property_name]
    })

@app.route('/entity/property/<entity_id>/<property_name>', methods=['POST'])
def set_entity_property(entity_id, property_name):
    if entity_id not in entities:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

    data = request.json
    if 'value' not in data:
        return jsonify({"error": "Value not provided in request body"}), 400

    entity = entities[entity_id]
    if 'properties' not in entity: # Should not happen if entity was added via add_entity
        entity['properties'] = {} # Ensure 'properties' dict exists

    entity['properties'][property_name] = data['value']

    return jsonify({
        "message": f"Property {property_name} set on entity {entity_id}",
        "entity": entity
    })

@app.route('/entity/script/<entity_id>', methods=['POST'])
def set_entity_script(entity_id):
    if entity_id not in entities:
        return jsonify({"error": f"Entity {entity_id} not found"}), 404

    data = request.json
    if 'script_code' not in data:
        return jsonify({"error": "script_code not provided in request body"}), 400

    entities[entity_id]['script_code'] = data['script_code']

    return jsonify({
        "message": f"Script set for entity {entity_id}",
        "entity_id": entity_id,
        "script_code": data['script_code']
    })

@app.route('/grid/cell/<int:x>/<int:y>', methods=['GET'])
def get_grid_cell(x, y):
    map_height = len(base_game_map)
    map_width = len(base_game_map[0])

    if not (0 <= y < map_height and 0 <= x < map_width):
        return jsonify({"error": "Coordinates out of map bounds"}), 404

    cell_info = {
        "x": x,
        "y": y,
        "base_char": base_game_map[y][x],
        "is_player": False,
        "entity": None
    }

    if player_pos['x'] == x and player_pos['y'] == y:
        cell_info['is_player'] = True

    for entity_id, entity_data in entities.items():
        if entity_data['x'] == x and entity_data['y'] == y:
            cell_info['entity'] = {
                "id": entity_id,
                "type": entity_data['type'],
                "sprite_char": entity_data['sprite_char']
            }
            # If an entity is here, and the player is also here,
            # the game.get_display_map() logic draws player on top.
            # For cell info, it's useful to know both can be there.
            break # Assuming one entity per cell for simplicity in this basic version

    return jsonify(cell_info)

# Game Log / Message Display
# This is a very simple version. A real game might use a list, logging, WebSockets, etc.
last_game_message = ""

@app.route('/game/message', methods=['POST'])
def display_message():
    global last_game_message
    data = request.json
    if 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    last_game_message = data['message']
    # In a real app, this message might be broadcast to UIs or logged more formally.
    # For now, we just acknowledge receipt and what was "displayed".
    return jsonify({"message_received": last_game_message, "status": "Message displayed (logged by server)"})

@app.route('/game/last_message', methods=['GET'])
def get_last_message():
    # Helper endpoint for testing, to see what the last message was.
    return jsonify({"last_message": last_game_message})

# Script Execution Endpoint
import io
import sys
import traceback
from game_api import sample_game_api_function, get_player_position as api_get_player_position

@app.route('/script/execute', methods=['POST'])
def execute_script():
    data = request.json
    script_code = data.get('script_code')

    if not script_code:
        return jsonify({"error": "No script_code provided"}), 400

    # Prepare a restricted global scope for exec
    # For now, only provide a custom print and a sample game API function
    # Later, this will be expanded with more game functions and RestrictedPython

    script_output_buffer = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = script_output_buffer

    # Make game functions available in the script's scope
    # A more complete set of safe builtins should be provided.
    # For now, let's add common exceptions to allow try/except blocks.
    # This is still not full sandboxing. RestrictedPython will be better.
    safe_builtins = {
        "print": lambda *args, **kwargs: print(*args, file=sys.stdout, **kwargs),
        "Exception": Exception,
        "NameError": NameError,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "ZeroDivisionError": ZeroDivisionError,
        # Commonly used functions that are generally safe:
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "range": range,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "bool": bool,
        "None": None,
        "True": True,
        "False": False,
    }

    # game_object will simulate the `game.` prefix for API calls from scripts
    # We use lambdas here to pass the current game state from app.py to the API functions
    # when they are called from the script.
    game_object = {
        "get_player_position": lambda: api_get_player_position(player_pos),
        "sample_function": sample_game_api_function, # This one doesn't need state
        # Add other refactored game API functions here, wrapping them with lambdas
        # if they need access to app.py's game state (player_pos, entities, base_game_map)
    }

    script_globals = {
        "__builtins__": safe_builtins,
        "game": game_object, # Expose the game object to the script
        # "game_api_call" can be removed once sample_function is part of game_object fully.
        "game_api_call": sample_game_api_function,
    }

    try:
        exec(script_code, script_globals)
        output = script_output_buffer.getvalue()
        # Potentially capture return value of the script if it's an expression
        # For now, focusing on print output and side effects
        return jsonify({"output": output, "status": "Script executed successfully"})
    except Exception as e:
        error_info = traceback.format_exc()
        output = script_output_buffer.getvalue() # Get any output before the error
        return jsonify({"error": str(e), "traceback": error_info, "output": output, "status": "Script execution failed"}), 500
    finally:
        sys.stdout = original_stdout # Restore stdout


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
