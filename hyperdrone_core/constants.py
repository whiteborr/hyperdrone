# hyperdrone_core/constants.py

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

# JSON and Dictionary Keys for drone_unlocks.json
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