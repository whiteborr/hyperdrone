"""
Defines the configurations for all available drones in the game.
Each drone has a unique ID (the key in DRONE_DATA), a display name,
paths to its sprite and icon, base statistics, an unlock condition,
and a descriptive text.
"""
import logging
from constants import ARCHITECT_REWARD_BLUEPRINT_ID
from settings_manager import get_setting

# Configure logger
logger = logging.getLogger(__name__)

# Get player settings
PLAYER_MAX_HEALTH = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
PLAYER_SPEED = get_setting("gameplay", "PLAYER_SPEED", 3)
ROTATION_SPEED = get_setting("gameplay", "ROTATION_SPEED", 5)

# Main dictionary holding all drone configurations
DRONE_DATA = {
    "DRONE": {
        "name": "Drone",
        "sprite_path": "assets/images/drones/drone_default.png",
        "icon_path": "assets/images/drones/drone_default.png",
        "ingame_sprite_path": "assets/images/drones/drone_default.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH,
            "speed": PLAYER_SPEED,
            "turn_speed": ROTATION_SPEED,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": None
        },
        "unlock_condition": {"type": "default", "value": None, "description": "Unlocked by default."},
        "description": "The reliable, battle-tested original drone. Balanced and versatile for any mission."
    },
    "VANTIS": {
        "name": "VANTIS",
        "sprite_path": "assets/images/drones/vantis.png",
        "icon_path": "assets/images/drones/vantis.png",
        "ingame_sprite_path": "assets/images/drones/vantis_default.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.9),
            "speed": PLAYER_SPEED * 1.1,
            "turn_speed": ROTATION_SPEED * 1.05,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 3, "description": "Unlock: Reach Level 3"},
        "description": "Sleek triangular stealth drone. A good all-rounder with balanced statistics."
    },
    "RHINOX": {
        "name": "RHINOX",
        "sprite_path": "assets/images/drones/rhinox.png",
        "icon_path": "assets/images/drones/rhinox.png",
        "ingame_sprite_path": "assets/images/drones/rhinox_default.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 1.5),
            "speed": PLAYER_SPEED * 0.8,
            "turn_speed": ROTATION_SPEED * 0.9,
            "fire_rate_multiplier": 1.05,
            "bullet_damage_multiplier": 1.1,
            "special_ability": None
        },
        "unlock_condition": {"type": "cores", "value": 1000, "description": "Unlock: 1000 Cores"},
        "description": "Broad heavy armor-plated drone. Trades speed for high HP and resilience."
    },
    "ZEPHYR": {
        "name": "ZEPHYR",
        "sprite_path": "assets/images/drones/zephyr.png",
        "icon_path": "assets/images/drones/zephyr.png",
        "ingame_sprite_path": "assets/images/drones/zephyr_default.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.75),
            "speed": PLAYER_SPEED * 1.3,
            "turn_speed": ROTATION_SPEED * 1.2,
            "fire_rate_multiplier": 0.9,
            "bullet_damage_multiplier": 0.9,
            "special_ability": None
        },
        "unlock_condition": {"type": "level", "value": 10, "description": "Unlock: Reach Level 10"},
        "description": "Lightweight quad-rotor frame. Excels in speed and agility but is more fragile."
    },
    "STRIX": {
        "name": "STRIX",
        "sprite_path": "assets/images/drones/strix.png",
        "icon_path": "assets/images/drones/strix.png",
        "ingame_sprite_path": "assets/images/drones/strix_default.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.3,
            "fire_rate_multiplier": 0.95,
            "bullet_damage_multiplier": 1.05,
            "special_ability": None
        },
        "unlock_condition": {"type": "boss", "value": "MAZE_GUARDIAN", "description": "Unlock: Defeat Maze Guardian (Not Implemented)"},
        "description": "Sharp, agile bird-like drone. Known for its exceptional maneuverability."
    },
    "OMEGA-9": {
        "name": "OMEGA-9",
        "sprite_path": "assets/images/drones/omega-9.png",
        "icon_path": "assets/images/drones/omega-9.png",
        "ingame_sprite_path": "assets/images/drones/omega-9_default.png",
        "base_stats": {
            "hp": PLAYER_MAX_HEALTH * 1.0,
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.0,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": "omega_boost"
        },
        "unlock_condition": {"type": "level", "value": 20, "description": "Unlock: Reach Level 20"},
        "description": "Futuristic experimental drone. Unstable: its core stats are randomized each run."
    },
    "PHANTOM": {
        "name": "PHANTOM",
        "sprite_path": "assets/images/drones/phantom.png",
        "icon_path": "assets/images/drones/phantom.png",
        "ingame_sprite_path": "assets/images/drones/phantom_default.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 0.6),
            "speed": PLAYER_SPEED * 1.0,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 1.0,
            "bullet_damage_multiplier": 1.0,
            "special_ability": "phantom_cloak"
        },
        "unlock_condition": {"type": "cores", "value": 50, "description": "Unlock: 50000 Cores"},
        "description": "Features a shimmer-based cloaking device. Can briefly turn invisible but is delicate."
    },
    ARCHITECT_REWARD_BLUEPRINT_ID: {
        "name": "Architect-X",
        "sprite_path": "assets/images/drones/architect_x.png",
        "icon_path": "assets/images/drones/architect_x.png",
        "ingame_sprite_path": "assets/images/drones/architect_x_default.png",
        "base_stats": {
            "hp": int(PLAYER_MAX_HEALTH * 1.2),
            "speed": PLAYER_SPEED * 1.1,
            "turn_speed": ROTATION_SPEED * 1.1,
            "fire_rate_multiplier": 0.85,
            "bullet_damage_multiplier": 1.15,
            "special_ability": "energy_shield_pulse"
        },
        "unlock_condition": {"type": "blueprint", "value": ARCHITECT_REWARD_BLUEPRINT_ID, "description": "Unlock: Architect's Vault Blueprint"},
        "description": "An advanced prototype recovered from the Architect's Vault. Possesses unique energy systems."
    }
}

DRONE_DISPLAY_ORDER = [
    "DRONE",
    "VANTIS",
    "RHINOX",
    "ZEPHYR",
    "STRIX",
    "OMEGA-9",
    "PHANTOM",
    ARCHITECT_REWARD_BLUEPRINT_ID
]

PHANTOM_CLOAK_DURATION_MS_CONFIG = 5000
PHANTOM_CLOAK_COOLDOWN_MS_CONFIG = 15000
PHANTOM_CLOAK_ALPHA_CONFIG = 70

OMEGA_STAT_RANGES = {
    "hp": (0.7, 1.5),
    "speed": (0.8, 1.3),
    "turn_speed": (0.9, 1.2),
    "fire_rate_multiplier": (0.7, 1.3),
    "bullet_damage_multiplier": (0.8, 1.4)
}

# Sanity checks
for drone_id_ordered in DRONE_DISPLAY_ORDER:
    if drone_id_ordered not in DRONE_DATA:
        logger.warning(f"Drone ID '{drone_id_ordered}' found in DRONE_DISPLAY_ORDER but not in DRONE_DATA.")

EXPECTED_BASE_STATS_KEYS = ["hp", "speed", "turn_speed", "fire_rate_multiplier", "bullet_damage_multiplier", "special_ability"]
for drone_id, data in DRONE_DATA.items():
    if "base_stats" not in data:
        logger.warning(f"Drone '{drone_id}' is missing 'base_stats' dictionary.")
        continue
    for stat_key in EXPECTED_BASE_STATS_KEYS:
        if stat_key not in data["base_stats"]:
            logger.warning(f"Drone '{drone_id}' base_stats is missing key '{stat_key}'.")