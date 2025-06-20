# player_scripts/entities/master_spawner_logic.py
import random # Assuming 'random' is available in entity script sandbox

def on_tick():
    # 'game' is the RuntimeGameAPI instance

    # Initialize properties if they don't exist
    if game.get_self_property("tick_count") is None:
        game.set_self_property("tick_count", 0)
    if game.get_self_property("current_spawn_index") is None:
        game.set_self_property("current_spawn_index", 0)

    # Increment tick count
    current_ticks = game.get_self_property("tick_count")
    game.set_self_property("tick_count", current_ticks + 1)

    # Get spawner's properties
    my_props = game.get_self_properties()
    spawn_interval = my_props.get("spawn_interval_ticks", 100) # Default to 100 ticks

    if current_ticks % spawn_interval != 0:
        return # Not time to spawn yet

    game.log_message(f"MasterSpawner '{game.get_self_id()}' attempting to spawn.")

    max_units = my_props.get("max_active_units", 5)
    my_faction = my_props.get("faction_id", "neutral")

    faction_units = 0
    all_entities_in_room = game.get_entities_in_radius(radius=100)
    for entity_data in all_entities_in_room:
        if entity_data.get("faction_id") == my_faction and entity_data.get("id") != game.get_self_id():
            faction_units += 1

    game.log_message(f"MasterSpawner '{game.get_self_id()}' counts {faction_units} units for faction '{my_faction}'. Max allowed: {max_units}")

    if faction_units >= max_units:
        game.log_message(f"MasterSpawner '{game.get_self_id()}' at unit capacity ({faction_units}/{max_units}).")
        return

    spawn_list = my_props.get("spawn_list")
    if not spawn_list or not isinstance(spawn_list, list) or len(spawn_list) == 0:
        game.log_message("MasterSpawner Error: 'spawn_list' property is missing, empty, or not a list.")
        return

    current_spawn_idx = game.get_self_property("current_spawn_index")
    unit_to_spawn_template = spawn_list[current_spawn_idx]

    potential_spawns = []
    for dy_offset in [-1, 0, 1]:
        for dx_offset in [-1, 0, 1]:
            if dx_offset == 0 and dy_offset == 0: continue
            px, py = my_props["x"] + dx_offset, my_props["y"] + dy_offset
            if 0 <= px < game.GRID_WIDTH and 0 <= py < game.GRID_HEIGHT:
                 tile_info = game.get_tile_info(px,py)
                 is_occupied = False
                 # Check only exact spot for existing entities
                 entities_at_spawn_spot = game.get_entities_in_radius(radius=0) # This needs to be centered on px, py not self
                 # Correction: get_entities_in_radius is centered on self.
                 # A direct game.get_entities_at(px, py) would be better if it exists.
                 # For now, let's iterate all entities and check coords.
                 all_ents = game.get_entities_in_radius(radius=100) # Get all entities
                 for ent_data_nearby in all_ents:
                     if ent_data_nearby['x'] == px and ent_data_nearby['y'] == py:
                         is_occupied = True
                         break
                 if not tile_info.get('is_wall') and not is_occupied:
                     potential_spawns.append((px,py))

    if not potential_spawns:
        game.log_message(f"MasterSpawner '{game.get_self_id()}' found no valid spawn location nearby.")
        return

    final_spawn_x, final_spawn_y = random.choice(potential_spawns)

    spawned_unit_properties = unit_to_spawn_template.get("properties", {}).copy()
    spawned_unit_properties["faction_id"] = my_props.get("faction_id", "neutral")

    # Assuming game.spawn_entity exists in RuntimeGameAPI and generates a unique ID if none provided
    # Or, the script should generate a unique ID. For simplicity, let's assume game.spawn_entity handles it or one isn't strictly needed by it.
    # The example in prompt quest used a constructed ID.
    new_entity_id = f"{my_props.get('faction_id','e')}_{game.get_self_id()}_{current_ticks}_{current_spawn_idx}"


    spawn_success = game.spawn_entity(
        # entity_id=new_entity_id, # If API supports/requires it
        type=unit_to_spawn_template.get("type", "bot"),
        x=final_spawn_x,
        y=final_spawn_y,
        sprite_char=unit_to_spawn_template.get("char", "?"),
        properties=spawned_unit_properties
    )

    if spawn_success:
        game.log_message(f"MasterSpawner '{game.get_self_id()}' successfully spawned unit '{unit_to_spawn_template.get('template_id_ref', 'unknown_type')}' at ({final_spawn_x},{final_spawn_y}).")
        game.set_self_property("current_spawn_index", (current_spawn_idx + 1) % len(spawn_list))
    else:
        game.log_message(f"MasterSpawner '{game.get_self_id()}' FAILED to spawn unit at ({final_spawn_x},{final_spawn_y}). Position might be blocked or invalid by game rule.")
