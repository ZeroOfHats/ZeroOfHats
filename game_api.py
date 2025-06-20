# Placeholder for game API functions that can be called by scripts
# For now, this file is empty.
# Functions like move_player, add_entity etc. will be refactored
# to be usable by both Flask routes and the script execution environment.

def sample_game_api_function():
    print("Sample game API function was called by an executed script.")
    return "Success from sample_game_api_function"

# TODO:
# - Move game logic from app.py routes into functions here.
# - Make these functions accessible to scripts run via exec().
# - Ensure player_pos, entities, base_game_map are accessible/modifiable safely.

# Game state variables will be passed as arguments to these functions.

def get_player_position(current_player_pos):
    """Returns the player's current coordinates."""
    return dict(current_player_pos) # Return a copy

# More functions will be added here:
# move_player(current_player_pos, direction, base_map, current_entities)
# add_entity(current_entities, entity_id, type, x, y, sprite_char, properties={})
# remove_entity(entity_id)
# set_entity_script(entity_id, script_code_string) # This one might stay in app.py or be a wrapper
# get_entity_property(entity_id, property_name)
# set_entity_property(entity_id, property_name, value)
# get_grid_cell(x, y)
# display_message(message_string)
