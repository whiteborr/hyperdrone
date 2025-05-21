import pygame # Pygame might be needed for color objects if used directly, though tuples are fine.

# ==========================
# General Display Settings
# ==========================
WIDTH = 1920
HEIGHT = 1080
FPS = 60
FULLSCREEN_MODE = False # Set to True for fullscreen, False for windowed

# ==========================
# UI & Layout Settings
# ==========================
BOTTOM_PANEL_HEIGHT = 120 # Height of the HUD panel at the bottom
GAME_PLAY_AREA_HEIGHT = HEIGHT - BOTTOM_PANEL_HEIGHT # Calculated play area height

# ==========================
# Tile & Maze Settings
# ==========================
TILE_SIZE = 80            # Pixel size of a single maze tile
MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE # Calculated number of rows in the maze

# ==========================
# Color Definitions
# ==========================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
DARK_RED = (100, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255) # General purpose blue
CYAN = (0, 255, 255)
LIGHT_BLUE = (173, 216, 230) # Often used for shields or UI highlights
YELLOW = (255, 255, 0)
GOLD = (255, 215, 0) # For scores, rings, special items
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
DARK_PURPLE = (40, 0, 70)
MAGENTA = (255, 0, 255) # For missiles or special effects
PINK = (255, 192, 203)
GREY = (100, 100, 100)
DARK_GREY = (50, 50, 50)
ELECTRIC_BLUE = (0, 128, 255) # For lightning effects

# Architect's Vault Specific Colors
ARCHITECT_VAULT_BG_COLOR = (20, 0, 30)
ARCHITECT_VAULT_WALL_COLOR = (150, 120, 200)
ARCHITECT_VAULT_ACCENT_COLOR = GOLD

# ==========================
# Player Drone Base Settings
# ==========================
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 3          # Base movement speed
PLAYER_LIVES = 3
ROTATION_SPEED = 5        # Base rotation speed in degrees per frame/tick

# Player Bullet & Weapon Base Settings
PLAYER_DEFAULT_BULLET_SIZE = 4 # Radius for circular bullets, or half-width for square
PLAYER_BIG_BULLET_SIZE = PLAYER_DEFAULT_BULLET_SIZE * 3 # Example for "Big Shot" mode
PLAYER_BULLET_COLOR = GOLD # Default color for player bullets
PLAYER_BULLET_SPEED = 7
PLAYER_BULLET_LIFETIME = 100 # In frames or ticks

PLAYER_BASE_SHOOT_COOLDOWN = 500 # Milliseconds for standard shots
PLAYER_RAPID_FIRE_COOLDOWN = 150 # Milliseconds for rapid fire modes

BOUNCING_BULLET_MAX_BOUNCES = 2
PIERCING_BULLET_MAX_PIERCES = 1 # How many enemies a piercing bullet can go through

# Missile Specific Settings
MISSILE_COLOR = MAGENTA
MISSILE_SPEED = PLAYER_BULLET_SPEED * 0.8 # Missiles are often slightly slower but track
MISSILE_LIFETIME = PLAYER_BULLET_LIFETIME * 3 # Missiles last longer
MISSILE_SIZE = 8 # Visual size
MISSILE_TURN_RATE = 4 # Degrees per frame the missile can turn
MISSILE_COOLDOWN = 3000 # Milliseconds
MISSILE_DAMAGE = 50

# Lightning Specific Settings
LIGHTNING_COLOR = ELECTRIC_BLUE
LIGHTNING_DAMAGE = 15
LIGHTNING_LIFETIME = 30 # Frames the visual effect lasts
LIGHTNING_COOLDOWN = 750 # Milliseconds
LIGHTNING_ZAP_RANGE = 250 # Max distance for lightning to jump to a target

# ==========================
# Player Weapon Modes
# ==========================
WEAPON_MODE_DEFAULT = 0
WEAPON_MODE_TRI_SHOT = 1
WEAPON_MODE_RAPID_SINGLE = 2
WEAPON_MODE_RAPID_TRI = 3
WEAPON_MODE_BIG_SHOT = 4
WEAPON_MODE_BOUNCE = 5
WEAPON_MODE_PIERCE = 6
WEAPON_MODE_HEATSEEKER = 7 # Missile only
WEAPON_MODE_HEATSEEKER_PLUS_BULLETS = 8 # Missiles + rapid bullets
WEAPON_MODE_LIGHTNING = 9

INITIAL_WEAPON_MODE = WEAPON_MODE_DEFAULT # Starting weapon mode for the player

WEAPON_MODES_SEQUENCE = [
    WEAPON_MODE_DEFAULT,
    WEAPON_MODE_TRI_SHOT,
    WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT,
    WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER,
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
]

WEAPON_MODE_NAMES = { # For UI display
    WEAPON_MODE_DEFAULT: "Single Shot",
    WEAPON_MODE_TRI_SHOT: "Tri-Shot",
    WEAPON_MODE_RAPID_SINGLE: "Rapid Single",
    WEAPON_MODE_RAPID_TRI: "Rapid Tri-Shot",
    WEAPON_MODE_BIG_SHOT: "Big Shot",
    WEAPON_MODE_BOUNCE: "Bounce Shot",
    WEAPON_MODE_PIERCE: "Pierce Shot",
    WEAPON_MODE_HEATSEEKER: "Heatseeker",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "Seeker + Rapid",
    WEAPON_MODE_LIGHTNING: "Chain Lightning"
}

WEAPON_MODE_ICONS = { # Emoji/symbols for UI
    WEAPON_MODE_DEFAULT: "🔫",
    WEAPON_MODE_TRI_SHOT: "🔱",
    WEAPON_MODE_RAPID_SINGLE: "💨",
    WEAPON_MODE_RAPID_TRI: "💨🔱",
    WEAPON_MODE_BIG_SHOT: "🔵",
    WEAPON_MODE_BOUNCE: "🏀",
    WEAPON_MODE_PIERCE: "➤",
    WEAPON_MODE_HEATSEEKER: "🚀",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "🚀💨",
    WEAPON_MODE_LIGHTNING: "⚡",
}

# ==========================
# Player Abilities Settings (e.g., Cloak)
# ==========================
PHANTOM_CLOAK_DURATION_MS = 5000
PHANTOM_CLOAK_COOLDOWN_MS = 15000
PHANTOM_CLOAK_ALPHA_SETTING = 70 # Alpha value (0-255) when cloaked

# ==========================
# Enemy Base Settings
# ==========================
ENEMY_SPEED = 1.5
ENEMY_HEALTH = 100
ENEMY_COLOR = RED # Default color for basic enemies
ENEMY_BULLET_SPEED = 5
ENEMY_BULLET_COOLDOWN = 1500 # Milliseconds
ENEMY_BULLET_LIFETIME = 75   # Frames
ENEMY_BULLET_COLOR = ORANGE
ENEMY_BULLET_DAMAGE = 10

# Architect's Vault Prototype Drone Settings (Example of specific enemy type)
PROTOTYPE_DRONE_HEALTH = 150
PROTOTYPE_DRONE_SPEED = 2.0
PROTOTYPE_DRONE_COLOR = MAGENTA # Distinct color
PROTOTYPE_DRONE_SHOOT_COOLDOWN = 1200
PROTOTYPE_DRONE_BULLET_SPEED = 6
PROTOTYPE_DRONE_SPRITE_PATH = "assets/images/drones/prototype_enemy.png" # Path to its sprite

# ==========================
# Power-up & Collectible Settings
# ==========================
POWERUP_SIZE = TILE_SIZE // 3 # Visual size of power-up items
POWERUP_SPAWN_CHANCE = 0.05 # Chance per second to spawn a power-up (adjust based on FPS in game loop)
MAX_POWERUPS_ON_SCREEN = 2 # Max number of non-weapon power-ups at a time
WEAPON_UPGRADE_ITEM_LIFETIME = 15000 # Milliseconds before it disappears
POWERUP_ITEM_LIFETIME = 12000      # Milliseconds for shield/speed boost items

POWERUP_TYPES = { # Defines properties for different power-ups
    "shield": {
        "color": LIGHT_BLUE,
        "image_filename": "shield_icon.png", # In assets/images/powerups/
        "duration": 10000 # Milliseconds the shield lasts
    },
    "speed_boost": {
        "color": GREEN,
        "image_filename": "speed_icon.png",
        "duration": 7000, # Milliseconds the speed boost lasts
        "multiplier": 1.8 # Player speed is multiplied by this
    },
    "weapon_upgrade": { # This item cycles to the next weapon mode
        "color": BLUE,
        "image_filename": "weapon_icon.png"
        # No duration/multiplier needed as it's an instant upgrade
    }
}
# For direct access if needed, though player usually gets duration from POWERUP_TYPES
SHIELD_POWERUP_DURATION = POWERUP_TYPES["shield"]["duration"]
SPEED_BOOST_POWERUP_DURATION = POWERUP_TYPES["speed_boost"]["duration"]

# ==========================
# Core Fragment & Architect's Vault Settings
# ==========================
TOTAL_CORE_FRAGMENTS_NEEDED = 3 # Number of unique fragments to collect for vault access
CORE_FRAGMENT_VISUAL_SIZE = TILE_SIZE // 2.5 # Visual size of fragment items

CORE_FRAGMENT_DETAILS = { # Details for each unique core fragment
    "fragment_alpha": {
        "id": "cf_alpha", "name": "Alpha Core Fragment", "icon_filename": "core_fragment_alpha.png",
        "description": "A corrupted fragment, pulses with unstable energy.",
        "spawn_info": {"level": 1}, # Example: when/where it might spawn
        "buff": {"type": "speed", "value": 1.05} # Example buff if player holds it in vault
    },
    "fragment_beta": {
        "id": "cf_beta", "name": "Beta Core Fragment", "icon_filename": "core_fragment_beta.png",
        "description": "This piece hums with a strange, alien resonance.",
        "spawn_info": {"level": 2},
        "buff": {"type": "bullet_damage_multiplier", "value": 1.05}
    },
    "fragment_gamma": {
        "id": "cf_gamma", "name": "Gamma Core Fragment", "icon_filename": "core_fragment_gamma.png",
        "description": "Seems to be a critical processing unit, heavily damaged.",
        "spawn_info": {"level": 3},
        "buff_alt": {"type": "damage_reduction", "value": 0.05} # Example: 5% damage reduction
    }
}

ARCHITECT_VAULT_EXTRACTION_TIMER_MS = 90000 # 90 seconds to escape
ARCHITECT_VAULT_GAUNTLET_WAVES = 3
ARCHITECT_VAULT_DRONES_PER_WAVE = [3, 4, 5] # Number of prototype drones per gauntlet wave

ARCHITECT_REWARD_BLUEPRINT_ID = "DRONE_ARCHITECT_X" # ID of the drone blueprint rewarded
ARCHITECT_REWARD_LORE_ID = "lore_architect_origin"  # ID of lore entry unlocked

# ==========================
# Game Progression & Miscellaneous
# ==========================
LEVEL_TIMER_DURATION = 150000  # Milliseconds per standard level (2.5 minutes)
BONUS_LEVEL_DURATION_MS = 60000 # Milliseconds for bonus levels

# Leaderboard Settings
LEADERBOARD_FILE_NAME = "leaderboard.json" # Name of the leaderboard file
LEADERBOARD_MAX_ENTRIES = 10               # Max number of scores to keep

# ==========================
# Game State Definitions
# ==========================
GAME_STATE_MAIN_MENU = "main_menu"
GAME_STATE_PLAYING = "playing"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_LEADERBOARD = "leaderboard_display"
GAME_STATE_ENTER_NAME = "enter_name"
GAME_STATE_SETTINGS = "settings_menu"
GAME_STATE_DRONE_SELECT = "drone_select_menu"

GAME_STATE_BONUS_LEVEL_TRANSITION = "bonus_level_transition" # If you have a screen before bonus level
GAME_STATE_BONUS_LEVEL_START = "bonus_level_start" # For initializing bonus level
GAME_STATE_BONUS_LEVEL_PLAYING = "bonus_level_playing"

GAME_STATE_ARCHITECT_VAULT_INTRO = "architect_vault_intro"
GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE = "architect_vault_entry_puzzle"
GAME_STATE_ARCHITECT_VAULT_GAUNTLET = "architect_vault_gauntlet"
GAME_STATE_ARCHITECT_VAULT_EXTRACTION = "architect_vault_extraction"
GAME_STATE_ARCHITECT_VAULT_SUCCESS = "architect_vault_success"
GAME_STATE_ARCHITECT_VAULT_FAILURE = "architect_vault_failure"

# ==============================================================================
# Dynamic Settings Management (allows changing settings via UI and affects game)
# ==============================================================================

# Dictionary to store the default values of all configurable settings.
# This MUST mirror the global constants defined above that you want to be configurable.
DEFAULT_SETTINGS = {
    "WIDTH": WIDTH, "HEIGHT": HEIGHT, "FPS": FPS, "FULLSCREEN_MODE": FULLSCREEN_MODE,
    "BOTTOM_PANEL_HEIGHT": BOTTOM_PANEL_HEIGHT,
    "TILE_SIZE": TILE_SIZE,
    "PLAYER_MAX_HEALTH": PLAYER_MAX_HEALTH, "PLAYER_LIVES": PLAYER_LIVES,
    "PLAYER_SPEED": PLAYER_SPEED, "ROTATION_SPEED": ROTATION_SPEED,
    "PLAYER_DEFAULT_BULLET_SIZE": PLAYER_DEFAULT_BULLET_SIZE, "PLAYER_BIG_BULLET_SIZE": PLAYER_BIG_BULLET_SIZE,
    "PLAYER_BULLET_COLOR": PLAYER_BULLET_COLOR, "PLAYER_BULLET_SPEED": PLAYER_BULLET_SPEED,
    "PLAYER_BULLET_LIFETIME": PLAYER_BULLET_LIFETIME,
    "PLAYER_BASE_SHOOT_COOLDOWN": PLAYER_BASE_SHOOT_COOLDOWN, "PLAYER_RAPID_FIRE_COOLDOWN": PLAYER_RAPID_FIRE_COOLDOWN,
    "BOUNCING_BULLET_MAX_BOUNCES": BOUNCING_BULLET_MAX_BOUNCES, "PIERCING_BULLET_MAX_PIERCES": PIERCING_BULLET_MAX_PIERCES,
    "MISSILE_COLOR": MISSILE_COLOR, "MISSILE_SPEED": MISSILE_SPEED, "MISSILE_LIFETIME": MISSILE_LIFETIME,
    "MISSILE_SIZE": MISSILE_SIZE, "MISSILE_TURN_RATE": MISSILE_TURN_RATE, "MISSILE_COOLDOWN": MISSILE_COOLDOWN, "MISSILE_DAMAGE": MISSILE_DAMAGE,
    "LIGHTNING_COLOR": LIGHTNING_COLOR, "LIGHTNING_DAMAGE": LIGHTNING_DAMAGE, "LIGHTNING_LIFETIME": LIGHTNING_LIFETIME,
    "LIGHTNING_COOLDOWN": LIGHTNING_COOLDOWN, "LIGHTNING_ZAP_RANGE": LIGHTNING_ZAP_RANGE,
    "INITIAL_WEAPON_MODE": INITIAL_WEAPON_MODE,
    "PHANTOM_CLOAK_DURATION_MS": PHANTOM_CLOAK_DURATION_MS, "PHANTOM_CLOAK_COOLDOWN_MS": PHANTOM_CLOAK_COOLDOWN_MS,
    "PHANTOM_CLOAK_ALPHA_SETTING": PHANTOM_CLOAK_ALPHA_SETTING,
    "ENEMY_SPEED": ENEMY_SPEED, "ENEMY_HEALTH": ENEMY_HEALTH, "ENEMY_COLOR": ENEMY_COLOR,
    "ENEMY_BULLET_SPEED": ENEMY_BULLET_SPEED, "ENEMY_BULLET_COOLDOWN": ENEMY_BULLET_COOLDOWN,
    "ENEMY_BULLET_LIFETIME": ENEMY_BULLET_LIFETIME, "ENEMY_BULLET_COLOR": ENEMY_BULLET_COLOR, "ENEMY_BULLET_DAMAGE": ENEMY_BULLET_DAMAGE,
    "PROTOTYPE_DRONE_HEALTH": PROTOTYPE_DRONE_HEALTH, "PROTOTYPE_DRONE_SPEED": PROTOTYPE_DRONE_SPEED,
    "PROTOTYPE_DRONE_SHOOT_COOLDOWN": PROTOTYPE_DRONE_SHOOT_COOLDOWN, "PROTOTYPE_DRONE_BULLET_SPEED": PROTOTYPE_DRONE_BULLET_SPEED,
    "POWERUP_SPAWN_CHANCE": POWERUP_SPAWN_CHANCE, "MAX_POWERUPS_ON_SCREEN": MAX_POWERUPS_ON_SCREEN,
    "WEAPON_UPGRADE_ITEM_LIFETIME": WEAPON_UPGRADE_ITEM_LIFETIME, "POWERUP_ITEM_LIFETIME": POWERUP_ITEM_LIFETIME,
    "SHIELD_POWERUP_DURATION": SHIELD_POWERUP_DURATION, "SPEED_BOOST_POWERUP_DURATION": SPEED_BOOST_POWERUP_DURATION,
    # Note: Complex types like POWERUP_TYPES, CORE_FRAGMENT_DETAILS, WEAPON_MODES_SEQUENCE etc.
    # are usually not part of simple dynamic settings UI but are listed here for completeness if ever needed.
    # For now, they are treated as fixed game data. If they were to be dynamic,
    # the set/get logic would need to handle deep copies or more complex updates.
    "LEVEL_TIMER_DURATION": LEVEL_TIMER_DURATION,
    "BONUS_LEVEL_DURATION_MS": BONUS_LEVEL_DURATION_MS,
    "LEADERBOARD_MAX_ENTRIES": LEADERBOARD_MAX_ENTRIES, "LEADERBOARD_FILE_NAME": LEADERBOARD_FILE_NAME,
    # Dependent calculated values are not in DEFAULT_SETTINGS as they derive from others.
}

# Global flag to track if any setting has been modified from its default.
SETTINGS_MODIFIED = False
# Internal dictionary to hold the current (potentially modified) settings.
_CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()

def get_game_setting(key):
    """Retrieves the current value of a game setting."""
    return _CURRENT_GAME_SETTINGS.get(key, DEFAULT_SETTINGS.get(key)) # Fallback to default if key somehow missing

def set_game_setting(key, value):
    """
    Sets a game setting to a new value and updates the SETTINGS_MODIFIED flag.
    Also updates the global variable for direct access if it exists.
    """
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    global GAME_PLAY_AREA_HEIGHT, MAZE_ROWS # Globals that depend on other settings

    if key in _CURRENT_GAME_SETTINGS:
        _CURRENT_GAME_SETTINGS[key] = value
        # Check if this change makes it different from the default
        if _CURRENT_GAME_SETTINGS[key] != DEFAULT_SETTINGS.get(key):
            SETTINGS_MODIFIED = True
        else:
            # If set back to default, re-check if any *other* settings are still modified
            SETTINGS_MODIFIED = any(
                _CURRENT_GAME_SETTINGS[k] != DEFAULT_SETTINGS.get(k)
                for k in DEFAULT_SETTINGS if k in _CURRENT_GAME_SETTINGS
            )

        # If the changed key corresponds to a global variable, update it too.
        # This allows other modules to use "from game_settings import WIDTH" and get the current value.
        if key in globals():
            globals()[key] = value

            # Handle dependent global variables
            if key == "HEIGHT" or key == "BOTTOM_PANEL_HEIGHT":
                GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
                globals()["GAME_PLAY_AREA_HEIGHT"] = GAME_PLAY_AREA_HEIGHT # Update global scope
                if get_game_setting("TILE_SIZE") > 0: # Avoid division by zero
                    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // get_game_setting("TILE_SIZE")
                    globals()["MAZE_ROWS"] = MAZE_ROWS # Update global scope
            elif key == "TILE_SIZE":
                if get_game_setting("TILE_SIZE") > 0:
                    MAZE_ROWS = get_game_setting("GAME_PLAY_AREA_HEIGHT") // get_game_setting("TILE_SIZE")
                    globals()["MAZE_ROWS"] = MAZE_ROWS
            # Add other dependent calculations here if needed (e.g., MISSILE_SPEED based on PLAYER_BULLET_SPEED)

    else:
        print(f"Warning (game_settings.py): Attempted to set an unknown game setting '{key}'.")

def reset_all_settings_to_default():
    """Resets all configurable settings back to their default values."""
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    global GAME_PLAY_AREA_HEIGHT, MAZE_ROWS # And any other dependent globals

    _CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()
    SETTINGS_MODIFIED = False
    print("Game settings have been reset to defaults.")

    # Update all global variables from the reset _CURRENT_GAME_SETTINGS
    for key, value in _CURRENT_GAME_SETTINGS.items():
        if key in globals(): # Check if it's a global we manage this way
            globals()[key] = value

    # Recalculate dependent globals explicitly after resetting all
    GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
    globals()["GAME_PLAY_AREA_HEIGHT"] = GAME_PLAY_AREA_HEIGHT
    if get_game_setting("TILE_SIZE") > 0:
        MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // get_game_setting("TILE_SIZE")
        globals()["MAZE_ROWS"] = MAZE_ROWS
    # Add other recalculations like MISSILE_SPEED if they were made dependent

# Initialize globals that are calculated from other settings
# This ensures they have correct values at startup and after any potential direct modifications.
GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
if TILE_SIZE > 0: # Check to avoid division by zero if TILE_SIZE was somehow 0
    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE
else:
    MAZE_ROWS = 0 # Default or error state for MAZE_ROWS
    print("Warning (game_settings.py): TILE_SIZE is 0 or invalid, MAZE_ROWS set to 0.")

# Example of another dependent variable (if it was global and not just used in player.py)
# MISSILE_SPEED = get_game_setting("PLAYER_BULLET_SPEED") * 0.8 # Already handled by direct constant definition