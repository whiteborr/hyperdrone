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
        "sprite_path": None, # This is used for the selection screen main display
        "icon_path": "assets/drones/original_icon.png", # For UI icons like lives
        "ingame_sprite_path": "assets/drones/original_drone_2d.png", # In-game sprite
        "base_stats": { # Base statistics for this drone
            "hp": PLAYER_MAX_HEALTH, # Default: 100
            "speed": PLAYER_SPEED,     # Default: 3
            "turn_speed": ROTATION_SPEED, # Default: 5
            "fire_rate_multiplier": 1.0, # Normal fire rate
            "special_ability": None      # No special ability
        },
        "unlock_condition": {"type": "default", "value": None, "description": "Unlocked by default."},
        "description": "The reliable, battle-tested original drone. Balanced and versatile for any mission.",
    },
    "VANTIS": {
        "name": "VANTIS",
        "sprite_path": "assets/drones/vantis.png", # Selection screen preview
        "icon_path": "assets/drones/vantis.png",   # UI icon
        "ingame_sprite_path": "assets/drones/vantis_2d.png", # In-game sprite
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 0.9, # Example: Slightly less HP
            "speed": PLAYER_SPEED * 1.1,   # Example: Slightly faster
            "turn_speed": ROTATION_SPEED * 1.05,
            "fire_rate_multiplier": 1.0,
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 3, "description": "Unlock: Reach Level 3"},
        "description": "Sleek triangular stealth drone. A good all-rounder with balanced statistics.",
    },
    "RHINOX": {
        "name": "RHINOX",
        "sprite_path": "assets/drones/rhinox.png",
        "icon_path": "assets/drones/rhinox.png",
        "ingame_sprite_path": "assets/drones/rhinox_2d.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.5, # More HP
            "speed": PLAYER_SPEED * 0.8,   # Slower
            "turn_speed": ROTATION_SPEED * 0.9,
            "fire_rate_multiplier": 1.0,
            "special_ability": None
        },
        "unlock_condition": {"type": "cores", "value": 1000, "description": "Unlock: 1000 Cores"},
        "description": "Broad heavy armor-plated drone. Trades speed for high HP and resilience.",
    },
    "ZEPHYR": {
        "name": "ZEPHYR",
        "sprite_path": "assets/drones/zephyr.png",
        "icon_path": "assets/drones/zephyr.png",
        "ingame_sprite_path": "assets/drones/zephyr_2d.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 0.75, # Less HP
            "speed": PLAYER_SPEED * 1.3,    # Much faster
            "turn_speed": ROTATION_SPEED * 1.2, # Turns faster
            "fire_rate_multiplier": 0.9, # Slightly faster fire rate
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 10, "description": "Unlock: Reach Level 10"},
        "description": "Lightweight quad-rotor frame. Excels in speed and agility but is more fragile.",
    },
    "STRIX": {
        "name": "STRIX",
        "sprite_path": "assets/drones/strix.png",
        "icon_path": "assets/drones/strix.png",
        "ingame_sprite_path": "assets/drones/strix_2d.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.3, # Very agile
            "fire_rate_multiplier": 1.0,
            "special_ability": None # Could have a dash or quick turn ability later
        },
        "unlock_condition": {"type": "boss", "value": "MAZE_GUARDIAN", "description": "Unlock: Defeat Maze Guardian"},
        "description": "Sharp, agile bird-like drone. Known for its exceptional maneuverability.",
    },
    "OMEGA-9": {
        "name": "OMEGA-9",
        "sprite_path": "assets/drones/omega-9.png",
        "icon_path": "assets/drones/omega-9.png",
        "ingame_sprite_path": "assets/drones/omega-9_2d.png",
        "base_stats": { # These are the 'pre-randomized' base values Omega-9 starts from
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.0,
            "fire_rate_multiplier": 1.0, # This multiplier itself will be randomized
            "special_ability": "omega_boost" # Special flag for DroneSystem to randomize
        },
        "unlock_condition": {"type": "level", "value": 20, "description": "Unlock: Reach Level 20"},
        "description": "Futuristic experimental drone. Unstable: its core stats are randomized each run.",
    },
    "PHANTOM": {
        "name": "PHANTOM",
        "sprite_path": "assets/drones/phantom.png",
        "icon_path": "assets/drones/phantom.png",
        "ingame_sprite_path": "assets/drones/phantom_2d.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 0.6, # Fragile
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 1.0,
            "special_ability": "phantom_cloak" # Flag for cloaking ability
        },
        "unlock_condition": {"type": "cores", "value": 50000, "description": "Unlock: 50000 Cores"},
        "description": "Features a shimmer-based cloaking device. Can briefly turn invisible but is delicate.",
    },
    # Example for a potential Architect's Vault reward drone
    "DRONE_ARCHITECT_X": {
        "name": "Architect-X",
        "sprite_path": "assets/drones/architect_x_icon.png", # Corrected path to use the icon for preview
        "icon_path": "assets/drones/architect_x_icon.png", 
        "ingame_sprite_path": "assets/drones/architect_x_2d.png", # Placeholder path for actual in-game sprite
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.2,
            "speed": PLAYER_SPEED * 1.1,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 0.85, # Faster fire rate
            "special_ability": "energy_shield_pulse" # Example new ability
        },
        "unlock_condition": {"type": "blueprint", "value": "ARCHITECT_REWARD_BLUEPRINT_ID", "description": "Unlock: Architect's Vault Blueprint"},
        "description": "An advanced prototype drone recovered from the Architect's Vault. Possesses unique energy systems.",
    }
}

# Define the order in which drones appear in the selection screen
DRONE_DISPLAY_ORDER = [
    "ORIGINAL_DRONE",
    "VANTIS",
    "RHINOX",
    "ZEPHYR",
    "STRIX",
    "OMEGA-9",
    "PHANTOM",
    "DRONE_ARCHITECT_X" # Add new drones to the display order
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

# Sanity check: Ensure all drones in DRONE_DISPLAY_ORDER are defined in DRONE_DATA
for drone_id_ordered in DRONE_DISPLAY_ORDER:
    if drone_id_ordered not in DRONE_DATA:
        print(f"Warning (drone_configs.py): Drone ID '{drone_id_ordered}' found in DRONE_DISPLAY_ORDER but not in DRONE_DATA.")

