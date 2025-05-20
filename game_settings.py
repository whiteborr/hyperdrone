# game_settings.py

# ==========================
# General Settings
# ==========================
WIDTH = 1920
HEIGHT = 1080
FPS = 60
BOTTOM_PANEL_HEIGHT = 120
GAME_PLAY_AREA_HEIGHT = HEIGHT - BOTTOM_PANEL_HEIGHT

# ==========================
# Tile & Maze Settings
# ==========================
TILE_SIZE = 80
MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE

# ==========================
# Color Definitions
# ==========================
BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
CYAN = (0, 255, 255)
DARK_RED = (100, 0, 0)
ELECTRIC_BLUE = (0, 128, 255)
GOLD = (255, 215, 0)
GREEN = (0, 255, 0)
GREY = (100, 100, 100)
LIGHT_BLUE = (173, 216, 230)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PINK = (255, 192, 203)
PURPLE = (128, 0, 128)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
PHANTOM_CLOAK_ALPHA_SETTING = 70

# ==========================
# Player Settings
# ==========================
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 3
PLAYER_LIVES = 3
ROTATION_SPEED = 5

PLAYER_BULLET_COLOR = (255, 200, 0)
PLAYER_BULLET_SPEED = 5
PLAYER_BULLET_LIFETIME = 100
PLAYER_DEFAULT_BULLET_SIZE = 4
PLAYER_BIG_BULLET_SIZE = PLAYER_DEFAULT_BULLET_SIZE * 4
PLAYER_BASE_SHOOT_COOLDOWN = 500
PLAYER_RAPID_FIRE_COOLDOWN = 150

BOUNCING_BULLET_MAX_BOUNCES = 2
PIERCING_BULLET_MAX_PIERCES = 1

MISSILE_COLOR = (200, 0, 200)
MISSILE_SPEED = PLAYER_BULLET_SPEED * 0.8
MISSILE_LIFETIME = PLAYER_BULLET_LIFETIME * 8
MISSILE_SIZE = 8
MISSILE_TURN_RATE = 4
MISSILE_COOLDOWN = 5000
MISSILE_DAMAGE = 50

LIGHTNING_COLOR = ELECTRIC_BLUE
LIGHTNING_DAMAGE = 15
LIGHTNING_LIFETIME = 60
LIGHTNING_COOLDOWN = 750
LIGHTNING_ZAP_RANGE = 250

# ==========================
# Weapon Modes
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
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
]

WEAPON_MODE_NAMES = {
    WEAPON_MODE_DEFAULT: "Single Shot", WEAPON_MODE_TRI_SHOT: "Tri-Shot",
    WEAPON_MODE_RAPID_SINGLE: "Rapid Single", WEAPON_MODE_RAPID_TRI: "Rapid Tri-Shot",
    WEAPON_MODE_BIG_SHOT: "Big Shot", WEAPON_MODE_BOUNCE: "Bounce Shot",
    WEAPON_MODE_PIERCE: "Pierce Shot", WEAPON_MODE_HEATSEEKER: "Heatseeker",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "Seeker + Rapid",
    WEAPON_MODE_LIGHTNING: "Lightning"
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
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "🚀🔫",
    WEAPON_MODE_LIGHTNING: "⚡",
}

# ==========================
# Enemy Settings
# ==========================
ENEMY_SPEED = 1.5
ENEMY_HEALTH = 100
ENEMY_COLOR = RED
ENEMY_BULLET_SPEED = 5
ENEMY_BULLET_COOLDOWN = 1500
ENEMY_BULLET_LIFETIME = 75
ENEMY_BULLET_COLOR = (255, 100, 0)
ENEMY_BULLET_DAMAGE = 10

# ==========================
# Power-up Settings
# ==========================
POWERUP_SIZE = TILE_SIZE // 3
POWERUP_SPAWN_CHANCE = 0.15
MAX_POWERUPS_ON_SCREEN = 1
WEAPON_UPGRADE_ITEM_LIFETIME = 15000
POWERUP_ITEM_LIFETIME = 12000

POWERUP_TYPES = {
    "shield": {"color": LIGHT_BLUE, "image_filename": "shield_icon.png", "duration": 35000},
    "speed_boost": {"color": GREEN, "image_filename": "speed_icon.png", "duration": 10000, "multiplier": 2.0},
    "weapon_upgrade": {"color": BLUE, "image_filename": "weapon_icon.png"}
}
SHIELD_POWERUP_DURATION = POWERUP_TYPES["shield"]["duration"]
SPEED_BOOST_POWERUP_DURATION = POWERUP_TYPES["speed_boost"]["duration"]

# ==========================
# Secret Blueprint Settings
# ==========================
TOTAL_CORE_FRAGMENTS_NEEDED = 3 # How many unique fragments to collect for the bonus

CORE_FRAGMENT_DETAILS = {
    "fragment_01": {
        "id": "cf_alpha", # Unique ID for this fragment
        "name": "Alpha Core Fragment",
        "icon_filename": "core_fragment_alpha.png", # Place in assets/images/collectibles/ or assets/drones/
        "description": "A corrupted fragment, pulses with unstable energy.",
        "spawn_info": {
            "level": 1, # Level this fragment can be found in
            # IMPORTANT: Update these tile_x, tile_y to valid hidden spots in your levels
            "tile_x": 2,# Replace with actual X coordinate (e.g., from your console print)
            "tile_y": 8 # Replace with actual Y coordinate (e.g., from your console print)
        }
    },
    "fragment_02": {
        "id": "cf_beta",
        "name": "Beta Core Fragment",
        "icon_filename": "core_fragment_beta.png",
        "description": "This piece hums with a strange, alien resonance.",
        "spawn_info": {
            "level": 2,
            "tile_x": 2, # Replace with actual X coordinate for Level 2
            "tile_y": 8  # Replace with actual Y coordinate for Level 2
        }
    },
    "fragment_03": {
        "id": "cf_gamma",
        "name": "Gamma Core Fragment",
        "icon_filename": "core_fragment_gamma.png",
        "description": "Seems to be a critical processing unit, heavily damaged.",
        "spawn_info": {
            "level": 3,
            "tile_x": 2,# Replace with actual X coordinate for Level 3
            "tile_y": 8 # Replace with actual Y coordinate for Level 3
        }
    }
}

# ==========================
# Miscellaneous
# ==========================
LEVEL_TIMER_DURATION = 150000
LEADERBOARD_MAX_ENTRIES = 10
LEADERBOARD_FILE_NAME = "leaderboard.json"

GAME_STATE_MAIN_MENU = "main_menu"
GAME_STATE_PLAYING = "playing"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_LEADERBOARD = "leaderboard_display"
GAME_STATE_ENTER_NAME = "enter_name"
GAME_STATE_SETTINGS = "settings_menu"
GAME_STATE_DRONE_SELECT = "drone_select_menu"
# New Game States for Bonus Level
GAME_STATE_BONUS_LEVEL_TRANSITION = "bonus_level_transition"
GAME_STATE_BONUS_LEVEL_START = "bonus_level_start"
GAME_STATE_BONUS_LEVEL_PLAYING = "bonus_level_playing"


try:
    from drone_configs import PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS
except ImportError:
    print("Warning (game_settings.py): Could not import from drone_configs. Using fallback values for cloak.")
    PHANTOM_CLOAK_DURATION_MS = 5000
    PHANTOM_CLOAK_COOLDOWN_MS = 15000

DEFAULT_SETTINGS = {
    "WIDTH": WIDTH,
    "HEIGHT": HEIGHT,
    "BOTTOM_PANEL_HEIGHT": BOTTOM_PANEL_HEIGHT,
    "GAME_PLAY_AREA_HEIGHT": GAME_PLAY_AREA_HEIGHT,
    "PLAYER_MAX_HEALTH": PLAYER_MAX_HEALTH,
    "PLAYER_LIVES": PLAYER_LIVES,
    "PLAYER_SPEED": PLAYER_SPEED,
    "ROTATION_SPEED": ROTATION_SPEED,
    "INITIAL_WEAPON_MODE": INITIAL_WEAPON_MODE,
    "WEAPON_MODES_SEQUENCE": WEAPON_MODES_SEQUENCE,
    "WEAPON_MODE_NAMES": WEAPON_MODE_NAMES,
    "PLAYER_BULLET_SPEED": PLAYER_BULLET_SPEED,
    "PLAYER_BULLET_LIFETIME": PLAYER_BULLET_LIFETIME,
    "PLAYER_DEFAULT_BULLET_SIZE": PLAYER_DEFAULT_BULLET_SIZE,
    "PLAYER_BIG_BULLET_SIZE": PLAYER_BIG_BULLET_SIZE,
    "PLAYER_BASE_SHOOT_COOLDOWN": PLAYER_BASE_SHOOT_COOLDOWN,
    "PLAYER_RAPID_FIRE_COOLDOWN": PLAYER_RAPID_FIRE_COOLDOWN,
    "PLAYER_BULLET_COLOR": PLAYER_BULLET_COLOR,
    "BOUNCING_BULLET_MAX_BOUNCES": BOUNCING_BULLET_MAX_BOUNCES,
    "PIERCING_BULLET_MAX_PIERCES": PIERCING_BULLET_MAX_PIERCES,
    "MISSILE_SPEED": MISSILE_SPEED,
    "MISSILE_LIFETIME": MISSILE_LIFETIME,
    "MISSILE_COOLDOWN": MISSILE_COOLDOWN,
    "MISSILE_DAMAGE": MISSILE_DAMAGE,
    "MISSILE_TURN_RATE": MISSILE_TURN_RATE,
    "LIGHTNING_COLOR": LIGHTNING_COLOR,
    "LIGHTNING_DAMAGE": LIGHTNING_DAMAGE,
    "LIGHTNING_LIFETIME": LIGHTNING_LIFETIME,
    "LIGHTNING_COOLDOWN": LIGHTNING_COOLDOWN,
    "LIGHTNING_ZAP_RANGE": LIGHTNING_ZAP_RANGE,
    "ENEMY_SPEED": ENEMY_SPEED,
    "ENEMY_HEALTH": ENEMY_HEALTH,
    "LEVEL_TIMER_DURATION": LEVEL_TIMER_DURATION,
    "POWERUP_TYPES": POWERUP_TYPES,
    "SHIELD_POWERUP_DURATION": SHIELD_POWERUP_DURATION,
    "SPEED_BOOST_POWERUP_DURATION": SPEED_BOOST_POWERUP_DURATION,
    "PHANTOM_CLOAK_DURATION_MS": PHANTOM_CLOAK_DURATION_MS,
    "PHANTOM_CLOAK_COOLDOWN_MS": PHANTOM_CLOAK_COOLDOWN_MS,
    "PHANTOM_CLOAK_ALPHA": PHANTOM_CLOAK_ALPHA_SETTING,
    "TILE_SIZE": TILE_SIZE,
    "TOTAL_CORE_FRAGMENTS_NEEDED": TOTAL_CORE_FRAGMENTS_NEEDED,
    "CORE_FRAGMENT_DETAILS": CORE_FRAGMENT_DETAILS,
    "GAME_STATE_MAIN_MENU": GAME_STATE_MAIN_MENU,
    "GAME_STATE_PLAYING": GAME_STATE_PLAYING,
    "GAME_STATE_GAME_OVER": GAME_STATE_GAME_OVER,
    "GAME_STATE_LEADERBOARD": GAME_STATE_LEADERBOARD,
    "GAME_STATE_ENTER_NAME": GAME_STATE_ENTER_NAME,
    "GAME_STATE_SETTINGS": GAME_STATE_SETTINGS,
    "GAME_STATE_DRONE_SELECT": GAME_STATE_DRONE_SELECT,
    "GAME_STATE_BONUS_LEVEL_TRANSITION": GAME_STATE_BONUS_LEVEL_TRANSITION,
    "GAME_STATE_BONUS_LEVEL_START": GAME_STATE_BONUS_LEVEL_START,
    "GAME_STATE_BONUS_LEVEL_PLAYING": GAME_STATE_BONUS_LEVEL_PLAYING,
}

SETTINGS_MODIFIED = False
_CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()

def set_game_setting(key, value):
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    if key in _CURRENT_GAME_SETTINGS:
        _CURRENT_GAME_SETTINGS[key] = value
        SETTINGS_MODIFIED = any(
            _CURRENT_GAME_SETTINGS[k] != v for k, v in DEFAULT_SETTINGS.items() if k in _CURRENT_GAME_SETTINGS
        )
        if key in globals():
            globals()[key] = value
            if key in {"HEIGHT", "BOTTOM_PANEL_HEIGHT"}:
                globals()["GAME_PLAY_AREA_HEIGHT"] = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
                globals()["MAZE_ROWS"] = globals()["GAME_PLAY_AREA_HEIGHT"] // get_game_setting("TILE_SIZE")
            elif key == "PLAYER_BULLET_SPEED":
                globals()["MISSILE_SPEED"] = get_game_setting("PLAYER_BULLET_SPEED") * 0.8
            elif key == "PLAYER_BULLET_LIFETIME":
                globals()["MISSILE_LIFETIME"] = get_game_setting("PLAYER_BULLET_LIFETIME") * 8
    else:
        print(f"Warning: Attempted to set an unknown game setting '{key}'.")

def get_game_setting(key):
    if key in _CURRENT_GAME_SETTINGS:
        return _CURRENT_GAME_SETTINGS[key]
    if key in globals():
        return globals()[key]
    return DEFAULT_SETTINGS.get(key)

for key, value in DEFAULT_SETTINGS.items():
    if key not in globals():
        globals()[key] = value

GAME_PLAY_AREA_HEIGHT = get_game_setting("HEIGHT") - get_game_setting("BOTTOM_PANEL_HEIGHT")
MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // get_game_setting("TILE_SIZE")
if get_game_setting("PLAYER_BULLET_SPEED") is not None:
    MISSILE_SPEED = get_game_setting("PLAYER_BULLET_SPEED") * 0.8
if get_game_setting("PLAYER_BULLET_LIFETIME") is not None:
    MISSILE_LIFETIME = get_game_setting("PLAYER_BULLET_LIFETIME") * 8

if 'WEAPON_MODES_SEQUENCE' not in globals() and 'WEAPON_MODES_SEQUENCE' in DEFAULT_SETTINGS:
    globals()['WEAPON_MODES_SEQUENCE'] = DEFAULT_SETTINGS['WEAPON_MODES_SEQUENCE']
if 'WEAPON_MODE_NAMES' not in globals() and 'WEAPON_MODE_NAMES' in DEFAULT_SETTINGS:
    globals()['WEAPON_MODE_NAMES'] = DEFAULT_SETTINGS['WEAPON_MODE_NAMES']
if 'POWERUP_TYPES' not in globals() and 'POWERUP_TYPES' in DEFAULT_SETTINGS:
    globals()['POWERUP_TYPES'] = DEFAULT_SETTINGS['POWERUP_TYPES']
if 'CORE_FRAGMENT_DETAILS' not in globals() and 'CORE_FRAGMENT_DETAILS' in DEFAULT_SETTINGS:
    globals()['CORE_FRAGMENT_DETAILS'] = DEFAULT_SETTINGS['CORE_FRAGMENT_DETAILS']