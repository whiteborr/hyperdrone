# ==========================
# Screen & Game Settings
# ==========================
WIDTH = 1920
HEIGHT = 1080
FPS = 60

# ==========================
# Tile & Maze Settings
# ==========================
TILE_SIZE = 80
MAZE_ROWS = HEIGHT // TILE_SIZE

# ==========================
# Basic Colors
# ==========================
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
RED     = (255, 0, 0)
GREEN   = (0, 255, 0)
BLUE    = (0, 100, 255)
CYAN    = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW  = (255, 255, 0)
ORANGE  = (255, 165, 0)
PURPLE  = (128, 0, 128)
PINK    = (255, 192, 203)
LIGHT_BLUE = (173, 216, 230)
GOLD = (255, 215, 0)
ELECTRIC_BLUE = (0, 128, 255)
DARK_RED = (100, 0, 0)
GREY = (100, 100, 100)
PHANTOM_CLOAK_ALPHA_SETTING = 70

# ==========================
# Player Base Settings
# ==========================
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 3
PLAYER_LIVES = 3
ROTATION_SPEED = 5

# ==========================
# Bullet Settings - Player
# ==========================
PLAYER_BULLET_COLOR = (255, 200, 0)
PLAYER_BULLET_SPEED = 5
PLAYER_BULLET_LIFETIME = 100
PLAYER_DEFAULT_BULLET_SIZE = 4
PLAYER_BIG_BULLET_SIZE = PLAYER_DEFAULT_BULLET_SIZE * 4
PLAYER_BASE_SHOOT_COOLDOWN = 500
PLAYER_RAPID_FIRE_COOLDOWN = 150

BOUNCING_BULLET_MAX_BOUNCES = 2
PIERCING_BULLET_MAX_PIERCES = 1

# ==========================
# Missile Settings - Player
# ==========================
MISSILE_COLOR = (200, 0, 200)
MISSILE_SPEED = PLAYER_BULLET_SPEED * 0.8
MISSILE_LIFETIME = PLAYER_BULLET_LIFETIME * 8 
MISSILE_SIZE = 8
MISSILE_TURN_RATE = 4
MISSILE_COOLDOWN = 5000
MISSILE_DAMAGE = 50

# ==========================
# Lightning Bullet Settings - Player (New "Zap" Version)
# ==========================
LIGHTNING_COLOR = ELECTRIC_BLUE
LIGHTNING_DAMAGE = 15
LIGHTNING_LIFETIME = 60  # Increased lifetime for visual zap effect (frames)
LIGHTNING_COOLDOWN = 750
LIGHTNING_ZAP_RANGE = 250

# ==========================
# Weapon Modes - Player
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

# ==========================
# Enemy Settings
# ==========================
ENEMY_SPEED = 1.5
ENEMY_HEALTH = 100
ENEMY_COLOR = (255, 0, 0)

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
    "shield": { "color": LIGHT_BLUE, "image_filename": "shield_icon.png", "duration": 35000 },
    "speed_boost": { "color": GREEN, "image_filename": "speed_icon.png", "duration": 10000, "multiplier": 2.0 },
    "weapon_upgrade": { "color": BLUE, "image_filename": "weapon_icon.png" }
}
SHIELD_POWERUP_DURATION = POWERUP_TYPES["shield"]["duration"]
SPEED_BOOST_POWERUP_DURATION = POWERUP_TYPES["speed_boost"]["duration"]

# ==========================
# Level Timer Settings
# ==========================
LEVEL_TIMER_DURATION = 150000

# ==========================
# Leaderboard Settings
# ==========================
LEADERBOARD_MAX_ENTRIES = 10
LEADERBOARD_FILE_NAME = "leaderboard.json"

# ==========================
# Game States
# ==========================
GAME_STATE_MAIN_MENU = "main_menu"
GAME_STATE_PLAYING = "playing"
GAME_STATE_GAME_OVER = "game_over"
GAME_STATE_LEADERBOARD = "leaderboard_display"
GAME_STATE_ENTER_NAME = "enter_name"
GAME_STATE_SETTINGS = "settings_menu"
GAME_STATE_DRONE_SELECT = "drone_select_menu"

from drone_configs import PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS

DEFAULT_SETTINGS = {
    # Screen dimensions
    "WIDTH": WIDTH,
    "HEIGHT": HEIGHT,

    # Player stats
    "PLAYER_MAX_HEALTH": PLAYER_MAX_HEALTH,
    "PLAYER_LIVES": PLAYER_LIVES,
    "PLAYER_SPEED": PLAYER_SPEED,

    # Weapon mode
    "INITIAL_WEAPON_MODE": INITIAL_WEAPON_MODE,

    # Player bullets
    "PLAYER_BULLET_SPEED": PLAYER_BULLET_SPEED,
    "PLAYER_BULLET_LIFETIME": PLAYER_BULLET_LIFETIME,
    "PLAYER_DEFAULT_BULLET_SIZE": PLAYER_DEFAULT_BULLET_SIZE,
    "PLAYER_BIG_BULLET_SIZE": PLAYER_BIG_BULLET_SIZE,
    "PLAYER_BASE_SHOOT_COOLDOWN": PLAYER_BASE_SHOOT_COOLDOWN,
    "PLAYER_RAPID_FIRE_COOLDOWN": PLAYER_RAPID_FIRE_COOLDOWN,

    # Missile settings
    "MISSILE_SPEED": PLAYER_BULLET_SPEED * 0.8,
    "MISSILE_LIFETIME": PLAYER_BULLET_LIFETIME * 8,
    "MISSILE_COOLDOWN": MISSILE_COOLDOWN,
    "MISSILE_DAMAGE": MISSILE_DAMAGE,

    # Enemy settings
    "ENEMY_SPEED": ENEMY_SPEED,
    "ENEMY_HEALTH": ENEMY_HEALTH,

    # Level timer
    "LEVEL_TIMER_DURATION": LEVEL_TIMER_DURATION,

    # Power-up durations
    "SHIELD_POWERUP_DURATION": SHIELD_POWERUP_DURATION,
    "SPEED_BOOST_POWERUP_DURATION": SPEED_BOOST_POWERUP_DURATION,

    # Phantom Cloak
    "PHANTOM_CLOAK_DURATION_MS": PHANTOM_CLOAK_DURATION_MS,
    "PHANTOM_CLOAK_COOLDOWN_MS": PHANTOM_CLOAK_COOLDOWN_MS,
    "PHANTOM_CLOAK_ALPHA": PHANTOM_CLOAK_ALPHA_SETTING,

    # Lightning weapon
    "LIGHTNING_COLOR": LIGHTNING_COLOR,
    "LIGHTNING_DAMAGE": LIGHTNING_DAMAGE,
    "LIGHTNING_LIFETIME": LIGHTNING_LIFETIME,
    "LIGHTNING_COOLDOWN": LIGHTNING_COOLDOWN,
    "LIGHTNING_ZAP_RANGE": LIGHTNING_ZAP_RANGE,

    # Piercing bullets
    "PIERCING_BULLET_MAX_PIERCES": PIERCING_BULLET_MAX_PIERCES,
}

SETTINGS_MODIFIED = False
_CURRENT_GAME_SETTINGS = DEFAULT_SETTINGS.copy()

def set_game_setting(key, value):
    global SETTINGS_MODIFIED, _CURRENT_GAME_SETTINGS
    _CURRENT_GAME_SETTINGS[key] = value
    is_modified_overall = False
    for k_check, v_default in DEFAULT_SETTINGS.items():
        if _CURRENT_GAME_SETTINGS.get(k_check) != v_default:
            is_modified_overall = True
            break
    SETTINGS_MODIFIED = is_modified_overall
    if key in globals():
        globals()[key] = value

def get_game_setting(key):
    if key in _CURRENT_GAME_SETTINGS:
        return _CURRENT_GAME_SETTINGS[key]
    if key in globals():
        return globals()[key]
    return DEFAULT_SETTINGS.get(key)

for key, value in DEFAULT_SETTINGS.items():
    globals()[key] = value

MISSILE_SPEED = get_game_setting("MISSILE_SPEED")
MISSILE_LIFETIME = get_game_setting("MISSILE_LIFETIME")
PLAYER_DEFAULT_BULLET_SIZE = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
LIGHTNING_LIFETIME = get_game_setting("LIGHTNING_LIFETIME")

if 'WEAPON_MODES_SEQUENCE' not in globals():
    globals()['WEAPON_MODES_SEQUENCE'] = WEAPON_MODES_SEQUENCE
if 'WEAPON_MODE_NAMES' not in globals():
    globals()['WEAPON_MODE_NAMES'] = WEAPON_MODE_NAMES
if 'POWERUP_TYPES' not in globals():
    globals()['POWERUP_TYPES'] = POWERUP_TYPES
