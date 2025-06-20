from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- Game State (Very Basic - In-Memory) ---
WORLD_WIDTH = 30
WORLD_HEIGHT = 20
world_map = [['.' for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]

for i in range(WORLD_WIDTH):
    world_map[0][i] = '#'
    world_map[WORLD_HEIGHT-1][i] = '#'
for i in range(WORLD_HEIGHT):
    world_map[i][0] = '#'
    world_map[i][WORLD_WIDTH-1] = '#'

world_map[5][15] = '#'

player_pos = {'x': 15, 'y': 10}
entities = {} # id: {type, x, y, sprite_char, properties, script_code}
game_messages_log = [] # For messages from game.display_message()

# --- Game API Functions ---

def get_player_position_api():
    # Returns a copy to prevent direct modification of internal state dict
    return dict(player_pos)

def move_player_api(direction_str):
    # This is a simplified version for API call.
    # A more advanced refactor would have a core movement function used by both this and the HTTP route.
    global player_pos # Ensure we are modifying the global
    dx, dy = 0, 0
    current_x, current_y = player_pos['x'], player_pos['y']

    if direction_str == 'left':
        dx = -1
    elif direction_str == 'right':
        dx = 1
    else:
        # display_message_api(f"API Error: Invalid direction '{direction_str}' for move_player_api.")
        return False # Invalid direction

    new_x, new_y = current_x + dx, current_y + dy
    original_new_y = new_y # Store Y before boundary clamp for checking if X-wrap caused Y OOB

    # X-axis wrapping logic
    if new_x >= WORLD_WIDTH:
        new_x = 0
        new_y += 1
    elif new_x < 0:
        new_x = WORLD_WIDTH - 1
        new_y -= 1

    # Y-axis boundary clamp and message handling
    y_boundary_hit = False
    if new_y >= WORLD_HEIGHT:
        new_y = WORLD_HEIGHT - 1
        if original_new_y != new_y: new_x = current_x # Block X if Y was changed by X-wrap OOB
        y_boundary_hit = True
    elif new_y < 0:
        new_y = 0
        if original_new_y != new_y: new_x = current_x # Block X if Y was changed by X-wrap OOB
        y_boundary_hit = True

    # Collision detection
    if world_map[new_y][new_x] == '#':
        # display_message_api("API: Blocked by a wall!")
        return False
    if any(e['x'] == new_x and e['y'] == new_y for e_id, e in entities.items()):
        # display_message_api("API: Blocked by an entity!")
        return False

    # If Y boundary was hit, but it wasn't a wall or entity, it's just edge of world.
    # The position (new_x, new_y) is already clamped.
    # if y_boundary_hit:
        # display_message_api("API: You've reached the edge of the known world.")
        # No specific message here, let script decide based on False from further moves

    player_pos['x'], player_pos['y'] = new_x, new_y
    # display_message_api(f"API: Moved {direction_str} to ({new_x},{new_y})")
    return True # Success

def add_entity_api(entity_id, type_str, x, y, sprite_char, properties_dict=None):
    global entities # Ensure modification of global
    if entity_id in entities:
        display_message_api(f"API Error: Entity ID '{entity_id}' already exists.")
        return False
    if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
        display_message_api(f"API Error: Entity coordinates ({x},{y}) out of bounds.")
        return False
    if world_map[y][x] == '#':
        display_message_api(f"API Error: Cannot place entity on a wall at ({x},{y}).")
        return False

    # Optional: Check if another entity is already at x,y
    if any(e['x'] == x and e['y'] == y for e_id, e in entities.items()):
        display_message_api(f"API Error: Another entity already at ({x},{y}).")
        return False

    entities[entity_id] = {
        'type': type_str,
        'x': x,
        'y': y,
        'sprite_char': sprite_char,
        'properties': properties_dict if properties_dict is not None else {},
        'script_code': None
    }
    display_message_api(f"API: Entity '{entity_id}' ({sprite_char}) added at ({x},{y}).")
    return True

def remove_entity_api(entity_id):
    global entities # Ensure modification of global
    if entity_id in entities:
        del entities[entity_id]
        display_message_api(f"API: Entity '{entity_id}' removed.")
        return True
    display_message_api(f"API Error: Entity '{entity_id}' not found for removal.")
    return False

def set_entity_script_api(entity_id, script_code_str):
    global entities # Ensure modification of global
    if entity_id in entities:
        entities[entity_id]['script_code'] = script_code_str
        display_message_api(f"API: Script set for entity '{entity_id}'.")
        return True
    display_message_api(f"API Error: Entity '{entity_id}' not found for setting script.")
    return False

def get_entity_property_api(entity_id, property_name_str):
    if entity_id in entities and 'properties' in entities[entity_id] and \
       property_name_str in entities[entity_id]['properties']:
        return entities[entity_id]['properties'][property_name_str]
    # display_message_api(f"API Warning: Property '{property_name_str}' not found for entity '{entity_id}'.")
    return None

def set_entity_property_api(entity_id, property_name_str, value):
    global entities # Ensure modification of global
    if entity_id in entities:
        if 'properties' not in entities[entity_id] or entities[entity_id]['properties'] is None:
            entities[entity_id]['properties'] = {}
        entities[entity_id]['properties'][property_name_str] = value
        display_message_api(f"API: Property '{property_name_str}' set for entity '{entity_id}'.")
        return True
    display_message_api(f"API Error: Entity '{entity_id}' not found for setting property.")
    return False

def get_grid_cell_api(x, y):
    if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
        # display_message_api(f"API Warning: get_grid_cell coordinates ({x},{y}) out of bounds.")
        return None

    for entity_id, entity_data in entities.items():
        if entity_data['x'] == x and entity_data['y'] == y:
            return {
                'type': 'entity',
                'entity_id': entity_id,
                'char': entity_data['sprite_char'],
                'entity_type': entity_data['type']
            }

    if player_pos['x'] == x and player_pos['y'] == y:
        return {'type': 'player', 'char': '@'}

    map_char = world_map[y][x]
    tile_type = 'wall' if map_char == '#' else 'floor'
    return {'type': tile_type, 'char': map_char}

def display_message_api(message_str):
    global game_messages_log # Ensure modification of global
    # This log is for script-generated messages that should be returned to the UI
    game_messages_log.append(str(message_str))
    print(f"GAME_API_MESSAGE_INTERNAL: {message_str}") # For server console log

# --- End Game API Functions ---

def get_10x10_grid_view(center_x, center_y):
    """
    Extracts a view from the world_map.
    This version uses player_pos as the top-left of the view for simplicity.
    """
    segment_x_start = (center_x // 10) * 10
    segment_y_start = (center_y // 10) * 10

    grid_lines = []
    for r_idx in range(10):
        y = segment_y_start + r_idx
        line = []
        for c_idx in range(10):
            x = segment_x_start + c_idx
            if 0 <= y < WORLD_HEIGHT and 0 <= x < WORLD_WIDTH:
                char_to_display = world_map[y][x]
                entity_at_loc = None
                for entity_id, entity_data in entities.items():
                    if entity_data['x'] == x and entity_data['y'] == y:
                        entity_at_loc = entity_data
                        break
                if entity_at_loc:
                    char_to_display = entity_at_loc['sprite_char']

                if x == player_pos['x'] and y == player_pos['y']:
                    char_to_display = '@'
                line.append(char_to_display)
            else:
                line.append(' ')
        grid_lines.append("".join(line))
    return "\n".join(grid_lines)

@app.route('/')
def index():
    initial_grid_str = get_10x10_grid_view(player_pos['x'], player_pos['y'])
    # Player position for UI display (absolute world coordinates)
    return render_template('index.html',
                           initial_grid=initial_grid_str,
                           player_x=player_pos['x'],
                           player_y=player_pos['y'])

@app.route('/move/<direction>', methods=['POST'])
def move_player_route(direction):
    global player_pos
    dx, dy = 0, 0
    current_x, current_y = player_pos['x'], player_pos['y']

    if direction == 'left':
        dx = -1
    elif direction == 'right':
        dx = 1

    new_x, new_y = current_x + dx, current_y + dy

    # X-axis wrapping logic
    if new_x >= WORLD_WIDTH:
        new_x = 0 # Leftmost x in next room segment
        new_y += 1 # Move to next row of rooms
    elif new_x < 0:
        new_x = WORLD_WIDTH - 1 # Rightmost x in previous room segment
        new_y -= 1 # Move to previous row of rooms

    message_to_user = ""
    final_x, final_y = new_x, new_y # Start with proposed new coordinates

    # Y-axis boundary check (block, don't wrap Y for now)
    y_boundary_clamped = False
    if final_y >= WORLD_HEIGHT:
        final_y = WORLD_HEIGHT - 1
        message_to_user = "You've reached the southern edge of the known world."
        if current_y != final_y : # If Y changed due to X-wrap that pushed it out of bounds
             final_x = current_x # Reset X to original, effectively blocking Y change from X-wrap
        y_boundary_clamped = True
    elif final_y < 0:
        final_y = 0
        message_to_user = "You've reached the northern edge of the known world."
        if current_y != final_y : # If Y changed due to X-wrap that pushed it out of bounds
            final_x = current_x # Reset X to original
        y_boundary_clamped = True

    # Collision detection with walls '#' at the (potentially Y-clamped) final_x, final_y
    if world_map[final_y][final_x] == '#':
        message_to_user = "Blocked by a wall!" # Wall message takes precedence if collision occurs
        final_x, final_y = current_x, current_y # Revert to original position
    # Collision detection with entities
    elif any(e['x'] == final_x and e['y'] == final_y for e_id, e in entities.items()):
        message_to_user = "Blocked by an entity!" # Entity collision message takes precedence
        final_x, final_y = current_x, current_y # Revert to original position

    # If no message was set by boundaries or collisions, it was a successful move relative to those checks
    if not message_to_user:
        message_to_user = f"Moved {direction} to ({final_x},{final_y})"

    player_pos['x'], player_pos['y'] = final_x, final_y

    grid_str = get_10x10_grid_view(player_pos['x'], player_pos['y'])
    return jsonify({
        'grid': grid_str,
        'player_pos': player_pos, # Absolute world position
        'message': message_to_user
    })

# Placeholder for /run_script
@app.route('/run_script', methods=['POST'])
def run_script_route():
    global game_messages_log # Ensure we can modify it
    game_messages_log = [] # Clear log for this script run

    data = request.get_json()
    code = data.get('code', '')

    # --- This is where the actual script execution will happen later ---
    # For now, simulate some API calls based on code content for testing
    output = f"Simulating execution of: {code[:100]}..."
    error_msg = ""
    tb = ""

    if "error_test" in code.lower():
        output = ""
        error_msg = "Simulated error from script!"
        tb = "Traceback: /script_execution_context.py:line 123: TestError: Something went wrong."
        display_message_api("This message should not appear if error stops execution.")
    elif "add_goblin" in code.lower():
        add_entity_api("goblin1", "monster", player_pos['x']+1, player_pos['y'], 'G', {'health':10})
        display_message_api("Goblin added via script (simulated).")
    elif "move_left" in code.lower():
        move_player_api("left")
        display_message_api("Player moved left via script (simulated).")
    elif "show_player_pos" in code.lower():
        pos = get_player_position_api()
        display_message_api(f"Player is at {pos['x']},{pos['y']}")
    # --- End of simulation block ---

    # Return any messages generated by display_message_api during this script's execution
    # The actual script execution environment will need to collect these.
    # For this placeholder, we use the global game_messages_log that API functions populate.
    script_generated_messages = list(game_messages_log) # Copy the collected messages

    return jsonify({
        'output': output,
        'error': error_msg,
        'traceback': tb,
        'message_log': script_generated_messages
    })

# Placeholder for /rag_query
@app.route('/rag_query', methods=['POST'])
def rag_query_route():
    data = request.get_json()
    query = data.get('query', '')
    suggestions = []
    if "move" in query.lower():
        suggestions.append({
            "type": "code_snippet",
            "title": "Move Player Right Example",
            "content": "game.move_player('right')"
        })
        suggestions.append({
            "type": "explanation",
            "title": "Player Movement API",
            "content": "Use game.move_player(direction). Valid directions are 'left' and 'right'."
        })
    elif "add entity" in query.lower():
        suggestions.append({
            "type": "code_snippet",
            "title": "Add a Goblin",
            "content": "game.add_entity('goblin1', 'monster', 10, 5, 'G', {'health': 10})"
        })
    else:
        suggestions.append({
            "type": "explanation",
            "title": "Query Not Understood",
            "content": "Sorry, I can only provide specific help for 'move' or 'add entity' queries for now."
        })
    return jsonify({'suggestions': suggestions})

if __name__ == '__main__':
    # This is for direct execution (python app/__init__.py)
    # For production, use a WSGI server like Gunicorn, typically via main.py
    app.run(debug=True, port=5001)
