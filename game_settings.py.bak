# game_settings.py
# This is a compatibility layer for the refactored settings system
# It allows existing code to continue working without major changes

import logging
from constants import *
from settings_manager import settings_manager, get_setting, set_setting, save_settings

logger = logging.getLogger(__name__)

# Re-export constants
# Colors are already imported from constants.py
# Game states are already imported from constants.py
# Weapon modes are already imported from constants.py

# Additional color definitions
ELECTRIC_BLUE = (0, 128, 255)

# Puzzle settings
TOTAL_CORE_FRAGMENTS_NEEDED = get_setting("gameplay", "TOTAL_CORE_FRAGMENTS_NEEDED", 3)
RING_PUZZLE_CORE_REWARD = get_setting("gameplay", "RING_PUZZLE_CORE_REWARD", 750)

# Asset paths
ASSET_PATHS = {
    "RING_UI_ICON": "images/collectibles/ring_ui_icon.png",
    "RING_UI_ICON_EMPTY": "images/collectibles/ring_ui_icon_empty.png",
    "MENU_LOGO": "images/ui/menu_logo_hyperdrone.png",
    "CORE_FRAGMENT_EMPTY_ICON": "images/collectibles/fragment_ui_icon_empty.png",
    "REACTOR_HUD_ICON": "images/level_elements/reactor_icon.png",
    "CORE_REACTOR_IMAGE": "images/level_elements/core_reactor.png",
    "SHIELD_POWERUP_ICON": "images/powerups/shield_icon.png",
    "SPEED_BOOST_POWERUP_ICON": "images/powerups/speed_icon.png",
    "WEAPON_UPGRADE_POWERUP_ICON": "images/powerups/weapon_icon.png",
    "DEFENSE_DRONE_1_SPRITE": "images/enemies/defense_drone_1.png",
    "DEFENSE_DRONE_2_SPRITE": "images/enemies/defense_drone_2.png",
    "DEFENSE_DRONE_3_SPRITE": "images/enemies/defense_drone_3.png",
    "DEFENSE_DRONE_4_SPRITE": "images/enemies/defense_drone_4.png",
    "DEFENSE_DRONE_5_SPRITE": "images/enemies/defense_drone_5.png",
    "LORE_SCENE_1": "images/lore/scene1.png",
    "LORE_SCENE_2": "images/lore/scene2.png",
    "LORE_SCENE_3": "images/lore/scene3.png",
    "LORE_SCENE_4": "images/lore/scene4.png",
    "COLLECT_RING_SOUND": "sounds/collect_ring.wav",
    "WEAPON_UPGRADE_COLLECT_SOUND": "sounds/weapon_upgrade_collect.wav",
    "COLLECT_FRAGMENT_SOUND": "sounds/collect_fragment.wav",
    "SHOOT_SOUND": "sounds/shoot.wav",
    "ENEMY_SHOOT_SOUND": "sounds/enemy_shoot.wav",
    "CRASH_SOUND": "sounds/crash.wav",
    "LEVEL_UP_SOUND": "sounds/level_up.wav",
    "UI_SELECT_SOUND": "sounds/ui_select.wav",
    "UI_CONFIRM_SOUND": "sounds/ui_confirm.wav",
    "UI_DENIED_SOUND": "sounds/ui_denied.wav",
    "MISSILE_LAUNCH_SOUND": "sounds/missile_launch.wav",
    "PROTOTYPE_DRONE_EXPLODE_SOUND": "sounds/prototype_drone_explode.wav",
    "UI_TEXT_FONT": "fonts/neuropol.otf",
    "MENU_THEME_MUSIC": "sounds/menu_music.wav",
    "GAMEPLAY_THEME_MUSIC": "sounds/gameplay_music.wav",
    "DEFENSE_THEME_MUSIC": "sounds/defense_mode_music.wav"
}

# HUD settings
HUD_RING_ICON_AREA_X_OFFSET = get_setting("display", "HUD_RING_ICON_AREA_X_OFFSET", 150)
HUD_RING_ICON_AREA_Y_OFFSET = get_setting("display", "HUD_RING_ICON_AREA_Y_OFFSET", 30)
HUD_RING_ICON_SIZE = get_setting("display", "HUD_RING_ICON_SIZE", 24)
HUD_RING_ICON_SPACING = get_setting("display", "HUD_RING_ICON_SPACING", 5)
MAX_RINGS_PER_LEVEL = get_setting("gameplay", "MAX_RINGS_PER_LEVEL", 5)

# Core Fragment Details
CORE_FRAGMENT_DETAILS = settings_manager.get_core_fragment_details() or {
    "fragment_alpha": {
        "id": "cf_alpha",
        "name": "Alpha Fragment",
        "description": "A fragment of the Architect's Vault core. Required to access the vault.",
        "required_for_vault": True,
        "display_color": (255, 0, 0),
        "icon_filename": "images/collectibles/core_fragment_alpha.png"
    },
    "fragment_beta": {
        "id": "cf_beta",
        "name": "Beta Fragment",
        "description": "A fragment of the Architect's Vault core. Required to access the vault.",
        "required_for_vault": True,
        "display_color": (0, 0, 255),
        "icon_filename": "images/collectibles/core_fragment_beta.png"
    },
    "fragment_gamma": {
        "id": "cf_gamma",
        "name": "Gamma Fragment",
        "description": "A fragment of the Architect's Vault core. Required to access the vault.",
        "required_for_vault": True,
        "display_color": (0, 255, 0),
        "icon_filename": "images/collectibles/core_fragment_gamma.png"
    },
    "fragment_vault_core": {
        "id": "vault_core",
        "name": "Vault Core",
        "description": "The complete core of the Architect's Vault. Contains immense power.",
        "required_for_vault": False,
        "display_color": (255, 215, 0),
        "icon_filename": "images/collectibles/vault_core_icon.png"
    }
}

# Weapon Mode Names and Icons
# WEAPON_MODE_NAMES is imported from constants.py
WEAPON_MODES_SEQUENCE = [
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
]

WEAPON_MODE_ICONS = {}
for mode in WEAPON_MODES_SEQUENCE:
    path = settings_manager.get_weapon_icon_path(mode)
    if path:
        WEAPON_MODE_ICONS[mode] = path

# Compatibility layer for direct access to settings
# This allows existing code to access settings as if they were global variables

# Display settings
WIDTH = get_setting("display", "WIDTH", 1920)
HEIGHT = get_setting("display", "HEIGHT", 1080)
FPS = get_setting("display", "FPS", 60)
FULLSCREEN_MODE = get_setting("display", "FULLSCREEN_MODE", True)
MUSIC_VOLUME_MULTIPLIER = get_setting("display", "MUSIC_VOLUME_MULTIPLIER", 0.5)
SFX_VOLUME_MULTIPLIER = get_setting("display", "SFX_VOLUME_MULTIPLIER", 0.7)
BOTTOM_PANEL_HEIGHT = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)

# Leaderboard settings
LEADERBOARD_FILE_NAME = get_setting("gameplay", "LEADERBOARD_FILE_NAME", "leaderboard.json")
LEADERBOARD_MAX_ENTRIES = get_setting("gameplay", "LEADERBOARD_MAX_ENTRIES", 10)

# Combat settings
LIGHTNING_DAMAGE = get_setting("gameplay", "LIGHTNING_DAMAGE", 15)
MAZE_GUARDIAN_HEALTH = get_setting("gameplay", "MAZE_GUARDIAN_HEALTH", 1000)
ARCHITECT_VAULT_DRONES_PER_WAVE = get_setting("gameplay", "ARCHITECT_VAULT_DRONES_PER_WAVE", 5)
ARCHITECT_VAULT_GAUNTLET_WAVES = get_setting("gameplay", "ARCHITECT_VAULT_GAUNTLET_WAVES", 3)
DEFENSE_REACTOR_HEALTH = get_setting("gameplay", "DEFENSE_REACTOR_HEALTH", 1000)
GAME_PLAY_AREA_HEIGHT = get_setting("gameplay", "GAME_PLAY_AREA_HEIGHT", HEIGHT)

# Enemy sprite paths
REGULAR_ENEMY_SPRITE_PATH = "images/enemies/prototype_enemy.png"
PROTOTYPE_DRONE_SPRITE_PATH = "images/enemies/prototype_enemy.png"
SENTINEL_DRONE_SPRITE_PATH = "images/enemies/sentinel_drone.png"
MAZE_GUARDIAN_SPRITE_PATH = "images/enemies/maze_guardian.png"

# Defense drone settings
DEFENSE_DRONE_1_HEALTH = get_setting("gameplay", "DEFENSE_DRONE_1_HEALTH", 100)
DEFENSE_DRONE_1_SPEED = get_setting("gameplay", "DEFENSE_DRONE_1_SPEED", 1.5)
DEFENSE_DRONE_2_HEALTH = get_setting("gameplay", "DEFENSE_DRONE_2_HEALTH", 120)
DEFENSE_DRONE_2_SPEED = get_setting("gameplay", "DEFENSE_DRONE_2_SPEED", 1.3)
DEFENSE_DRONE_3_HEALTH = get_setting("gameplay", "DEFENSE_DRONE_3_HEALTH", 80)
DEFENSE_DRONE_3_SPEED = get_setting("gameplay", "DEFENSE_DRONE_3_SPEED", 1.8)
DEFENSE_DRONE_4_HEALTH = get_setting("gameplay", "DEFENSE_DRONE_4_HEALTH", 150)
DEFENSE_DRONE_4_SPEED = get_setting("gameplay", "DEFENSE_DRONE_4_SPEED", 1.2)
DEFENSE_DRONE_5_HEALTH = get_setting("gameplay", "DEFENSE_DRONE_5_HEALTH", 130)
DEFENSE_DRONE_5_SPEED = get_setting("gameplay", "DEFENSE_DRONE_5_SPEED", 1.4)

# Player weapon settings
PLAYER_BULLET_SPEED = get_setting("gameplay", "PLAYER_BULLET_SPEED", 10)
PLAYER_BULLET_LIFETIME = get_setting("gameplay", "PLAYER_BULLET_LIFETIME", 1500)
PLAYER_DEFAULT_BULLET_SIZE = get_setting("gameplay", "PLAYER_DEFAULT_BULLET_SIZE", 6)
PLAYER_BIG_BULLET_SIZE = get_setting("gameplay", "PLAYER_BIG_BULLET_SIZE", 12)
PLAYER_BULLET_COLOR = get_setting("gameplay", "PLAYER_BULLET_COLOR", CYAN)
PLAYER_BASE_SHOOT_COOLDOWN = get_setting("gameplay", "PLAYER_BASE_SHOOT_COOLDOWN", 300)
PLAYER_RAPID_FIRE_COOLDOWN = get_setting("gameplay", "PLAYER_RAPID_FIRE_COOLDOWN", 150)
MISSILE_COOLDOWN = get_setting("gameplay", "MISSILE_COOLDOWN", 1000)
MISSILE_DAMAGE = get_setting("gameplay", "MISSILE_DAMAGE", 50)
MISSILE_SPEED = get_setting("gameplay", "MISSILE_SPEED", 5)
MISSILE_LIFETIME = get_setting("gameplay", "MISSILE_LIFETIME", 3000)
MISSILE_COLOR = get_setting("gameplay", "MISSILE_COLOR", RED)
MISSILE_SIZE = get_setting("gameplay", "MISSILE_SIZE", 8)
LIGHTNING_COOLDOWN = get_setting("gameplay", "LIGHTNING_COOLDOWN", 1200)
LIGHTNING_LIFETIME = get_setting("gameplay", "LIGHTNING_LIFETIME", 500)
LIGHTNING_COLOR = get_setting("gameplay", "LIGHTNING_COLOR", ELECTRIC_BLUE)
BOUNCING_BULLET_MAX_BOUNCES = get_setting("gameplay", "BOUNCING_BULLET_MAX_BOUNCES", 3)
PIERCING_BULLET_MAX_PIERCES = get_setting("gameplay", "PIERCING_BULLET_MAX_PIERCES", 3)

# Gameplay settings
TILE_SIZE = get_setting("gameplay", "TILE_SIZE", 80)
PLAYER_MAX_HEALTH = get_setting("gameplay", "PLAYER_MAX_HEALTH", 100)
PLAYER_LIVES = get_setting("gameplay", "PLAYER_LIVES", 3)
PLAYER_SPEED = get_setting("gameplay", "PLAYER_SPEED", 3)
ROTATION_SPEED = get_setting("gameplay", "ROTATION_SPEED", 5)
PLAYER_INVINCIBILITY = get_setting("gameplay", "PLAYER_INVINCIBILITY", False)
INITIAL_WEAPON_MODE = get_setting("gameplay", "INITIAL_WEAPON_MODE", 0)

# Power-up settings
POWERUP_SIZE = get_setting("gameplay", "POWERUP_SIZE", 30)
POWERUP_SPAWN_CHANCE = get_setting("gameplay", "POWERUP_SPAWN_CHANCE", 0.01)
MAX_POWERUPS_ON_SCREEN = get_setting("gameplay", "MAX_POWERUPS_ON_SCREEN", 3)
POWERUP_TYPES = {
    "weapon_upgrade": {"weight": 0.4, "duration": 0},
    "shield": {"weight": 0.3, "duration": get_setting("gameplay", "SHIELD_POWERUP_DURATION", 10000)},
    "speed_boost": {"weight": 0.3, "duration": get_setting("gameplay", "SPEED_BOOST_POWERUP_DURATION", 5000)}
}
WEAPON_UPGRADE_ITEM_LIFETIME = get_setting("gameplay", "WEAPON_UPGRADE_ITEM_LIFETIME", 15000)
POWERUP_ITEM_LIFETIME = get_setting("gameplay", "POWERUP_ITEM_LIFETIME", 10000)
CORE_FRAGMENT_VISUAL_SIZE = get_setting("gameplay", "CORE_FRAGMENT_VISUAL_SIZE", 24)

# Compatibility function to get any setting
def get_game_setting(key, default_override=None):
    """
    Get a game setting by key, searching through all categories.
    
    Args:
        key: The setting key
        default_override: Default value if setting is not found
        
    Returns:
        The setting value or default if not found
    """
    for category in settings_manager.settings:
        if key in settings_manager.settings[category]:
            return settings_manager.settings[category][key]
    return default_override

# Compatibility function to set any setting
def set_game_setting(key, value):
    """
    Set a game setting by key, updating the appropriate category.
    
    Args:
        key: The setting key
        value: The value to set
    """
    # Find which category the key belongs to
    for category in settings_manager.settings:
        if key in settings_manager.settings[category]:
            set_setting(category, key, value)
            
            # Update the corresponding global variable if it exists
            if key in globals():
                globals()[key] = value
            return
    
    # If key wasn't found in any category, add it to 'gameplay' as a fallback
    set_setting("gameplay", key, value)
    
    # Update the corresponding global variable if it exists
    if key in globals():
        globals()[key] = value

# Function to reset all settings to defaults
def reset_all_settings_to_default():
    """Reset all settings to their default values."""
    settings_manager._load_settings()  # Reload settings from file
    
    # Update all global variables
    for category in settings_manager.settings:
        for key, value in settings_manager.settings[category].items():
            if key in globals():
                globals()[key] = value
    
    logger.info("Game settings have been reset to defaults.")