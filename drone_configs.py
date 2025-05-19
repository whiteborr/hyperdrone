"""
Defines the configurations for all available drones in the game.
Each drone has a unique ID (the key in DRONE_DATA), a display name,
paths to its sprite and icon, base statistics, an unlock condition,
and a descriptive text.
"""

# Import necessary constants from game_settings for default drone values
# This helps keep base stats for the Original Drone consistent with general player settings.
try:
    from game_settings import PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED
except ImportError:
    # Fallback values if game_settings.py is not available during direct import (e.g. linting)
    # The game itself should ensure game_settings is loaded correctly.
    print("Warning (drone_configs.py): Could not import from game_settings. Using fallback default stats for ORIGINAL_DRONE.")
    PLAYER_MAX_HEALTH = 100
    PLAYER_SPEED = 3
    ROTATION_SPEED = 5

# Main dictionary holding all drone configurations
DRONE_DATA = {
    "ORIGINAL_DRONE": {
        "name": "Original Drone",
        "sprite_path": None, # Indicates to use the fallback drawing logic in the Player/Drone class
        "icon_path": "assets/drones/original_icon.png", # Path to the UI icon for selection
        "base_stats": { # Base statistics for this drone
            "hp": PLAYER_MAX_HEALTH, # Hit Points
            "speed": PLAYER_SPEED,   # Movement speed
            "turn_speed": ROTATION_SPEED, # Rotation speed
            "fire_rate_multiplier": 1.0, # Affects weapon cooldown (1.0 = normal, <1.0 = faster, >1.0 = slower)
            "special_ability": None, # String key for a special ability, or None
        },
        "unlock_condition": {"type": "default", "value": None, "description": "Unlocked by default."},
        "description": "The reliable, battle-tested original drone. Balanced and versatile for any mission.",
    },
    "VANTIS": {
        "name": "VANTIS",
        "sprite_path": "assets/drones/vantis.png", # Path to the in-game sprite
        "icon_path": "assets/drones/vantis.png",   # Path to UI icon (can be same as sprite)
        "base_stats": {
            "hp": 100,
            "speed": 3,
            "turn_speed": 5,
            "fire_rate_multiplier": 1.0,
            "special_ability": None,
        },
        "unlock_condition": {"type": "level", "value": 2, "description": "Unlock: Reach Level 2"},
        "description": "Sleek triangular stealth drone. A good all-rounder with balanced statistics.",
    },
    "RHINOX": {
        "name": "RHINOX",
        "sprite_path": "assets/drones/rhinox.png",
        "icon_path": "assets/drones/rhinox.png",
        "base_stats": {
            "hp": 150, # Higher health
            "speed": 2.5, # Slower speed
            "turn_speed": 4, # Slower turning
            "fire_rate_multiplier": 1.2, # 20% slower fire rate (cooldown * 1.2)
            "special_ability": None,
        },
        "unlock_condition": {"type": "cores", "value": 500, "description": "Unlock: 500 Cores"},
        "description": "Broad heavy armor-plated drone. Trades speed for high HP and resilience.",
    },
    "ZEPHYR": {
        "name": "ZEPHYR",
        "sprite_path": "assets/drones/zephyr.png",
        "icon_path": "assets/drones/zephyr.png",
        "base_stats": {
            "hp": 75, # Lower health
            "speed": 4, # Higher speed
            "turn_speed": 6, # Faster turning
            "fire_rate_multiplier": 0.9, # 10% faster fire rate (cooldown * 0.9)
            "special_ability": None,
        },
        "unlock_condition": {"type": "level", "value": 5, "description": "Unlock: Reach Level 5"},
        "description": "Lightweight quad-rotor frame. Excels in speed and agility but is more fragile.",
    },
    "STRIX": {
        "name": "STRIX",
        "sprite_path": "assets/drones/strix.png",
        "icon_path": "assets/drones/strix.png",
        "base_stats": {
            "hp": 90,
            "speed": 3.5,
            "turn_speed": 7, # Very fast turning
            "fire_rate_multiplier": 1.0,
            "special_ability": None,
        },
        "unlock_condition": {"type": "boss", "value": "MAZE_GUARDIAN", "description": "Unlock: Defeat Maze Guardian"},
        "description": "Sharp, agile bird-like drone. Known for its exceptional maneuverability.",
    },
    "OMEGA-9": {
        "name": "OMEGA-9",
        "sprite_path": "assets/drones/omega-9.png",
        "icon_path": "assets/drones/omega-9.png",
        "base_stats": { # These are "base" before randomization is applied by DroneSystem
            "hp": 80,
            "speed": 3,
            "turn_speed": 5,
            "fire_rate_multiplier": 1.0,
            "special_ability": "omega_boost", # Key for its unique randomization ability
        },
        "unlock_condition": {"type": "level", "value": 10, "description": "Unlock: Reach Level 10"},
        "description": "Futuristic experimental drone. Unstable: its core stats are randomized each run.",
    },
    "PHANTOM": {
        "name": "PHANTOM",
        "sprite_path": "assets/drones/phantom.png",
        "icon_path": "assets/drones/phantom.png",
        "base_stats": {
            "hp": 60, # Fragile
            "speed": 3.2,
            "turn_speed": 5.5,
            "fire_rate_multiplier": 1.1, # Slightly slower fire rate
            "special_ability": "phantom_cloak", # Key for cloaking ability
        },
        "unlock_condition": {"type": "cores", "value": 1000, "description": "Unlock: 1000 Cores"},
        "description": "Features a shimmer-based cloaking device. Can briefly turn invisible but is delicate.",
    },
    # Add more drone configurations here following the same structure
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

