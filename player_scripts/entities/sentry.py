# player_scripts/entities/sentry.py

def on_tick():
    game.log_message("Sentry standing guard...")

    self_props = game.get_self_properties()
    # game.log_message(f"My properties: {self_props}") # For debugging

    # Example: Look for player entity
    player_pos = game.get_player_position() # Returns (x,y) or None

    if player_pos and self_props: # self_props should always exist if script is running for self
        dist_sq = (self_props['x'] - player_pos[0])**2 + (self_props['y'] - player_pos[1])**2
        if dist_sq < 5**2: # If player is within 5 tiles (distance squared for efficiency)
             game.log_message("Player detected nearby!")

    my_faction = game.get_self_property("faction_id")
    if my_faction:
        game.log_message(f"My faction is '{my_faction}'.")
    else:
        game.log_message("I have no faction property.")
