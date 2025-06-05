# hyperdrone_core/game_loop.py
import sys
import os
import random
import math
import json
import logging # Import logging

import pygame

# Core game modules
from .scene_manager import SceneManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from . import leaderboard

# Import NEW Controllers
from .combat_controller import CombatController
from .puzzle_controller import PuzzleController
from .ui_flow_controller import UIFlowController

# UI and Entity imports
from ui import UIManager
from entities import (
    PlayerDrone,
    Ring as CollectibleRing,
    WeaponUpgradeItem,
    ShieldItem,
    SpeedBoostItem,
    CoreFragmentItem,
    VaultLogItem,
    GlyphTabletItem,
    AncientAlienTerminal,
    ArchitectEchoItem,
    CoreReactor,
    Turret,
    LightningZap,
    Missile,
    Particle,
    MazeGuardian,
    SentinelDrone,
    EscapeZone,
    Maze,
    MazeChapter2,
    Bullet
)

# Drone system and configurations
from drone_management import DroneSystem, DRONE_DATA

# Game settings and constants
import game_settings as gs
from game_settings import (
    BLACK, WHITE, GOLD, CYAN, RED, YELLOW, GREEN, ORANGE, DARK_RED, GREY, PURPLE,
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_CODEX,
    GAME_STATE_DRONE_SELECT, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_BONUS_LEVEL_START,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_GAME_INTRO_SCROLL, GAME_STATE_MAZE_DEFENSE,
    ARCHITECT_VAULT_BG_COLOR,
    TILE_SIZE, POWERUP_TYPES, WEAPON_MODES_SEQUENCE, WEAPON_MODE_NAMES,
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
    ARCHITECT_VAULT_DRONES_PER_WAVE, ARCHITECT_VAULT_GAUNTLET_WAVES,
    DEFAULT_SETTINGS, get_game_setting, set_game_setting, reset_all_settings_to_default,
    WIDTH, BOTTOM_PANEL_HEIGHT, GAME_PLAY_AREA_HEIGHT, HEIGHT, FPS
)

logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


if not hasattr(gs, 'GAME_STATE_MAZE_DEFENSE'):
    GAME_STATE_MAZE_DEFENSE = "maze_defense_mode"
    gs.GAME_STATE_MAZE_DEFENSE = GAME_STATE_MAZE_DEFENSE
else:
    GAME_STATE_MAZE_DEFENSE = gs.GAME_STATE_MAZE_DEFENSE

class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen_flags = pygame.FULLSCREEN if gs.get_game_setting("FULLSCREEN_MODE") else 0
        self.screen = pygame.display.set_mode(
            (gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")),
            self.screen_flags
        )
        pygame.display.set_caption("HYPERDRONE")
        self.clock = pygame.time.Clock()

        self.drone_system = DroneSystem()

        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf")
        self.font_path_neuropol = os.path.join("assets", "fonts", "neuropol.otf")
        self.fonts = {}
        self._initialize_fonts()

        self.scene_manager = SceneManager(self)
        self.player_actions = PlayerActions(self)

        self.combat_controller = CombatController(self)
        self.puzzle_controller = PuzzleController(self)
        self.ui_flow_controller = UIFlowController(self)

        self.ui_manager = UIManager(self.screen, self.fonts, self, self.scene_manager, self.drone_system)
        self.event_manager = EventManager(self, self.scene_manager, self.combat_controller, self.puzzle_controller, self.ui_flow_controller)

        self.ui_flow_controller.set_dependencies(self.scene_manager, self.ui_manager, self.drone_system)

        self.player = None
        self.maze = None

        self.collectible_rings_group = pygame.sprite.Group()
        self.power_ups_group = pygame.sprite.Group()
        self.core_fragments_group = pygame.sprite.Group()
        self.vault_logs_group = pygame.sprite.Group()
        self.glyph_tablets_group = pygame.sprite.Group()
        self.architect_echoes_group = pygame.sprite.Group()
        self.alien_terminals_group = pygame.sprite.Group()
        self.architect_vault_puzzle_terminals_group = pygame.sprite.Group()
        self.explosion_particles_group = pygame.sprite.Group()
        self.escape_zone_group = pygame.sprite.GroupSingle()
        self.reactor_group = pygame.sprite.GroupSingle()
        self.turrets_group = pygame.sprite.Group()

        self.score = 0
        self.level = 1
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        self.paused = False
        self.is_build_phase = False

        self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")

        self.bonus_level_timer_start = 0
        self.bonus_level_duration_ms = gs.get_game_setting("BONUS_LEVEL_DURATION_MS")
        self.bonus_level_start_display_end_time = 0

        self.architect_vault_current_phase = None
        self.architect_vault_phase_timer_start = 0
        self.architect_vault_message = ""
        self.architect_vault_message_timer = 0
        self.architect_vault_failure_reason = ""

        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.total_rings_per_level = 5
        self.animating_rings_to_hud = []
        self.ring_ui_target_pos = (WIDTH - 50, HEIGHT - BOTTOM_PANEL_HEIGHT + 50)

        self.hud_displayed_fragments = set()
        self.animating_fragments_to_hud = []
        self.fragment_ui_target_positions = {}

        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False

        self.story_message = ""
        self.story_message_active = False
        self.STORY_MESSAGE_DURATION = 5000
        self.triggered_story_beats = set()

        self.current_intro_image_surface = None
        self.intro_screen_text_surfaces_current = []
        self.intro_font_key = "codex_category_font"

        self.drone_main_display_cache = {}
        self._load_drone_main_display_images()

        self.sounds = {}
        self.load_sfx()

        if self.drone_system:
            self.drone_system.unlock_lore_entry_by_id("architect_legacy_intro")
            self.drone_system.check_and_unlock_lore_entries(event_trigger="game_start")

        if self.ui_flow_controller:
            self.ui_flow_controller.settings_items_data = self._get_settings_menu_items_data_structure()
            self.ui_flow_controller.intro_screens_data = self._load_intro_data_from_json_internal()

        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        logger.info("GameController initialized successfully.")

    def _initialize_fonts(self):
        font_configs = {
            "ui_text": (self.font_path_neuropol, 28), "ui_values": (self.font_path_neuropol, 30),
            "ui_emoji_general": (self.font_path_emoji, 32), "ui_emoji_small": (self.font_path_emoji, 20),
            "small_text": (self.font_path_neuropol, 24), "medium_text": (self.font_path_neuropol, 48),
            "large_text": (self.font_path_neuropol, 74), "input_text": (self.font_path_neuropol, 50),
            "menu_text": (self.font_path_neuropol, 60), "title_text": (self.font_path_neuropol, 90),
            "drone_name_grid": (self.font_path_neuropol, 36), "drone_desc_grid": (self.font_path_neuropol, 22),
            "drone_unlock_grid": (self.font_path_neuropol, 20), "drone_name_cycle": (self.font_path_neuropol, 42),
            "drone_stats_label_cycle": (self.font_path_neuropol, 26), "drone_stats_value_cycle": (self.font_path_neuropol, 28),
            "drone_desc_cycle": (self.font_path_neuropol, 22), "drone_unlock_cycle": (self.font_path_neuropol, 20),
            "vault_message": (self.font_path_neuropol, 36), "vault_timer": (self.font_path_neuropol, 48),
            "leaderboard_header": (self.font_path_neuropol, 32), "leaderboard_entry": (self.font_path_neuropol, 28),
            "arrow_font_key": (self.font_path_emoji, 60), "story_message_font": (self.font_path_neuropol, 26),
            "codex_title_font": (self.font_path_neuropol, 60), "codex_category_font": (self.font_path_neuropol, 38),
            "codex_entry_font": (self.font_path_neuropol, 30), "codex_content_font": (self.font_path_neuropol, 24)
        }
        for name, (path, size) in font_configs.items():
            try:
                self.fonts[name] = pygame.font.Font(path, size)
            except pygame.error as e:
                logger.error(f"GameController Font Error: Could not load font '{name}' from '{path}'. Using default. Error: {e}")
                self.fonts[name] = pygame.font.Font(None, size)

    def _get_settings_menu_items_data_structure(self):
        """
        Defines the structure and content of the settings menu items.
        This is where all configurable game settings are listed for the UI.
        """
        return [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice",
             "choices":WEAPON_MODES_SEQUENCE, "get_display":lambda val:WEAPON_MODE_NAMES.get(val,"Unknown")},
            {"label":"Missile Damage","key":"MISSILE_DAMAGE","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","type":"numeric","min":0.5,"max":5,"step":0.5},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","type":"numeric","min":25,"max":300,"step":25},
            {"label":"Level Timer (sec)","key":"LEVEL_TIMER_DURATION","type":"numeric","min":60000,"max":300000,"step":15000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","type":"numeric","min":5000,"max":60000,"step":5000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Speed Boost Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","type":"numeric","min":3000,"max":30000,"step":2000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label": "Invincibility", "key": "PLAYER_INVINCIBILITY", "type": "choice",
             "choices": [False, True], "get_display": lambda val: "ON" if val else "OFF",
             "note": "Player does not take damage."},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ]

    def _load_intro_data_from_json_internal(self):
        # This method loads intro data (omitted for brevity but unchanged from your original)
        fallback_data = [
            {"text": "The Architect — creator of the Vault\nand all drone intelligence — has vanished.\n\nNo warning. No trace. Only silence.", "image_path": "assets/images/lore/scene1.png"},
            # ... more scenes ...
        ]
        # ... loading logic ...
        intro_file_path = os.path.join("data", "intro.json")
        if os.path.exists(intro_file_path):
            try:
                with open(intro_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, list) and all(isinstance(item, dict) and "text" in item and "image_path" in item for item in loaded_data):
                        logger.info(f"Successfully loaded {len(loaded_data)} intro screens from intro.json.")
                        return loaded_data
                    else:
                        logger.warning("Intro.json has incorrect format. Using fallback intro data.")
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Error loading or parsing intro.json: {e}. Using fallback intro data.")
        else:
            logger.info("intro.json not found. Using fallback intro data.")
        return fallback_data


    def _create_fallback_image_surface(self, size=(200,200), text="?", color=(80,80,80), text_color=WHITE, font_key="large_text"):
        # This method creates fallback images (omitted for brevity but unchanged from your original)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        if text:
            font_to_use = self.fonts.get(font_key, pygame.font.Font(None, size[1] // 3 if size[1] // 3 > 0 else 10))
            text_s = font_to_use.render(str(text), True, text_color)
            surface.blit(text_s, text_s.get_rect(center=(size[0]//2, size[1]//2)))
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 1)
        return surface

    def _load_drone_main_display_images(self):
        self.drone_main_display_cache = {}
        target_size = (200, 200) # Example size for drone select screen
        for drone_id, config in DRONE_DATA.items():
            sprite_path = config.get("sprite_path")
            if sprite_path and os.path.exists(sprite_path):
                try:
                    raw_image = pygame.image.load(sprite_path).convert_alpha()
                    # Scale to fit within target_size while maintaining aspect ratio
                    original_w, original_h = raw_image.get_size()
                    aspect = original_w / original_h if original_h > 0 else 1
                    
                    scaled_w, scaled_h = target_size
                    if aspect > 1: # Wider than tall
                        scaled_h = int(target_size[0] / aspect)
                    else: # Taller than wide or square
                        scaled_w = int(target_size[1] * aspect)
                    
                    scaled_w = max(1, scaled_w) # Ensure positive dimensions
                    scaled_h = max(1, scaled_h)

                    self.drone_main_display_cache[drone_id] = pygame.transform.smoothscale(raw_image, (scaled_w, scaled_h))
                except pygame.error as e:
                    logger.error(f"GameController: Error loading drone display image for '{drone_id}': {e}")
                    self.drone_main_display_cache[drone_id] = self._create_fallback_image_surface(target_size, drone_id[:1], font_key="medium_text")
            else:
                if sprite_path: logger.warning(f"GameController: Drone display sprite_path not found for '{drone_id}': {sprite_path}")
                self.drone_main_display_cache[drone_id] = self._create_fallback_image_surface(target_size, drone_id[:1], font_key="medium_text")
       
    def load_sfx(self):
        # This method loads sound effects (omitted for brevity but unchanged from your original)
        sound_files = {
            'collect_ring': "collect_ring.wav", 'weapon_upgrade_collect': "weapon_upgrade_collect.wav",
            'collect_fragment': "collect_fragment.wav", 'collect_log': "collect_log.wav",
            'shoot': "shoot.wav", 'enemy_shoot': "enemy_shoot.wav", 'crash': "crash.wav",
            'timer_out': "timer_out.wav", 'level_up': "level_up.wav", 'boss_intro': "boss_intro.wav",
            'boss_hit': "boss_hit.wav", 'boss_death': "boss_death.wav",
            'cloak_activate': "cloak_activate.wav", 'missile_launch': "missile_launch.wav",
            'ui_select': "ui_select.wav", 'ui_confirm': "ui_confirm.wav", 'ui_denied': "ui_denied.wav",
            'lore_unlock': "lore_unlock.wav", 'vault_alarm': "vault_alarm.wav",
            'prototype_drone_explode': "prototype_drone_explode.wav",
            'vault_barrier_disable': "vault_barrier_disable.wav",
            'turret_place_placeholder': "turret_place.wav", 
            'reactor_hit_placeholder': "reactor_hit.wav",   
            'reactor_destroyed_placeholder': "reactor_destroyed.wav", 
            'turret_shoot_placeholder': "turret_shoot.wav" 
        }
        for name, filename in sound_files.items():
            path = os.path.join("assets", "sounds", filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    logger.error(f"GameController: Error loading sound '{name}' from '{path}': {e}")
                    self.sounds[name] = None
            else:
                logger.warning(f"GameController: Sound file not found for '{name}': {path}")
                self.sounds[name] = None
       
    def play_sound(self, name, volume_multiplier=0.7):
        if name in self.sounds and self.sounds[name]:
            try:
                base_sfx_volume = gs.get_game_setting("SFX_VOLUME_MULTIPLIER", 0.7)
                final_volume = base_sfx_volume * volume_multiplier
                self.sounds[name].set_volume(final_volume)
                self.sounds[name].play()
            except pygame.error as e:
                 logger.error(f"GameController: Error playing sound '{name}': {e}")
        else:
            logger.debug(f"GameController: Sound '{name}' not found or not loaded, play attempt skipped.")

    def set_story_message(self, message, duration=None): 
        self.story_message = message
        self.story_message_active = True
        logger.info(f"Story message set: {message}")

    def trigger_story_beat(self, beat_id):
        if beat_id not in self.triggered_story_beats:
            if self.drone_system.has_unlocked_lore(beat_id):
                lore_entry = self.drone_system.get_lore_entry_details(beat_id)
                if lore_entry:
                    self.set_story_message(lore_entry.get("content", f"Event: {lore_entry.get('title', beat_id)}"))
                    self.triggered_story_beats.add(beat_id)
                    self.play_sound('lore_unlock', 0.6) 
                    logger.info(f"Story beat '{beat_id}' triggered.")
                    return True
            else:
                logger.debug(f"GameController: Story beat '{beat_id}' lore not found or not unlocked.")
        return False

    def _create_explosion(self, x, y, num_particles=20, specific_sound='prototype_drone_explode'):
        colors = [ORANGE, YELLOW, RED, DARK_RED, GREY] 
        for _ in range(num_particles):
            particle = Particle(x, y, colors, 1, 4, 2, 5, 0.05, 0.1, random.randint(20,40))
            self.explosion_particles_group.add(particle)
        if specific_sound: 
            self.play_sound(specific_sound) 

    def handle_scene_transition(self, new_state, old_state, **kwargs): 
        logger.info(f"GameController: Handling scene transition from '{old_state}' to '{new_state}' with kwargs: {kwargs}")
        pygame.mouse.set_visible(False) 

        if new_state == GAME_STATE_MAIN_MENU:
            self.ui_flow_controller.initialize_main_menu()
            pygame.mouse.set_visible(True) 
        elif new_state == GAME_STATE_DRONE_SELECT:
            self.ui_flow_controller.initialize_drone_select()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_SETTINGS:
            self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure())
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_LEADERBOARD:
            self.ui_flow_controller.initialize_leaderboard()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_CODEX:
            self.ui_flow_controller.initialize_codex()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_ENTER_NAME:
            self.ui_flow_controller.initialize_enter_name()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_GAME_OVER:
            self.handle_game_over_scene_entry()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_GAME_INTRO_SCROLL:
            self.ui_flow_controller.initialize_game_intro(self._load_intro_data_from_json_internal())
            self._prepare_current_intro_screen_surfaces() 
        elif new_state == GAME_STATE_PLAYING:
            logger.debug(f"GameController: Transitioning to PLAYING from {old_state}.")
            self.initialize_specific_game_mode("standard_play", old_state=old_state, **kwargs) 
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_BONUS_LEVEL_START:
            self.initialize_specific_game_mode("bonus_level_start", old_state=old_state) 
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            self.initialize_specific_game_mode("architect_vault_entry", old_state=old_state, phase_to_start="intro") 
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: 
            self.initialize_architect_vault_session_phases("entry_puzzle")
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET: 
            self.initialize_architect_vault_session_phases("gauntlet_intro")
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT: 
             self.initialize_architect_vault_session_phases("architect_vault_boss_fight")
             pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION: 
            self.initialize_architect_vault_session_phases("extraction")
            pygame.mouse.set_visible(False)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS:
            self.handle_architect_vault_success_scene()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            self.handle_architect_vault_failure_scene()
            pygame.mouse.set_visible(True)
        elif new_state == GAME_STATE_RING_PUZZLE:
            triggering_terminal = kwargs.get('triggering_terminal')
            if triggering_terminal and self.puzzle_controller:
                self.puzzle_controller.start_ring_puzzle(triggering_terminal) 
            elif not self.puzzle_controller.ring_puzzle_active_flag: 
                logger.warning("Transition to RING_PUZZLE state without active puzzle from terminal.")
        elif new_state == GAME_STATE_MAZE_DEFENSE:
            logger.debug(f"GameController: Transitioning to MAZE_DEFENSE from {old_state}.")
            self.initialize_specific_game_mode("maze_defense", old_state=old_state) 
            pygame.mouse.set_visible(True) 

    def _prepare_current_intro_screen_surfaces(self):
        ui_flow_ctrl = self.ui_flow_controller
        if not ui_flow_ctrl.intro_screens_data or \
           ui_flow_ctrl.current_intro_screen_index >= len(ui_flow_ctrl.intro_screens_data):
            ui_flow_ctrl.intro_sequence_finished = True 
            self.current_intro_image_surface = None
            self.intro_screen_text_surfaces_current = []
            return

        if ui_flow_ctrl.intro_sequence_finished: 
            self.current_intro_image_surface = None
            self.intro_screen_text_surfaces_current = []
            return
            
        screen_data = ui_flow_ctrl.intro_screens_data[ui_flow_ctrl.current_intro_screen_index]
        text_content = screen_data["text"]
        image_path = screen_data["image_path"]
        
        if image_path not in self.ui_manager.codex_image_cache: 
            if os.path.exists(image_path):
                try: 
                    self.ui_manager.codex_image_cache[image_path] = pygame.image.load(image_path).convert_alpha()
                except pygame.error as e:
                    logger.error(f"GameController: Error loading intro image '{image_path}': {e}")
                    self.ui_manager.codex_image_cache[image_path] = None 
            else: 
                logger.warning(f"GameController: Intro image path not found: '{image_path}'")
                self.ui_manager.codex_image_cache[image_path] = None
        self.current_intro_image_surface = self.ui_manager.codex_image_cache.get(image_path)

        self.intro_screen_text_surfaces_current = []
        font = self.fonts.get(self.intro_font_key, pygame.font.Font(None, 36)) 
        raw_lines = text_content.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip(): 
                self.intro_screen_text_surfaces_current.append(font.render(" ", True, GOLD)) 
            else: 
                self.intro_screen_text_surfaces_current.append(font.render(raw_line, True, GOLD))

    def initialize_specific_game_mode(self, mode_type="standard_play", old_state=None, **kwargs): 
        logger.info(f"GameController: Initializing game mode: {mode_type} from old_state: {old_state} with kwargs: {kwargs}. Current state before this call: {self.scene_manager.get_current_state()}")
        self.paused = False
        self.collectible_rings_group.empty()
        self.power_ups_group.empty()
        self.core_fragments_group.empty()
        self.vault_logs_group.empty()
        self.glyph_tablets_group.empty()
        self.architect_echoes_group.empty()
        self.alien_terminals_group.empty()
        self.architect_vault_puzzle_terminals_group.empty()
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
        self.reactor_group.empty() 
        self.turrets_group.empty()
        if self.combat_controller: self.combat_controller.reset_combat_state()
        if self.puzzle_controller: self.puzzle_controller.reset_puzzles_state()
        if self.ui_flow_controller: self.ui_flow_controller.reset_ui_flow_states()

        self.player = None 
        self.maze = None   


        if mode_type == "architect_vault_entry":
            self.is_build_phase = False
            if self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            self.level = 1 
            
            self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault")
            player_spawn_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            if player_spawn_pos:
                self._create_or_reset_player(player_spawn_pos, is_vault=True, preserve_weapon_on_reset=True)
            else:
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
                return
            
            self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group)
            
            phase_to_start = kwargs.get('phase_to_start', 'intro') 
            self.initialize_architect_vault_session_phases(phase_to_start)


        elif mode_type == "maze_defense":
            self.level = 1 
            self.score = 0
            self.lives = get_game_setting("PLAYER_LIVES") 
            if self.drone_system:
                self.drone_system.reset_collected_fragments_in_storage() 
                self.drone_system.reset_architect_vault_status()

            self.maze = MazeChapter2(game_area_x_offset=0, maze_type="chapter2_tilemap") 
            self.player = None 
            
            reactor_spawn_pos = self.maze.get_core_reactor_spawn_position_abs()
            core_reactor_entity = None
            if reactor_spawn_pos:
                reactor_health = gs.get_game_setting("DEFENSE_REACTOR_HEALTH", 1000)
                core_reactor_entity = CoreReactor(reactor_spawn_pos[0], reactor_spawn_pos[1], health=reactor_health)
                self.reactor_group.add(core_reactor_entity)
            else:
                logger.critical("GameController ERROR: Could not get reactor spawn position for Maze Defense. Aborting mode.")
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) 
                return

            self.combat_controller.set_active_entities(
                player=None,
                maze=self.maze,
                core_reactor=core_reactor_entity,
                turrets_group=self.turrets_group, 
                explosion_particles_group=self.explosion_particles_group
            )
            self.combat_controller.wave_manager.start_first_build_phase()
            self.is_build_phase = True 
            if self.ui_manager.build_menu:
                self.ui_manager.build_menu.activate()
            
        elif mode_type == "bonus_level_start":
            self.is_build_phase = False
            if self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            self.maze = Maze(game_area_x_offset=0, maze_type="bonus") 
            player_spawn_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            if player_spawn_pos:
                self._create_or_reset_player(player_spawn_pos, is_vault=False, preserve_weapon_on_reset=True)

            else:
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
                return
            
            self._place_collectibles_for_bonus_level()
            self.bonus_level_timer_start = pygame.time.get_ticks()
            self.level_time_remaining_ms = self.bonus_level_duration_ms 
            self.bonus_level_start_display_end_time = pygame.time.get_ticks() + 3000 
            self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager)

        else: # Default to "standard_play"
            self.is_build_phase = False
            if self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            
            self.level = kwargs.get('start_level', 1 if old_state == GAME_STATE_GAME_INTRO_SCROLL else self.level)
            if old_state == GAME_STATE_GAME_INTRO_SCROLL: 
                 self.score = 0
                 self.lives = get_game_setting("PLAYER_LIVES")
                 self.triggered_story_beats.clear()
                 if self.drone_system: 
                     self.drone_system.reset_collected_fragments_in_storage()
                     self.drone_system.reset_architect_vault_status()
            
            self.collected_rings_count = 0
            self.displayed_collected_rings_count = 0
            self.total_rings_per_level = 5
            self.all_enemies_killed_this_level = False
            self.animating_rings_to_hud.clear()
            self.animating_fragments_to_hud.clear()
            self.hud_displayed_fragments.clear()

            self.maze = Maze(game_area_x_offset=0, maze_type="standard")

            player_spawn_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            if player_spawn_pos:
                self._create_or_reset_player(player_spawn_pos, is_vault=False, preserve_weapon_on_reset=(old_state == GAME_STATE_PLAYING)) 

            else: 
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
                return

            self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, alien_terminals_group=self.alien_terminals_group)
            self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
            self._place_collectibles_for_level(initial_setup=True)
            self._reset_level_timer_internal()
            self.level_cleared_pending_animation = False
            self.level_clear_fragment_spawned_this_level = False

        logger.info(f"GameController: Finished initialize_specific_game_mode for {mode_type}. Player: {type(self.player)}, Maze: {type(self.maze)}")


    def _create_or_reset_player(self, position, is_vault=False, preserve_weapon_on_reset=False):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=is_vault)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_sprite_path = drone_config.get("ingame_sprite_path") 


        if self.player is None: 
            self.player = PlayerDrone(position[0], position[1], drone_id=selected_drone_id, 
                                      drone_stats=effective_stats, drone_sprite_path=player_sprite_path, 
                                      crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        else: 
            self.player.reset(position[0], position[1], drone_id=selected_drone_id, 
                              drone_stats=effective_stats, drone_sprite_path=player_sprite_path, 
                              preserve_weapon=preserve_weapon_on_reset)
        

        if self.ui_manager: 
            self.ui_manager.update_player_life_icon_surface() 
        if self.combat_controller: 
            self.combat_controller.player = self.player 
        if self.puzzle_controller: 
            self.puzzle_controller.player = self.player 

    def initialize_architect_vault_session_phases(self, phase):
        self.architect_vault_current_phase = phase
        self.architect_vault_phase_timer_start = pygame.time.get_ticks() 
        logger.info(f"Architect Vault Phase Initialized: {phase}")

        if phase == "intro":
            self.architect_vault_message = "The Architect's Vault... Entry protocol initiated."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000 
            self.drone_system.check_and_unlock_lore_entries(event_trigger="architect_vault_entered")
        elif phase == "entry_puzzle":
            self.puzzle_controller.architect_vault_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
            self._spawn_architect_vault_puzzle_terminals() 
            self.architect_vault_message = "Activate terminals with collected Core Fragments."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        elif phase == "gauntlet_intro":
            self.combat_controller.architect_vault_gauntlet_current_wave = 0 
            self.combat_controller.enemy_manager.reset_all() 
            self.architect_vault_message = "Security systems online. Prepare for hostiles."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
        elif phase.startswith("gauntlet_wave_"): 
            wave_num_str = phase.split("_")[-1]
            try: 
                wave_num = int(wave_num_str)
            except ValueError: 
                wave_num = 1 
            self.combat_controller.architect_vault_gauntlet_current_wave = wave_num
            num_drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[wave_num -1] if wave_num-1 < len(ARCHITECT_VAULT_DRONES_PER_WAVE) else ARCHITECT_VAULT_DRONES_PER_WAVE[-1]
            self.combat_controller.enemy_manager.spawn_prototype_drones(num_drones_this_wave) 
            self.architect_vault_message = f"Wave {wave_num} initiated!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif phase == "architect_vault_boss_fight":
            self.architect_vault_message = "MAZE GUARDIAN DETECTED. PREPARE FOR ENGAGEMENT!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            self.combat_controller.spawn_maze_guardian() 
        elif phase == "extraction":
            self.play_sound('vault_alarm', 0.7) 
            self.architect_vault_message = "SELF-DESTRUCT SEQUENCE ACTIVATED! REACH THE EXTRACTION POINT!"
            self._spawn_escape_zone() 
            self.level_time_remaining_ms = gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") 
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        
        self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
        self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group)

    def handle_architect_vault_success_scene(self):
        self.ui_flow_controller.initialize_architect_vault_result_screen(success=True)
        if self.drone_system:
            self.drone_system.mark_architect_vault_completed(True) 
            self.score += 2500 
            self.drone_system.add_player_cores(500) 
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB05")
            self.trigger_story_beat("story_beat_SB05") 
        if self.escape_zone_group.sprite: 
            self.escape_zone_group.sprite.kill() 
        
        self.set_story_message("Architect's Vault conquered! Entering defensive perimeter...", 5000)


    def handle_architect_vault_failure_scene(self):
        self.ui_flow_controller.initialize_architect_vault_result_screen(success=False, failure_reason=self.architect_vault_failure_reason)
        if self.drone_system:
            self.drone_system.mark_architect_vault_completed(False) 
        if self.escape_zone_group.sprite: 
            self.escape_zone_group.sprite.kill()

    def handle_game_over_scene_entry(self):
        if self.escape_zone_group.sprite: 
            self.escape_zone_group.sprite.kill() 
        if self.drone_system:
            self.drone_system.set_player_level(self.level) 
            self.drone_system._save_unlocks() 

    def handle_maze_defense_victory(self):
        logger.info("GameController: Maze Defense Victory achieved!")
        self.set_story_message("CORE REACTOR SECURED! ALL WAVES DEFEATED!", 10000) 
        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) 

    def get_enemy_spawn_points_for_defense(self):
        if self.maze and hasattr(self.maze, 'get_enemy_spawn_points_abs'):
            return self.maze.get_enemy_spawn_points_abs()
        logger.warning("GameController WARNING: get_enemy_spawn_points_for_defense called but maze is invalid or missing method.")
        return [] 

    def update(self, delta_time_ms):
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()

        self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_game_state)

        if current_game_state == GAME_STATE_GAME_INTRO_SCROLL and \
           not self.ui_flow_controller.intro_sequence_finished:
            self._prepare_current_intro_screen_surfaces()

        if current_game_state == GAME_STATE_RING_PUZZLE:
            self.puzzle_controller.update(current_time_ms, current_game_state)
        elif current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_standard_playing_state(current_time_ms, delta_time_ms)
        elif current_game_state == GAME_STATE_MAZE_DEFENSE and not self.paused:
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.player and self.player.alive: 
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
            if self.ui_manager.build_menu and self.ui_manager.build_menu.is_active:
                self.ui_manager.build_menu.update(pygame.mouse.get_pos(), current_game_state)

        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused:
            self._update_bonus_level_state(current_time_ms)
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state_machine(current_time_ms, delta_time_ms)
            if self.player and self.player.alive: 
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
        
        self._update_hud_animations()
        
        if self.scene_manager: 
            self.scene_manager.update()

    def _update_standard_playing_state(self, current_time_ms, delta_time_ms):

        if not self.level_cleared_pending_animation: 
            elapsed_time_current_level_ms = current_time_ms - self.level_timer_start_ticks
            self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION") - elapsed_time_current_level_ms
            if self.level_time_remaining_ms <= 0: 
                self.play_sound('timer_out')
                self._handle_player_death_or_life_loss("Time Ran Out!")
                return 
            
            if self.player.alive:
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
            else: 
                self._handle_player_death_or_life_loss("Drone Destroyed!")
                return 
            
            self.combat_controller.update(current_time_ms, delta_time_ms) 

            self.collectible_rings_group.update()
            self.core_fragments_group.update()
            self.vault_logs_group.update()
            self.glyph_tablets_group.update()
            self.architect_echoes_group.update()
            self.alien_terminals_group.update() 

            self._handle_collectible_collisions() 
            
            if not self.level_clear_fragment_spawned_this_level and \
               self.collected_rings_count >= self.total_rings_per_level and \
               self.all_enemies_killed_this_level: 
                if self._attempt_level_clear_fragment_spawn(): 
                    self.level_clear_fragment_spawned_this_level = True
        
        if self.level_cleared_pending_animation and not self.animating_rings_to_hud and not self.animating_fragments_to_hud:
            self._prepare_for_next_level()
            self.level_cleared_pending_animation = False 

    def _update_architect_vault_state_machine(self, current_time_ms, delta_time_ms):
        if not self.player or not self.maze: 
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
            return

        if not self.player.alive: 
            self.architect_vault_failure_reason = "Drone critically damaged."
            if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
            return
        
        current_phase = self.architect_vault_current_phase
        
        if current_phase == "intro":
            if current_time_ms > self.architect_vault_message_timer: 
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        elif current_phase == "entry_puzzle":
            if all(self.puzzle_controller.architect_vault_terminals_activated):
                 if current_time_ms > self.architect_vault_message_timer: 
                    self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        elif current_phase == "gauntlet_intro":
            if current_time_ms > self.architect_vault_message_timer: 
                self.initialize_architect_vault_session_phases(f"gauntlet_wave_1") 
        elif current_phase and current_phase.startswith("gauntlet_wave"):
            self.combat_controller.update(current_time_ms, delta_time_ms) 
            if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
                current_wave_num = self.combat_controller.architect_vault_gauntlet_current_wave
                if current_wave_num >= ARCHITECT_VAULT_GAUNTLET_WAVES: 
                    self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT)
                else: 
                    next_wave_num = current_wave_num + 1
                    self.initialize_architect_vault_session_phases(f"gauntlet_wave_{next_wave_num}")
        elif current_phase == "architect_vault_boss_fight":
            self.combat_controller.update(current_time_ms, delta_time_ms) 
            if not self.combat_controller.boss_active and self.combat_controller.maze_guardian_defeat_processed:
                if current_time_ms > self.architect_vault_message_timer: 
                    self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif current_phase == "extraction":
            self.combat_controller.update(current_time_ms, delta_time_ms) 
            time_elapsed_extraction = current_time_ms - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - time_elapsed_extraction)
            
            if self.escape_zone_group.sprite and self.player.rect.colliderect(self.escape_zone_group.sprite.rect):
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS)
                return
            
            if self.level_time_remaining_ms <= 0:
                self.architect_vault_failure_reason = "Extraction Failed: Time Expired."
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
                return
            
            if random.random() < 0.008 : 
                 if self.combat_controller.enemy_manager.get_active_enemies_count() < 3: 
                     self.combat_controller.enemy_manager.spawn_prototype_drones(1)

    def _update_bonus_level_state(self, current_time_ms):
        if not self.player or not self.player.alive: 
            self._end_bonus_level(completed=False)
            return

        self.player.update(current_time_ms, self.maze, None, self.maze.game_area_x_offset if self.maze else 0)
        
        elapsed_bonus_time = current_time_ms - self.bonus_level_timer_start
        self.level_time_remaining_ms = max(0, self.bonus_level_duration_ms - elapsed_bonus_time)
        if self.level_time_remaining_ms <= 0: 
            self._end_bonus_level(completed=True)
            return
        
        self.explosion_particles_group.update() 

    def _update_hud_animations(self):
        for ring_anim in list(self.animating_rings_to_hud): 
            dx = ring_anim['target_pos'][0] - ring_anim['pos'][0]
            dy = ring_anim['target_pos'][1] - ring_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < ring_anim['speed']: 
                self.animating_rings_to_hud.remove(ring_anim)
                self.displayed_collected_rings_count += 1
                self.displayed_collected_rings_count = min(self.displayed_collected_rings_count, self.collected_rings_count)
            else: 
                ring_anim['pos'][0] += (dx / dist) * ring_anim['speed']
                ring_anim['pos'][1] += (dy / dist) * ring_anim['speed']
        
        for frag_anim in list(self.animating_fragments_to_hud): 
            dx = frag_anim['target_pos'][0] - frag_anim['pos'][0]
            dy = frag_anim['target_pos'][1] - frag_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < frag_anim['speed']: 
                self.animating_fragments_to_hud.remove(frag_anim)
                if 'id' in frag_anim: 
                    self.hud_displayed_fragments.add(frag_anim['id']) 
            else: 
                frag_anim['pos'][0] += (dx / dist) * frag_anim['speed']
                frag_anim['pos'][1] += (dy / dist) * frag_anim['speed']

    def _handle_collectible_collisions(self):
        if not self.player or not self.player.alive: return

        collided_rings = pygame.sprite.spritecollide(self.player, self.collectible_rings_group, True, pygame.sprite.collide_rect_ratio(0.7))
        for ring_sprite in collided_rings:
            self.score += 10
            self.play_sound('collect_ring')
            self.collected_rings_count += 1
            self.drone_system.add_player_cores(5) 
            
            anim_surf = None
            if hasattr(ring_sprite, 'image') and self.ui_manager.ui_assets.get("ring_icon"):
                try: 
                    anim_surf = pygame.transform.smoothscale(self.ui_manager.ui_assets["ring_icon"], (15,15))
                except Exception as e:
                    logger.error(f"GameController: Error scaling ring icon for animation: {e}")
            if anim_surf: 
                self.animating_rings_to_hud.append({
                    'pos': list(ring_sprite.rect.center), 
                    'target_pos': self.ring_ui_target_pos, 
                    'speed': 15, 
                    'surface': anim_surf
                })
            
            self._check_level_clear_condition() 
            if self.level_cleared_pending_animation: break 

        collided_fragments = pygame.sprite.spritecollide(self.player, self.core_fragments_group, True, pygame.sprite.collide_rect_ratio(0.7))
        for frag_sprite in collided_fragments:
            if hasattr(frag_sprite, 'apply_effect') and frag_sprite.apply_effect(self.player, self):
                self.play_sound('collect_fragment')
                self.score += 100
                frag_id = getattr(frag_sprite, 'fragment_id', None)
                
                if frag_id and self.drone_system:
                    unlocked_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{frag_id}")
                    if unlocked_lore: 
                        self.set_story_message(f"Lore: {self.drone_system.get_lore_entry_details(unlocked_lore[0]).get('title', 'New Data')}")
                
                if frag_id and hasattr(self.ui_manager, 'get_scaled_fragment_icon'):
                    is_animating = any(anim.get('id') == frag_id for anim in self.animating_fragments_to_hud)
                    if frag_id not in self.hud_displayed_fragments and not is_animating:
                        icon_surf = self.ui_manager.get_scaled_fragment_icon(frag_id)
                        target_pos = self.fragment_ui_target_positions.get(frag_id)
                        if icon_surf and target_pos: 
                            self.animating_fragments_to_hud.append({
                                'pos': list(frag_sprite.rect.center), 
                                'target_pos': target_pos, 
                                'speed': 12, 
                                'surface': icon_surf, 
                                'id': frag_id
                            })
                
                if self.drone_system and self.drone_system.are_all_core_fragments_collected():
                    self.architect_vault_message = "All Core Fragments Acquired! Vault Access Imminent!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 4000
                
                self._check_level_clear_condition() 

        for item_group, sound_name, score_val, lore_prefix_for_event_trigger in [
            (self.vault_logs_group, 'collect_log', 50, "collect_log_"), 
            (self.glyph_tablets_group, 'collect_log', 75, "collect_glyph_tablet_"), 
            (self.architect_echoes_group, 'collect_fragment', 150, "collect_echo_")
        ]:
            collided_items = pygame.sprite.spritecollide(self.player, item_group, True, pygame.sprite.collide_rect_ratio(0.7))
            for item in collided_items:
                item_id_attr = None
                if item_group == self.vault_logs_group: item_id_attr = 'log_id'
                elif item_group == self.glyph_tablets_group: item_id_attr = 'tablet_id'
                elif item_group == self.architect_echoes_group: item_id_attr = 'echo_id'
                
                item_id_val = getattr(item, item_id_attr, None) if item_id_attr else None
                
                if hasattr(item, 'apply_effect') and item.apply_effect(self.player, self): 
                    self.play_sound(sound_name)
                    self.score += score_val
                    
                    if item_group == self.glyph_tablets_group and item_id_val:
                        self.drone_system.add_collected_glyph_tablet(item_id_val)
                        all_tablets_lore_check = self.drone_system.check_and_unlock_lore_entries(event_trigger="collect_all_architect_glyph_tablets") 
                        if "race_nordics" in all_tablets_lore_check: 
                             nordic_lore_details = self.drone_system.get_lore_entry_details("race_nordics")
                             nordic_title = nordic_lore_details.get("title", "NORDIC Preservers") if nordic_lore_details else "NORDIC Preservers"
                             self.set_story_message(f"All Glyphs Collected! Lore Unlocked: {nordic_title}")
                    
                    elif item_id_val:
                         self.drone_system.check_and_unlock_lore_entries(event_trigger=f"{lore_prefix_for_event_trigger}{item_id_val}")

        collided_alien_terminal = pygame.sprite.spritecollideany(self.player, self.alien_terminals_group)
        if collided_alien_terminal and isinstance(collided_alien_terminal, AncientAlienTerminal):
            if not collided_alien_terminal.interacted: 
                self.scene_manager.set_game_state(GAME_STATE_RING_PUZZLE, triggering_terminal=collided_alien_terminal)

    def _handle_player_death_or_life_loss(self, reason=""):
        if self.player: 
            self.player.reset_active_powerups() 

        self.lives -= 1
        logger.info(f"Player lost a life. Reason: {reason}. Lives remaining: {self.lives}")
        if self.lives <= 0: 
            if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
            self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
        else: 
            if self.player: 
                self._reset_player_after_death_internal() 
            
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state == GAME_STATE_PLAYING or \
               (current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and self.player):
                self._reset_level_timer_internal()

    def _check_level_clear_condition(self):
        if self.player and self.collected_rings_count >= self.total_rings_per_level and \
           self.all_enemies_killed_this_level and not self.level_cleared_pending_animation:
            
            if not self.level_clear_fragment_spawned_this_level:
                if self._attempt_level_clear_fragment_spawn(): 
                    self.level_clear_fragment_spawned_this_level = True
                    return 
            
            if self.player: self.player.moving_forward = False 
            self.level_cleared_pending_animation = True 

    def _attempt_level_clear_fragment_spawn(self):
        fragment_id_to_spawn = None
        fragment_details_to_spawn = None
        
        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details.get("reward_level") == self.level: 
                fragment_id_to_spawn = details.get("id")
                fragment_details_to_spawn = details
                break
        
        if fragment_id_to_spawn and fragment_details_to_spawn:
            if self.drone_system and not self.drone_system.has_collected_fragment(fragment_id_to_spawn) and \
               not any(getattr(frag, 'fragment_id', None) == fragment_id_to_spawn for frag in self.core_fragments_group):
                
                spawn_pos = self._get_safe_spawn_point(TILE_SIZE, TILE_SIZE) 
                if spawn_pos:
                    self.core_fragments_group.add(CoreFragmentItem(spawn_pos[0], spawn_pos[1], fragment_id_to_spawn, fragment_details_to_spawn))
                    self.play_sound('collect_fragment', 0.8) 
                    logger.info(f"Level clear fragment '{fragment_id_to_spawn}' spawned at {spawn_pos}.")
                    return True 
        return False 

    def _prepare_for_next_level(self, from_bonus_level_completion=False):
        logger.info(f"Preparing for next level. Current level: {self.level}, From bonus: {from_bonus_level_completion}")
        self.explosion_particles_group.empty() 
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
        self.level_clear_fragment_spawned_this_level = False 

        if self.player and not self.player.alive and self.lives > 0:
            self.player.health = self.player.max_health
            self.player.alive = True
        
        all_frags_collected = self.drone_system.are_all_core_fragments_collected() if self.drone_system else False
        vault_not_done = not self.drone_system.has_completed_architect_vault() if self.drone_system else True
        if not from_bonus_level_completion and all_frags_collected and vault_not_done and \
           not self.scene_manager.get_current_state().startswith("architect_vault"):
            self.initialize_specific_game_mode("architect_vault_entry", old_state=self.scene_manager.get_current_state(), phase_to_start="intro") # Pass old_state
            return

        if not from_bonus_level_completion: 
            self.level += 1 
        
        self.collected_rings_count = 0
        self.displayed_collected_rings_count = 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15) 
        
        if self.drone_system: 
            self.drone_system.set_player_level(self.level) 
        
        if self.level == 7 and "story_beat_SB03" not in self.triggered_story_beats: 
            if self.drone_system: self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB03")
            self.trigger_story_beat("story_beat_SB03")
        if self.level == 10 and self.drone_system and self.drone_system.has_completed_architect_vault() and \
           "story_beat_SB04" not in self.triggered_story_beats:
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB04")
            self.trigger_story_beat("story_beat_SB04")
        
        new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        if not new_player_pos: 
            logger.error("CRITICAL: _prepare_for_next_level could not get safe spawn point. Defaulting player pos.")
            new_player_pos = (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)

        self._create_or_reset_player(new_player_pos, is_vault=False, preserve_weapon_on_reset=True) 
        
        self.all_enemies_killed_this_level = False 
        
        self.maze = Maze(game_area_x_offset=0, maze_type="standard")
        self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
        self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level) 
        
        self.core_fragments_group.empty()
        self.vault_logs_group.empty()
        self.glyph_tablets_group.empty()
        self.alien_terminals_group.empty()
        self.architect_echoes_group.empty()
        self._place_collectibles_for_level(initial_setup=True)
        
        self._reset_level_timer_internal() 
        self.play_sound('level_up') 
        
        self.animating_rings_to_hud.clear()
        self.animating_fragments_to_hud.clear()
        
        if self.player: self.player.moving_forward = False 
        self.scene_manager.set_game_state(GAME_STATE_PLAYING) 

    def _reset_player_after_death_internal(self):
        if not self.player: return

        self.explosion_particles_group.empty() 
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
        self.level_clear_fragment_spawned_this_level = False 

        new_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8) 
        if not new_pos: 
            logger.error("CRITICAL: _reset_player_after_death_internal could not get safe spawn point. Defaulting player pos.")
            new_pos = (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)

        is_vault = self.scene_manager.get_current_state().startswith("architect_vault")
        
        self._create_or_reset_player(new_pos, is_vault=is_vault, preserve_weapon_on_reset=False) 
        
        if is_vault and self.architect_vault_current_phase not in ["intro", "entry_puzzle"]:
            self.architect_vault_failure_reason = "Drone destroyed mid-mission."
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
            return
        
        self.animating_rings_to_hud.clear()
        self.animating_fragments_to_hud.clear()
        self.level_cleared_pending_animation = False

    def _reset_level_timer_internal(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level(self, completed=True):
        logger.info(f"Bonus level ended. Completed: {completed}")
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.level_clear_fragment_spawned_this_level = False

        if completed: 
            self.score += 500 
        
        if self.drone_system: 
            self.drone_system.add_player_cores(250) 
            self.drone_system._save_unlocks() 
        
        self._prepare_for_next_level(from_bonus_level_completion=True)

    def _get_safe_spawn_point(self, entity_width, entity_height):
        if not self.maze: 
            logger.warning("GameController: _get_safe_spawn_point called but maze is not initialized. Using fallback (center screen).")
            return (WIDTH // 2, GAME_PLAY_AREA_HEIGHT // 2) 
        
        path_cells_abs = [] 
        if hasattr(self.maze, 'get_path_cells_abs'): 
            path_cells_abs = self.maze.get_path_cells_abs()
        elif hasattr(self.maze, 'get_path_cells'): 
            path_cells_rel = self.maze.get_path_cells()
            path_cells_abs = [(x + self.maze.game_area_x_offset, y) for x,y in path_cells_rel]
        
        if not path_cells_abs: 
            logger.warning("GameController: No path cells found from maze.get_path_cells. Using hardcoded fallback (maze top-left path-like).")
            return (getattr(self.maze, 'game_area_x_offset', 0) + TILE_SIZE // 2 + TILE_SIZE, TILE_SIZE // 2 + TILE_SIZE) 

        random.shuffle(path_cells_abs) 
        
        for abs_x, abs_y in path_cells_abs:
            if not self.maze.is_wall(abs_x, abs_y, entity_width, entity_height):
                return (abs_x, abs_y) 
        
        logger.warning(f"GameController: No non-wall spawn point found in {len(path_cells_abs)} path cells. Returning first path cell ({path_cells_abs[0] if path_cells_abs else 'N/A'}) as risky fallback.")
        return path_cells_abs[0] 

    def _spawn_architect_vault_puzzle_terminals(self):
        self.architect_vault_puzzle_terminals_group.empty() 
        if not self.maze or not CORE_FRAGMENT_DETAILS: return

        path_cells_abs = self.maze.get_path_cells_abs() if hasattr(self.maze, 'get_path_cells_abs') else []
        frag_ids_for_terminals = ["cf_alpha", "cf_beta", "cf_gamma"] 
        num_to_spawn = len(frag_ids_for_terminals)

        if len(path_cells_abs) < num_to_spawn: 
            num_to_spawn = len(path_cells_abs) 
        if num_to_spawn == 0: return

        spawn_points = random.sample(path_cells_abs, k=num_to_spawn) 
        
        for i in range(num_to_spawn):
            abs_x, abs_y = spawn_points[i]
            terminal_sprite = pygame.sprite.Sprite() 
            terminal_sprite.image = pygame.Surface([TILE_SIZE * 0.6, TILE_SIZE * 0.6], pygame.SRCALPHA)
            terminal_sprite.image.fill(RED) 
            terminal_sprite.rect = terminal_sprite.image.get_rect(center=(abs_x, abs_y))
            terminal_sprite.terminal_id = i 
            terminal_sprite.required_fragment_id = frag_ids_for_terminals[i] 
            terminal_sprite.is_active = False 
            self.architect_vault_puzzle_terminals_group.add(terminal_sprite)
        logger.info(f"Spawned {num_to_spawn} Architect Vault puzzle terminals.")

    def _spawn_escape_zone(self):
        if self.maze and self.player: 
            spawn_pos = self._get_safe_spawn_point(TILE_SIZE * 1.5, TILE_SIZE * 1.5) 
            if spawn_pos: 
                self.escape_zone_group.add(EscapeZone(spawn_pos[0], spawn_pos[1]))
                logger.info(f"Escape zone spawned at {spawn_pos}")

    def _place_collectibles_for_level(self, initial_setup=False):
        if not self.maze or not self.player: 
            logger.warning("GameController._place_collectibles_for_level: Maze or Player not initialized. Skipping collectible placement.")
            return

        path_cells_abs = []
        if hasattr(self.maze, 'get_path_cells_abs'): 
            path_cells_abs = self.maze.get_path_cells_abs()
        elif hasattr(self.maze, 'get_path_cells'): 
            path_cells_rel = self.maze.get_path_cells()
            path_cells_abs = [(x + self.maze.game_area_x_offset, y) for x,y in path_cells_rel]

        if not path_cells_abs: 
            logger.warning("GameController._place_collectibles_for_level: No path cells found to place collectibles.")
            return

        if initial_setup:
            self.collectible_rings_group.empty()
            num_rings = min(self.total_rings_per_level, len(path_cells_abs))
            logger.info(f"Placing rings: total_rings_per_level={self.total_rings_per_level}, num_path_cells={len(path_cells_abs)}, num_rings_to_spawn={num_rings}")
            if num_rings > 0:
                ring_spawns = random.sample(path_cells_abs, k=num_rings)
                for x,y in ring_spawns:
                    new_ring = CollectibleRing(x,y)
                    self.collectible_rings_group.add(new_ring)
            logger.info(f"Total rings in group after placement: {len(self.collectible_rings_group)}")
        
        occupied_tiles = set() 

        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details and details.get("spawn_info", {}).get("level") == self.level and \
               details.get("reward_level") is None and self.drone_system and \
               not self.drone_system.has_collected_fragment(details["id"]) and \
               not any(getattr(f,'fragment_id',None) == details["id"] for f in self.core_fragments_group):
                
                spawn_pos = self._get_random_valid_collectible_spawn_abs(path_cells_abs, occupied_tiles)
                if spawn_pos:
                    self.core_fragments_group.add(CoreFragmentItem(spawn_pos[0], spawn_pos[1], details["id"], details))
                    occupied_tiles.add(spawn_pos) 

        if self.level == 2 and self.drone_system and not self.drone_system.has_unlocked_lore("race_greys"): 
             if not any(getattr(log, 'log_id', None) == "GRX-23" for log in self.vault_logs_group):
                spawn_pos = self._get_random_valid_collectible_spawn_abs(path_cells_abs, occupied_tiles)
                if spawn_pos: 
                    self.vault_logs_group.add(VaultLogItem(spawn_pos[0], spawn_pos[1], "GRX-23", "vault_log_grx23_icon.png"))
                    occupied_tiles.add(spawn_pos)
        
        terminal_id = f"level_5_element115_terminal" 
        if self.level == 5 and self.drone_system and not self.drone_system.has_puzzle_terminal_been_solved(terminal_id):
            if not any(getattr(t, 'item_id', '') == terminal_id for t in self.alien_terminals_group):
                spawn_pos = self._get_random_valid_collectible_spawn_abs(path_cells_abs, occupied_tiles, min_dist_player=TILE_SIZE*3)
                if spawn_pos:
                    term = AncientAlienTerminal(spawn_pos[0], spawn_pos[1])
                    term.item_id = terminal_id 
                    self.alien_terminals_group.add(term)
                    occupied_tiles.add(spawn_pos)

    def _place_collectibles_for_bonus_level(self):
        logger.info("GameController: Placing collectibles for Bonus Level.")
        if not self.maze or not self.player:
            logger.warning("GameController: Cannot place bonus collectibles - maze or player missing.")
            return

        path_cells_abs = []
        if hasattr(self.maze, 'get_path_cells_abs'):
            path_cells_abs = self.maze.get_path_cells_abs()
        elif hasattr(self.maze, 'get_path_cells'): 
            path_cells_rel = self.maze.get_path_cells()
            path_cells_abs = [(x + self.maze.game_area_x_offset, y) for x,y in path_cells_rel]

        if not path_cells_abs:
            logger.warning("GameController: No path cells to spawn bonus rings.")
            return
        
        self.collectible_rings_group.empty() 
        num_bonus_rings = gs.get_game_setting("BONUS_LEVEL_NUM_RINGS", 50) 
        
        if len(path_cells_abs) < num_bonus_rings: 
            num_bonus_rings = len(path_cells_abs) 
        
        if num_bonus_rings > 0:
            ring_spawn_points_abs = random.sample(path_cells_abs, k=num_bonus_rings)
            for x,y in ring_spawn_points_abs:
                self.collectible_rings_group.add(CollectibleRing(x,y))
        logger.info(f"GameController: Spawned {num_bonus_rings} rings for bonus level.")
        
    def _get_random_valid_collectible_spawn_abs(self, available_path_cells_abs, occupied_coords_abs, min_dist_player=TILE_SIZE*2):
        if not available_path_cells_abs: return None
        
        potential_spawns = [
            cell for cell in available_path_cells_abs 
            if cell not in occupied_coords_abs and 
               (not self.player or math.hypot(cell[0] - self.player.x, cell[1] - self.player.y) > min_dist_player) 
        ]
        
        return random.choice(potential_spawns) if potential_spawns else None

    def submit_leaderboard_name(self, name_from_ui_flow):
        if leaderboard.add_score(name_from_ui_flow, self.score, self.level): 
            self.play_sound('ui_confirm') 
        else: 
            self.play_sound('ui_denied') 
        
        self.ui_flow_controller.leaderboard_scores = leaderboard.load_scores()
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD) 

    def toggle_pause(self):
        self.paused = not self.paused
        logger.debug(f"Pause state toggled. Paused: {self.paused}")
        if self.paused: 
            pygame.mixer.music.pause() 
        else: 
            pygame.mixer.music.unpause() 
            current_time = pygame.time.get_ticks()
            current_state = self.scene_manager.get_current_state()
            if current_state == GAME_STATE_PLAYING: 
                self.level_timer_start_ticks = current_time - (gs.get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif current_state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction": 
                self.architect_vault_phase_timer_start = current_time - (gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - self.level_time_remaining_ms)
            elif current_state == GAME_STATE_BONUS_LEVEL_PLAYING: 
                self.bonus_level_timer_start = current_time - (self.bonus_level_duration_ms - self.level_time_remaining_ms)

    def unpause_and_set_state(self, new_state):
        if self.paused: 
            self.toggle_pause() 
        self.scene_manager.set_game_state(new_state) 

    def quit_game(self):
        logger.info("Quitting game...")
        if self.drone_system: 
            self.drone_system._save_unlocks() 
        pygame.quit()
        sys.exit()

    def _draw_game_world(self):
        current_game_state = self.scene_manager.get_current_state()

        if current_game_state.startswith("architect_vault"):
            self.screen.fill(ARCHITECT_VAULT_BG_COLOR)
        elif current_game_state == GAME_STATE_MAZE_DEFENSE:
            self.screen.fill(gs.DARK_GREY) 
        else:
            self.screen.fill(BLACK)

        if self.maze:
            self.maze.draw(self.screen)

        if current_game_state != GAME_STATE_MAZE_DEFENSE:
            self.collectible_rings_group.draw(self.screen)
            self.core_fragments_group.draw(self.screen)
            self.vault_logs_group.draw(self.screen)
            self.glyph_tablets_group.draw(self.screen)
            self.architect_echoes_group.draw(self.screen)
            self.alien_terminals_group.draw(self.screen)


        self.power_ups_group.draw(self.screen) 
        self.escape_zone_group.draw(self.screen) 

        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_puzzle_terminals_group.draw(self.screen)

        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            self.reactor_group.draw(self.screen) 

            if self.turrets_group:
                for turret_sprite in self.turrets_group: 
                    if hasattr(turret_sprite, 'draw') and callable(getattr(turret_sprite, 'draw')):
                        try:
                            turret_sprite.draw(self.screen) 
                        except Exception as e:
                            logger.error(f"Error drawing turret {turret_sprite}: {e}")
                            logger.exception("Turret draw exception details:")

            if self.player and self.player.alive: 
                self.player.draw(self.screen)


        if self.combat_controller and self.combat_controller.enemy_manager:
            self.combat_controller.enemy_manager.draw_all(self.screen)
        if self.combat_controller and self.combat_controller.boss_active and self.combat_controller.maze_guardian:
            self.combat_controller.maze_guardian.draw(self.screen)

        if self.player and current_game_state != GAME_STATE_MAZE_DEFENSE : 
             if self.player.alive or self.player.bullets_group or self.player.missiles_group or self.player.lightning_zaps_group:
                 self.player.draw(self.screen) 
        elif self.player and current_game_state == GAME_STATE_MAZE_DEFENSE and hasattr(self.player, 'draw_health_bar'): 
            pass 

        self.explosion_particles_group.draw(self.screen) 

    def is_current_score_a_high_score(self): 
        return leaderboard.is_high_score(self.score, self.level)

    def check_and_apply_screen_settings_change(self):
        current_fullscreen_setting = gs.get_game_setting("FULLSCREEN_MODE")
        required_flags = pygame.FULLSCREEN if current_fullscreen_setting else 0
        
        if self.screen_flags != required_flags:
            logger.info("GameController: Screen mode changed, reinitializing display.")
            self.screen_flags = required_flags
            current_w = gs.get_game_setting("WIDTH")
            current_h = gs.get_game_setting("HEIGHT")
            self.screen = pygame.display.set_mode((current_w, current_h), self.screen_flags)

    def handle_pause_menu_input(self, key_pressed, current_game_state):
        logger.debug(f"Pause menu input: Key {key_pressed} in state {current_game_state}")
        if key_pressed == pygame.K_p: 
            self.toggle_pause()
        elif key_pressed == pygame.K_m: 
            if current_game_state.startswith("architect_vault"):
                self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
            else:
                self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_pressed == pygame.K_q: 
            self.quit_game()
        elif key_pressed == pygame.K_l and current_game_state == GAME_STATE_PLAYING: 
            self.unpause_and_set_state(GAME_STATE_LEADERBOARD)
        elif key_pressed == pygame.K_ESCAPE and current_game_state.startswith("architect_vault"): 
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_pressed == pygame.K_m and current_game_state == GAME_STATE_MAZE_DEFENSE: 
            logger.info("Exiting Maze Defense to Main Menu from pause.")
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)


    def run(self):
        """Main game loop."""
        self.check_and_apply_screen_settings_change()

        while True:
            delta_time_ms = self.clock.tick(gs.get_game_setting("FPS", 60))

            self.event_manager.process_events()
            self.update(delta_time_ms)

            current_game_state = self.scene_manager.get_current_state()

            if current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
                self.ui_manager.draw_current_scene_ui()
            elif current_game_state == GAME_STATE_RING_PUZZLE:
                self.screen.fill(gs.DARK_GREY)
                self.puzzle_controller.draw_active_puzzle(self.screen)
            elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING,
                                        GAME_STATE_MAZE_DEFENSE] or \
                 current_game_state.startswith("architect_vault"):
                self._draw_game_world() 
                self.ui_manager.draw_current_scene_ui() 
            else: 
                self.ui_manager.draw_current_scene_ui()

            pygame.display.flip()