# player_scripts/entities/random_walker.py
# Note: Python's 'random' is made available in the sandbox for entity scripts.
# If you need game-world seeded random, game.get_random_int() would need to be part of RuntimeGameAPI
import random

def on_tick():
    # 'game' is the RuntimeGameAPI instance, injected by the execution environment
    dx = random.randint(-1, 1)
    dy = random.randint(-1, 1)

    if dx != 0 or dy != 0:
        moved = game.move_self(dx, dy)
        if moved:
            game.log_message(f"Randomly moved ({dx},{dy}).")
        # else: # Optional: log failed moves, can be spammy
            # game.log_message(f"Random move ({dx},{dy}) failed.")
    # else: # Optional: log decision not to move
        # game.log_message("Decided not to move.")

    # Example of using another API
    # nearby = game.get_entities_in_radius(3) # Assuming radius is in tile units
    # if nearby:
    #     game.log_message(f"Found {len(nearby)} entities within 3 tiles.")
