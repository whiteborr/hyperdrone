# constants.py
# Contains unchanging constants that should not be modified during gameplay
# This file now only contains true constants, not configurable settings

from typing import Dict, List, Tuple, Any, Optional

# ==========================
# Color Definitions
# ==========================
# Define color type for clarity
ColorRGB = Tuple[int, int, int]

# Base colors
BLACK: ColorRGB = (0, 0, 0)
WHITE: ColorRGB = (255, 255, 255)
RED: ColorRGB = (255, 0, 0)
DARK_RED: ColorRGB = (100, 0, 0)
GREEN: ColorRGB = (0, 255, 0)
BLUE: ColorRGB = (0, 100, 255)
CYAN: ColorRGB = (0, 255, 255)
LIGHT_BLUE: ColorRGB = (173, 216, 230)
YELLOW: ColorRGB = (255, 255, 0)
GOLD: ColorRGB = (255, 215, 0)
ORANGE: ColorRGB = (255, 165, 0)
PURPLE: ColorRGB = (128, 0, 128)
DARK_PURPLE: ColorRGB = (40, 0, 70)
MAGENTA: ColorRGB = (255, 0, 255)
PINK: ColorRGB = (255, 192, 203)
GREY: ColorRGB = (100, 100, 100)
DARK_GREY: ColorRGB = (50, 50, 50)
ELECTRIC_BLUE: ColorRGB = (0, 128, 255)
ESCAPE_ZONE_COLOR: ColorRGB = (0, 255, 120)

# Bullet colors
PLAYER_BULLET_COLOR: ColorRGB = CYAN
MISSILE_COLOR: ColorRGB = RED
LIGHTNING_COLOR: ColorRGB = ELECTRIC_BLUE

# Effect colors
FLAME_COLORS: List[ColorRGB] = [(255, 100, 0), (255, 165, 0), (255, 215, 0), (255, 255, 100)]

# Environment colors
ARCHITECT_VAULT_BG_COLOR: ColorRGB = (20, 0, 30)
ARCHITECT_VAULT_WALL_COLOR: ColorRGB = (150, 120, 200)
ARCHITECT_VAULT_ACCENT_COLOR: ColorRGB = GOLD

# ==========================
# Game State Definitions
# ==========================
# Define a class for game states to group them logically
class GameStates:
    # Core game states
    MAIN_MENU: str = "main_menu"
    PLAYING: str = "playing"
    GAME_OVER: str = "game_over"
    LEADERBOARD: str = "leaderboard_display"
    ENTER_NAME: str = "enter_name"
    SETTINGS: str = "settings_menu"
    DRONE_SELECT: str = "drone_select_menu"
    CODEX: str = "codex_screen"
    GAME_INTRO_SCROLL: str = "game_intro_scroll"
    STORY_MAP: str = "story_map"
    
    # Chapter-specific states
    BOSS_FIGHT: str = "boss_fight"
    CORRUPTED_SECTOR: str = "corrupted_sector"
    HARVEST_CHAMBER: str = "harvest_chamber"

    # Bonus level states
    BONUS_LEVEL_START: str = "bonus_level_start"
    BONUS_LEVEL_PLAYING: str = "bonus_level_playing"
    
    # Architect vault states
    ARCHITECT_VAULT_INTRO: str = "architect_vault_intro"
    ARCHITECT_VAULT_ENTRY_PUZZLE: str = "architect_vault_entry_puzzle"
    ARCHITECT_VAULT_GAUNTLET: str = "architect_vault_gauntlet"
    ARCHITECT_VAULT_BOSS_FIGHT: str = "architect_vault_boss_fight"
    ARCHITECT_VAULT_EXTRACTION: str = "architect_vault_extraction"
    ARCHITECT_VAULT_SUCCESS: str = "architect_vault_success"
    ARCHITECT_VAULT_FAILURE: str = "architect_vault_failure"
    
    # Puzzle and special mode states
    RING_PUZZLE: str = "ring_puzzle_active"
    MAZE_DEFENSE: str = "maze_defense_mode"

# For backward compatibility
GAME_STATE_MAIN_MENU = GameStates.MAIN_MENU
GAME_STATE_PLAYING = GameStates.PLAYING
GAME_STATE_GAME_OVER = GameStates.GAME_OVER
GAME_STATE_LEADERBOARD = GameStates.LEADERBOARD
GAME_STATE_ENTER_NAME = GameStates.ENTER_NAME
GAME_STATE_SETTINGS = GameStates.SETTINGS
GAME_STATE_DRONE_SELECT = GameStates.DRONE_SELECT
GAME_STATE_CODEX = GameStates.CODEX
GAME_STATE_BONUS_LEVEL_START = GameStates.BONUS_LEVEL_START
GAME_STATE_BONUS_LEVEL_PLAYING = GameStates.BONUS_LEVEL_PLAYING
GAME_STATE_ARCHITECT_VAULT_INTRO = GameStates.ARCHITECT_VAULT_INTRO
GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE = GameStates.ARCHITECT_VAULT_ENTRY_PUZZLE
GAME_STATE_ARCHITECT_VAULT_GAUNTLET = GameStates.ARCHITECT_VAULT_GAUNTLET
GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT = GameStates.ARCHITECT_VAULT_BOSS_FIGHT
GAME_STATE_ARCHITECT_VAULT_EXTRACTION = GameStates.ARCHITECT_VAULT_EXTRACTION
GAME_STATE_ARCHITECT_VAULT_SUCCESS = GameStates.ARCHITECT_VAULT_SUCCESS
GAME_STATE_ARCHITECT_VAULT_FAILURE = GameStates.ARCHITECT_VAULT_FAILURE
GAME_STATE_RING_PUZZLE = GameStates.RING_PUZZLE
GAME_STATE_GAME_INTRO_SCROLL = GameStates.GAME_INTRO_SCROLL
GAME_STATE_STORY_MAP = GameStates.STORY_MAP
GAME_STATE_MAZE_DEFENSE = GameStates.MAZE_DEFENSE
GAME_STATE_BOSS_FIGHT = GameStates.BOSS_FIGHT
GAME_STATE_CORRUPTED_SECTOR = GameStates.CORRUPTED_SECTOR
GAME_STATE_HARVEST_CHAMBER = GameStates.HARVEST_CHAMBER

# New chapter states
GAME_STATE_EARTH_CORE = "earth_core"
GAME_STATE_FIRE_CORE = "fire_core"
GAME_STATE_AIR_CORE = "air_core"
GAME_STATE_WATER_CORE = "water_core"
GAME_STATE_ORICHALC_CORE = "orichalc_core"
GAME_STATE_SKYWARD_GRID = "skyward_grid"
GAME_STATE_TEMPEST_FIGHT = "tempest_fight"
GAME_STATE_WEAPONS_UPGRADE_SHOP = "weapons_upgrade_shop"
GAME_STATE_NARRATIVE = "narrative"

# ==========================
# Player Weapon Modes
# ==========================
class WeaponModes:
    # Basic weapons
    DEFAULT: int = 0
    TRI_SHOT: int = 1
    RAPID_SINGLE: int = 2
    RAPID_TRI: int = 3
    
    # BIG SHOT Tree - Elemental Weaponry
    BIG_SHOT_FIRE: int = 10
    BIG_SHOT_EARTH: int = 11
    BIG_SHOT_WATER: int = 12
    BIG_SHOT_AIR: int = 13
    BIG_SHOT_CONVERGENCE: int = 14
    
    # BOUNCE/PIERCE Tree - Vault Disruption Logic
    BOUNCE: int = 20
    PIERCE: int = 21
    RICOCHET_CHAIN: int = 22
    TUNNEL_SHOT: int = 23
    DISRUPTOR_CORE: int = 24
    
    # HEATSEEKER Tree - Autonomous Pursuit Logic
    HEATSEEKER: int = 30
    HEATSEEKER_PLUS_BULLETS: int = 31
    TRACK_SPIKE: int = 32
    GORGON_MARK: int = 33
    ORBITAL_ECHO: int = 34
    
    # LIGHTNING Tree - Cognition Cascade Arc
    ARC_SPARK: int = 40
    LIGHTNING: int = 41
    CHAIN_BURST: int = 42
    MINDLASH: int = 43
    QUASINET: int = 44
    
    @classmethod
    def get_all_modes(cls) -> List[int]:
        """Return all weapon modes as a list"""
        return [
            cls.DEFAULT, cls.TRI_SHOT, cls.RAPID_SINGLE, cls.RAPID_TRI,
            cls.BIG_SHOT_FIRE, cls.BIG_SHOT_EARTH, cls.BIG_SHOT_WATER, cls.BIG_SHOT_AIR, cls.BIG_SHOT_CONVERGENCE,
            cls.BOUNCE, cls.PIERCE, cls.RICOCHET_CHAIN, cls.TUNNEL_SHOT, cls.DISRUPTOR_CORE,
            cls.HEATSEEKER, cls.HEATSEEKER_PLUS_BULLETS, cls.TRACK_SPIKE, cls.GORGON_MARK, cls.ORBITAL_ECHO,
            cls.ARC_SPARK, cls.LIGHTNING, cls.CHAIN_BURST, cls.MINDLASH, cls.QUASINET
        ]
    
    @classmethod
    def get_weapon_tree(cls, base_weapon: int) -> List[int]:
        """Get weapon upgrade tree for a base weapon"""
        trees = {
            cls.BIG_SHOT_FIRE: [cls.BIG_SHOT_FIRE, cls.BIG_SHOT_EARTH, cls.BIG_SHOT_WATER, cls.BIG_SHOT_AIR, cls.BIG_SHOT_CONVERGENCE],
            cls.BOUNCE: [cls.BOUNCE, cls.PIERCE, cls.RICOCHET_CHAIN, cls.TUNNEL_SHOT, cls.DISRUPTOR_CORE],
            cls.HEATSEEKER: [cls.HEATSEEKER, cls.HEATSEEKER_PLUS_BULLETS, cls.TRACK_SPIKE, cls.GORGON_MARK, cls.ORBITAL_ECHO],
            cls.ARC_SPARK: [cls.ARC_SPARK, cls.LIGHTNING, cls.CHAIN_BURST, cls.MINDLASH, cls.QUASINET]
        }
        for base, tree in trees.items():
            if base_weapon in tree:
                return tree
        return [base_weapon]

# For backward compatibility
WEAPON_MODE_DEFAULT = WeaponModes.DEFAULT
WEAPON_MODE_TRI_SHOT = WeaponModes.TRI_SHOT
WEAPON_MODE_RAPID_SINGLE = WeaponModes.RAPID_SINGLE
WEAPON_MODE_RAPID_TRI = WeaponModes.RAPID_TRI
WEAPON_MODE_BIG_SHOT = WeaponModes.BIG_SHOT_FIRE  # Map old to new
WEAPON_MODE_BOUNCE = WeaponModes.BOUNCE
WEAPON_MODE_PIERCE = WeaponModes.PIERCE
WEAPON_MODE_HEATSEEKER = WeaponModes.HEATSEEKER
WEAPON_MODE_HEATSEEKER_PLUS_BULLETS = WeaponModes.HEATSEEKER_PLUS_BULLETS
WEAPON_MODE_LIGHTNING = WeaponModes.LIGHTNING

# ==========================
# Fixed Identifiers
# ==========================
class ArchitectVaultRewards:
    BLUEPRINT_ID: str = "DRONE_ARCHITECT_X"
    LORE_ID: str = "lore_architect_origin"

# For backward compatibility
ARCHITECT_REWARD_BLUEPRINT_ID = ArchitectVaultRewards.BLUEPRINT_ID
ARCHITECT_REWARD_LORE_ID = ArchitectVaultRewards.LORE_ID

# Powerup types
class PowerupTypes:
    WEAPON_UPGRADE: str = "weapon_upgrade"
    SHIELD: str = "shield"
    SPEED_BOOST: str = "speed_boost"
    
    @classmethod
    def get_display_names(cls) -> Dict[str, str]:
        """Get display names for all powerup types"""
        return {
            cls.WEAPON_UPGRADE: "Weapon Upgrade",
            cls.SHIELD: "Shield",
            cls.SPEED_BOOST: "Speed Boost"
        }

# For backward compatibility
POWERUP_TYPES = PowerupTypes.get_display_names()

# Weapon mode names and icons
def get_weapon_mode_names() -> Dict[int, str]:
    """Get the display names for all weapon modes"""
    return {
        WeaponModes.DEFAULT: "Single Shot", 
        WeaponModes.TRI_SHOT: "Tri-Shot",
        WeaponModes.RAPID_SINGLE: "Rapid Single", 
        WeaponModes.RAPID_TRI: "Rapid Tri-Shot",
        
        # Big Shot Tree
        WeaponModes.BIG_SHOT_FIRE: "Fire Shot",
        WeaponModes.BIG_SHOT_EARTH: "Earth Shot", 
        WeaponModes.BIG_SHOT_WATER: "Water Shot",
        WeaponModes.BIG_SHOT_AIR: "Air Shot",
        WeaponModes.BIG_SHOT_CONVERGENCE: "Convergence Shot",
        
        # Bounce/Pierce Tree
        WeaponModes.BOUNCE: "Bounce Shot",
        WeaponModes.PIERCE: "Pierce Shot",
        WeaponModes.RICOCHET_CHAIN: "Ricochet Chain",
        WeaponModes.TUNNEL_SHOT: "Tunnel Shot",
        WeaponModes.DISRUPTOR_CORE: "Disruptor Core",
        
        # Heatseeker Tree
        WeaponModes.HEATSEEKER: "Heatseeker",
        WeaponModes.HEATSEEKER_PLUS_BULLETS: "Seeker + Rapid",
        WeaponModes.TRACK_SPIKE: "Track Spike",
        WeaponModes.GORGON_MARK: "Gorgon Mark",
        WeaponModes.ORBITAL_ECHO: "Orbital Echo",
        
        # Lightning Tree
        WeaponModes.ARC_SPARK: "Arc Spark",
        WeaponModes.LIGHTNING: "Chain Lightning",
        WeaponModes.CHAIN_BURST: "Chain Burst",
        WeaponModes.MINDLASH: "Mindlash",
        WeaponModes.QUASINET: "Quasinet"
    }

# Cache the weapon mode names
WEAPON_MODE_NAMES: Dict[int, str] = get_weapon_mode_names()

# Base weapon modes sequence - defines the initial unlock path
WEAPON_MODES_SEQUENCE: List[int] = [WeaponModes.DEFAULT, WeaponModes.TRI_SHOT, WeaponModes.RAPID_SINGLE, WeaponModes.RAPID_TRI]

# ==========================
# Asset Paths
# ==========================
# Turret asset paths
TURRET_ASSET_PATHS: Dict[str, str] = {
    f"WEAPON_MODE_{mode}": f"images/level_elements/turret_{mode.lower()}.png"
    for mode in ["DEFAULT", "TRI_SHOT", "RAPID_SINGLE", "RAPID_TRI", "BIG_SHOT", "BOUNCE", "PIERCE", "HEATSEEKER", "HEATSEEKER_PLUS_BULLETS", "LIGHTNING"]
}

# ==========================
# UI Layout Constants
# ==========================
class HUDLayout:
    """Constants for HUD layout positioning and sizing"""
    # Ring icon positioning
    RING_ICON_AREA_X_OFFSET: int = 200
    RING_ICON_AREA_Y_OFFSET: int = 20
    RING_ICON_SIZE: int = 40
    RING_ICON_SPACING: int = 10

# For backward compatibility
HUD_RING_ICON_AREA_X_OFFSET = HUDLayout.RING_ICON_AREA_X_OFFSET
HUD_RING_ICON_AREA_Y_OFFSET = HUDLayout.RING_ICON_AREA_Y_OFFSET
HUD_RING_ICON_SIZE = HUDLayout.RING_ICON_SIZE
HUD_RING_ICON_SPACING = HUDLayout.RING_ICON_SPACING

# ==========================
# JSON and Dictionary Keys
# ==========================
class JsonKeys:
    """Constants for JSON file keys to ensure consistency across the codebase"""
    
    class DroneUnlocks:
        """Keys for drone_unlocks.json file"""
        UNLOCKED_DRONES: str = "unlocked_drones"
        SELECTED_DRONE_ID: str = "selected_drone_id"
        CORES: str = "cores"
        UNLOCKED_LORE_IDS: str = "unlocked_lore_ids"
        COLLECTED_CORE_FRAGMENTS: str = "collected_core_fragments"
        ARCHITECT_VAULT_COMPLETED: str = "architect_vault_completed"
        COLLECTED_GLYPH_TABLETS: str = "collected_glyph_tablets"
        SOLVED_PUZZLE_TERMINALS: str = "solved_puzzle_terminals"
        DEFEATED_BOSSES: str = "defeated_bosses"
    
    class Lore:
        """Keys for lore entries in lore_entries.json"""
        ENTRIES: str = "entries"
        ID: str = "id"
        CATEGORY: str = "category"
        TITLE: str = "title"
        CONTENT: str = "content"
        SEQUENCE: str = "sequence"
        UNLOCKED_BY: str = "unlocked_by"
        ECHO_MESSAGE: str = "echo_message"
    
    class DroneConfig:
        """Keys for drone configuration in drone_configs.py"""
        BASE_STATS: str = "base_stats"
        VAULT_STATS: str = "vault_stats"
        UNLOCK_CONDITION: str = "unlock_condition"
        UNLOCK_TYPE: str = "unlock_type"
        DRONE_ID: str = "drone_id"
        DISPLAY_NAME: str = "display_name"
        DESCRIPTION: str = "description"
        SPECIAL_ABILITY: str = "special_ability"

# For backward compatibility
# drone_unlocks.json keys
KEY_UNLOCKED_DRONES = JsonKeys.DroneUnlocks.UNLOCKED_DRONES
KEY_SELECTED_DRONE_ID = JsonKeys.DroneUnlocks.SELECTED_DRONE_ID
KEY_CORES = JsonKeys.DroneUnlocks.CORES
KEY_UNLOCKED_LORE_IDS = JsonKeys.DroneUnlocks.UNLOCKED_LORE_IDS
KEY_COLLECTED_CORE_FRAGMENTS = JsonKeys.DroneUnlocks.COLLECTED_CORE_FRAGMENTS
KEY_ARCHITECT_VAULT_COMPLETED = JsonKeys.DroneUnlocks.ARCHITECT_VAULT_COMPLETED
KEY_COLLECTED_GLYPH_TABLETS = JsonKeys.DroneUnlocks.COLLECTED_GLYPH_TABLETS
KEY_SOLVED_PUZZLE_TERMINALS = JsonKeys.DroneUnlocks.SOLVED_PUZZLE_TERMINALS
KEY_DEFEATED_BOSSES = JsonKeys.DroneUnlocks.DEFEATED_BOSSES

# Lore entry keys
KEY_LORE_ENTRIES = JsonKeys.Lore.ENTRIES
KEY_LORE_ID = JsonKeys.Lore.ID
KEY_LORE_CATEGORY = JsonKeys.Lore.CATEGORY
KEY_LORE_TITLE = JsonKeys.Lore.TITLE
KEY_LORE_CONTENT = JsonKeys.Lore.CONTENT
KEY_LORE_SEQUENCE = JsonKeys.Lore.SEQUENCE
KEY_LORE_UNLOCKED_BY = JsonKeys.Lore.UNLOCKED_BY
KEY_LORE_ECHO_MESSAGE = JsonKeys.Lore.ECHO_MESSAGE

# Drone config keys
KEY_BASE_STATS = JsonKeys.DroneConfig.BASE_STATS
KEY_VAULT_STATS = JsonKeys.DroneConfig.VAULT_STATS
KEY_UNLOCK_CONDITION = JsonKeys.DroneConfig.UNLOCK_CONDITION
KEY_UNLOCK_TYPE = JsonKeys.DroneConfig.UNLOCK_TYPE
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

# Enemy types
ENEMY_TYPE_SENTINEL = "sentinel"
ENEMY_TYPE_DEFENSE = "defense"
ENEMY_TYPE_TR3B = "tr3b"
ENEMY_TYPE_GUARDIAN = "guardian"

# Game difficulty levels
DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"
DIFFICULTY_NIGHTMARE = "nightmare"

# Game modes
GAME_MODE_STORY = "story"
GAME_MODE_ARCADE = "arcade"
GAME_MODE_SURVIVAL = "survival"
GAME_MODE_DEFENSE = "defense"

# Achievement types
ACHIEVEMENT_TYPE_PROGRESSION = "progression"
ACHIEVEMENT_TYPE_COLLECTION = "collection"
ACHIEVEMENT_TYPE_CHALLENGE = "challenge"
ACHIEVEMENT_TYPE_SECRET = "secret"

# Event types
EVENT_ENEMY_DEFEATED = "enemy_defeated"
EVENT_ITEM_COLLECTED = "item_collected"
EVENT_LEVEL_COMPLETED = "level_completed"
EVENT_PLAYER_DAMAGED = "player_damaged"
EVENT_PLAYER_HEALED = "player_healed"
EVENT_WEAPON_CHANGED = "weapon_changed"
EVENT_PUZZLE_SOLVED = "puzzle_solved"
EVENT_TERMINAL_ACTIVATED = "terminal_activated"
EVENT_BOSS_DEFEATED = "boss_defeated"
EVENT_GAME_OVER = "game_over"
EVENT_ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
