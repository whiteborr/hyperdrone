import pygame
import sys
import os
import random
import math # Keep math import if used directly for calculations here

# Core Game System Imports
try:
    from scene_manager import SceneManager
    from event_manager import EventManager
    from ui import UIManager
    from player_actions import PlayerActions
    from drone_system import DroneSystem
    from bullet import LightningZap
    import leaderboard # For loading/saving scores
except ImportError as e:
    print(f"Critical Error (game_loop.py): Failed to import core system modules: {e}")
    pygame.quit()
    sys.exit()

# Game Object Imports
try:
    from player import Drone # Your updated Player class
    from enemy import Enemy
    from maze import Maze
    from collectibles import Ring, WeaponUpgradeItem, ShieldItem, SpeedBoostItem, CoreFragmentItem
    # Bullet class is used by Player and Enemy, not directly instantiated in game_loop typically
except ImportError as e:
    print(f"Critical Error (game_loop.py): Failed to import game object modules: {e}")
    pygame.quit()
    sys.exit()

# Game Settings and Configuration Imports
try:
    from game_settings import (
        WIDTH, HEIGHT, FPS, TILE_SIZE, # MAZE_ROWS is calculated in game_settings
        BLACK, WHITE, GOLD, CYAN, RED, YELLOW, # Basic colors
        GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
        GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
        GAME_STATE_BONUS_LEVEL_PLAYING, # Assuming bonus level concept might still exist
        GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
        GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
        GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
        ARCHITECT_VAULT_BG_COLOR, # Specific background for vault
        POWERUP_TYPES, # Added missing import for POWERUP_TYPES
        POWERUP_SPAWN_CHANCE, MAX_POWERUPS_ON_SCREEN,
        WEAPON_MODES_SEQUENCE, WEAPON_MODE_NAMES, # For settings UI
        CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
        ARCHITECT_VAULT_DRONES_PER_WAVE, ARCHITECT_VAULT_GAUNTLET_WAVES,
        PROTOTYPE_DRONE_HEALTH, PROTOTYPE_DRONE_SPEED, PROTOTYPE_DRONE_SHOOT_COOLDOWN, PROTOTYPE_DRONE_SPRITE_PATH,
        ARCHITECT_VAULT_EXTRACTION_TIMER_MS, DEFAULT_SETTINGS, ENEMY_BULLET_DAMAGE,
        PLAYER_DEFAULT_BULLET_SIZE, # For enemy creation
        get_game_setting, set_game_setting, reset_all_settings_to_default # For managing dynamic settings
    )
    from drone_configs import DRONE_DISPLAY_ORDER, DRONE_DATA # For drone selection UI
except ImportError as e:
    print(f"Critical Error (game_loop.py): Failed to import from game_settings.py or drone_configs.py: {e}")
    pygame.quit()
    sys.exit()


class GameController:
    def __init__(self):
        """Initializes the GameController and all its subsystems."""
        pygame.init()
        pygame.mixer.init() # Initialize the sound mixer

        # Screen setup (respects FULLSCREEN_MODE from game_settings)
        self.screen_flags = pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0
        self.screen = pygame.display.set_mode((get_game_setting("WIDTH"), get_game_setting("HEIGHT")), self.screen_flags)
        pygame.display.set_caption("HYPERDRONE")
        self.clock = pygame.time.Clock()

        # Core game systems
        self.drone_system = DroneSystem() # Manages drone data, unlocks, player progress

        # Fonts (paths should be correct in your assets)
        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf") # For emoji icons
        self.font_path_neuropol = os.path.join("assets", "fonts", "neuropol.otf") # Main game font
        self.fonts = {}
        self._initialize_fonts() # Load all necessary fonts

        # Instantiate other managers, passing 'self' (GameController) as a reference
        self.scene_manager = SceneManager(self)
        self.player_actions = PlayerActions(self)
        self.event_manager = EventManager(self, self.scene_manager) # EventManager needs SceneManager too
        self.ui_manager = UIManager(self.screen, self.fonts, self, self.scene_manager, self.drone_system)

        # Game world objects (initialized as None or empty groups)
        self.player = None # Will be a Drone instance
        self.maze = None   # Will be a Maze instance
        self.enemies = pygame.sprite.Group()
        self.rings = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group() # For shield, speed boost, weapon upgrades
        self.core_fragments = pygame.sprite.Group() # For Architect's Vault progression
        self.architect_vault_terminals = pygame.sprite.Group() # Specific to vault puzzle
        # self.architect_vault_hazards = pygame.sprite.Group() # If you add hazards

        # Game state variables
        self.score = 0
        self.level = 1
        self.lives = get_game_setting("PLAYER_LIVES") # Initial lives from settings
        self.paused = False

        # Timers
        self.level_timer_start_ticks = 0 # For current level's timer
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")
        self.bonus_level_timer_start = 0 # For bonus levels, if used
        self.bonus_level_duration_ms = get_game_setting("BONUS_LEVEL_DURATION_MS")

        # Collectibles tracking for UI and game logic
        self.collected_rings = 0 # Rings collected in current level
        self.displayed_collected_rings = 0 # For UI animation smoothing
        self.total_rings_per_level = 5 # Initial number, can increase
        self.animating_rings = [] # For ring collection animation to HUD
        self.ring_ui_target_pos = (0,0) # Target for ring animation, UIManager updates this

        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False # True if rings collected, waiting for anim

        # Architect's Vault specific state
        self.architect_vault_current_phase = None # E.g., "intro", "entry_puzzle", "gauntlet_wave_1", "extraction"
        self.architect_vault_phase_timer_start = 0 # Timer for phases like intro or extraction
        self.architect_vault_gauntlet_current_wave = 0
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self.architect_vault_message = "" # Message to display during vault
        self.architect_vault_message_timer = 0 # When the message should disappear
        self.architect_vault_failure_reason = "" # For game over screen after vault fail

        # Menu related attributes
        self.menu_options = ["Start Game", "Select Drone", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.player_name_input_display_cache = "" # For UIManager to display name entry
        self.leaderboard_scores = leaderboard.load_scores() # Load scores at startup

        # Drone selection attributes
        self.drone_select_options = DRONE_DISPLAY_ORDER # From drone_configs
        self.selected_drone_preview_index = 0 # Index in drone_select_options
        self.drone_main_display_cache = {} # Cache for large drone preview images
        self._load_drone_main_display_images() # Pre-load these images

        # Sound effects
        self.sounds = {}
        self.load_sfx()

        # Visuals for menus (e.g., background stars)
        self.menu_stars = []
        self._initialize_menu_stars()

        # Settings menu data
        self._initialize_settings_menu_items_data() # Defines the structure for settings UI

        # Set initial game state via SceneManager
        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def _initialize_fonts(self):
        """Loads all fonts required by the UI."""
        # Define font configurations (name, path, size)
        font_configs = {
            "ui_text": (self.font_path_neuropol, 28), "ui_values": (self.font_path_neuropol, 30),
            "ui_emoji_general": (self.font_path_emoji, 32), "ui_emoji_small": (self.font_path_emoji, 20),
            "small_text": (self.font_path_neuropol, 24), "medium_text": (self.font_path_neuropol, 48),
            "large_text": (self.font_path_neuropol, 74), "input_text": (self.font_path_neuropol, 50),
            "menu_text": (self.font_path_neuropol, 60), "title_text": (self.font_path_neuropol, 90),
            "drone_name_grid": (self.font_path_neuropol, 36), # For drone select grid (if used)
            "drone_desc_grid": (self.font_path_neuropol, 22), # For drone select grid (if used)
            "drone_unlock_grid": (self.font_path_neuropol, 20), # For drone select grid (if used)
            "drone_name_cycle": (self.font_path_neuropol, 42), # For main drone preview name
            "drone_stats_label_cycle": (self.font_path_neuropol, 26),
            "drone_stats_value_cycle": (self.font_path_neuropol, 28),
            "drone_desc_cycle": (self.font_path_neuropol, 22),
            "drone_unlock_cycle": (self.font_path_neuropol, 20),
            "vault_message": (self.font_path_neuropol, 36), "vault_timer": (self.font_path_neuropol, 48),
            "leaderboard_header": (self.font_path_neuropol, 32), "leaderboard_entry": (self.font_path_neuropol, 28),
            "arrow_font_key": (self.font_path_emoji, 60) # For large UI arrows
        }
        for name, (path, size) in font_configs.items():
            try:
                self.fonts[name] = pygame.font.Font(path, size)
            except pygame.error as e:
                print(f"GameController: Font loading error for '{name}' ('{path}', size {size}): {e}. Using fallback.")
                self.fonts[name] = pygame.font.Font(None, size) # Pygame's default font

    def _initialize_menu_stars(self, num_stars=150):
        """Creates a list of star parameters for the menu background."""
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, get_game_setting("WIDTH"))
            y = random.randint(0, get_game_setting("HEIGHT"))
            speed = random.uniform(0.1, 0.7) # Slower, more subtle star movement
            size = random.randint(1, 2) # Smaller stars
            self.menu_stars.append([x, y, speed, size]) # Store as [x, y, speed, radius]

    def _initialize_settings_menu_items_data(self):
        """Defines the data structure for items in the settings menu."""
        # This structure is used by UIManager to draw the settings and by EventManager to handle input
        self.settings_items_data = [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice",
             "choices":WEAPON_MODES_SEQUENCE, "get_display":lambda val:WEAPON_MODE_NAMES.get(val,"Unknown")},
            {"label":"Bullet Speed","key":"PLAYER_BULLET_SPEED","type":"numeric","min":2,"max":15,"step":1},
            {"label":"Bullet Lifetime (frames)","key":"PLAYER_BULLET_LIFETIME","type":"numeric","min":30,"max":300,"step":10},
            {"label":"Base Shoot Cooldown (ms)","key":"PLAYER_BASE_SHOOT_COOLDOWN","type":"numeric","min":100,"max":1000,"step":50},
            {"label":"Rapid Fire Cooldown (ms)","key":"PLAYER_RAPID_FIRE_COOLDOWN","type":"numeric","min":50,"max":500,"step":25},
            {"label":"Missile Cooldown (ms)","key":"MISSILE_COOLDOWN","type":"numeric","min":1000,"max":10000,"step":500},
            {"label":"Missile Damage","key":"MISSILE_DAMAGE","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Lightning Cooldown (ms)","key":"LIGHTNING_COOLDOWN","type":"numeric","min":200,"max":2000,"step":50},
            {"label":"Lightning Damage","key":"LIGHTNING_DAMAGE","type":"numeric","min":5,"max":50,"step":1},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","type":"numeric","min":0.5,"max":5,"step":0.5},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","type":"numeric","min":25,"max":300,"step":25},
            {"label":"Level Timer (sec)","key":"LEVEL_TIMER_DURATION","type":"numeric","min":60000,"max":300000,"step":15000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"}, # is_ms_to_sec for display conversion
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","type":"numeric","min":5000,"max":60000,"step":5000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Speed Boost Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","type":"numeric","min":3000,"max":30000,"step":2000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Fullscreen Mode","key":"FULLSCREEN_MODE","type":"choice",
             "choices":[False, True], "get_display":lambda val: "ON" if val else "OFF"},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"}, # Key for action
        ]
        self.selected_setting_index = 0 # Currently selected item in the settings menu

    def _create_fallback_image_surface(self, size=(200,200), text="?", color=(80,80,80), text_color=WHITE, font_key="large_text"):
        """Creates a fallback surface for drone images if they fail to load."""
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2) # Border
        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, size[1]//2)) # Fallback font
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e:
                print(f"GameController: Error rendering fallback image text '{text}': {e}")
        return surface

    def _load_drone_main_display_images(self):
        """Pre-loads and caches larger preview images for the drone selection screen."""
        self.drone_main_display_cache = {}
        display_size = (200, 200) # Standard size for main preview image in drone select

        for drone_id, data in DRONE_DATA.items():
            image_surface = None
            # Prefer "sprite_path" for main display, fallback to "icon_path"
            path_to_try = data.get("sprite_path") # From drone_configs.py
            if not path_to_try or not os.path.exists(path_to_try):
                path_to_try = data.get("icon_path") # Fallback to the smaller icon if main sprite missing

            if path_to_try and os.path.exists(path_to_try):
                try:
                    loaded_image = pygame.image.load(path_to_try).convert_alpha()
                    image_surface = pygame.transform.smoothscale(loaded_image, display_size)
                except pygame.error as e:
                    print(f"GameController: Error loading main display image for {drone_id} ('{path_to_try}'): {e}.")
                    # Fallback handled below if image_surface is still None
            else:
                 if path_to_try: print(f"GameController: Warning - Main display image path not found: {path_to_try}")

            if image_surface is None: # If loading failed or path was invalid/missing
                initials = data.get("name", "?")[:2].upper() # Use drone initials as text
                image_surface = self._create_fallback_image_surface(
                    size=display_size, text=initials, font_key="large_text" # Use a large font for initials
                )
            self.drone_main_display_cache[drone_id] = image_surface

    def load_sfx(self):
        """Loads all sound effects."""
        sound_files = {
            'collect_ring': "collect_ring.wav", 'weapon_upgrade_collect': "collect_powerup.wav",
            'collect_fragment': "collect_fragment.wav", 'crash': "crash.wav",
            'shoot': "shoot.wav", 'missile_launch': "missile_launch.wav",
            'level_up': "level_up.wav", 'player_death': "player_death.wav",
            'enemy_shoot': "enemy_shoot.wav", 'timer_out': "timer_warning.wav",
            'ui_select': "ui_select.wav", 'ui_confirm': "ui_confirm.wav", 'ui_denied': "ui_denied.wav",
            'cloak_activate': "cloak_on.wav", # Example sound
            'vault_alarm': "vault_alarm.wav",
            'vault_barrier_disable': "vault_barrier_disable.wav",
            'prototype_drone_explode': "prototype_drone_explode.wav"
            # Add more sounds here: 'lightning_zap_sound': "lightning.wav", etc.
        }
        sound_dir = os.path.join("assets", "sounds")
        for name, filename in sound_files.items():
            path = os.path.join(sound_dir, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    print(f"GameController: Sound load error for '{name}' ('{path}'): {e}")
            else:
                print(f"GameController: Sound file not found for '{name}': {path}")

    def play_sound(self, name, volume=0.7): # Default volume slightly lower
        """Plays a loaded sound effect by name."""
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()
        # else:
        #     print(f"GameController: Attempted to play unknown or unloaded sound '{name}'.")

    # --- Scene Initialization Methods (called by SceneManager) ---
    def initialize_main_menu_scene(self):
        self.selected_menu_option = 0
        # Any other specific setup for main menu

    def initialize_drone_select_scene(self):
        current_selected_id = self.drone_system.get_selected_drone_id()
        try:
            self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
        except ValueError:
            self.selected_drone_preview_index = 0 # Default to first drone if current not in list
        # UIManager will use drone_main_display_cache for drawing
        self.ui_manager.update_player_life_icon_surface() # Ensure life icon is up-to-date

    def initialize_settings_scene(self):
        self.selected_setting_index = 0
        # Potentially refresh displayed values if settings can change elsewhere

    def initialize_leaderboard_scene(self):
        self.leaderboard_scores = leaderboard.load_scores() # Reload scores when entering

    def initialize_enter_name_scene(self):
        self.player_name_input_display_cache = "" # Clear previous input

    def initialize_game_session(self):
        """Sets up a new game or a new level within a game session."""
        self.level = 1 # Reset to level 1 for a new game
        self.lives = get_game_setting("PLAYER_LIVES")
        self.score = 0
        self.drone_system.set_player_level(self.level) # Inform drone system of current level
        self.level_cleared_pending_animation = False
        self.all_enemies_killed_this_level = False

        self.maze = Maze(game_area_x_offset=0, maze_type="standard") # Standard maze for regular levels
        player_start_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8) # Use drone size for check

        selected_drone_id = self.drone_system.get_selected_drone_id()
        # Get stats for normal gameplay (not in architect vault)
        effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=False)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite_path = drone_config.get("ingame_sprite_path")

        # Create or reset the player instance
        if self.player is None:
            self.player = Drone(player_start_pos[0], player_start_pos[1],
                                drone_id=selected_drone_id, drone_stats=effective_drone_stats,
                                drone_sprite_path=player_ingame_sprite_path,
                                crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        else: # Player exists, reset it for new game/level
            self.player.reset(player_start_pos[0], player_start_pos[1],
                              drone_id=selected_drone_id, drone_stats=effective_drone_stats,
                              drone_sprite_path=player_ingame_sprite_path)

        self.ui_manager.update_player_life_icon_surface() # Update life icon based on selected drone

        # Clear and repopulate game world objects
        self.enemies.empty(); self._spawn_enemies_for_level()
        if self.player: # Ensure player exists before accessing its groups
            self.player.bullets_group.empty()
            self.player.missiles_group.empty()
            self.player.lightning_zaps_group.empty()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.architect_vault_terminals.empty() # Clear vault specific items

        self.collected_rings = 0; self.displayed_collected_rings = 0
        self.total_rings_per_level = 5 # Reset or adjust based on level design
        self.paused = False
        self.player_name_input_display_cache = "" # Clear name input
        self.animating_rings.clear()

        self._place_collectibles_for_level(initial_setup=True)
        self._reset_level_timer_internal()
        # SceneManager.set_game_state(GAME_STATE_PLAYING) is typically called by the menu action that starts the game.

    def initialize_architect_vault_session(self):
        """Initializes the game state for entering the Architect's Vault."""
        print("GameController: Initializing Architect's Vault session...")
        self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault") # Vault-specific maze

        # Preserve current weapon mode if player exists, otherwise use initial
        prev_weapon_mode_idx = WEAPON_MODES_SEQUENCE.index(get_game_setting("INITIAL_WEAPON_MODE"))
        prev_current_weapon_mode = get_game_setting("INITIAL_WEAPON_MODE")
        if self.player:
            prev_weapon_mode_idx = self.player.weapon_mode_index
            prev_current_weapon_mode = self.player.current_weapon_mode

        safe_spawn = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        selected_drone_id = self.drone_system.get_selected_drone_id() # Player uses their chosen drone
        # Get stats specifically for Architect's Vault (may include buffs/debuffs)
        effective_drone_stats_vault = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=True)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite_path = drone_config.get("ingame_sprite_path")

        if self.player:
            self.player.reset(safe_spawn[0], safe_spawn[1],
                              drone_id=selected_drone_id, drone_stats=effective_drone_stats_vault,
                              drone_sprite_path=player_ingame_sprite_path)
        else: # Should ideally not happen if player is needed for vault, but as a fallback
            self.player = Drone(safe_spawn[0], safe_spawn[1],
                                drone_id=selected_drone_id, drone_stats=effective_drone_stats_vault,
                                drone_sprite_path=player_ingame_sprite_path,
                                crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        
        # Restore previous weapon mode after reset
        if self.player:
            self.player.weapon_mode_index = prev_weapon_mode_idx
            self.player.current_weapon_mode = prev_current_weapon_mode
            self.player._update_weapon_attributes() # Apply the restored weapon mode settings
            self.player.reset_active_powerups() # Clear any powerups from previous level
            self.player.health = self.player.max_health # Full health for vault start
            self.player.moving_forward = False # Ensure not moving initially
            # Give a brief shield on entering the vault
            if hasattr(self.player, 'activate_shield'):
                self.player.activate_shield(1500, is_from_speed_boost=False) # 1.5 second shield

        self.enemies.empty()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.architect_vault_terminals.empty()

        self.architect_vault_current_phase = "intro" # Start with the intro phase
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.level_time_remaining_ms = 0 # Vault phases might have their own timers or conditions
        self.architect_vault_failure_reason = "" # Reset failure reason

        # SceneManager will call start_architect_vault_intro() next

    # --- Methods called by SceneManager for specific Architect's Vault phases ---
    def start_architect_vault_intro(self):
        self.architect_vault_current_phase = "intro"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.architect_vault_message = "The Architect's Vault... Entry protocol initiated."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000 # Message display duration

    def start_architect_vault_entry_puzzle(self):
        self.architect_vault_current_phase = "entry_puzzle"
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self._spawn_architect_vault_terminals() # Place terminals for the puzzle
        self.architect_vault_message = "Activate terminals with collected Core Fragments."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000

    def start_architect_vault_gauntlet(self):
        self.architect_vault_current_phase = "gauntlet_intro" # Transition phase before first wave
        self.architect_vault_gauntlet_current_wave = 0 # Reset wave count
        self.enemies.empty() # Clear any previous enemies
        self.architect_vault_message = "Security systems online. Prepare for hostiles."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 3000 # Short message

    def start_architect_vault_extraction(self):
        self.architect_vault_current_phase = "extraction"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.play_sound('vault_alarm', 0.7) # Play alarm sound
        self.architect_vault_message = "SELF-DESTRUCT SEQUENCE ACTIVATED! ESCAPE NOW!"
        # Set timer for extraction
        self.level_time_remaining_ms = get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS")
        self.architect_vault_message_timer = pygame.time.get_ticks() + self.level_time_remaining_ms # Message lasts as long as timer

    # --- Methods for handling outcomes of Architect's Vault ---
    def handle_architect_vault_success_scene(self): # Called by SceneManager when state changes to SUCCESS
        self.architect_vault_message = "Vault Conquered! Blueprint Acquired!"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000 # Display success message
        # DroneSystem handles actual unlocking of blueprint/lore
        self.drone_system.mark_architect_vault_completed(True)
        self.score += 2500 # Bonus score for vault completion
        self.drone_system.add_player_cores(500) # Bonus cores
        self.drone_system._save_unlocks() # Ensure progress is saved

    def handle_architect_vault_failure_scene(self): # Called by SceneManager for FAILURE state
        # Failure reason should be set before this state is entered
        self.architect_vault_message = f"Vault Mission Failed: {self.architect_vault_failure_reason}"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        self.drone_system.mark_architect_vault_completed(False) # Mark as failed attempt
        # No score/core penalty or bonus, just failure

    def handle_game_over_scene_entry(self): # Called by SceneManager for GAME_OVER state
        """Prepares data for the game over screen."""
        self.drone_system.set_player_level(self.level) # Update max level reached
        self.drone_system._save_unlocks() # Save final progress
        # UIManager will draw the game over screen using self.score, self.level, etc.
        # EventManager handles input for restart/menu/quit options.

    # --- Main Game Update Method ---
    def update(self):
        """Main update logic called every frame by the run loop."""
        current_game_state = self.scene_manager.get_current_state()
        current_time = pygame.time.get_ticks()

        if current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_playing_state(current_time)
        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused:
            self._update_bonus_level_state(current_time)
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state(current_time)
        elif current_game_state in [GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
                                    GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD]:
            # Update menu elements like scrolling stars
            if hasattr(self, 'menu_stars') and self.menu_stars:
                for star in self.menu_stars:
                    star[0] -= star[2] # Move star left
                    if star[0] < 0: # If star goes off screen, reset its position
                        star[0] = get_game_setting("WIDTH")
                        star[1] = random.randint(0, get_game_setting("HEIGHT"))

        # SceneManager might have its own update logic (e.g., for timed transitions)
        if hasattr(self.scene_manager, 'update'):
            self.scene_manager.update()

    # --- State-Specific Update Methods ---
    def _update_playing_state(self, current_time):
        """Update logic for the main gameplay state."""
        if not self.player or not self.maze:
            print("GameController: Error - Player or Maze not initialized for PLAYING state.")
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return

        if not self.level_cleared_pending_animation: # Only update game logic if level not cleared
            # Update level timer
            elapsed_time_current_level_ms = current_time - self.level_timer_start_ticks
            self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION") - elapsed_time_current_level_ms
            if self.level_time_remaining_ms <= 0:
                self.play_sound('timer_out')
                self._handle_player_death_or_life_loss("Time Ran Out!") # Common handler
                return # Stop further updates this frame

            # Update player (movement, abilities, etc.)
            if self.player.alive:
                # PlayerActions might handle some input continuously, player.update handles state changes
                self.player.update(current_time, self.maze, self.enemies, 0) # game_area_x_offset is 0
            else: # Player died
                self._handle_player_death_or_life_loss("Drone Destroyed!")
                return

            # Update enemies
            for enemy_obj in list(self.enemies): # Iterate over a copy for safe removal
                if enemy_obj.alive:
                    enemy_obj.update(self.player.get_position() if self.player else (0,0), self.maze, current_time, 0)
                elif not enemy_obj.bullets: # If dead and no bullets left
                    enemy_obj.kill()
            
            # Update collectibles
            self.rings.update() # Rings update their visuals
            for p_up in list(self.power_ups):
                if p_up.update(): p_up.kill() # Powerup update returns True if expired/collected
            for fragment in list(self.core_fragments):
                fragment.update() # Fragments update visuals

            self._check_collisions_playing() # Handle all gameplay collisions

            # Spawn power-ups periodically
            if random.random() < (get_game_setting("POWERUP_SPAWN_CHANCE") / get_game_setting("FPS")):
                 if len(self.power_ups) < get_game_setting("MAX_POWERUPS_ON_SCREEN"):
                    self._try_spawn_powerup_item()

        # Update ring collection animation
        for ring_anim in list(self.animating_rings):
            dx = ring_anim['target_pos'][0] - ring_anim['pos'][0]
            dy = ring_anim['target_pos'][1] - ring_anim['pos'][1]
            dist = math.hypot(dx,dy)
            if dist < ring_anim['speed']: # Reached target
                self.animating_rings.remove(ring_anim)
                self.displayed_collected_rings += 1
                self.displayed_collected_rings = min(self.displayed_collected_rings, self.collected_rings)
            else: # Move towards target
                ring_anim['pos'][0] += (dx / dist) * ring_anim['speed']
                ring_anim['pos'][1] += (dy / dist) * ring_anim['speed']

        # If level clear condition met and animations finished, proceed to next level
        if self.level_cleared_pending_animation and not self.animating_rings:
            self._prepare_for_next_level() # Renamed from _level_up_logic for clarity
            self.level_cleared_pending_animation = False


    def _update_bonus_level_state(self, current_time): # If bonus levels are used
        """Update logic for the bonus level state."""
        if not self.player or not self.player.alive:
            self._end_bonus_level(completed=False)
            return
        
        self.player.update(current_time, self.maze, None, 0) # No enemies in typical bonus, no offset
        
        elapsed_bonus_time = current_time - self.bonus_level_timer_start
        self.level_time_remaining_ms = max(0, self.bonus_level_duration_ms - elapsed_bonus_time)
        if self.level_time_remaining_ms <= 0:
            self._end_bonus_level(completed=True)
            return
        # Bonus level specific collision checks or collectible logic here


    def _update_architect_vault_state(self, current_time):
        """Update logic for various phases of the Architect's Vault."""
        if not self.player or not self.maze:
            print("GameController: Error - Player or Maze not initialized for ARCHITECT_VAULT state.")
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
        if not self.player.alive:
            self.architect_vault_failure_reason = "Drone critically damaged."
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
            return
        if self.paused: return

        # Player update is common to most vault phases
        self.player.update(current_time, self.maze, self.enemies, 0) # game_area_x_offset is 0

        # Phase-specific logic
        current_phase = self.architect_vault_current_phase
        if current_phase == "intro":
            # SceneManager's update handles timed transition from intro
            pass
        elif current_phase == "entry_puzzle":
            if hasattr(self.architect_vault_terminals, 'update'):
                self.architect_vault_terminals.update() # Terminals might have animations
            self._check_collisions_architect_vault_puzzle() # Check player interaction with terminals
            # Transition to gauntlet is handled by try_activate_vault_terminal if all are active
        elif current_phase == "gauntlet_intro":
            if current_time > self.architect_vault_message_timer: # After intro message
                self.architect_vault_gauntlet_current_wave = 1
                self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                self._spawn_prototype_drones(ARCHITECT_VAULT_DRONES_PER_WAVE[0])
                self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif current_phase and current_phase.startswith("gauntlet_wave"):
            self.enemies.update(self.player.get_position() if self.player else (0,0), self.maze, current_time, 0)
            self._check_collisions_architect_vault_combat()
            if not self.enemies: # All enemies in wave defeated
                self.play_sound('level_up') # Or a specific wave clear sound
                self.architect_vault_gauntlet_current_wave += 1
                if self.architect_vault_gauntlet_current_wave > ARCHITECT_VAULT_GAUNTLET_WAVES:
                    self.architect_vault_message = "Gauntlet cleared. Accessing core systems..."
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                    self.architect_vault_current_phase = "gauntlet_cleared_transition"
                    self.architect_vault_phase_timer_start = current_time # Timer for this transition
                else:
                    self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                    num_drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[self.architect_vault_gauntlet_current_wave - 1]
                    self._spawn_prototype_drones(num_drones_this_wave)
                    self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif current_phase == "gauntlet_cleared_transition":
            if current_time - self.architect_vault_phase_timer_start > 2000: # Short delay
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif current_phase == "extraction":
            time_elapsed_extraction = current_time - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - time_elapsed_extraction)
            if self.level_time_remaining_ms <= 0:
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS)
                return
            # Optionally spawn more enemies during extraction
            if random.random() < 0.008 : # Small chance to spawn an enemy
                 if len(self.enemies) < 3: # Limit max enemies during extraction
                     self._spawn_prototype_drones(1, far_from_player=True)
            self.enemies.update(self.player.get_position() if self.player else (0,0), self.maze, current_time, 0)
            self._check_collisions_architect_vault_combat() # Collisions still active


    # --- Collision Handling Methods ---
    def _check_collisions_playing(self):
        """Handles collisions for the standard gameplay state."""
        if not self.player or not self.player.alive: return

        # Player vs Rings
        if not self.level_cleared_pending_animation:
            collided_rings_sprites = pygame.sprite.spritecollide(self.player, self.rings, True, pygame.sprite.collide_rect_ratio(0.7))
            for ring_sprite in collided_rings_sprites:
                self.score += 10
                self.play_sound('collect_ring')
                self.collected_rings += 1
                self.drone_system.add_player_cores(5) # Add cores for rings

                # Start animation for ring flying to HUD
                anim_ring_surf = None
                if hasattr(ring_sprite, 'image') and self.ui_manager.ui_assets.get("ring_icon"): # Use a small version of UI icon
                    try:
                        anim_ring_surf = pygame.transform.smoothscale(self.ui_manager.ui_assets["ring_icon"], (15,15))
                    except Exception as e: print(f"Error scaling ring for anim: {e}")
                if anim_ring_surf:
                    self.animating_rings.append({
                        'pos': list(ring_sprite.rect.center),
                        'target_pos': self.ring_ui_target_pos, # UIManager updates this
                        'speed': 15, 'surface': anim_ring_surf
                    })
                self._check_level_clear_condition() # Check if all rings collected
                if self.level_cleared_pending_animation: break # Stop collecting if level cleared

        # Player vs Power-ups
        collided_powerups = pygame.sprite.spritecollide(self.player, self.power_ups, False, pygame.sprite.collide_rect_ratio(0.7))
        for item in collided_powerups:
            if not item.collected and not item.expired and hasattr(item, 'apply_effect'):
                item.apply_effect(self.player) # Item applies its effect to player
                item.collected = True; item.kill() # Mark collected and remove
                self.play_sound('weapon_upgrade_collect') # Generic powerup sound
                self.score += 25

        # Player vs Core Fragments
        collided_fragments = pygame.sprite.spritecollide(self.player, self.core_fragments, False, pygame.sprite.collide_rect_ratio(0.7))
        for fragment in collided_fragments:
            if not fragment.collected and hasattr(fragment, 'apply_effect'):
                # fragment.apply_effect now takes game_controller to access drone_system
                if fragment.apply_effect(self.player, self): # Pass self (GameController)
                    fragment.collected = True; fragment.kill()
                    self.play_sound('collect_fragment')
                    self.score += 100
                    if self.drone_system.are_all_core_fragments_collected():
                        self.architect_vault_message = "All Core Fragments Acquired! Vault Access Imminent!"
                        self.architect_vault_message_timer = pygame.time.get_ticks() + 4000

        # Player Projectiles vs Enemies
        if self.player.alive:
            player_projectiles = pygame.sprite.Group() # Combine all player projectile types
            player_projectiles.add(self.player.bullets_group, self.player.missiles_group, self.player.lightning_zaps_group)
            
            for projectile in list(player_projectiles):
                if not projectile.alive: continue # Should be removed by their own update
                # Lightning might need special collision (line segment vs enemy rect)
                if isinstance(projectile, LightningZap): # Example for lightning
                    # For lightning, check intersection of its line segment with enemies
                    # This is a simplified rect collision for now; line segment is better
                    hit_enemies_lightning = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.8))
                    for enemy_hit in hit_enemies_lightning:
                        if enemy_hit.alive:
                            enemy_hit.take_damage(projectile.damage)
                            # Lightning might not be "killed" on hit, but could chain or fade
                    projectile.alive = False # Basic lightning zap hits once or fades
                else: # Bullets and Missiles
                    hit_enemies = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.8))
                    for enemy_obj in hit_enemies:
                        if enemy_obj.alive:
                            enemy_obj.take_damage(projectile.damage)
                            # Handle piercing for bullets
                            if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                                projectile.pierces_done += 1
                            else: # Not piercing or max pierces reached
                                projectile.alive = False; projectile.kill() # Kill projectile on hit
                            
                            if not enemy_obj.alive: # If enemy died
                                self.score += 50
                                self.drone_system.add_player_cores(25)
                                self.all_enemies_killed_this_level = all(not e.alive for e in self.enemies)
                                if self.all_enemies_killed_this_level:
                                    self._check_level_clear_condition() # Check if this also clears level
                            if not projectile.alive: break # Projectile is used up

        # Enemy Projectiles vs Player
        for enemy_obj in self.enemies:
            if hasattr(enemy_obj, 'bullets') and enemy_obj.bullets: # Check if enemy has bullets group
                for bullet_obj in list(enemy_obj.bullets):
                    if self.player.alive and bullet_obj.rect.colliderect(self.player.collision_rect): # Player collision_rect
                        self.player.take_damage(get_game_setting("ENEMY_BULLET_DAMAGE"), self.sounds.get('crash'))
                        bullet_obj.alive = False; bullet_obj.kill()
                    if not bullet_obj.alive and bullet_obj in enemy_obj.bullets: # Should be handled by bullet's update
                        pass # enemy_obj.bullets.remove(bullet_obj) - sprite.kill() handles group removal

        # Player vs Enemies (Physical Collision)
        if self.player.alive:
            # Use player's collision_rect for more accurate physical collision
            enemy_physical_collisions = pygame.sprite.spritecollide(self.player, self.enemies, False, 
                                                                    lambda drone, enemy: drone.collision_rect.colliderect(enemy.collision_rect))
            for enemy_obj in enemy_physical_collisions:
                if enemy_obj.alive:
                    self.player.take_damage(34, self.sounds.get('crash')) # Example damage for physical collision
                    # Optionally, enemy also takes damage or bounces off
                    # enemy_obj.take_damage(10)
                if not self.player.alive: break # Stop checking if player died


    def _check_collisions_architect_vault_puzzle(self):
        """Handles collisions for the Architect's Vault puzzle phase (player vs terminals)."""
        if not self.player or not self.player.alive or not self.architect_vault_terminals:
            return

        # Check collision between player and terminals
        # Player needs to be near a terminal and press a key (handled by EventManager)
        # This method could highlight a terminal if player is close enough.
        for terminal_sprite in self.architect_vault_terminals:
            if self.player.rect.colliderect(terminal_sprite.rect): # Simple rect collision for proximity
                # UI could show "Press [1/2/3] to activate" if player is near terminal_id
                # Actual activation is via EventManager calling try_activate_vault_terminal
                pass


    def _check_collisions_architect_vault_combat(self):
        """Handles combat collisions within the Architect's Vault (similar to _check_collisions_playing)."""
        if not self.player or not self.player.alive: return

        # Player Projectiles vs Prototype Drones (Enemies)
        player_projectiles = pygame.sprite.Group(self.player.bullets_group, self.player.missiles_group, self.player.lightning_zaps_group)
        for projectile in list(player_projectiles):
            if not projectile.alive: continue
            if isinstance(projectile, LightningZap):
                hit_prototypes_lightning = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.8))
                for enemy_hit in hit_prototypes_lightning:
                    if enemy_hit.alive: enemy_hit.take_damage(projectile.damage)
                projectile.alive = False
            else:
                hit_prototypes = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.7))
                for enemy_obj in hit_prototypes:
                    if enemy_obj.alive:
                        enemy_obj.take_damage(projectile.damage)
                        if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                            projectile.pierces_done +=1
                        else:
                            projectile.alive = False; projectile.kill()
                        if not enemy_obj.alive:
                            self.score += 75 # More score for tougher vault enemies
                            self.drone_system.add_player_cores(10)
                            self.play_sound('prototype_drone_explode')
                        if not projectile.alive: break

        # Prototype Drone Projectiles vs Player
        for enemy_obj in self.enemies: # Enemies are prototype drones in this context
            if hasattr(enemy_obj, 'bullets') and enemy_obj.bullets:
                for bullet_obj in list(enemy_obj.bullets):
                    if self.player.alive and bullet_obj.rect.colliderect(self.player.collision_rect):
                        self.player.take_damage(get_game_setting("ENEMY_BULLET_DAMAGE") * 1.2, self.sounds.get('crash')) # Vault bullets might hurt more
                        bullet_obj.alive = False; bullet_obj.kill()

        # Player vs Prototype Drones (Physical Collision)
        if self.player.alive:
            enemy_physical_collisions = pygame.sprite.spritecollide(self.player, self.enemies, False,
                                                                    lambda drone, enemy: drone.collision_rect.colliderect(enemy.collision_rect))
            for enemy_obj in enemy_physical_collisions:
                if enemy_obj.alive:
                    self.player.take_damage(40, self.sounds.get('crash')) # Higher collision damage in vault
                if not self.player.alive: break


    # --- Level Progression and Game State Helpers ---
    def _handle_player_death_or_life_loss(self, reason=""):
        """Handles logic when player loses a life or timer runs out."""
        if self.player: self.player.reset_active_powerups() # Clear powerups on death/timeout
        self.lives -= 1
        if self.lives <= 0:
            self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
        else: # Still has lives, reset player and timer for current level
            self._reset_player_after_death_internal() # Resets player position and health
            self._reset_level_timer_internal() # Resets level timer

    def _check_level_clear_condition(self):
        """Checks if conditions to clear the current level are met."""
        # Standard level clear: collect all rings AND kill all enemies (optional for enemies)
        # For now, let's stick to rings primarily, and all_enemies_killed for bonus.
        if self.player and self.collected_rings >= self.total_rings_per_level and \
           not self.level_cleared_pending_animation:
            # Optional: Check if all_enemies_killed_this_level is also required
            # if self.all_enemies_killed_this_level:
            self.player.moving_forward = False # Stop player movement
            self.level_cleared_pending_animation = True # Wait for ring animations
            print("Level clear condition met (rings). Pending animation.")

    def _prepare_for_next_level(self, from_bonus_level_completion=False):
        """Sets up the game for the next level or transitions after bonus/vault."""
        # Check if Architect's Vault should be triggered
        if self.drone_system.are_all_core_fragments_collected() and \
           not self.drone_system.has_completed_architect_vault() and \
           not from_bonus_level_completion: # Don't go to vault from bonus level
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_INTRO)
            return

        if not from_bonus_level_completion:
            self.level += 1
        
        self.collected_rings = 0
        self.displayed_collected_rings = 0 # Reset for UI
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15) # Increase rings for next level, cap at 15
        self.drone_system.set_player_level(self.level) # Inform DroneSystem of new level

        if self.player:
            # Weapon upgrade if all enemies were killed (optional rule)
            if self.all_enemies_killed_this_level and hasattr(self.player, 'cycle_weapon_state'):
                self.player.cycle_weapon_state(force_cycle=False) # False = don't cycle if at max
            self.player.health = min(self.player.health + 25, self.player.max_health) # Small health bonus
            # Reset player for the new level (position, clear powerups, etc.)
            new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            # Get current drone's data for reset
            current_drone_id = self.player.drone_id
            current_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False)
            current_drone_config = self.drone_system.get_drone_config(current_drone_id)
            current_ingame_sprite = current_drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1],
                              drone_id=current_drone_id, drone_stats=current_drone_stats,
                              drone_sprite_path=current_ingame_sprite)
            # Preserve weapon mode through level up
            # self.player.current_weapon_mode and self.player.weapon_mode_index are preserved by player.reset if not explicitly changed

        self.all_enemies_killed_this_level = False # Reset for new level
        self.maze = Maze(game_area_x_offset=0, maze_type="standard") # New maze for new level
        self._spawn_enemies_for_level()
        self.core_fragments.empty() # Core fragments are specific to certain levels usually
        self._place_collectibles_for_level(initial_setup=True) # Place new rings and powerups
        
        self._reset_level_timer_internal()
        self.play_sound('level_up')
        self.animating_rings.clear()
        if self.player: self.player.moving_forward = False # Ensure player isn't moving at level start

        # Ensure game state is set back to playing if not handled by a special transition
        if not self.scene_manager.get_current_state().startswith("architect_vault"):
            self.scene_manager.set_game_state(GAME_STATE_PLAYING)


    def _reset_player_after_death_internal(self):
        """Resets player's position and health after losing a life, without changing level."""
        if not self.player: return

        new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        # Get current drone's data for reset
        current_drone_id = self.player.drone_id
        # Determine if currently in vault to get correct stats
        is_in_vault = self.scene_manager.get_current_state().startswith("architect_vault")
        current_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=is_in_vault)
        current_drone_config = self.drone_system.get_drone_config(current_drone_id)
        current_ingame_sprite = current_drone_config.get("ingame_sprite_path")
        
        # Preserve weapon mode through death
        prev_weapon_idx = self.player.weapon_mode_index
        prev_weapon_mode = self.player.current_weapon_mode

        self.player.reset(new_player_pos[0], new_player_pos[1],
                          drone_id=current_drone_id, drone_stats=current_drone_stats,
                          drone_sprite_path=current_ingame_sprite,
                          health_override=self.player.max_health) # Reset to full health for this life
        
        self.player.weapon_mode_index = prev_weapon_idx
        self.player.current_weapon_mode = prev_weapon_mode
        self.player._update_weapon_attributes()

        self.animating_rings.clear() # Clear any pending ring animations
        self.level_cleared_pending_animation = False # Reset level clear flag

    def _reset_level_timer_internal(self):
        """Resets the timer for the current level."""
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level(self, completed=True): # If bonus levels are used
        """Handles logic at the end of a bonus level."""
        print(f"GameController: Bonus Level Ended. Completed: {completed}")
        if completed:
            self.score += 500 # Example bonus score
            self.drone_system.add_player_cores(250) # Example bonus cores
        self.drone_system._save_unlocks() # Save any earned cores
        self._prepare_for_next_level(from_bonus_level_completion=True) # Transition back to normal progression

    # --- Spawning and Placement Helpers ---
    def _get_safe_spawn_point(self, entity_width, entity_height):
        """Finds a random valid path cell center for spawning, avoiding walls."""
        if not self.maze: # Should not happen if maze is initialized
            print("GameController: Warning - Attempted to get spawn point without a maze.")
            return (get_game_setting("WIDTH") // 4, get_game_setting("GAME_PLAY_AREA_HEIGHT") // 2) # Fallback

        # Get path cell centers relative to maze origin (0,0)
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative:
            print("GameController: Warning - No path cells found in maze for spawning.")
            return (self.maze.game_area_x_offset + TILE_SIZE//2, TILE_SIZE//2) # Fallback to top-left of maze

        # Convert to absolute screen coordinates and shuffle for randomness
        path_cells_absolute = [(x + self.maze.game_area_x_offset, y) for x, y in path_cells_relative]
        random.shuffle(path_cells_absolute)

        for spawn_x_abs, spawn_y_abs in path_cells_absolute:
            # Check if this absolute position is clear of walls using entity dimensions
            if not self.maze.is_wall(spawn_x_abs, spawn_y_abs, entity_width, entity_height):
                return (spawn_x_abs, spawn_y_abs)
        
        # If all shuffled cells failed (highly unlikely with proper maze), return first one
        print("GameController: Warning - Could not find a 'perfectly safe' spawn point. Using first available path cell.")
        first_abs_x = path_cells_relative[0][0] + self.maze.game_area_x_offset
        first_abs_y = path_cells_relative[0][1]
        return (first_abs_x, first_abs_y)

    def _spawn_enemies_for_level(self):
        """Spawns enemies for the current regular level."""
        self.enemies.empty()
        num_enemies = min(self.level + 1, 7) # Example: level number + 1, max 7 enemies
        
        enemy_shoot_sound = self.sounds.get('enemy_shoot')
        # Get PLAYER_DEFAULT_BULLET_SIZE once to pass to Enemy constructor, used for enemy bullet size scaling
        player_bullet_size_setting = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

        for _ in range(num_enemies):
            # Try to find a spawn point away from player and other enemies
            spawn_attempts = 0
            spawned = False
            while spawn_attempts < 10 and not spawned:
                abs_x, abs_y = self._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7) # Enemy size for check
                if abs_x is None: break # No safe points

                # Check distance from player
                if self.player and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 4: # Too close to player
                    spawn_attempts += 1; continue
                # Check distance from other enemies
                if any(math.hypot(abs_x - e.x, abs_y - e.y) < TILE_SIZE * 2 for e in self.enemies): # Too close to another enemy
                    spawn_attempts += 1; continue
                
                self.enemies.add(Enemy(abs_x, abs_y, player_bullet_size_setting, shoot_sound=enemy_shoot_sound))
                spawned = True
            
            if not spawned: # If too many attempts, just spawn at a random safe spot
                abs_x_fallback, abs_y_fallback = self._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7)
                if abs_x_fallback is not None:
                    self.enemies.add(Enemy(abs_x_fallback, abs_y_fallback, player_bullet_size_setting, shoot_sound=enemy_shoot_sound))

    def _spawn_prototype_drones(self, count, far_from_player=False):
        """Spawns prototype drones for the Architect's Vault."""
        if not self.maze: return
        
        enemy_shoot_sound = self.sounds.get('enemy_shoot')
        player_bullet_size_setting = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        prototype_sprite = get_game_setting("PROTOTYPE_DRONE_SPRITE_PATH")

        for _ in range(count):
            spawn_attempts = 0; spawned = False
            while spawn_attempts < 10 and not spawned:
                abs_x, abs_y = self._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7)
                if abs_x is None: break

                if self.player and far_from_player and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 7:
                    spawn_attempts += 1; continue
                if any(math.hypot(abs_x - e.x, abs_y - e.y) < TILE_SIZE * 3 for e in self.enemies):
                    spawn_attempts += 1; continue
                
                proto_drone = Enemy(abs_x, abs_y, player_bullet_size_setting,
                                    shoot_sound=enemy_shoot_sound, sprite_path=prototype_sprite)
                # Customize stats for prototype drone
                proto_drone.health = get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.max_health = get_game_setting("PROTOTYPE_DRONE_HEALTH")
                proto_drone.speed = get_game_setting("PROTOTYPE_DRONE_SPEED")
                proto_drone.shoot_cooldown = get_game_setting("PROTOTYPE_DRONE_SHOOT_COOLDOWN")
                # proto_drone.enemy_bullet_size could also be customized
                self.enemies.add(proto_drone)
                spawned = True
            
            if not spawned: # Fallback if specific placement fails
                abs_x_fb, abs_y_fb = self._get_safe_spawn_point(TILE_SIZE * 0.7, TILE_SIZE * 0.7)
                if abs_x_fb is not None:
                    proto_drone_fb = Enemy(abs_x_fb, abs_y_fb, player_bullet_size_setting,
                                           shoot_sound=enemy_shoot_sound, sprite_path=prototype_sprite)
                    proto_drone_fb.health = get_game_setting("PROTOTYPE_DRONE_HEALTH"); # etc. for other stats
                    self.enemies.add(proto_drone_fb)


    def _spawn_architect_vault_terminals(self):
        """Spawns interactive terminals for the Architect's Vault entry puzzle."""
        self.architect_vault_terminals.empty()
        if not self.maze or not CORE_FRAGMENT_DETAILS: return

        path_cells_relative = self.maze.get_path_cells()
        if len(path_cells_relative) < TOTAL_CORE_FRAGMENTS_NEEDED:
            print("GameController: Warning - Not enough path cells to spawn all vault terminals.")
            return

        # Ensure we only try to spawn terminals for which we have fragment details
        num_terminals_to_spawn = min(TOTAL_CORE_FRAGMENTS_NEEDED, len(CORE_FRAGMENT_DETAILS))
        
        # Get distinct spawn locations
        available_spawn_points_rel = random.sample(path_cells_relative, k=num_terminals_to_spawn)

        for i in range(num_terminals_to_spawn):
            pos_rel = available_spawn_points_rel[i]
            abs_x = pos_rel[0] + self.maze.game_area_x_offset # Apply offset for absolute position
            abs_y = pos_rel[1]

            terminal = pygame.sprite.Sprite() # Basic sprite for terminal
            # Visual representation of the terminal
            terminal.image = pygame.Surface([TILE_SIZE * 0.6, TILE_SIZE * 0.6], pygame.SRCALPHA)
            terminal.image.fill(DARK_PURPLE) # Base color for inactive terminal
            pygame.draw.rect(terminal.image, ARCHITECT_VAULT_ACCENT_COLOR, terminal.image.get_rect(), 2) # Border
            # Add a small visual cue, like a number or symbol
            num_font = self.fonts.get("ui_text", pygame.font.Font(None, 24))
            num_surf = num_font.render(str(i+1), True, WHITE)
            terminal.image.blit(num_surf, num_surf.get_rect(center=(terminal.image.get_width()//2, terminal.image.get_height()//2)))

            terminal.rect = terminal.image.get_rect(center=(abs_x, abs_y))
            terminal.terminal_id = i # Corresponds to index in CORE_FRAGMENT_DETAILS or puzzle sequence
            terminal.is_active = False # Player needs to activate it
            self.architect_vault_terminals.add(terminal)

    def _try_spawn_powerup_item(self):
        """Attempts to spawn a random power-up item (shield, speed, weapon upgrade) in a valid location."""
        if not self.maze: return

        # Use the global POWERUP_TYPES imported from game_settings
        if not POWERUP_TYPES: # Check if POWERUP_TYPES is empty or not loaded
            # print("GameController: POWERUP_TYPES not defined or empty. Cannot spawn powerup.") # Optional debug
            return

        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return

        # Create a set of existing collectible absolute center coordinates to avoid overlap
        existing_coords_abs = set(r.rect.center for r in self.rings)
        for p_up in self.power_ups: existing_coords_abs.add(p_up.rect.center)
        for frag in self.core_fragments: existing_coords_abs.add(frag.rect.center)

        # Filter path cells to find available spawn locations
        available_spawn_cells_abs = []
        for rcx_rel, rcy_rel in path_cells_relative:
            abs_center_x = rcx_rel + self.maze.game_area_x_offset
            abs_center_y = rcy_rel
            if (abs_center_x, abs_center_y) not in existing_coords_abs:
                # Further check: ensure it's not too close to player if player exists
                if self.player and math.hypot(abs_center_x - self.player.x, abs_center_y - self.player.y) < TILE_SIZE * 2:
                    continue
                available_spawn_cells_abs.append((abs_center_x, abs_center_y))

        if not available_spawn_cells_abs: return # No suitable spot found
        
        abs_x, abs_y = random.choice(available_spawn_cells_abs)
        
        powerup_type_keys = list(POWERUP_TYPES.keys()) # Get available types
        if not powerup_type_keys: return # No powerup types defined

        chosen_type_key = random.choice(powerup_type_keys)
        
        new_powerup = None
        if chosen_type_key == "weapon_upgrade": new_powerup = WeaponUpgradeItem(abs_x, abs_y)
        elif chosen_type_key == "shield": new_powerup = ShieldItem(abs_x, abs_y)
        elif chosen_type_key == "speed_boost": new_powerup = SpeedBoostItem(abs_x, abs_y)
        
        if new_powerup:
            self.power_ups.add(new_powerup)

    def _place_collectibles_for_level(self, initial_setup=False):
        """Places rings, core fragments, and potentially initial power-ups for a level."""
        if not self.maze: return

        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return

        # Place Rings
        if initial_setup: # Only place rings at the very start of a new level setup
            self.rings.empty()
            # Ensure we don't try to sample more rings than available path cells
            num_rings_to_place = min(self.total_rings_per_level, len(path_cells_relative))
            if num_rings_to_place > 0:
                ring_spawn_points_rel = random.sample(path_cells_relative, k=num_rings_to_place)
                for rel_x, rel_y in ring_spawn_points_rel:
                    abs_x = rel_x + self.maze.game_area_x_offset
                    abs_y = rel_y
                    self.rings.add(Ring(abs_x, abs_y))

        # Spawn Core Fragments if they are due for this level (DroneSystem tracks collection)
        self._spawn_core_fragments_for_level_internal()

        # Spawn initial power-up(s)
        # For example, spawn one power-up at the start of the level
        if initial_setup:
            self._try_spawn_powerup_item()


    def _spawn_core_fragments_for_level_internal(self):
        """Spawns core fragments in REGULAR levels based on conditions (e.g., specific level)."""
        if not self.maze or not CORE_FRAGMENT_DETAILS: return

        occupied_fragment_tiles_this_level = set() # To avoid spawning multiple fragments on the same tile
        
        for frag_key, details in CORE_FRAGMENT_DETAILS.items():
            if not details or not isinstance(details, dict): continue # Skip if details are malformed
            
            spawn_info = details.get("spawn_info", {})
            # Check if this fragment should spawn on the current game level
            # and if the player hasn't collected it yet (tracked by DroneSystem)
            if spawn_info.get("level") == self.level and \
               not self.drone_system.has_collected_fragment(details["id"]):
                
                # Find a valid, unoccupied tile for this fragment
                random_tile_coords_rel = self._get_random_valid_fragment_tile_internal(occupied_fragment_tiles_this_level)
                
                if random_tile_coords_rel:
                    tile_c_rel, tile_r_rel = random_tile_coords_rel # c, r from maze grid
                    # Convert relative grid coords to absolute screen center coords
                    abs_x = tile_c_rel * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = tile_r_rel * TILE_SIZE + TILE_SIZE // 2
                    
                    self.core_fragments.add(CoreFragmentItem(abs_x, abs_y, details["id"], details))
                    occupied_fragment_tiles_this_level.add(random_tile_coords_rel) # Mark tile as occupied for this level's spawn

    def _get_random_valid_fragment_tile_internal(self, existing_fragment_tiles_rel):
        """ Helper to find a random valid tile (relative grid coords) for fragment spawning, avoiding occupied ones."""
        if not self.maze or not self.maze.grid: return None
        
        available_path_tiles_rel = [] # List of (c, r) tuples
        for r_idx in range(self.maze.actual_maze_rows):
            for c_idx in range(self.maze.actual_maze_cols):
                if self.maze.grid[r_idx][c_idx] == 0 and (c_idx, r_idx) not in existing_fragment_tiles_rel:
                    available_path_tiles_rel.append((c_idx, r_idx))
        
        if not available_path_tiles_rel:
            return None # No available spots
        return random.choice(available_path_tiles_rel)


    # --- Input Handling Wrappers (called by EventManager) ---
    # These methods now mostly delegate to specific handlers or change game state.
    def handle_main_menu_input(self, key_event):
        # Logic for navigating main menu options
        if key_event == pygame.K_UP:
            self.selected_menu_option = (self.selected_menu_option - 1 + len(self.menu_options)) % len(self.menu_options)
            self.play_sound('ui_select')
        elif key_event == pygame.K_DOWN:
            self.selected_menu_option = (self.selected_menu_option + 1) % len(self.menu_options)
            self.play_sound('ui_select')
        elif key_event == pygame.K_RETURN:
            self.play_sound('ui_confirm')
            action = self.menu_options[self.selected_menu_option]
            if action == "Start Game":
                self.initialize_game_session() # Setup game for level 1
                self.scene_manager.set_game_state(GAME_STATE_PLAYING)
            elif action == "Select Drone":
                self.scene_manager.set_game_state(GAME_STATE_DRONE_SELECT)
            elif action == "Settings":
                self.scene_manager.set_game_state(GAME_STATE_SETTINGS)
            elif action == "Leaderboard":
                self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif action == "Quit":
                self.quit_game()

    def handle_drone_select_input(self, key_event):
        num_options = len(self.drone_select_options)
        if num_options == 0: return

        if key_event == pygame.K_LEFT:
            self.selected_drone_preview_index = (self.selected_drone_preview_index - 1 + num_options) % num_options
            self.play_sound('ui_select')
        elif key_event == pygame.K_RIGHT:
            self.selected_drone_preview_index = (self.selected_drone_preview_index + 1) % num_options
            self.play_sound('ui_select')
        elif key_event == pygame.K_RETURN:
            selected_id = self.drone_select_options[self.selected_drone_preview_index]
            if self.drone_system.is_drone_unlocked(selected_id):
                if self.drone_system.set_selected_drone_id(selected_id): # This saves
                    self.play_sound('ui_confirm')
                    self.ui_manager.update_player_life_icon_surface() # Update HUD icon
            else: # Attempt to unlock with cores
                if self.drone_system.attempt_unlock_drone_with_cores(selected_id): # This saves
                    self.play_sound('ui_confirm')
                    # If unlocked, it might also become selected if logic allows, or user selects again
                else:
                    self.play_sound('ui_denied')
        elif key_event == pygame.K_ESCAPE:
            self.play_sound('ui_select')
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def handle_settings_input(self, key_event):
        if not self.settings_items_data: return

        current_setting_item = self.settings_items_data[self.selected_setting_index]
        setting_key = current_setting_item["key"]

        if key_event == pygame.K_UP:
            self.selected_setting_index = (self.selected_setting_index - 1 + len(self.settings_items_data)) % len(self.settings_items_data)
            self.play_sound('ui_select')
        elif key_event == pygame.K_DOWN:
            self.selected_setting_index = (self.selected_setting_index + 1) % len(self.settings_items_data)
            self.play_sound('ui_select')
        elif key_event == pygame.K_RETURN:
            if current_setting_item["type"] == "action" and setting_key == "RESET_SETTINGS_ACTION":
                reset_all_settings_to_default() # Call the function from game_settings
                # Potentially re-apply screen mode if it changed
                if self.screen_flags != (pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0):
                    self.screen_flags = pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0
                    self.screen = pygame.display.set_mode((get_game_setting("WIDTH"), get_game_setting("HEIGHT")), self.screen_flags)
                self.play_sound('ui_confirm')
        elif key_event == pygame.K_LEFT or key_event == pygame.K_RIGHT:
            if current_setting_item["type"] != "action":
                self.play_sound('ui_select', 0.7)
                current_val = get_game_setting(setting_key)
                direction = 1 if key_event == pygame.K_RIGHT else -1

                if current_setting_item["type"] == "numeric":
                    step = current_setting_item["step"]
                    new_val = current_val + step * direction
                    new_val = max(current_setting_item["min"], min(current_setting_item["max"], new_val))
                    # Ensure type consistency (int for int steps, float for float steps)
                    if isinstance(step, float) or isinstance(current_val, float): new_val = float(new_val)
                    else: new_val = int(new_val)
                    set_game_setting(setting_key, new_val)
                elif current_setting_item["type"] == "choice":
                    choices = current_setting_item.get("choices", [])
                    if choices:
                        try:
                            current_choice_idx = choices.index(current_val)
                            new_choice_idx = (current_choice_idx + direction + len(choices)) % len(choices)
                            set_game_setting(setting_key, choices[new_choice_idx])
                            # Special handling for FULLSCREEN_MODE
                            if setting_key == "FULLSCREEN_MODE":
                                self.screen_flags = pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0
                                self.screen = pygame.display.set_mode((get_game_setting("WIDTH"), get_game_setting("HEIGHT")), self.screen_flags)
                        except ValueError: # Current value not in choices, reset to first
                            set_game_setting(setting_key, choices[0])
        elif key_event == pygame.K_ESCAPE:
            self.play_sound('ui_select')
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)


    def handle_pause_menu_input(self, key_event, game_state_when_paused):
        if key_event == pygame.K_l and game_state_when_paused == GAME_STATE_PLAYING:
            self.unpause_and_set_state(GAME_STATE_LEADERBOARD) # Unpause before changing state
        elif key_event == pygame.K_m:
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_event == pygame.K_q: # Quit from pause menu
            self.quit_game()
        elif key_event == pygame.K_ESCAPE and game_state_when_paused.startswith("architect_vault"):
            # Exit vault to main menu from pause
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_event == pygame.K_p: # Unpause by pressing P again
            self.toggle_pause()


    def handle_game_over_input(self, key_event):
        can_submit_score = not get_game_setting("SETTINGS_MODIFIED")
        is_new_high = can_submit_score and leaderboard.is_high_score(self.score, self.level)

        # If it's a new high score, any relevant key press should go to name entry
        if is_new_high and key_event in [pygame.K_r, pygame.K_l, pygame.K_m, pygame.K_q, pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE]:
            self.scene_manager.set_game_state(GAME_STATE_ENTER_NAME)
            return

        # Standard game over options
        if key_event == pygame.K_r:
            self.initialize_game_session() # Start a new game
            self.scene_manager.set_game_state(GAME_STATE_PLAYING)
        elif key_event == pygame.K_l and can_submit_score: # Show leaderboard
            self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
        elif key_event == pygame.K_m: # Back to main menu
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        # Q to quit is handled globally by EventManager for this state

    def submit_leaderboard_name(self, name_cache_from_event_manager):
        """Submits the player's name and score to the leaderboard."""
        if leaderboard.add_score(name_cache_from_event_manager, self.score, self.level):
            self.play_sound('ui_confirm')
        else: # Should not happen if is_high_score was true, but as a fallback
            self.play_sound('ui_denied')
        self.leaderboard_scores = leaderboard.load_scores() # Refresh scores
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD) # Go to leaderboard screen

    def update_player_name_input_display(self, name_cache_from_event_manager):
        """Updates the cache used by UIManager to display the name being entered."""
        self.player_name_input_display_cache = name_cache_from_event_manager

    def try_activate_vault_terminal(self, terminal_idx_pressed):
        """Logic for when player tries to activate a vault terminal."""
        if not (0 <= terminal_idx_pressed < len(self.architect_vault_puzzle_terminals_activated)):
            print(f"GameController: Invalid terminal index {terminal_idx_pressed} attempted.")
            return

        # Find the corresponding terminal sprite (optional, for visual feedback)
        target_terminal_sprite = None
        for t_sprite in self.architect_vault_terminals:
            if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx_pressed:
                target_terminal_sprite = t_sprite
                break

        if not target_terminal_sprite or (hasattr(target_terminal_sprite, 'is_active') and target_terminal_sprite.is_active):
            self.play_sound('ui_denied') # Already active or terminal not found
            return

        # Check if player has the required core fragment
        # This assumes CORE_FRAGMENT_DETAILS keys are ordered or mapped to terminal_ids
        fragment_keys = list(CORE_FRAGMENT_DETAILS.keys())
        required_fragment_id = None
        required_fragment_name = "a specific Core Fragment"
        if terminal_idx_pressed < len(fragment_keys):
            frag_details = CORE_FRAGMENT_DETAILS[fragment_keys[terminal_idx_pressed]]
            if frag_details and "id" in frag_details:
                required_fragment_id = frag_details["id"]
                required_fragment_name = frag_details.get("name", required_fragment_name)

        if required_fragment_id and self.drone_system.has_collected_fragment(required_fragment_id):
            self.architect_vault_puzzle_terminals_activated[terminal_idx_pressed] = True
            if hasattr(target_terminal_sprite, 'is_active'): target_terminal_sprite.is_active = True
            if hasattr(target_terminal_sprite, 'image'): target_terminal_sprite.image.fill(GREEN) # Visual feedback: turn green

            self.play_sound('vault_barrier_disable') # Sound for successful activation
            self.architect_vault_message = f"Terminal {terminal_idx_pressed+1} ({required_fragment_name}) activated!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000

            # Check if all terminals are now active
            if all(self.architect_vault_puzzle_terminals_activated):
                self.architect_vault_message = "All terminals active. Lockdown disengaged. Prepare for Gauntlet!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 4000 # Longer message
                # Transition to the gauntlet after a short delay (handled by SceneManager or here)
                # For now, SceneManager can handle this transition based on state change.
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAUNTLET)
        else:
            self.architect_vault_message = f"Terminal {terminal_idx_pressed+1} requires {required_fragment_name}."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            self.play_sound('ui_denied')


    # --- Game State Control ---
    def toggle_pause(self):
        self.paused = not self.paused
        # Music pausing/unpausing is handled by SceneManager._update_music based on self.paused
        if self.paused:
            print("GameController: Game Paused.")
        else:
            print("GameController: Game Resumed.")
            # Adjust timers if unpausing a timed state to prevent lost time
            current_time = pygame.time.get_ticks()
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state == GAME_STATE_PLAYING:
                self.level_timer_start_ticks = current_time - (get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif current_game_state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction":
                 self.architect_vault_phase_timer_start = current_time - (get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - self.level_time_remaining_ms)
            elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING:
                self.bonus_level_timer_start = current_time - (self.bonus_level_duration_ms - self.level_time_remaining_ms)


    def unpause_and_set_state(self, new_state):
        """Helper to unpause the game and then change its state."""
        if self.paused: self.toggle_pause() # Unpause first
        self.scene_manager.set_game_state(new_state)

    def quit_game(self):
        print("GameController: Quitting game.")
        if self.drone_system: self.drone_system._save_unlocks() # Ensure all progress is saved
        pygame.quit()
        sys.exit()

    # --- Main Game Loop Execution ---
    def _draw_game_world(self):
        """Draws the core game elements like maze, player, enemies, collectibles. Called by run()."""
        current_game_state = self.scene_manager.get_current_state()

        # Set background color based on state
        if current_game_state.startswith("architect_vault"):
            self.screen.fill(get_game_setting("ARCHITECT_VAULT_BG_COLOR"))
            if self.maze: self.maze.draw_architect_vault(self.screen) # Use vault-specific drawing
        else: # Regular playing state or bonus level
            self.screen.fill(BLACK) # Default background for gameplay
            if self.maze: self.maze.draw(self.screen) # Standard maze drawing

        # Draw collectibles (these groups should be populated based on current level/state)
        self.rings.draw(self.screen)
        self.power_ups.draw(self.screen)
        self.core_fragments.draw(self.screen)

        # Draw Architect's Vault specific elements (like terminals if in puzzle phase)
        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_terminals.draw(self.screen)
        # if self.architect_vault_hazards: self.architect_vault_hazards.draw(self.screen)

        # Draw enemies and player
        # Enemies group contains regular enemies or prototype drones depending on state
        if self.enemies: self.enemies.draw(self.screen)
        if self.player: self.player.draw(self.screen) # Player's draw method handles its own projectiles

    def run(self):
        """Main game loop."""
        # Ensure screen mode is correctly set at start or if changed in settings
        current_fullscreen_setting = get_game_setting("FULLSCREEN_MODE")
        if self.screen_flags != (pygame.FULLSCREEN if current_fullscreen_setting else 0):
            self.screen_flags = pygame.FULLSCREEN if current_fullscreen_setting else 0
            self.screen = pygame.display.set_mode((get_game_setting("WIDTH"), get_game_setting("HEIGHT")), self.screen_flags)

        while True:
            self.event_manager.process_events() # Handle inputs and system events
            self.update() # Update game logic and state

            # --- Main Drawing Logic ---
            # 1. Draw Game World (maze, player, enemies, collectibles) if in a gameplay state
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
               current_game_state.startswith("architect_vault"):
                self._draw_game_world() # Draws the actual game scene

            # 2. Draw UI (Menus, HUD, Overlays) on top of everything else
            # UIManager's draw_current_scene_ui handles filling screen for full-screen menus
            self.ui_manager.draw_current_scene_ui()

            pygame.display.flip() # Update the full display
            self.clock.tick(get_game_setting("FPS")) # Control game speed