# constants.py
# Contains unchanging constants that should not be modified during gameplay

# ==========================
# Color Definitions
# ==========================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
DARK_RED = (100, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255) 
CYAN = (0, 255, 255)
LIGHT_BLUE = (173, 216, 230) 
YELLOW = (255, 255, 0)
GOLD = (255, 215, 0) 
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
DARK_PURPLE = (40, 0, 70)
MAGENTA = (255, 0, 255) 
PINK = (255, 192, 203)
GREY = (100, 100, 100)
DARK_GREY = (50, 50, 50)
ELECTRIC_BLUE = (0, 128, 255) 
ESCAPE_ZONE_COLOR = (0, 255, 120)

FLAME_COLORS = [(255, 100, 0), (255, 165, 0), (255, 215, 0), (255, 255, 100)]

ARCHITECT_VAULT_BG_COLOR = (20, 0, 30)
ARCHITECT_VAULT_WALL_COLOR = (150, 120, 200)
ARCHITECT_VAULT_ACCENT_COLOR = GOLD

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
GAME_STATE_CODEX = "codex_screen"
GAME_STATE_BONUS_LEVEL_START = "bonus_level_start" 
GAME_STATE_BONUS_LEVEL_PLAYING = "bonus_level_playing"
GAME_STATE_ARCHITECT_VAULT_INTRO = "architect_vault_intro"
GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE = "architect_vault_entry_puzzle"
GAME_STATE_ARCHITECT_VAULT_GAUNTLET = "architect_vault_gauntlet"
GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT = "architect_vault_boss_fight" 
GAME_STATE_ARCHITECT_VAULT_EXTRACTION = "architect_vault_extraction"
GAME_STATE_ARCHITECT_VAULT_SUCCESS = "architect_vault_success"
GAME_STATE_ARCHITECT_VAULT_FAILURE = "architect_vault_failure"
GAME_STATE_RING_PUZZLE = "ring_puzzle_active"
GAME_STATE_GAME_INTRO_SCROLL = "game_intro_scroll"
GAME_STATE_MAZE_DEFENSE = "maze_defense_mode"

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

# ==========================
# Fixed Identifiers
# ==========================
ARCHITECT_REWARD_BLUEPRINT_ID = "DRONE_ARCHITECT_X"
ARCHITECT_REWARD_LORE_ID = "lore_architect_origin"

# Weapon mode names and icons (these don't change)
WEAPON_MODE_NAMES = {
    WEAPON_MODE_DEFAULT: "Single Shot", WEAPON_MODE_TRI_SHOT: "Tri-Shot",
    WEAPON_MODE_RAPID_SINGLE: "Rapid Single", WEAPON_MODE_RAPID_TRI: "Rapid Tri-Shot",
    WEAPON_MODE_BIG_SHOT: "Big Shot", WEAPON_MODE_BOUNCE: "Bounce Shot",
    WEAPON_MODE_PIERCE: "Pierce Shot", WEAPON_MODE_HEATSEEKER: "Heatseeker",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "Seeker + Rapid", WEAPON_MODE_LIGHTNING: "Chain Lightning"
}

# Weapon modes sequence
WEAPON_MODES_SEQUENCE = [
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
]

# ==========================
# Asset Paths
# ==========================
# Turret asset paths
TURRET_ASSET_PATHS = {
    "WEAPON_MODE_DEFAULT": "images/level_elements/turret_default_base_img.png",
    "WEAPON_MODE_TRI_SHOT": "images/level_elements/turret_trishot_base_img.png",
    "WEAPON_MODE_RAPID_SINGLE": "images/level_elements/turret_default_base_img.png",
    "WEAPON_MODE_RAPID_TRI": "images/level_elements/turret_trishot_base_img.png",
    "WEAPON_MODE_BIG_SHOT": "images/level_elements/turret_default_base_img.png",
    "WEAPON_MODE_BOUNCE": "images/level_elements/turret_default_base_img.png",
    "WEAPON_MODE_PIERCE": "images/level_elements/turret_default_base_img.png",
    "WEAPON_MODE_HEATSEEKER": "images/level_elements/turret_seeker_base_img.png",
    "WEAPON_MODE_HEATSEEKER_PLUS_BULLETS": "images/level_elements/turret_seeker_base_img.png",
    "WEAPON_MODE_LIGHTNING": "images/level_elements/turret_lightning_base_img.png",
}

# ==========================
# JSON and Dictionary Keys
# ==========================
# drone_unlocks.json keys
KEY_UNLOCKED_DRONES = "unlocked_drones"
KEY_SELECTED_DRONE_ID = "selected_drone_id"
KEY_PLAYER_CORES = "player_cores"
KEY_UNLOCKED_LORE_IDS = "unlocked_lore_ids"
KEY_COLLECTED_CORE_FRAGMENTS = "collected_core_fragments"
KEY_ARCHITECT_VAULT_COMPLETED = "architect_vault_completed"
KEY_COLLECTED_GLYPH_TABLETS = "collected_glyph_tablets"
KEY_SOLVED_PUZZLE_TERMINALS = "solved_puzzle_terminals"
KEY_DEFEATED_BOSSES = "defeated_bosses"

# Lore entry keys
KEY_LORE_ENTRIES = "entries"
KEY_LORE_ID = "id"
KEY_LORE_CATEGORY = "category"
KEY_LORE_TITLE = "title"
KEY_LORE_CONTENT = "content"
KEY_LORE_SEQUENCE = "sequence"
KEY_LORE_UNLOCKED_BY = "unlocked_by"
KEY_LORE_ECHO_MESSAGE = "echo_message"

# Drone config keys
KEY_BASE_STATS = "base_stats"
KEY_VAULT_STATS = "vault_stats"
KEY_UNLOCK_CONDITION = "unlock_condition"
KEY_UNLOCK_TYPE = "type"
KEY_UNLOCK_VALUE = "value"
KEY_DRONE_NAME = "name"
KEY_DRONE_DESCRIPTION = "description"
KEY_SPRITE_PATH = "sprite_path"

# Core fragment keys
KEY_FRAGMENT_ID = "id"
KEY_FRAGMENT_NAME = "name"
KEY_FRAGMENT_DESCRIPTION = "description"
KEY_FRAGMENT_REQUIRED_FOR_VAULT = "required_for_vault"
KEY_FRAGMENT_DISPLAY_COLOR = "display_color"

# Leaderboard keys
KEY_LEADERBOARD_NAME = "name"
KEY_LEADERBOARD_SCORE = "score"
KEY_LEADERBOARD_LEVEL = "level"