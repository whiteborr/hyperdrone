"""
Defines the configurations for all available drones in the game.
Each drone has a unique ID (the key in DRONE_DATA), a display name,
paths to its sprite and icon, base statistics, an unlock condition,
and a descriptive text.
"""
# Import base values from game_settings to ensure consistency or provide defaults
try:
    from game_settings import (
        PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED,
        ARCHITECT_REWARD_BLUEPRINT_ID # For the Architect-X unlock condition
    )
except ImportError:
    print("Warning (drone_configs.py): Could not import all constants from game_settings. Using fallbacks.")
    PLAYER_MAX_HEALTH = 100
    PLAYER_SPEED = 3
    ROTATION_SPEED = 5
    ARCHITECT_REWARD_BLUEPRINT_ID = "DRONE_ARCHITECT_X" # Fallback, should match game_settings

# Main dictionary holding all drone configurations
DRONE_DATA = {
    "DRONE": {
        "name": "Drone",
        "sprite_path": "assets/images/drones/drone_2d.png", # Main display image for selection screen
        "icon_path": "assets/images/drones/original_icon.png",      # Small UI icon (e.g., for lives)
        "ingame_sprite_path": "assets/images/drones/drone_2d.png", # Sprite used during gameplay
        "base_stats": { # Base statistics for this drone
            "hp": PLAYER_MAX_HEALTH,
            "speed": PLAYER_SPEED,
            "turn_speed": ROTATION_SPEED,
            "fire_rate_multiplier": 1.0, # 1.0 is normal, <1.0 is faster, >1.0 is slower
            "bullet_damage_multiplier": 1.0, # 1.0 is normal damage
            "special_ability": None      # No special ability
        },
        "unlock_condition": {"type": "default", "value": None, "description": "Unlocked by default."},
        "description": "The reliable, battle-tested original drone. Balanced and versatile for any mission.",
    },
    "VANTIS": {
        "name": "VANTIS",
        "sprite_path": "assets/images/drones/vantis.png",
        "icon_path": "assets/images/drones/vantis.png", # Assuming a specific icon variant
        "ingame_sprite_path": "assets/images/drones/vantis_2d.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.9), # Slightly less HP
            "speed": PLAYER_SPEED * 1.1,        # Slightly faster
            "turn_speed": ROTATION_SPEED * 1.05,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 3, "description": "Unlock: Reach Level 3"},
        "description": "Sleek triangular stealth drone. A good all-rounder with balanced statistics.",
    },
    "RHINOX": {
        "name": "RHINOX",
        "sprite_path": "assets/images/drones/rhinox.png",
        "icon_path": "assets/images/drones/rhinox_icon.png",
        "ingame_sprite_path": "assets/images/drones/rhinox_2d.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 1.5), # More HP
            "speed": PLAYER_SPEED * 0.8,        # Slower
            "turn_speed": ROTATION_SPEED * 0.9,
            "fire_rate_multiplier": 1.05, # Slightly slower fire rate
            "bullet_damage_multiplier": 1.1, # Slightly more damage
            "special_ability": None
        },
        "unlock_condition": {"type": "cores", "value": 1000, "description": "Unlock: 1000 Cores"},
        "description": "Broad heavy armor-plated drone. Trades speed for high HP and resilience.",
    },
    "ZEPHYR": {
        "name": "ZEPHYR",
        "sprite_path": "assets/images/drones/zephyr.png",
        "icon_path": "assets/images/drones/zephyr_icon.png",
        "ingame_sprite_path": "assets/images/drones/zephyr_2d.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.75), # Less HP
            "speed": PLAYER_SPEED * 1.3,         # Much faster
            "turn_speed": ROTATION_SPEED * 1.2,  # Turns faster
            "fire_rate_multiplier": 0.9, # Slightly faster fire rate (lower is faster)
            "bullet_damage_multiplier": 0.9, # Slightly less damage
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 10, "description": "Unlock: Reach Level 10"},
        "description": "Lightweight quad-rotor frame. Excels in speed and agility but is more fragile.",
    },
    "STRIX": {
        "name": "STRIX",
        "sprite_path": "assets/images/drones/strix.png",
        "icon_path": "assets/images/drones/strix_icon.png",
        "ingame_sprite_path": "assets/images/drones/strix_2d.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.3, # Very agile
            "fire_rate_multiplier": 0.95, # Slightly faster fire rate
            "bullet_damage_multiplier": 1.05,
            "special_ability": None # Could have a dash or quick turn ability later
        },
        "unlock_condition": {"type": "boss", "value": "MAZE_GUARDIAN", "description": "Unlock: Defeat Maze Guardian (Not Implemented)"},
        "description": "Sharp, agile bird-like drone. Known for its exceptional maneuverability.",
    },
    "OMEGA-9": {
        "name": "OMEGA-9",
        "sprite_path": "assets/images/drones/omega-9.png",
        "icon_path": "assets/images/drones/omega-9_icon.png",
        "ingame_sprite_path": "assets/images/drones/omega-9_2d.png",
        "base_stats": { # These are the 'pre-randomized' base values Omega-9 starts from
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.0,
            "fire_rate_multiplier": 1.0, # This multiplier itself will be randomized
            "bullet_damage_multiplier": 1.0, # This can also be randomized
            "special_ability": "omega_boost" # Special flag for DroneSystem to randomize
        },
        "unlock_condition": {"type": "level", "value": 20, "description": "Unlock: Reach Level 20"},
        "description": "Futuristic experimental drone. Unstable: its core stats are randomized each run.",
    },
    "PHANTOM": {
        "name": "PHANTOM",
        "sprite_path": "assets/images/drones/phantom.png",
        "icon_path": "assets/images/drones/phantom_icon.png",
        "ingame_sprite_path": "assets/images/drones/phantom_2d.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.6), # Fragile
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": "phantom_cloak" # Flag for cloaking ability
        },
        "unlock_condition": {"type": "cores", "value": 50000, "description": "Unlock: 50000 Cores"},
        "description": "Features a shimmer-based cloaking device. Can briefly turn invisible but is delicate.",
    },
    "DRONE_ARCHITECT_X": { # ID should match ARCHITECT_REWARD_BLUEPRINT_ID from game_settings
        "name": "Architect-X",
        "sprite_path": "assets/images/drones/architect_x_icon.png", # Preview for selection screen
        "icon_path": "assets/images/drones/architect_x_icon.png",   # Small UI icon
        "ingame_sprite_path": "assets/images/drones/architect_x_2d.png", # Actual in-game sprite
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 1.2),
            "speed": PLAYER_SPEED * 1.1,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 0.85, # Faster fire rate (lower is faster)
            "bullet_damage_multiplier": 1.15, # Higher damage
            "special_ability": "energy_shield_pulse" # Example new ability
        },
        # Unlock condition uses the constant imported from game_settings
        "unlock_condition": {"type": "blueprint", "value": ARCHITECT_REWARD_BLUEPRINT_ID, "description": "Unlock: Architect's Vault Blueprint"},
        "description": "An advanced prototype recovered from the Architect's Vault. Possesses unique energy systems.",
    }
}

# Define the order in which drones appear in the selection screen
# Ensure all drone_ids from DRONE_DATA that should be selectable are listed here.
DRONE_DISPLAY_ORDER = [
    "DRONE",
    "VANTIS",
    "RHINOX",
    "ZEPHYR",
    "STRIX",
    "OMEGA-9",
    "PHANTOM",
    "DRONE_ARCHITECT_X"
]

# --- Special Ability Constants ---

# Phantom Cloak Ability (values can also be in game_settings.py if preferred for central tweaking)
# If defined here, game_settings.py might import them or player.py might get them from drone_system.
# For now, keeping them here as they are closely tied to the PHANTOM drone config.
PHANTOM_CLOAK_DURATION_MS_CONFIG = 5000  # Duration of cloak in milliseconds (5 seconds)
PHANTOM_CLOAK_COOLDOWN_MS_CONFIG = 15000 # Cooldown after cloak ends in milliseconds (15 seconds)
PHANTOM_CLOAK_ALPHA_CONFIG = 70 # Alpha value (0-255) when cloaked (lower is more transparent)

# Omega-9 Stat Randomization Ranges
# These are multipliers applied to Omega-9's base stats at the start of a run.
OMEGA_STAT_RANGES = {
    "hp": (0.7, 1.5), # HP can be 70% to 150% of its base
    "speed": (0.8, 1.3), # Speed can be 80% to 130% of its base
    "turn_speed": (0.9, 1.2), # Turn speed can be 90% to 120% of its base
    "fire_rate_multiplier": (0.7, 1.3), # Fire rate can be 30% faster to 30% slower (0.7 means 1/0.7 = 1.42x faster)
    "bullet_damage_multiplier": (0.8, 1.4) # Damage can be 80% to 140%
}

# Sanity check: Ensure all drones in DRONE_DISPLAY_ORDER are defined in DRONE_DATA
for drone_id_ordered in DRONE_DISPLAY_ORDER:
    if drone_id_ordered not in DRONE_DATA:
        print(f"Warning (drone_configs.py): Drone ID '{drone_id_ordered}' found in DRONE_DISPLAY_ORDER but not in DRONE_DATA.")

# Sanity check: Ensure all DRONE_DATA entries have necessary base_stats keys
EXPECTED_BASE_STATS_KEYS = ["hp", "speed", "turn_speed", "fire_rate_multiplier", "bullet_damage_multiplier", "special_ability"]
for drone_id, data in DRONE_DATA.items():
    if "base_stats" not in data:
        print(f"Warning (drone_configs.py): Drone '{drone_id}' is missing 'base_stats' dictionary.")
        continue
    for stat_key in EXPECTED_BASE_STATS_KEYS:
        if stat_key not in data["base_stats"]:
            print(f"Warning (drone_configs.py): Drone '{drone_id}' base_stats is missing key '{stat_key}'.")