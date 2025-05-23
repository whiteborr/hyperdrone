import pygame

# ==========================
# General Display Settings
# ==========================
WIDTH = 1920
HEIGHT = 1080
FPS = 60
FULLSCREEN_MODE = True # Set to True for fullscreen, False for windowed

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
PLAYER_INVINCIBILITY = False 

# Player Bullet & Weapon Base Settings
PLAYER_DEFAULT_BULLET_SIZE = 4 
PLAYER_BIG_BULLET_SIZE = PLAYER_DEFAULT_BULLET_SIZE * 3 
PLAYER_BULLET_COLOR = GOLD 
PLAYER_BULLET_SPEED = 7
PLAYER_BULLET_LIFETIME = 100 

PLAYER_BASE_SHOOT_COOLDOWN = 500 
PLAYER_RAPID_FIRE_COOLDOWN = 150 

BOUNCING_BULLET_MAX_BOUNCES = 2
PIERCING_BULLET_MAX_PIERCES = 1 

# Missile Specific Settings
MISSILE_COLOR = MAGENTA
MISSILE_SPEED = PLAYER_BULLET_SPEED * 0.8 
MISSILE_LIFETIME = PLAYER_BULLET_LIFETIME * 3 
MISSILE_SIZE = 8 
MISSILE_TURN_RATE = 4 
MISSILE_COOLDOWN = 3000 
MISSILE_DAMAGE = 50

# Lightning Specific Settings
LIGHTNING_COLOR = ELECTRIC_BLUE 
LIGHTNING_DAMAGE = 100
LIGHTNING_LIFETIME = 20 
LIGHTNING_COOLDOWN = 750 
LIGHTNING_ZAP_RANGE = 250 

LIGHTNING_BASE_THICKNESS = 5        
LIGHTNING_CORE_THICKNESS_RATIO = 0.4 
LIGHTNING_SEGMENTS = 12             
LIGHTNING_MAX_OFFSET = 18           
LIGHTNING_CORE_OFFSET_RATIO = 0.3   
LIGHTNING_CORE_COLOR = WHITE        
LIGHTNING_BRANCH_CHANCE = 0.25      
LIGHTNING_BRANCH_MAX_SEGMENTS = 5   
LIGHTNING_BRANCH_MAX_OFFSET = 10    
LIGHTNING_BRANCH_THICKNESS_RATIO = 0.5 

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
WEAPON_MODE_HEATSEEKER = 7 
WEAPON_MODE_HEATSEEKER_PLUS_BULLETS = 8 
WEAPON_MODE_LIGHTNING = 9

INITIAL_WEAPON_MODE = WEAPON_MODE_DEFAULT 

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

WEAPON_MODE_NAMES = { 
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

WEAPON_MODE_ICONS = { 
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
PHANTOM_CLOAK_ALPHA_SETTING = 70 

# ==========================
# Enemy Base Settings
# ==========================
ENEMY_SPEED = 1.5
ENEMY_HEALTH = 100
ENEMY_COLOR = RED 
REGULAR_ENEMY_SPRITE_PATH = "assets/images/enemies/TR-3B_enemy.png"
ENEMY_BULLET_SPEED = 5
ENEMY_BULLET_COOLDOWN = 1500 
ENEMY_BULLET_LIFETIME = 75   
ENEMY_BULLET_COLOR = ORANGE
ENEMY_BULLET_DAMAGE = 10

# Architect's Vault Prototype Drone Settings (Example of specific enemy type)
PROTOTYPE_DRONE_HEALTH = 150
PROTOTYPE_DRONE_SPEED = 2.0
PROTOTYPE_DRONE_COLOR = MAGENTA 
PROTOTYPE_DRONE_SHOOT_COOLDOWN = 1200
PROTOTYPE_DRONE_BULLET_SPEED = 6
PROTOTYPE_DRONE_SPRITE_PATH = "assets/images/enemies/prototype_enemy.png" # CORRECTED PATH

# ==========================
# MAZE_GUARDIAN Boss Settings
# ==========================
MAZE_GUARDIAN_HEALTH = 5000
MAZE_GUARDIAN_SPEED = 1.0 
MAZE_GUARDIAN_COLOR = (80, 0, 120) 
MAZE_GUARDIAN_SPRITE_PATH = "assets/images/enemies/maze_guardian.png" 
MAZE_GUARDIAN_BULLET_SPEED = 6
MAZE_GUARDIAN_BULLET_LIFETIME = 80
MAZE_GUARDIAN_BULLET_COLOR = RED
MAZE_GUARDIAN_BULLET_DAMAGE = 15

MAZE_GUARDIAN_LASER_DAMAGE = 20 
MAZE_GUARDIAN_LASER_COOLDOWN = 5000 
MAZE_GUARDIAN_LASER_SWEEP_ARC = 90 

MAZE_GUARDIAN_SHIELD_DURATION_MS = 6000 
MAZE_GUARDIAN_SHIELD_COOLDOWN_MS = 10000 

MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS = 3000 
MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS = 1000 
MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS = 7000 

# Sentinel Drone (Mini-drone summoned by MazeGuardian)
SENTINEL_DRONE_HEALTH = 75
SENTINEL_DRONE_SPEED = 3.0
SENTINEL_DRONE_SPRITE_PATH = "assets/images/enemies/sentinel_drone.png" 


# ==========================
# Power-up & Collectible Settings
# ==========================
POWERUP_SIZE = TILE_SIZE // 3 
POWERUP_SPAWN_CHANCE = 0.05 
MAX_POWERUPS_ON_SCREEN = 2 
WEAPON_UPGRADE_ITEM_LIFETIME = 15000 
POWERUP_ITEM_LIFETIME = 12000      

POWERUP_TYPES = { 
    "shield": {
        "color": LIGHT_BLUE,
        "image_filename": "shield_icon.png", 
        "duration": 10000 
    },
    "speed_boost": {
        "color": GREEN,
        "image_filename": "speed_icon.png",
        "duration": 7000, 
        "multiplier": 1.8 
    },
    "weapon_upgrade": { 
        "color": BLUE,
        "image_filename": "weapon_icon.png"
    }
}
SHIELD_POWERUP_DURATION = POWERUP_TYPES["shield"]["duration"]
SPEED_BOOST_POWERUP_DURATION = POWERUP_TYPES["speed_boost"]["duration"]

# ==========================
# Core Fragment & Architect's Vault Settings
# ==========================
TOTAL_CORE_FRAGMENTS_NEEDED = 3 
CORE_FRAGMENT_VISUAL_SIZE = TILE_SIZE // 2.5 

CORE_FRAGMENT_DETAILS = { 
    "fragment_alpha": {
        "id": "cf_alpha", "name": "Alpha Core Fragment", "icon_filename": "core_fragment_alpha.png",
        "description": "A corrupted fragment, pulses with unstable energy.",
        "spawn_info": {"level": 1}, 
        "buff": {"type": "speed", "value": 1.05} 
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
        "buff_alt": {"type": "damage_reduction", "value": 0.05} 
    },
    "fragment_vault_core": { 
        "id": "vault_core", "name": "Vault Core", "icon_filename": "vault_core_icon.png",
        "description": "The heart of the Architect's Vault defenses. A valuable prize.",
        "display_color": GOLD 
    }
}

ARCHITECT_VAULT_EXTRACTION_TIMER_MS = 90000 
ARCHITECT_VAULT_GAUNTLET_WAVES = 3
ARCHITECT_VAULT_DRONES_PER_WAVE = [3, 4, 5] 

ARCHITECT_REWARD_BLUEPRINT_ID = "DRONE_ARCHITECT_X" 
ARCHITECT_REWARD_LORE_ID = "lore_architect_origin"  

# ==========================
# Game Progression & Miscellaneous
# ==========================
LEVEL_TIMER_DURATION = 150000  
BONUS_LEVEL_DURATION_MS = 60000 

# Leaderboard Settings
LEADERBOARD_FILE_NAME = "leaderboard.json" 
LEADERBOARD_MAX_ENTRIES = 10               

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

GAME_STATE_BONUS_LEVEL_TRANSITION = "bonus_level_transition" 
GAME_STATE_BONUS_LEVEL_START = "bonus_level_start" 
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

DEFAULT_SETTINGS = {
    "WIDTH": WIDTH, "HEIGHT": HEIGHT, "FPS": FPS, "FULLSCREEN_MODE": FULLSCREEN_MODE,
    "BOTTOM_PANEL_HEIGHT": BOTTOM_PANEL_HEIGHT,
    "TILE_SIZE": TILE_SIZE,
    "PLAYER_MAX_HEALTH": PLAYER_MAX_HEALTH, "PLAYER_LIVES": PLAYER_LIVES,
    "PLAYER_SPEED": PLAYER_SPEED, "ROTATION_SPEED": ROTATION_SPEED,
    "PLAYER_INVINCIBILITY": PLAYER_INVINCIBILITY, 
    "PLAYER_DEFAULT_BULLET_SIZE": PLAYER_DEFAULT_BULLET_SIZE, "PLAYER_BIG_BULLET_SIZE": PLAYER_BIG_BULLET_SIZE,
    "PLAYER_BULLET_COLOR": PLAYER_BULLET_COLOR, "PLAYER_BULLET_SPEED": PLAYER_BULLET_SPEED,
    "PLAYER_BULLET_LIFETIME": PLAYER_BULLET_LIFETIME,
    "PLAYER_BASE_SHOOT_COOLDOWN": PLAYER_BASE_SHOOT_COOLDOWN, "PLAYER_RAPID_FIRE_COOLDOWN": PLAYER_RAPID_FIRE_COOLDOWN,
    "BOUNCING_BULLET_MAX_BOUNCES": BOUNCING_BULLET_MAX_BOUNCES, "PIERCING_BULLET_MAX_PIERCES": PIERCING_BULLET_MAX_PIERCES,
    "MISSILE_COLOR": MISSILE_COLOR, "MISSILE_SPEED": MISSILE_SPEED, "MISSILE_LIFETIME": MISSILE_LIFETIME,
    "MISSILE_SIZE": MISSILE_SIZE, "MISSILE_TURN_RATE": MISSILE_TURN_RATE, "MISSILE_COOLDOWN": MISSILE_COOLDOWN, "MISSILE_DAMAGE": MISSILE_DAMAGE,
    
    "LIGHTNING_COLOR": LIGHTNING_COLOR, "LIGHTNING_DAMAGE": LIGHTNING_DAMAGE, "LIGHTNING_LIFETIME": LIGHTNING_LIFETIME,
    "LIGHTNING_COOLDOWN": LIGHTNING_COOLDOWN, "LIGHTNING_ZAP_RANGE": LIGHTNING_ZAP_RANGE,
    "LIGHTNING_BASE_THICKNESS": LIGHTNING_BASE_THICKNESS, 
    "LIGHTNING_CORE_THICKNESS_RATIO": LIGHTNING_CORE_THICKNESS_RATIO, 
    "LIGHTNING_SEGMENTS": LIGHTNING_SEGMENTS, 
    "LIGHTNING_MAX_OFFSET": LIGHTNING_MAX_OFFSET, 
    "LIGHTNING_CORE_OFFSET_RATIO": LIGHTNING_CORE_OFFSET_RATIO, 
    "LIGHTNING_CORE_COLOR": LIGHTNING_CORE_COLOR, 
    "LIGHTNING_BRANCH_CHANCE": LIGHTNING_BRANCH_CHANCE, 
    "LIGHTNING_BRANCH_MAX_SEGMENTS": LIGHTNING_BRANCH_MAX_SEGMENTS, 
    "LIGHTNING_BRANCH_MAX_OFFSET": LIGHTNING_BRANCH_MAX_OFFSET, 
    "LIGHTNING_BRANCH_THICKNESS_RATIO": LIGHTNING_BRANCH_THICKNESS_RATIO, 

    "INITIAL_WEAPON_MODE": INITIAL_WEAPON_MODE,
    "PHANTOM_CLOAK_DURATION_MS": PHANTOM_CLOAK_DURATION_MS, "PHANTOM_CLOAK_COOLDOWN_MS": PHANTOM_CLOAK_COOLDOWN_MS,
    "PHANTOM_CLOAK_ALPHA_SETTING": PHANTOM_CLOAK_ALPHA_SETTING,
    "ENEMY_SPEED": ENEMY_SPEED, "ENEMY_HEALTH": ENEMY_HEALTH, "ENEMY_COLOR": ENEMY_COLOR,
    "ENEMY_BULLET_SPEED": ENEMY_BULLET_SPEED, "ENEMY_BULLET_COOLDOWN": ENEMY_BULLET_COOLDOWN,
    "ENEMY_BULLET_LIFETIME": ENEMY_BULLET_LIFETIME, "ENEMY_BULLET_COLOR": ENEMY_BULLET_COLOR, "ENEMY_BULLET_DAMAGE": ENEMY_BULLET_DAMAGE,
    "PROTOTYPE_DRONE_HEALTH": PROTOTYPE_DRONE_HEALTH, "PROTOTYPE_DRONE_SPEED": PROTOTYPE_DRONE_SPEED,
    "PROTOTYPE_DRONE_SHOOT_COOLDOWN": PROTOTYPE_DRONE_SHOOT_COOLDOWN, "PROTOTYPE_DRONE_BULLET_SPEED": PROTOTYPE_DRONE_BULLET_SPEED,
    "PROTOTYPE_DRONE_SPRITE_PATH": PROTOTYPE_DRONE_SPRITE_PATH, # Path updated here
    
    "MAZE_GUARDIAN_HEALTH": MAZE_GUARDIAN_HEALTH, "MAZE_GUARDIAN_SPEED": MAZE_GUARDIAN_SPEED,
    "MAZE_GUARDIAN_COLOR": MAZE_GUARDIAN_COLOR, "MAZE_GUARDIAN_SPRITE_PATH": MAZE_GUARDIAN_SPRITE_PATH,
    "MAZE_GUARDIAN_BULLET_SPEED": MAZE_GUARDIAN_BULLET_SPEED, "MAZE_GUARDIAN_BULLET_LIFETIME": MAZE_GUARDIAN_BULLET_LIFETIME,
    "MAZE_GUARDIAN_BULLET_COLOR": MAZE_GUARDIAN_BULLET_COLOR, "MAZE_GUARDIAN_BULLET_DAMAGE": MAZE_GUARDIAN_BULLET_DAMAGE,
    "MAZE_GUARDIAN_LASER_DAMAGE": MAZE_GUARDIAN_LASER_DAMAGE, "MAZE_GUARDIAN_LASER_COOLDOWN": MAZE_GUARDIAN_LASER_COOLDOWN,
    "MAZE_GUARDIAN_LASER_SWEEP_ARC": MAZE_GUARDIAN_LASER_SWEEP_ARC,
    "MAZE_GUARDIAN_SHIELD_DURATION_MS": MAZE_GUARDIAN_SHIELD_DURATION_MS, "MAZE_GUARDIAN_SHIELD_COOLDOWN_MS": MAZE_GUARDIAN_SHIELD_COOLDOWN_MS,
    "MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS": MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS,
    "MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS": MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS,
    "MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS": MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS,
    "SENTINEL_DRONE_HEALTH": SENTINEL_DRONE_HEALTH, "SENTINEL_DRONE_SPEED": SENTINEL_DRONE_SPEED,
    "SENTINEL_DRONE_SPRITE_PATH": SENTINEL_DRONE_SPRITE_PATH,

    "POWERUP_SPAWN_CHANCE": POWERUP_SPAWN_CHANCE, "MAX_POWERUPS_ON_SCREEN": MAX_POWERUPS_ON_SCREEN,
    "WEAPON_UPGRADE_ITEM_LIFETIME": WEAPON_UPGRADE_ITEM_LIFETIME, "POWERUP_ITEM_LIFETIME": POWERUP_ITEM_LIFETIME,
    "SHIELD_POWERUP_DURATION": SHIELD_POWERUP_DURATION, "SPEED_BOOST_POWERUP_DURATION": SPEED_BOOST_POWERUP_DURATION,
    "REGULAR_ENEMY_SPRITE_PATH" : REGULAR_ENEMY_SPRITE_PATH,
    "LEVEL_TIMER_DURATION": LEVEL_TIMER_DURATION,
    "BONUS_LEVEL_DURATION_MS": BONUS_LEVEL_DURATION_MS,
    "LEADERBOARD_MAX_ENTRIES": LEADERBOARD_MAX_ENTRIES, "LEADERBOARD_FILE_NAME": LEADERBOARD_FILE_NAME,
}

SETTINGS_MODIFIED = False
_CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()

def get_game_setting(key, default_override=None): 
    if key not in _CURRENT_GAME_SETTINGS and default_override is not None:
        return default_override
    return _CURRENT_GAME_SETTINGS.get(key, DEFAULT_SETTINGS.get(key))


def set_game_setting(key, value):
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    global GAME_PLAY_AREA_HEIGHT, MAZE_ROWS 

    if key in _CURRENT_GAME_SETTINGS or key == "PLAYER_INVINCIBILITY": 
        _CURRENT_GAME_SETTINGS[key] = value
        if _CURRENT_GAME_SETTINGS.get(key) != DEFAULT_SETTINGS.get(key): 
            SETTINGS_MODIFIED = True
        else:
            SETTINGS_MODIFIED = any(
                _CURRENT_GAME_SETTINGS.get(k) != DEFAULT_SETTINGS.get(k)
                for k in DEFAULT_SETTINGS if k in _CURRENT_GAME_SETTINGS 
            )
            if "PLAYER_INVINCIBILITY" in _CURRENT_GAME_SETTINGS and \
               _CURRENT_GAME_SETTINGS["PLAYER_INVINCIBILITY"] != DEFAULT_SETTINGS.get("PLAYER_INVINCIBILITY", False): 
                SETTINGS_MODIFIED = True


        if key in globals(): 
            globals()[key] = value
            if key == "HEIGHT" or key == "BOTTOM_PANEL_HEIGHT":
                GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
                globals()["GAME_PLAY_AREA_HEIGHT"] = GAME_PLAY_AREA_HEIGHT 
                if get_game_setting("TILE_SIZE") > 0:
                    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // get_game_setting("TILE_SIZE")
                    globals()["MAZE_ROWS"] = MAZE_ROWS
            elif key == "TILE_SIZE":
                if get_game_setting("TILE_SIZE") > 0: 
                    current_game_play_height = get_game_setting("GAME_PLAY_AREA_HEIGHT") 
                    MAZE_ROWS = current_game_play_height // get_game_setting("TILE_SIZE")
                    globals()["MAZE_ROWS"] = MAZE_ROWS
    else:
        print(f"Warning (game_settings.py): Attempted to set an unknown game setting '{key}'.")

def reset_all_settings_to_default():
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    global GAME_PLAY_AREA_HEIGHT, MAZE_ROWS

    _CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()
    _CURRENT_GAME_SETTINGS["PLAYER_INVINCIBILITY"] = DEFAULT_SETTINGS.get("PLAYER_INVINCIBILITY", False)

    SETTINGS_MODIFIED = False
    print("Game settings have been reset to defaults.")

    for key, value in _CURRENT_GAME_SETTINGS.items():
        if key in globals():
            globals()[key] = value

    GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
    globals()["GAME_PLAY_AREA_HEIGHT"] = GAME_PLAY_AREA_HEIGHT
    if get_game_setting("TILE_SIZE") > 0:
        MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // get_game_setting("TILE_SIZE")
        globals()["MAZE_ROWS"] = MAZE_ROWS
    else: 
        MAZE_ROWS = 0
        globals()["MAZE_ROWS"] = MAZE_ROWS


GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
if TILE_SIZE > 0:
    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE
else:
    MAZE_ROWS = 0
    print("Warning (game_settings.py): TILE_SIZE is 0 or invalid, MAZE_ROWS set to 0.")

