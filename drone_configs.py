"""
Defines the configurations for all available drones in the game.
Each drone has a unique ID (the key in DRONE_DATA), a display name,
paths to its sprite and icon, base statistics, an unlock condition,
and a descriptive text.
"""
from game_settings import PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED

# Main dictionary holding all drone configurations
DRONE_DATA = {
    "ORIGINAL_DRONE": {
        "name": "Drone",
        "sprite_path": None, # This is used for the selection screen main display, keep as is or point to a preview image
        "icon_path": "assets/drones/original_icon.png", # For UI icons like lives
        "ingame_sprite_path": "assets/drones/original_drone_2d.png", # <--- NEW: Assuming you have one, or it can be None to use fallback
        "base_stats": { # Base statistics for this drone
            # ...
        },
        "unlock_condition": {"type": "default", "value": None, "description": "Unlocked by default."},
        "description": "The reliable, battle-tested original drone. Balanced and versatile for any mission.",
    },
    "VANTIS": {
        "name": "VANTIS",
        "sprite_path": "assets/drones/vantis.png", # Selection screen preview
        "icon_path": "assets/drones/vantis.png",   # UI icon
        "ingame_sprite_path": "assets/drones/vantis_2d.png", # <--- NEW: Path to your in-game sprite
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "level", "value": 3, "description": "Unlock: Reach Level 3"},
        "description": "Sleek triangular stealth drone. A good all-rounder with balanced statistics.",
    },
    "RHINOX": {
        "name": "RHINOX",
        "sprite_path": "assets/drones/rhinox.png", # Selection screen preview
        "icon_path": "assets/drones/rhinox.png",   # UI icon
        "ingame_sprite_path": "assets/drones/rhinox_2d.png", # <--- NEW
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "cores", "value": 1000, "description": "Unlock: 1000 Cores"},
        "description": "Broad heavy armor-plated drone. Trades speed for high HP and resilience.",
    },
    "ZEPHYR": {
        "name": "ZEPHYR",
        "sprite_path": "assets/drones/zephyr.png", # Selection screen preview
        "icon_path": "assets/drones/zephyr.png",   # UI icon
        "ingame_sprite_path": "assets/drones/zephyr_2d.png", # <--- NEW
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "level", "value": 10, "description": "Unlock: Reach Level 10"},
        "description": "Lightweight quad-rotor frame. Excels in speed and agility but is more fragile.",
    },
    "STRIX": {
        "name": "STRIX",
        "sprite_path": "assets/drones/strix.png", # Selection screen preview
        "icon_path": "assets/drones/strix.png",   # UI icon
        "ingame_sprite_path": "assets/drones/strix_2d.png", # <--- NEW
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "boss", "value": "MAZE_GUARDIAN", "description": "Unlock: Defeat Maze Guardian"},
        "description": "Sharp, agile bird-like drone. Known for its exceptional maneuverability.",
    },
    "OMEGA-9": {
        "name": "OMEGA-9",
        "sprite_path": "assets/drones/omega-9.png", # Selection screen preview
        "icon_path": "assets/drones/omega-9.png",   # UI icon
        "ingame_sprite_path": "assets/drones/omega-9_2d.png", # <--- NEW
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "level", "value": 20, "description": "Unlock: Reach Level 20"},
        "description": "Futuristic experimental drone. Unstable: its core stats are randomized each run.",
    },
    "PHANTOM": {
        "name": "PHANTOM",
        "sprite_path": "assets/drones/phantom.png", # Selection screen preview
        "icon_path": "assets/drones/phantom.png",   # UI icon
        "ingame_sprite_path": "assets/drones/phantom_2d.png", # <--- NEW
        "base_stats": {
            # ...
        },
        "unlock_condition": {"type": "cores", "value": 50000, "description": "Unlock: 50000 Cores"},
        "description": "Features a shimmer-based cloaking device. Can briefly turn invisible but is delicate.",
    },
    # ... Add for any other drones ...
}

# Define the order in which drones appear in the selection screen
# This should include all keys from DRONE_DATA that are meant to be selectable.
DRONE_DISPLAY_ORDER = [
    "ORIGINAL_DRONE",
    "VANTIS",
    "RHINOX",
    "ZEPHYR",
    "STRIX",
    "OMEGA-9",
    "PHANTOM"
]

# --- Special Ability Constants ---

# Phantom Cloak Ability
PHANTOM_CLOAK_DURATION_MS = 5000  # Duration of cloak in milliseconds (5 seconds)
PHANTOM_CLOAK_COOLDOWN_MS = 15000 # Cooldown after cloak ends in milliseconds (15 seconds)
PHANTOM_CLOAK_ALPHA = 70 # Alpha value (0-255) when cloaked (lower is more transparent)

# Omega-9 Stat Randomization Ranges
# These are multipliers applied to Omega-9's base stats at the start of a run.
OMEGA_STAT_RANGES = {
    "hp": (0.7, 1.5), # HP can be 70% to 150% of its base
    "speed": (0.8, 1.3), # Speed can be 80% to 130% of its base
    "turn_speed": (0.9, 1.2), # Turn speed can be 90% to 120% of its base
    "fire_rate_multiplier": (0.7, 1.3) # Fire rate can be 30% faster to 30% slower
}

# Ensure all drones in DRONE_DISPLAY_ORDER are defined in DRONE_DATA
# This is a sanity check that can be useful during development.
for drone_id_ordered in DRONE_DISPLAY_ORDER:
    if drone_id_ordered not in DRONE_DATA:
        print(f"Warning (drone_configs.py): Drone ID '{drone_id_ordered}' found in DRONE_DISPLAY_ORDER but not in DRONE_DATA.")
