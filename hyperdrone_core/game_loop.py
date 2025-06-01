import sys
import os
import random
import math
import traceback

import pygame

from .scene_manager import SceneManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from . import leaderboard
from .enemy_manager import EnemyManager
from .ring_puzzle_module import RingPuzzle

from ui import UIManager
from entities import (
    PlayerDrone,
    Ring,
    WeaponUpgradeItem,
    ShieldItem,
    SpeedBoostItem,
    CoreFragmentItem,
    VaultLogItem,
    GlyphTabletItem,
    AncientAlienTerminal,
    LightningZap,
    Particle,
    MazeGuardian,
    SentinelDrone,
    EscapeZone
)
from entities.maze import Maze

from drone_management import DroneSystem, DRONE_DATA, DRONE_DISPLAY_ORDER

import game_settings as gs
from game_settings import (
    BLACK, WHITE, GOLD, CYAN, RED, YELLOW, GREEN, ORANGE, DARK_RED, GREY, PURPLE,
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_CODEX,
    GAME_STATE_DRONE_SELECT, GAME_STATE_BONUS_LEVEL_PLAYING,
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE,
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    GAME_STATE_RING_PUZZLE, GAME_STATE_GAME_INTRO_SCROLL,
    ARCHITECT_VAULT_BG_COLOR, ARCHITECT_VAULT_WALL_COLOR,
    TILE_SIZE,
    POWERUP_TYPES,
    WEAPON_MODES_SEQUENCE, WEAPON_MODE_NAMES,
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
    ARCHITECT_VAULT_DRONES_PER_WAVE, ARCHITECT_VAULT_GAUNTLET_WAVES,
    DEFAULT_SETTINGS,
    get_game_setting, set_game_setting, reset_all_settings_to_default,
    MAZE_GUARDIAN_HEALTH,
    WIDTH, GAME_PLAY_AREA_HEIGHT, HEIGHT
)


class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.mouse.set_visible(False)
        self.screen_flags = pygame.FULLSCREEN if gs.get_game_setting("FULLSCREEN_MODE") else 0
        self.screen = pygame.display.set_mode((gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")), self.screen_flags)
        pygame.display.set_caption("HYPERDRONE")
        self.clock = pygame.time.Clock()
        self.drone_system = DroneSystem()
        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf")
        self.font_path_neuropol = os.path.join("assets", "fonts", "neuropol.otf")
        self.fonts = {}
        self._initialize_fonts()
        self.scene_manager = SceneManager(self)
        self.player_actions = PlayerActions(self)
        self.event_manager = EventManager(self, self.scene_manager)
        self.ui_manager = UIManager(self.screen, self.fonts, self, self.scene_manager, self.drone_system)
        self.player = None
        self.maze = None
        self.enemy_manager = EnemyManager(self)
        self.rings = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group()
        self.core_fragments = pygame.sprite.Group()
        self.vault_logs = pygame.sprite.Group()
        self.glyph_tablets = pygame.sprite.Group()
        self.architect_vault_terminals = pygame.sprite.Group()
        self.alien_terminals_group = pygame.sprite.Group()
        self.explosion_particles = pygame.sprite.Group()
        self.maze_guardian = None
        self.boss_active = False
        self.escape_zone = None
        self.escape_zone_group = pygame.sprite.GroupSingle()
        self.score = 0
        self.level = 1
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        self.paused = False
        self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")
        self.bonus_level_timer_start = 0
        self.bonus_level_duration_ms = gs.get_game_setting("BONUS_LEVEL_DURATION_MS")
        self.collected_rings = 0
        self.displayed_collected_rings = 0
        self.total_rings_per_level = 5
        self.animating_rings = []
        self.ring_ui_target_pos = (0,0)
        self.animating_fragments = []
        self.fragment_ui_target_positions = {}
        self.hud_displayed_fragments = set()
        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False # New flag

        self.architect_vault_current_phase = None
        self.architect_vault_phase_timer_start = 0
        self.architect_vault_gauntlet_current_wave = 0
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self.architect_vault_message = ""
        self.architect_vault_message_timer = 0
        self.architect_vault_failure_reason = ""
        self.story_message = ""
        self.story_message_active = False
        self.STORY_MESSAGE_DURATION = 5000
        self.triggered_story_beats = set()

        # --- Cinematic Intro Attributes ---
        self.intro_screens_data = [
            {
                "text": "The Architect — creator of the Vault\nand all drone intelligence — has vanished.\n\nNo warning. No trace. Only silence.",
                "image_path": "assets/images/lore/scene1.png"
            },
            {
                "text": "In their absence, the Vault has shifted.\n\nIts corridors twisted into cryptic mazes,\nteeming with automated defences.",
                "image_path": "assets/images/lore/scene2.png"
            },
            {
                "text": "You are a pilot. An explorer.\n\nEntering the Vault to unravel the AI’s enigma —\n\nand stop a system-wide fail-safe\nbefore it activates.",
                "image_path": "assets/images/lore/scene3.png"
            },
            {
                "text": "The Architect’s secrets lie ahead.\n\nSolve the puzzles. Survive the machines.\n\nOr be erased with everything else.",
                "image_path": "assets/images/lore/scene4.png"
            }
        ]
        self.current_intro_screen_index = 0
        self.intro_screen_start_time = 0
        self.INTRO_SCREEN_DURATION_MS = 6000 # 6 seconds per screen
        self.intro_screen_text_surfaces_current = []
        self.current_intro_image_surface = None
        self.intro_font_key = "codex_category_font"
        self.intro_text_color = gs.GOLD
        self.intro_text_max_width_ratio = 0.8
        self.intro_sequence_finished = False


        self.menu_options = ["Start Game", "Select Drone", "Codex", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.player_name_input_display_cache = ""
        self.leaderboard_scores = leaderboard.load_scores()
        self.drone_select_options = DRONE_DISPLAY_ORDER
        self.selected_drone_preview_index = 0
        self.drone_main_display_cache = {}
        self._load_drone_main_display_images()
        self.sounds = {}
        self.load_sfx()
        self.menu_stars = []
        self._initialize_menu_stars()
        self._initialize_settings_menu_items_data()
        self.codex_current_view = "categories"
        self.codex_categories_list = []
        self.codex_selected_category_index = 0
        self.codex_current_category_name = None
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0
        self.current_ring_puzzle = None
        self.ring_puzzle_active_flag = False
        self.screen_width_for_puzzle = gs.get_game_setting("WIDTH")
        self.screen_height_for_puzzle = gs.get_game_setting("HEIGHT")
        self.ring_puzzle_has_been_officially_handled_as_solved = False
        self.last_interacted_terminal = None

        if self.drone_system:
            self.drone_system.unlock_lore_entry_by_id("architect_legacy_intro")
            self.drone_system.check_and_unlock_lore_entries(event_trigger="game_start")


        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def _initialize_fonts(self):
        font_configs = {
            "ui_text": (self.font_path_neuropol, 28), "ui_values": (self.font_path_neuropol, 30),
            "ui_emoji_general": (self.font_path_emoji, 32), "ui_emoji_small": (self.font_path_emoji, 20),
            "small_text": (self.font_path_neuropol, 24), "medium_text": (self.font_path_neuropol, 48),
            "large_text": (self.font_path_neuropol, 74), "input_text": (self.font_path_neuropol, 50),
            "menu_text": (self.font_path_neuropol, 60), "title_text": (self.font_path_neuropol, 90),
            "drone_name_grid": (self.font_path_neuropol, 36),
            "drone_desc_grid": (self.font_path_neuropol, 22),
            "drone_unlock_grid": (self.font_path_neuropol, 20),
            "drone_name_cycle": (self.font_path_neuropol, 42),
            "drone_stats_label_cycle": (self.font_path_neuropol, 26),
            "drone_stats_value_cycle": (self.font_path_neuropol, 28),
            "drone_desc_cycle": (self.font_path_neuropol, 22),
            "drone_unlock_cycle": (self.font_path_neuropol, 20),
            "vault_message": (self.font_path_neuropol, 36), "vault_timer": (self.font_path_neuropol, 48),
            "leaderboard_header": (self.font_path_neuropol, 32), "leaderboard_entry": (self.font_path_neuropol, 28),
            "arrow_font_key": (self.font_path_emoji, 60),
            "story_message_font": (self.font_path_neuropol, 26),
            "codex_title_font": (self.font_path_neuropol, 60),
            "codex_category_font": (self.font_path_neuropol, 38), # Used for intro screen text
            "codex_entry_font": (self.font_path_neuropol, 30),
            "codex_content_font": (self.font_path_neuropol, 24)
        }
        for name, (path, size) in font_configs.items():
            try:
                self.fonts[name] = pygame.font.Font(path, size)
            except pygame.error as e:
                print(f"GameController: Font loading error for '{name}' ('{path}', size {size}): {e}. Using fallback.")
                self.fonts[name] = pygame.font.Font(None, size)

    def _initialize_menu_stars(self, num_stars=150):
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            speed = random.uniform(0.1, 0.7)
            size = random.randint(1, 2)
            self.menu_stars.append([x, y, speed, size])

    def _initialize_settings_menu_items_data(self):
        self.settings_items_data = [
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
        self.selected_setting_index = 0

    def _create_fallback_image_surface(self, size=(200,200), text="?", color=(80,80,80), text_color=WHITE, font_key="large_text"):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2)
        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, size[1]//2))
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e:
                print(f"GameController: Error rendering fallback image text '{text}': {e}")
        return surface

    def _load_drone_main_display_images(self):
        self.drone_main_display_cache = {}
        display_size = (200, 200)
        for drone_id, data in DRONE_DATA.items():
            image_surface = None
            path_to_try = data.get("sprite_path")
            if not path_to_try or not os.path.exists(path_to_try):
                path_to_try = data.get("icon_path")
            if path_to_try and os.path.exists(path_to_try):
                try:
                    loaded_image = pygame.image.load(path_to_try).convert_alpha()
                    image_surface = pygame.transform.smoothscale(loaded_image, display_size)
                except pygame.error as e:
                    print(f"GameController: Error loading main display image for {drone_id} ('{path_to_try}'): {e}.")
            else:
                 if path_to_try: print(f"GameController: Warning - Main display image path not found: {path_to_try}")
            if image_surface is None:
                initials = data.get("name", "?")[:2].upper()
                image_surface = self._create_fallback_image_surface(
                    size=display_size, text=initials, font_key="large_text"
                )
            self.drone_main_display_cache[drone_id] = image_surface

    def load_sfx(self):
        sound_files = {
            'collect_ring': "collect_ring.wav", 'weapon_upgrade_collect': "collect_powerup.wav",
            'collect_fragment': "collect_fragment.wav", 'crash': "crash.wav",
            'shoot': "shoot.wav", 'missile_launch': "missile_launch.wav",
            'level_up': "level_up.wav", 'player_death': "player_death.wav",
            'enemy_shoot': "enemy_shoot.wav", 'timer_out': "timer_warning.wav",
            'ui_select': "ui_select.wav", 'ui_confirm': "ui_confirm.wav", 'ui_denied': "ui_denied.wav",
            'cloak_activate': "cloak_on.wav",
            'vault_alarm': "vault_alarm.wav",
            'vault_barrier_disable': "vault_barrier_disable.wav",
            'prototype_drone_explode': "prototype_drone_explode.wav",
            'boss_intro': "boss_intro.wav",
            'laser_charge': "laser_charge.wav",
            'laser_fire': "laser_fire.wav",
            'shield_activate': "shield_activate.wav",
            'minion_spawn': "minion_spawn.wav",
            'wall_shift': "wall_shift.wav",
            'boss_hit': "boss_hit.wav",
            'boss_death': "boss_death.wav",
            'lore_unlock': "ui_confirm.wav" ,
            'collect_log': "collect_fragment.wav"
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

    def play_sound(self, name, volume=0.7):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()

    def set_story_message(self, message, duration=None):
        self.story_message = message
        self.story_message_active = True
        print(f"STORY (persistent): {message}")

    def trigger_story_beat(self, beat_id):
        if beat_id not in self.triggered_story_beats:
            if self.drone_system.has_unlocked_lore(beat_id):
                lore_entry = self.drone_system.get_lore_entry_details(beat_id)
                if lore_entry:
                    self.set_story_message(lore_entry.get("content", f"Event: {lore_entry.get('title', beat_id)}"))
                    self.triggered_story_beats.add(beat_id)
                    self.play_sound('lore_unlock', 0.6)
                    print(f"GameController: Story Beat '{beat_id}' triggered and message displayed.")
                    return True
                else:
                     print(f"GameController: Story Beat '{beat_id}' was marked unlocked, but details not found.")
            else:
                print(f"GameController: Story Beat ID '{beat_id}' lore not yet unlocked. Cannot display.")
        return False

    def _create_explosion(self, x, y, num_particles=20, specific_sound='prototype_drone_explode'):
        colors = [gs.ORANGE, gs.YELLOW, gs.RED, gs.DARK_RED, gs.GREY]
        min_speed = 1
        max_speed = 4
        min_size = 2
        max_size = 5
        gravity = 0.05
        shrink_rate = 0.1
        lifetime = random.randint(20, 40)

        for _ in range(num_particles):
            particle = Particle(x, y, colors, min_speed, max_speed, min_size, max_size, gravity, shrink_rate, lifetime)
            self.explosion_particles.add(particle)

        if specific_sound and hasattr(self, 'play_sound'):
            self.play_sound(specific_sound)

    def initialize_main_menu_scene(self):
        self.selected_menu_option = 0

    def initialize_drone_select_scene(self):
        current_selected_id = self.drone_system.get_selected_drone_id()
        try:
            self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
        except ValueError:
            self.selected_drone_preview_index = 0
        self.ui_manager.update_player_life_icon_surface()

    def initialize_settings_scene(self):
        self.selected_setting_index = 0

    def initialize_leaderboard_scene(self):
        self.leaderboard_scores = leaderboard.load_scores()

    def initialize_enter_name_scene(self):
        self.player_name_input_display_cache = ""

    def initialize_codex_scene(self):
        self.codex_current_view = "categories"
        unlocked_lore_ids = self.drone_system.get_unlocked_lore_ids()
        all_lore_data = self.drone_system.get_all_loaded_lore_entries()

        self.codex_categories_list = sorted(list(set(
            entry.get("category", "Misc")
            for entry_id, entry in all_lore_data.items()
            if entry_id in unlocked_lore_ids and entry
        )))
        if not self.codex_categories_list and unlocked_lore_ids:
             self.codex_categories_list = ["Misc"]

        self.codex_selected_category_index = 0
        self.codex_current_category_name = None
        self.codex_entries_in_category_list = []
        self.codex_selected_entry_index_in_category = 0
        self.codex_selected_entry_id = None
        self.codex_content_scroll_offset = 0
        self.codex_current_entry_total_lines = 0
        print(f"GameController: Codex scene initialized. Categories: {self.codex_categories_list}")

    def initialize_ring_puzzle_scene(self):
        print("GameController: Initializing Ring Puzzle Scene...")
        ring_configs = [
            ("ring1.png", 6),
            ("ring2.png", 8),
            ("ring3.png", 12)
        ]
        puzzle_asset_path = "assets/images/puzzles/"

        try:
            self.current_ring_puzzle = RingPuzzle(
                self.screen_width_for_puzzle,
                self.screen_height_for_puzzle,
                ring_configs,
                assets_path=puzzle_asset_path
            )
            self.ring_puzzle_has_been_officially_handled_as_solved = False
            self.ring_puzzle_active_flag = True
            print("GameController: Ring Puzzle initialized successfully.")
        except Exception as e:
            print(f"GameController: CRITICAL Error initializing ring puzzle: {e}")
            traceback.print_exc()
            self.ring_puzzle_active_flag = False
            self.current_ring_puzzle = None
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def initialize_game_intro_scene(self):
        """Prepares the first cinematic intro screen."""
        print("GameController: Initializing Cinematic Intro Scene...")
        self.current_intro_screen_index = 0
        self.intro_sequence_finished = False
        self._prepare_current_intro_screen()

    def _prepare_current_intro_screen(self):
        """Loads image and renders text for the current intro screen."""
        if self.current_intro_screen_index >= len(self.intro_screens_data):
            self.intro_sequence_finished = True
            self.intro_screen_text_surfaces_current = []
            print("GameController: Intro sequence finished. Last image retained.")
            return

        screen_data = self.intro_screens_data[self.current_intro_screen_index]
        text_content = screen_data["text"]
        image_path = screen_data["image_path"]

        if image_path not in self.ui_manager.codex_image_cache:
            if os.path.exists(image_path):
                try:
                    self.ui_manager.codex_image_cache[image_path] = pygame.image.load(image_path).convert_alpha()
                except pygame.error as e:
                    print(f"GameController: Error loading intro image '{image_path}': {e}")
                    self.ui_manager.codex_image_cache[image_path] = None
            else:
                print(f"GameController: Intro image not found: '{image_path}'")
                self.ui_manager.codex_image_cache[image_path] = None
        self.current_intro_image_surface = self.ui_manager.codex_image_cache.get(image_path)


        self.intro_screen_text_surfaces_current = []
        font = self.fonts.get(self.intro_font_key, pygame.font.Font(None, 36))
        max_text_width = int(gs.WIDTH * self.intro_text_max_width_ratio)

        raw_lines = text_content.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip():
                space_surf = font.render(" ", True, self.intro_text_color)
                self.intro_screen_text_surfaces_current.append(space_surf)
                continue
            line_surf = font.render(raw_line, True, self.intro_text_color)
            self.intro_screen_text_surfaces_current.append(line_surf)

        self.intro_screen_start_time = pygame.time.get_ticks()
        print(f"GameController: Prepared intro screen {self.current_intro_screen_index + 1}/{len(self.intro_screens_data)}")

    def skip_current_intro_screen(self):
        """Advances to the next intro screen or finishes the sequence."""
        if not self.intro_sequence_finished:
            self.current_intro_screen_index += 1
            if self.current_intro_screen_index >= len(self.intro_screens_data):
                self.intro_sequence_finished = True
                self.intro_screen_text_surfaces_current = [] 
                print("GameController: Cinematic intro sequence skipped to end. Last image retained.")
            else:
                self._prepare_current_intro_screen()
                print(f"GameController: Skipped to intro screen {self.current_intro_screen_index + 1}")
            self.intro_screen_start_time = pygame.time.get_ticks() 


    def initialize_game_session(self):
        print("DEBUG: Initializing new game session...")
        if self.drone_system:
            self.drone_system.reset_collected_fragments_in_storage()
            self.drone_system.reset_architect_vault_status()
            if hasattr(self.drone_system, 'unlock_data') and "collected_glyph_tablet_ids" in self.drone_system.unlock_data:
                self.drone_system.unlock_data["collected_glyph_tablet_ids"] = []
            if hasattr(self.drone_system, 'unlock_data') and "solved_puzzle_terminals" in self.drone_system.unlock_data:
                self.drone_system.unlock_data["solved_puzzle_terminals"] = []

            self.drone_system._save_unlocks()
            print(f"DEBUG INIT: Vault completed status after reset: {self.drone_system.has_completed_architect_vault()}")
            self.drone_system.unlock_lore_entry_by_id("architect_legacy_intro")
            game_start_lore_unlocked = self.drone_system.check_and_unlock_lore_entries(event_trigger="game_start")
            if game_start_lore_unlocked:
                print(f"GameController: Lore unlocked at game start: {game_start_lore_unlocked}")


        self.level = 1
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        self.score = 0
        self.drone_system.set_player_level(self.level)

        self.level_cleared_pending_animation = False
        self.all_enemies_killed_this_level = False
        self.level_clear_fragment_spawned_this_level = False # Reset for new game
        self.explosion_particles.empty()
        self.triggered_story_beats.clear()

        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.alien_terminals_group.empty()
        self.last_interacted_terminal = None

        self.maze = Maze(game_area_x_offset=0, maze_type="standard")
        player_start_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)

        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=False)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite_path = drone_config.get("ingame_sprite_path")

        if self.player is None:
            self.player = PlayerDrone(player_start_pos[0], player_start_pos[1],
                                drone_id=selected_drone_id, drone_stats=effective_drone_stats,
                                drone_sprite_path=player_ingame_sprite_path,
                                crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        else:
            self.player.reset(player_start_pos[0], player_start_pos[1],
                              drone_id=selected_drone_id, drone_stats=effective_drone_stats,
                              drone_sprite_path=player_ingame_sprite_path, preserve_weapon=False)

        self.ui_manager.update_player_life_icon_surface()

        self.enemy_manager.spawn_enemies_for_level(self.level)
        if self.player:
            self.player.bullets_group.empty()
            self.player.missiles_group.empty()
            self.player.lightning_zaps_group.empty()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.vault_logs.empty()
        self.glyph_tablets.empty()
        self.architect_vault_terminals.empty()
        self.maze_guardian = None
        self.boss_active = False

        self.collected_rings = 0; self.displayed_collected_rings = 0
        self.total_rings_per_level = 5
        self.paused = False
        self.player_name_input_display_cache = ""
        self.animating_rings.clear()
        self.animating_fragments.clear()

        self.hud_displayed_fragments.clear()
        if self.drone_system:
            for frag_id in self.drone_system.get_collected_fragments_ids():
                self.hud_displayed_fragments.add(frag_id)

        self._place_collectibles_for_level(initial_setup=True)
        self._reset_level_timer_internal()

    def initialize_architect_vault_session(self):
        print("GameController: Initializing Architect's Vault session...")
        self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault")
        self.explosion_particles.empty()
        self.maze_guardian = None
        self.boss_active = False
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.alien_terminals_group.empty()
        self.last_interacted_terminal = None
        self.level_clear_fragment_spawned_this_level = False # Reset for vault

        prev_weapon_mode_idx = WEAPON_MODES_SEQUENCE.index(gs.get_game_setting("INITIAL_WEAPON_MODE"))
        prev_current_weapon_mode = gs.get_game_setting("INITIAL_WEAPON_MODE")
        if self.player:
            prev_weapon_mode_idx = self.player.weapon_mode_index
            prev_current_weapon_mode = self.player.current_weapon_mode

        safe_spawn = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_drone_stats_vault = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=True)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite_path = drone_config.get("ingame_sprite_path")

        if self.player:
            self.player.reset(safe_spawn[0], safe_spawn[1],
                              drone_id=selected_drone_id, drone_stats=effective_drone_stats_vault,
                              drone_sprite_path=player_ingame_sprite_path, preserve_weapon=True)
        else:
            self.player = PlayerDrone(safe_spawn[0], safe_spawn[1],
                                drone_id=selected_drone_id, drone_stats=effective_drone_stats_vault,
                                drone_sprite_path=player_ingame_sprite_path,
                                crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)

        if self.player:
            self.player.reset_active_powerups()
            self.player.health = self.player.max_health
            self.player.moving_forward = False
            if hasattr(self.player, 'activate_shield'):
                self.player.activate_shield(1500, is_from_speed_boost=False)

        self.enemy_manager.reset_all()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.vault_logs.empty()
        self.glyph_tablets.empty()
        self.architect_vault_terminals.empty()
        self.animating_fragments.clear()
        self.hud_displayed_fragments.clear()
        if self.drone_system:
            for frag_id in self.drone_system.get_collected_fragments_ids():
                self.hud_displayed_fragments.add(frag_id)

        self.architect_vault_current_phase = "intro"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.level_time_remaining_ms = 0
        self.architect_vault_failure_reason = ""

    def start_architect_vault_intro(self):
        self.architect_vault_current_phase = "intro"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.architect_vault_message = "The Architect's Vault... Entry protocol initiated."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        self.drone_system.check_and_unlock_lore_entries(event_trigger="architect_vault_entered")

    def start_architect_vault_entry_puzzle(self):
        self.architect_vault_current_phase = "entry_puzzle"
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self._spawn_architect_vault_terminals()
        self.architect_vault_message = "Activate terminals with collected Core Fragments."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000

    def start_architect_vault_gauntlet(self):
        self.architect_vault_current_phase = "gauntlet_intro"
        self.architect_vault_gauntlet_current_wave = 0
        self.enemy_manager.reset_all()
        self.architect_vault_message = "Security systems online. Prepare for hostiles."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 3000

    def start_architect_vault_extraction(self):
        print("DEBUG: start_architect_vault_extraction called")
        self.architect_vault_current_phase = "extraction"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.play_sound('vault_alarm', 0.7)
        self.architect_vault_message = "SELF-DESTRUCT SEQUENCE ACTIVATED! REACH THE EXTRACTION POINT!"

        if self.maze and self.player:
            spawn_attempts = 0
            max_attempts = 10
            min_dist_from_player = TILE_SIZE * 5

            zone_x, zone_y = None, None
            path_cells = self.maze.get_path_cells()
            if path_cells:
                random.shuffle(path_cells)
                for rel_x, rel_y in path_cells:
                    abs_x = rel_x + self.maze.game_area_x_offset
                    abs_y = rel_y
                    if math.hypot(abs_x - self.player.x, abs_y - self.player.y) > min_dist_from_player:
                        zone_x, zone_y = abs_x, abs_y
                        break
                    spawn_attempts +=1
                    if spawn_attempts >= max_attempts : break

            if zone_x is None or zone_y is None:
                if path_cells:
                    rel_x, rel_y = random.choice(path_cells)
                    zone_x = rel_x + self.maze.game_area_x_offset
                    zone_y = rel_y
                else:
                    zone_x, zone_y = WIDTH / 2, GAME_PLAY_AREA_HEIGHT / 2
                    print("WARNING: No path cells found for escape zone, placing at center.")

            if zone_x is not None and zone_y is not None:
                self.escape_zone = EscapeZone(zone_x, zone_y)
                self.escape_zone_group.add(self.escape_zone)
                print(f"DEBUG: Escape zone spawned at ({zone_x}, {zone_y})")
            else:
                print("ERROR: Could not determine spawn location for escape zone!")
                self.escape_zone = None

        self.level_time_remaining_ms = gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS")
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        print(f"DEBUG: Extraction started. Timer: {self.level_time_remaining_ms}ms. Escape zone: {self.escape_zone}")

    def handle_architect_vault_success_scene(self):
        print("DEBUG: handle_architect_vault_success_scene called")
        self.architect_vault_message = "Vault Conquered! Blueprint Acquired!"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
        self.drone_system.mark_architect_vault_completed(True)
        self.score += 2500
        self.drone_system.add_player_cores(500)
        self.drone_system._save_unlocks()
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None

        self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB05")
        self.trigger_story_beat("story_beat_SB05")

        print("Architect Vault Success: Preparing for next standard level.")
        self._prepare_for_next_level(from_bonus_level_completion=False)

    def handle_architect_vault_failure_scene(self):
        self.architect_vault_message = f"Vault Mission Failed: {self.architect_vault_failure_reason}"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        self.drone_system.mark_architect_vault_completed(False)
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None

    def handle_game_over_scene_entry(self):
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.drone_system.set_player_level(self.level)
        self.drone_system._save_unlocks()

    def update(self):
        current_game_state = self.scene_manager.get_current_state()
        current_time = pygame.time.get_ticks()

        if current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
            if not self.intro_sequence_finished:
                if current_time - self.intro_screen_start_time >= self.INTRO_SCREEN_DURATION_MS:
                    self.current_intro_screen_index += 1
                    if self.current_intro_screen_index >= len(self.intro_screens_data):
                        self.intro_sequence_finished = True
                        self.intro_screen_text_surfaces_current = [] 
                        print("GameController: Cinematic intro sequence finished. Last image retained.")
                    else:
                        self._prepare_current_intro_screen()
            
        elif current_game_state == GAME_STATE_RING_PUZZLE:
            if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                self.current_ring_puzzle.update()

                if self.current_ring_puzzle.is_solved() and \
                   not self.current_ring_puzzle.active and \
                   not self.ring_puzzle_has_been_officially_handled_as_solved:

                    self.ring_puzzle_has_been_officially_handled_as_solved = True
                    print("GameController: Ring Puzzle solution registered! Performing post-solve actions (ONCE).")

                    if hasattr(self.drone_system, 'add_player_cores'):
                        core_reward = 750
                        self.drone_system.add_player_cores(core_reward)
                        print(f"Awarded {core_reward} cores for solving the Element-115 puzzle.")

                    if hasattr(self.drone_system, 'check_and_unlock_lore_entries'):
                        unlocked_lore_ids = self.drone_system.check_and_unlock_lore_entries(event_trigger="element115_puzzle_solved")
                        if unlocked_lore_ids:
                            first_lore_id = unlocked_lore_ids[0]
                            lore_details = self.drone_system.get_lore_entry_details(first_lore_id)
                            lore_title = lore_details.get("title", "New Data") if lore_details else "New Data"
                            self.set_story_message(f"E-115 Casing Opened: {lore_title} data acquired.")
                            print(f"Unlocked lore: {unlocked_lore_ids}")
                        else:
                            self.set_story_message("Element-115 Casing re-analyzed. No new primary data.")

        elif current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_playing_state(current_time)
        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused:
            self._update_bonus_level_state(current_time)
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state(current_time)
        elif current_game_state in [GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT,
                                    GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX]:
            if hasattr(self, 'menu_stars') and self.menu_stars:
                 for star in self.menu_stars:
                    star[0] -= star[2]
                    if star[0] < 0:
                        star[0] = WIDTH
                        star[1] = random.randint(0, HEIGHT)

        if hasattr(self.scene_manager, 'update'):
            self.scene_manager.update()

    def _update_playing_state(self, current_time):
        if not self.player or not self.maze:
            print("GameController: Error - Player or Maze not initialized for PLAYING state.")
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
        
        if not self.level_cleared_pending_animation:
            elapsed_time_current_level_ms = current_time - self.level_timer_start_ticks
            self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION") - elapsed_time_current_level_ms
            if self.level_time_remaining_ms <= 0:
                self.play_sound('timer_out')
                self._handle_player_death_or_life_loss("Time Ran Out!")
                return
            if self.player.alive:
                self.player.update(current_time, self.maze, self.enemy_manager.get_sprites(), 0)
            else:
                self._handle_player_death_or_life_loss("Drone Destroyed!")
                return

            player_pixel_pos = self.player.get_position() if self.player and self.player.alive else None
            self.enemy_manager.update_all(player_pixel_pos, self.maze, current_time, 0)
            self.explosion_particles.update()
            self.alien_terminals_group.update()

            self.rings.update()
            self.vault_logs.update()
            self.glyph_tablets.update()
            for p_up in list(self.power_ups):
                if p_up.update(): p_up.kill()
            for fragment in list(self.core_fragments):
                fragment.update()
            self._check_collisions_playing()
            if random.random() < (gs.get_game_setting("POWERUP_SPAWN_CHANCE") / gs.get_game_setting("FPS")):
                 if len(self.power_ups) < gs.get_game_setting("MAX_POWERUPS_ON_SCREEN"):
                    self._try_spawn_powerup_item()
            
            # Check for conditional fragment spawn after all updates and collisions
            if not self.level_clear_fragment_spawned_this_level and \
               self.collected_rings >= self.total_rings_per_level and \
               self.all_enemies_killed_this_level:
                if self._attempt_level_clear_fragment_spawn():
                    self.level_clear_fragment_spawned_this_level = True


        for ring_anim in list(self.animating_rings):
            dx = ring_anim['target_pos'][0] - ring_anim['pos'][0]
            dy = ring_anim['target_pos'][1] - ring_anim['pos'][1]
            dist = math.hypot(dx,dy)
            if dist < ring_anim['speed']:
                self.animating_rings.remove(ring_anim)
                self.displayed_collected_rings += 1
                self.displayed_collected_rings = min(self.displayed_collected_rings, self.collected_rings)
            else:
                ring_anim['pos'][0] += (dx / dist) * ring_anim['speed']
                ring_anim['pos'][1] += (dy / dist) * ring_anim['speed']

        for frag_anim in list(self.animating_fragments):
            dx = frag_anim['target_pos'][0] - frag_anim['pos'][0]
            dy = frag_anim['target_pos'][1] - frag_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < frag_anim['speed']:
                self.animating_fragments.remove(frag_anim)
                if 'id' in frag_anim:
                    self.hud_displayed_fragments.add(frag_anim['id'])
            else:
                frag_anim['pos'][0] += (dx / dist) * frag_anim['speed']
                frag_anim['pos'][1] += (dy / dist) * frag_anim['speed']

        if self.level_cleared_pending_animation and not self.animating_rings and not self.animating_fragments:
            self._prepare_for_next_level()
            self.level_cleared_pending_animation = False

    def _update_bonus_level_state(self, current_time):
        if not self.player or not self.player.alive:
            self._end_bonus_level(completed=False)
            return
        self.player.update(current_time, self.maze, None, 0)
        elapsed_bonus_time = current_time - self.bonus_level_timer_start
        self.level_time_remaining_ms = max(0, self.bonus_level_duration_ms - elapsed_bonus_time)
        if self.level_time_remaining_ms <= 0:
            self._end_bonus_level(completed=True)
            return
        self.explosion_particles.update()

    def _update_architect_vault_state(self, current_time):
        if not self.player or not self.maze:
            print("GameController: Error - Player or Maze not initialized for ARCHITECT_VAULT state.")
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
        if not self.player.alive:
            self.architect_vault_failure_reason = "Drone critically damaged."
            if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
            return
        if self.paused: return

        self.player.update(current_time, self.maze, self.enemy_manager.get_sprites(), 0)
        self.explosion_particles.update()
        if self.escape_zone_group: self.escape_zone_group.update()

        current_phase = self.architect_vault_current_phase
        player_pixel_pos = self.player.get_position() if self.player and self.player.alive else None

        if current_phase == "intro":
            pass
        elif current_phase == "entry_puzzle":
            if hasattr(self.architect_vault_terminals, 'update'):
                self.architect_vault_terminals.update()
            self._check_collisions_architect_vault_puzzle()
        elif current_phase == "gauntlet_intro":
            if current_time > self.architect_vault_message_timer:
                self.architect_vault_gauntlet_current_wave = 1
                self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                self.enemy_manager.spawn_prototype_drones(ARCHITECT_VAULT_DRONES_PER_WAVE[0])
                self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif current_phase and current_phase.startswith("gauntlet_wave"):
            self.enemy_manager.update_all(player_pixel_pos, self.maze, current_time, 0)
            self._check_collisions_architect_vault_combat()

            if self.enemy_manager.get_active_enemies_count() == 0:
                self.play_sound('level_up')
                self.architect_vault_gauntlet_current_wave += 1
                if self.architect_vault_gauntlet_current_wave > ARCHITECT_VAULT_GAUNTLET_WAVES:
                    print("GameController: All gauntlet waves cleared. Spawning MAZE_GUARDIAN.")
                    self.architect_vault_message = "MAZE GUARDIAN DETECTED. PREPARE FOR ENGAGEMENT!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                    self.play_sound('boss_intro', 0.8)
                    self._spawn_maze_guardian()
                    self.architect_vault_current_phase = "architect_vault_boss_fight"
                else:
                    self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                    num_drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[self.architect_vault_gauntlet_current_wave - 1]
                    self.enemy_manager.spawn_prototype_drones(num_drones_this_wave)
                    self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 2000

        elif current_phase == "architect_vault_boss_fight":
            if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
                self.maze_guardian.update(player_pixel_pos, self.maze, current_time, 0)
                self.enemy_manager.update_all(player_pixel_pos, self.maze, current_time, 0) # Update any remaining minions
                self._check_collisions_architect_vault_combat()
            elif self.boss_active and self.maze_guardian and not self.maze_guardian.alive: # Boss defeated
                if self.architect_vault_message == "MAZE GUARDIAN DEFEATED! ACCESS GRANTED!": # Check if message is set
                    if current_time > self.architect_vault_message_timer: # Wait for message to display
                        self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
                        self.boss_active = False
                        if self.maze_guardian: self.maze_guardian.kill(); self.maze_guardian = None
            elif not self.boss_active and not self.maze_guardian: # Should not happen if boss was spawned
                 pass # Or handle error

        elif current_phase == "gauntlet_cleared_transition": # This state might be redundant if boss fight follows directly
            if current_time - self.architect_vault_phase_timer_start > 2000: # Short delay
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif current_phase == "extraction":
            time_elapsed_extraction = current_time - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - time_elapsed_extraction)

            if self.escape_zone and self.player and self.player.rect.colliderect(self.escape_zone.rect):
                print("DEBUG: Player reached escape zone!")
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS)
                return

            if self.level_time_remaining_ms <= 0:
                print("DEBUG: Extraction timer ran out before reaching escape zone!")
                self.architect_vault_failure_reason = "Extraction Failed: Time Expired."
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
                return

            if random.random() < 0.008 : # Chance to spawn more enemies during extraction
                 if self.enemy_manager.get_active_enemies_count() < 3: # Limit max enemies
                     self.enemy_manager.spawn_prototype_drones(1, far_from_player=True)

            self.enemy_manager.update_all(player_pixel_pos, self.maze, current_time, 0)
            self._check_collisions_architect_vault_combat()

    def _check_collisions_playing(self):
        if not self.player or not self.player.alive: return

        if self.alien_terminals_group:
            collided_terminal = pygame.sprite.spritecollideany(self.player, self.alien_terminals_group)
            if collided_terminal and isinstance(collided_terminal, AncientAlienTerminal):
                if not collided_terminal.interacted:
                    self.last_interacted_terminal = collided_terminal
                    if collided_terminal.interact(self):
                        return # Interaction might change game state, so return early

        if not self.level_cleared_pending_animation:
            collided_rings_sprites = pygame.sprite.spritecollide(self.player, self.rings, True, pygame.sprite.collide_rect_ratio(0.7))
            for ring_sprite in collided_rings_sprites:
                self.score += 10
                self.play_sound('collect_ring')
                self.collected_rings += 1
                self.drone_system.add_player_cores(5)
                anim_ring_surf = None
                if hasattr(ring_sprite, 'image') and self.ui_manager.ui_assets.get("ring_icon"):
                    try:
                        anim_ring_surf = pygame.transform.smoothscale(self.ui_manager.ui_assets["ring_icon"], (15,15))
                    except Exception as e: print(f"Error scaling ring for anim: {e}")
                if anim_ring_surf:
                    self.animating_rings.append({
                        'pos': list(ring_sprite.rect.center),
                        'target_pos': self.ring_ui_target_pos,
                        'speed': 15, 'surface': anim_ring_surf
                    })
                self._check_level_clear_condition() # Check if level should end or fragment spawn
                if self.level_cleared_pending_animation: break # Stop processing if level is ending

        collided_powerups = pygame.sprite.spritecollide(self.player, self.power_ups, False, pygame.sprite.collide_rect_ratio(0.7))
        for item in collided_powerups:
            if not item.collected and not item.expired and hasattr(item, 'apply_effect'):
                item.apply_effect(self.player)
                item.collected = True; item.kill()
                self.play_sound('weapon_upgrade_collect')
                self.score += 25

        collided_fragments_sprites = pygame.sprite.spritecollide(self.player, self.core_fragments, True, pygame.sprite.collide_rect_ratio(0.7))
        for fragment_sprite in collided_fragments_sprites:
            if hasattr(fragment_sprite, 'apply_effect') and fragment_sprite.apply_effect(self.player, self):
                self.play_sound('collect_fragment')
                self.score += 100
                fragment_id = getattr(fragment_sprite, 'fragment_id', None)

                if fragment_id and self.drone_system:
                    unlocked_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{fragment_id}")
                    if unlocked_lore:
                        self.set_story_message(f"Lore Unlocked: {self.drone_system.get_lore_entry_details(unlocked_lore[0]).get('title', 'New Data')}")

                if fragment_id and hasattr(self.ui_manager, 'get_scaled_fragment_icon'):
                    is_already_animating_or_shown = False
                    if fragment_id in self.hud_displayed_fragments:
                        is_already_animating_or_shown = True
                    for anim in self.animating_fragments:
                        if anim.get('id') == fragment_id:
                            is_already_animating_or_shown = True
                            break
                    if not is_already_animating_or_shown:
                        icon_surface = self.ui_manager.get_scaled_fragment_icon(fragment_id)
                        target_pos = self.fragment_ui_target_positions.get(fragment_id)
                        if icon_surface and target_pos:
                            self.animating_fragments.append({
                                'pos': list(fragment_sprite.rect.center),
                                'target_pos': target_pos,
                                'speed': 12,
                                'surface': icon_surface,
                                'id': fragment_id
                            })
                if self.drone_system.are_all_core_fragments_collected():
                    print("DEBUG: All fragments collected, setting vault message.")
                    self.architect_vault_message = "All Core Fragments Acquired! Vault Access Imminent!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 4000
                
                # After collecting a fragment, check if it was the last objective for level clear
                self._check_level_clear_condition() 


        collided_vault_logs = pygame.sprite.spritecollide(self.player, self.vault_logs, True, pygame.sprite.collide_rect_ratio(0.7))
        for log_item in collided_vault_logs:
            if hasattr(log_item, 'apply_effect') and log_item.apply_effect(self.player, self):
                self.play_sound('collect_log')
                self.score += 50
                log_id = getattr(log_item, 'log_id', None)
                if log_id and self.drone_system:
                    unlocked_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_log_{log_id}")
                    if unlocked_lore:
                        first_unlocked_id = unlocked_lore[0]
                        lore_details = self.drone_system.get_lore_entry_details(first_unlocked_id)
                        log_title = lore_details.get("title", "Vault Log") if lore_details else "Vault Log"
                        self.set_story_message(f"Data Acquired: {log_title}")
                        print(f"GameController: Vault Log '{log_id}' collected, unlocked lore: {unlocked_lore}")
                    else:
                         print(f"GameController: Vault Log '{log_id}' collected, but no new lore unlocked by this trigger (already unlocked or misconfigured).")

        collided_glyph_tablets = pygame.sprite.spritecollide(self.player, self.glyph_tablets, True, pygame.sprite.collide_rect_ratio(0.7))
        for tablet_item in collided_glyph_tablets:
            if hasattr(tablet_item, 'apply_effect') and tablet_item.apply_effect(self.player, self):
                self.play_sound('collect_log')
                self.score += 75
                tablet_id = getattr(tablet_item, 'tablet_id', None)
                if tablet_id and self.drone_system:
                    unlocked_specific_tablet_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_glyph_tablet_{tablet_id}")
                    self.drone_system.add_collected_glyph_tablet(tablet_id)
                    all_tablets_lore_check = self.drone_system.check_and_unlock_lore_entries()
                    message_to_show = ""
                    if unlocked_specific_tablet_lore:
                        first_unlocked_id = unlocked_specific_tablet_lore[0]
                        lore_details = self.drone_system.get_lore_entry_details(first_unlocked_id)
                        tablet_title = lore_details.get("title", f"Glyph Tablet ({tablet_id.capitalize()})") if lore_details else f"Glyph Tablet ({tablet_id.capitalize()})"
                        message_to_show = f"Artifact Found: {tablet_title}"
                        print(f"GameController: Glyph Tablet '{tablet_id}' collected, unlocked specific lore: {unlocked_specific_tablet_lore}")

                    if "race_nordics" in all_tablets_lore_check:
                        nordic_lore_details = self.drone_system.get_lore_entry_details("race_nordics")
                        nordic_title = nordic_lore_details.get("title", "NORDIC Preservers") if nordic_lore_details else "NORDIC Preservers"
                        message_to_show = f"All Glyphs Collected! Lore Unlocked: {nordic_title}"
                        print(f"GameController: All Glyph Tablets collected! Unlocked: {nordic_title}")

                    if message_to_show:
                        self.set_story_message(message_to_show)
                    elif not unlocked_specific_tablet_lore:
                        print(f"GameController: Glyph Tablet '{tablet_id}' collected, but no new lore unlocked (already unlocked or misconfigured).")

        if self.player.alive:
            player_projectiles = pygame.sprite.Group()
            player_projectiles.add(self.player.bullets_group, self.player.missiles_group, self.player.lightning_zaps_group)

            enemies_to_check = self.enemy_manager.get_sprites()
            for projectile in list(player_projectiles):
                if not projectile.alive: continue

                if isinstance(projectile, LightningZap):
                    if not projectile.damage_applied:
                        hit_enemies_lightning = pygame.sprite.spritecollide(projectile, enemies_to_check, False, pygame.sprite.collide_rect_ratio(0.8))
                        if hit_enemies_lightning:
                            for enemy_hit in hit_enemies_lightning:
                                if hasattr(enemy_hit, 'alive') and enemy_hit.alive:
                                    enemy_hit.take_damage(projectile.damage)
                            projectile.damage_applied = True
                else:
                    hit_enemies = pygame.sprite.spritecollide(projectile, enemies_to_check, False,
                                                              lambda proj, enemy_hit: proj.rect.colliderect(enemy_hit.collision_rect))
                    for enemy_obj in hit_enemies:
                        if enemy_obj.alive:
                            enemy_obj.take_damage(projectile.damage)
                            if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                                projectile.pierces_done += 1
                            else:
                                projectile.alive = False; projectile.kill()
                            if not enemy_obj.alive:
                                self.score += 50
                                self.drone_system.add_player_cores(25)
                                self.all_enemies_killed_this_level = all(not e.alive for e in enemies_to_check)
                                if self.all_enemies_killed_this_level:
                                    self._check_level_clear_condition() # Check if level should end or fragment spawn
                            if not projectile.alive: break

        for enemy_obj in self.enemy_manager.get_sprites():
            if hasattr(enemy_obj, 'bullets') and enemy_obj.bullets:
                for bullet_obj in list(enemy_obj.bullets):
                    if self.player.alive and bullet_obj.rect.colliderect(self.player.collision_rect):
                        self.player.take_damage(gs.get_game_setting("ENEMY_BULLET_DAMAGE"), self.sounds.get('crash'))
                        bullet_obj.alive = False; bullet_obj.kill()

        if self.player.alive:
            enemy_physical_collisions = pygame.sprite.spritecollide(self.player, self.enemy_manager.get_sprites(), False,
                                                                    lambda drone, enemy: drone.collision_rect.colliderect(enemy.collision_rect))
            for enemy_obj in enemy_physical_collisions:
                if enemy_obj.alive:
                    self.player.take_damage(34, self.sounds.get('crash'))
                if not self.player.alive: break

    def _check_collisions_architect_vault_puzzle(self):
        if not self.player or not self.player.alive or not self.architect_vault_terminals:
            return

    def _check_collisions_architect_vault_combat(self):
        if not self.player or not self.player.alive: return
        player_projectiles = pygame.sprite.Group(self.player.bullets_group, self.player.missiles_group, self.player.lightning_zaps_group)

        all_targets_for_player_projectiles = pygame.sprite.Group()
        all_targets_for_player_projectiles.add(self.enemy_manager.get_sprites())
        if self.boss_active and self.maze_guardian and self.maze_guardian.alive:
            all_targets_for_player_projectiles.add(self.maze_guardian)

        for projectile in list(player_projectiles):
            if not projectile.alive: continue

            if isinstance(projectile, LightningZap):
                if not projectile.damage_applied:
                    hit_targets_lightning = pygame.sprite.spritecollide(projectile, all_targets_for_player_projectiles, False, pygame.sprite.collide_rect_ratio(0.8))
                    if hit_targets_lightning:
                        for target_hit in hit_targets_lightning:
                            if target_hit.alive:
                                target_hit.take_damage(projectile.damage)
                                if target_hit is self.maze_guardian:
                                    self.play_sound('boss_hit')
                        projectile.damage_applied = True
            else:
                hit_targets = pygame.sprite.spritecollide(projectile, all_targets_for_player_projectiles, False,
                                                          lambda proj, target_hit: proj.rect.colliderect(target_hit.collision_rect))
                for target_obj in hit_targets:
                    if target_obj.alive:
                        target_obj.take_damage(projectile.damage)
                        if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                            projectile.pierces_done += 1
                        else:
                            projectile.alive = False; projectile.kill()

                        if not target_obj.alive:
                            if target_obj is self.maze_guardian:
                                self.score += 1000
                                self.drone_system.add_player_cores(1000)
                            elif isinstance(target_obj, SentinelDrone):
                                self.score += 75
                                self.drone_system.add_player_cores(10)
                            else:
                                self.score += 75
                                self.drone_system.add_player_cores(10)

                        if not projectile.alive: break

        all_enemy_projectiles = pygame.sprite.Group()
        for enemy_obj in self.enemy_manager.get_sprites():
            if hasattr(enemy_obj, 'bullets') and enemy_obj.bullets:
                all_enemy_projectiles.add(enemy_obj.bullets)
        if self.boss_active and self.maze_guardian and hasattr(self.maze_guardian, 'bullets') and self.maze_guardian.bullets:
            all_enemy_projectiles.add(self.maze_guardian.bullets)
        if self.boss_active and self.maze_guardian and hasattr(self.maze_guardian, 'laser_beams') and self.maze_guardian.laser_beams:
            all_enemy_projectiles.add(self.maze_guardian.laser_beams)

        for projectile_obj in list(all_enemy_projectiles):
            if self.player.alive and projectile_obj.rect.colliderect(self.player.collision_rect):
                if isinstance(projectile_obj, LightningZap):
                    self.player.take_damage(gs.get_game_setting("MAZE_GUARDIAN_LASER_DAMAGE"), self.sounds.get('crash'))
                else:
                    self.player.take_damage(gs.get_game_setting("ENEMY_BULLET_DAMAGE") * 1.2, self.sounds.get('crash'))

                if not isinstance(projectile_obj, LightningZap):
                    projectile_obj.alive = False; projectile_obj.kill()

        if self.player.alive:
            physical_collisions = pygame.sprite.spritecollide(self.player, all_targets_for_player_projectiles, False,
                                                              lambda drone, enemy: drone.collision_rect.colliderect(enemy.collision_rect))
            for entity_obj in physical_collisions:
                if entity_obj.alive:
                    if entity_obj is self.maze_guardian:
                        self.player.take_damage(gs.get_game_setting("MAZE_GUARDIAN_LASER_DAMAGE") * 1.5, self.sounds.get('crash'))
                    else:
                        self.player.take_damage(40, self.sounds.get('crash'))
                if not self.player.alive: break

    def _handle_player_death_or_life_loss(self, reason=""):
        if self.player: self.player.reset_active_powerups()
        self.lives -= 1
        if self.lives <= 0:
            if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
            self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
        else:
            self._reset_player_after_death_internal()
            self._reset_level_timer_internal()

    def _check_level_clear_condition(self):
        # This method is called when a ring is collected OR when the last enemy is killed.
        # It now also attempts to spawn a fragment if conditions are met.
        if self.player and \
           self.collected_rings >= self.total_rings_per_level and \
           self.all_enemies_killed_this_level and \
           not self.level_cleared_pending_animation:
            
            # Attempt to spawn a fragment if this level is a reward level and fragment not yet spawned/collected
            if not self.level_clear_fragment_spawned_this_level:
                if self._attempt_level_clear_fragment_spawn():
                    self.level_clear_fragment_spawned_this_level = True
                    # Fragment spawned. Level should not end yet. Player needs to collect it.
                    return 

            # If no fragment was due or it was already spawned/collected, proceed with level clear animation.
            self.player.moving_forward = False
            self.level_cleared_pending_animation = True
            print("Level clear condition met (rings & enemies). Pending animation.")


    def _attempt_level_clear_fragment_spawn(self):
        """
        Checks if the current level is a reward level for a core fragment
        and spawns it if conditions are met (all rings collected, all enemies killed,
        fragment not yet collected or already present).
        Returns True if a fragment was spawned, False otherwise.
        """
        fragment_id_to_spawn = None
        fragment_details_to_spawn = None

        # Determine which fragment (if any) is associated with the current level
        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details.get("reward_level") == self.level:
                fragment_id_to_spawn = details.get("id")
                fragment_details_to_spawn = details
                break
        
        if fragment_id_to_spawn and fragment_details_to_spawn:
            # Check if fragment already collected or already spawned on this level
            if not self.drone_system.has_collected_fragment(fragment_id_to_spawn) and \
               not any(getattr(frag, 'fragment_id', None) == fragment_id_to_spawn for frag in self.core_fragments):
                
                spawn_pos = self._get_random_valid_fragment_tile_internal(set())
                if spawn_pos:
                    tile_c_rel, tile_r_rel = spawn_pos
                    abs_x = tile_c_rel * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = tile_r_rel * TILE_SIZE + TILE_SIZE // 2
                    
                    self.core_fragments.add(CoreFragmentItem(abs_x, abs_y, fragment_id_to_spawn, fragment_details_to_spawn))
                    print(f"GameController: Spawned reward fragment '{fragment_id_to_spawn}' on level {self.level} clear.")
                    self.play_sound('collect_fragment', 0.8) 
                    return True 
        return False 

    def _prepare_for_next_level(self, from_bonus_level_completion=False):
        print(f"DEBUG PREPARE_LEVEL: Called. from_bonus: {from_bonus_level_completion}, Current Lvl: {self.level}, Rings: {self.collected_rings}/{self.total_rings_per_level}, Vault Completed: {self.drone_system.has_completed_architect_vault()}, Fragments: {self.drone_system.get_collected_fragments_ids()} (Need {gs.TOTAL_CORE_FRAGMENTS_NEEDED})")
        self.explosion_particles.empty()
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.level_clear_fragment_spawned_this_level = False # Reset for next level

        if self.player and not self.player.alive and self.lives > 0:
            print("GameController: Player won the level but was destroyed. Reviving for next level transition.")
            self.player.health = self.player.max_health
            self.player.alive = True

        all_fragments_collected = self.drone_system.are_all_core_fragments_collected()
        vault_not_completed_yet = not self.drone_system.has_completed_architect_vault()

        should_trigger_vault = (
            not from_bonus_level_completion and
            all_fragments_collected and
            vault_not_completed_yet and
            (not self.boss_active or (self.boss_active and self.maze_guardian and not self.maze_guardian.alive)) and
            not self.scene_manager.get_current_state().startswith("architect_vault")
        )
        print(f"DEBUG PREPARE_LEVEL: Should trigger vault? {should_trigger_vault}")

        if should_trigger_vault:
            print("GameController: Conditions met for Architect's Vault. Setting state to GAME_STATE_ARCHITECT_VAULT_INTRO")
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_INTRO)
            return

        if not from_bonus_level_completion:
            self.level += 1
            print(f"DEBUG: Incremented level to: {self.level}")
        else:
            print(f"DEBUG: Returning to level {self.level} after bonus level.")

        self.collected_rings = 0
        self.displayed_collected_rings = 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15)
        self.drone_system.set_player_level(self.level)

        if self.level == 7 and "story_beat_SB03" not in self.triggered_story_beats:
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB03")
            self.trigger_story_beat("story_beat_SB03")

        if self.level == 10 and self.drone_system.has_completed_architect_vault() and "story_beat_SB04" not in self.triggered_story_beats:
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB04")
            self.trigger_story_beat("story_beat_SB04")
            print("GameController: Sentinel Protocol (SB04) would activate now - Spawning Sentinel-X (placeholder).")

        if self.player:
            self.player.health = min(self.player.health + 25, self.player.max_health)
            new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            current_drone_id = self.player.drone_id
            current_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False)
            current_drone_config = self.drone_system.get_drone_config(current_drone_id)
            current_ingame_sprite = current_drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1],
                              drone_id=current_drone_id, drone_stats=current_drone_stats,
                              drone_sprite_path=current_ingame_sprite,
                              preserve_weapon=True)

        self.all_enemies_killed_this_level = False
        self.maze = Maze(game_area_x_offset=0, maze_type="standard")
        self.enemy_manager.spawn_enemies_for_level(self.level)
        self.core_fragments.empty() # Clear any previously spawned fragments
        self.vault_logs.empty()
        self.glyph_tablets.empty()
        self.alien_terminals_group.empty()
        self._place_collectibles_for_level(initial_setup=True) # This will call _spawn_core_fragments_for_level_internal
        self._reset_level_timer_internal()
        self.play_sound('level_up')
        self.animating_rings.clear()
        self.animating_fragments.clear()
        if self.player: self.player.moving_forward = False

        print(f"DEBUG: Setting game state to PLAYING for level {self.level}")
        self.scene_manager.set_game_state(GAME_STATE_PLAYING)

    def _reset_player_after_death_internal(self):
        if not self.player: return
        self.explosion_particles.empty()
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.level_clear_fragment_spawned_this_level = False # Reset on death too

        new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        current_drone_id = self.player.drone_id

        is_currently_in_vault_state = self.scene_manager.get_current_state().startswith("architect_vault")

        current_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=is_currently_in_vault_state)

        current_drone_config = self.drone_system.get_drone_config(current_drone_id)
        current_ingame_sprite = current_drone_config.get("ingame_sprite_path")

        self.player.reset(new_player_pos[0], new_player_pos[1],
                          drone_id=current_drone_id, drone_stats=current_drone_stats,
                          drone_sprite_path=current_ingame_sprite,
                          health_override=self.player.max_health,
                          preserve_weapon=False)

        if is_currently_in_vault_state and self.architect_vault_current_phase in ["gauntlet_wave", "architect_vault_boss_fight", "extraction"]:
            self.enemy_manager.reset_all()
            if self.maze_guardian:
                self.maze_guardian.kill()
                self.maze_guardian = None
            self.boss_active = False
            self.architect_vault_failure_reason = "Drone destroyed mid-mission."
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE)
            return

        self.animating_rings.clear()
        self.animating_fragments.clear()
        self.level_cleared_pending_animation = False

    def _reset_level_timer_internal(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level(self, completed=True):
        print(f"GameController: Bonus Level Ended. Completed: {completed}")
        self.explosion_particles.empty()
        if self.escape_zone: self.escape_zone.kill(); self.escape_zone = None
        self.level_clear_fragment_spawned_this_level = False # Reset after bonus
        if completed:
            self.score += 500
            self.drone_system.add_player_cores(250)
        self.drone_system._save_unlocks()
        self._prepare_for_next_level(from_bonus_level_completion=True)

    def _get_safe_spawn_point(self, entity_width, entity_height):
        if not self.maze:
            print("GameController: Warning - Attempted to get spawn point without a maze.")
            return (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative:
            print("GameController: Warning - No path cells found in maze for spawning.")
            return (self.maze.game_area_x_offset + TILE_SIZE//2, TILE_SIZE//2)
        random.shuffle(path_cells_relative)
        for spawn_x_rel, spawn_y_rel in path_cells_relative:
            abs_x = spawn_x_rel + self.maze.game_area_x_offset
            abs_y = spawn_y_rel

            if self.player and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 4:
                continue

            if any(math.hypot(abs_x - e.x, abs_y - e.y) < TILE_SIZE * 2 for e in self.enemy_manager.get_sprites()):
                continue

            if self.escape_zone and math.hypot(abs_x - self.escape_zone.rect.centerx, abs_y - self.escape_zone.rect.centery) < TILE_SIZE * 3 :
                continue

            if any(math.hypot(abs_x - term.rect.centerx, abs_y - term.rect.centery) < TILE_SIZE * 1.5 for term in self.alien_terminals_group):
                continue
            
            # Check against already spawned core fragments as well
            if any(math.hypot(abs_x - frag.rect.centerx, abs_y - frag.rect.centery) < TILE_SIZE * 1.5 for frag in self.core_fragments):
                continue


            if not self.maze.is_wall(abs_x, abs_y, entity_width, entity_height):
                return (abs_x, abs_y)

        print("GameController: Warning - Could not find a 'perfectly safe' spawn point. Using first available path cell.")
        if not path_cells_relative:
             return (self.maze.game_area_x_offset + TILE_SIZE // 2, TILE_SIZE // 2)
        first_rel_x, first_rel_y = random.choice(path_cells_relative)
        return (first_rel_x + self.maze.game_area_x_offset, first_rel_y)

    def _spawn_maze_guardian(self):
        self.enemy_manager.reset_all()
        boss_spawn_x = WIDTH // 2
        boss_spawn_y = GAME_PLAY_AREA_HEIGHT // 2

        self.maze_guardian = MazeGuardian(
            x=boss_spawn_x,
            y=boss_spawn_y,
            player_ref=self.player,
            maze_ref=self.maze,
            game_controller_ref=self
        )
        self.boss_active = True
        print("MAZE_GUARDIAN spawned!")

    def _maze_guardian_defeated(self):
        print("DEBUG: _maze_guardian_defeated called.")
        if self.maze_guardian:
            self.maze_guardian.alive = False

        self.enemy_manager.reset_all()

        self.score += 5000
        self.drone_system.add_player_cores(1500)
        self.drone_system.add_defeated_boss("MAZE_GUARDIAN")

        self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB01")
        self.trigger_story_beat("story_beat_SB01")

        vault_core_id = "vault_core"
        vault_core_details = CORE_FRAGMENT_DETAILS.get("fragment_vault_core")
        if vault_core_details:
            if self.drone_system.collect_core_fragment(vault_core_id):
                if hasattr(self.ui_manager, 'get_scaled_fragment_icon') and vault_core_id in self.ui_manager.ui_assets["core_fragment_icons"]:
                    icon_surface = self.ui_manager.ui_assets["core_fragment_icons"][vault_core_id]
                    target_pos = self.fragment_ui_target_positions.get(vault_core_id)
                    if target_pos:
                        self.animating_fragments.append({
                            'pos': list(self.player.rect.center),
                            'target_pos': target_pos,
                            'speed': 15,
                            'surface': icon_surface,
                            'id': vault_core_id
                        })

        self.architect_vault_message = "MAZE GUARDIAN DEFEATED! ACCESS GRANTED!"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 4000
        print(f"DEBUG: Maze Guardian defeated message set. Timer ends at: {self.architect_vault_message_timer}")

    def _spawn_architect_vault_terminals(self):
        self.architect_vault_terminals.empty()
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        path_cells_relative = self.maze.get_path_cells()
        if len(path_cells_relative) < TOTAL_CORE_FRAGMENTS_NEEDED:
            print("GameController: Warning - Not enough path cells to spawn all vault terminals.")
            return

        # Filter for fragments that are part of the entry puzzle (alpha, beta, gamma)
        # This relies on them NOT having a "reward_level" or having a specific flag if needed.
        # For now, assuming alpha, beta, gamma are the ones for the puzzle.
        puzzle_fragment_keys = [
            k for k, v in CORE_FRAGMENT_DETAILS.items() 
            if v.get("id") in ["cf_alpha", "cf_beta", "cf_gamma"]
        ]
        # Ensure a consistent order for terminal_id mapping if needed, though direct ID matching is better.
        # Here, we'll just use the order they appear in CORE_FRAGMENT_DETAILS if filtered.
        
        num_terminals_to_spawn = TOTAL_CORE_FRAGMENTS_NEEDED # Should be 3

        if len(path_cells_relative) < num_terminals_to_spawn:
            print(f"GameController: Warning - Not enough path cells ({len(path_cells_relative)}) to spawn {num_terminals_to_spawn} vault terminals.")
            num_terminals_to_spawn = len(path_cells_relative) 
            if num_terminals_to_spawn == 0: return

        available_spawn_points_rel = random.sample(path_cells_relative, k=num_terminals_to_spawn)
        
        # We need to map terminal_id (0, 1, 2) to specific fragment_ids (cf_alpha, cf_beta, cf_gamma)
        # Let's assume a fixed mapping for now or use the order from CORE_FRAGMENT_DETAILS
        fragment_ids_for_puzzle_terminals = ["cf_alpha", "cf_beta", "cf_gamma"]


        for i in range(num_terminals_to_spawn):
            pos_rel = available_spawn_points_rel[i]
            abs_x = pos_rel[0] + self.maze.game_area_x_offset
            abs_y = pos_rel[1]
            terminal = pygame.sprite.Sprite()
            terminal.image = pygame.Surface([TILE_SIZE * 0.6, TILE_SIZE * 0.6], pygame.SRCALPHA)
            terminal.image.fill(RED) 
            pygame.draw.rect(terminal.image, GOLD, terminal.image.get_rect(), 2)
            num_font = self.fonts.get("ui_text", pygame.font.Font(None, 24))
            # Displaying 1, 2, 3 on terminals for player clarity
            num_surf = num_font.render(str(i+1), True, WHITE) 
            terminal.image.blit(num_surf, num_surf.get_rect(center=(terminal.image.get_width()//2, terminal.image.get_height()//2)))
            terminal.rect = terminal.image.get_rect(center=(abs_x, abs_y))
            # Store which fragment this terminal corresponds to
            terminal.required_fragment_id = fragment_ids_for_puzzle_terminals[i] 
            terminal.terminal_id_display = i + 1 # For messages
            terminal.is_active = False 
            self.architect_vault_terminals.add(terminal)


    def _try_spawn_powerup_item(self):
        if not self.maze: return
        if not POWERUP_TYPES: return
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return
        existing_coords_abs = set(r.rect.center for r in self.rings)
        for p_up in self.power_ups: existing_coords_abs.add(p_up.rect.center)
        for frag in self.core_fragments: existing_coords_abs.add(frag.rect.center)
        for v_log in self.vault_logs: existing_coords_abs.add(v_log.rect.center)
        for g_tablet in self.glyph_tablets: existing_coords_abs.add(g_tablet.rect.center)
        for term in self.alien_terminals_group : existing_coords_abs.add(term.rect.center)
        available_spawn_cells_abs = []
        for rcx_rel, rcy_rel in path_cells_relative:
            abs_center_x = rcx_rel + self.maze.game_area_x_offset
            abs_center_y = rcy_rel
            if (abs_center_x, abs_center_y) not in existing_coords_abs:
                if self.player and math.hypot(abs_center_x - self.player.x, abs_center_y - self.player.y) < TILE_SIZE * 2:
                    continue
                available_spawn_cells_abs.append((abs_center_x, abs_center_y))
        if not available_spawn_cells_abs: return
        abs_x, abs_y = random.choice(available_spawn_cells_abs)
        powerup_type_keys = list(POWERUP_TYPES.keys())
        if not powerup_type_keys: return
        chosen_type_key = random.choice(powerup_type_keys)
        new_powerup = None
        if chosen_type_key == "weapon_upgrade": new_powerup = WeaponUpgradeItem(abs_x, abs_y)
        elif chosen_type_key == "shield": new_powerup = ShieldItem(abs_x, abs_y)
        elif chosen_type_key == "speed_boost": new_powerup = SpeedBoostItem(abs_x, abs_y)
        if new_powerup:
            self.power_ups.add(new_powerup)

    def _place_collectibles_for_level(self, initial_setup=False):
        if not self.maze: return
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return
        if initial_setup:
            self.rings.empty()
            num_rings_to_place = min(self.total_rings_per_level, len(path_cells_relative))
            if num_rings_to_place > 0:
                ring_spawn_points_rel = random.sample(path_cells_relative, k=num_rings_to_place)
                for rel_x, rel_y in ring_spawn_points_rel:
                    abs_x = rel_x + self.maze.game_area_x_offset
                    abs_y = rel_y
                    self.rings.add(Ring(abs_x, abs_y))

        self._spawn_core_fragments_for_level_internal() 
        self._spawn_lore_collectibles_for_level()

        target_level_for_terminal = 5
        terminal_unique_id = f"level_{target_level_for_terminal}_element115_terminal"

        if self.level == target_level_for_terminal:
            if not self.drone_system.has_puzzle_terminal_been_solved(terminal_unique_id):
                already_spawned = any(getattr(t, 'item_id', '') == terminal_unique_id for t in self.alien_terminals_group)
                if not already_spawned:
                    print(f"GameController: Attempting to spawn Ancient Alien Terminal '{terminal_unique_id}' on level {self.level}")
                    available_path_tiles_for_terminal = [
                        (c_idx, r_idx) for r_idx in range(self.maze.actual_maze_rows)
                        for c_idx in range(self.maze.actual_maze_cols)
                        if self.maze.grid[r_idx][c_idx] == 0
                    ]
                    if available_path_tiles_for_terminal:
                        random.shuffle(available_path_tiles_for_terminal)
                        spawned_terminal = False
                        for _ in range(min(10, len(available_path_tiles_for_terminal))):
                            col, row = available_path_tiles_for_terminal.pop()
                            abs_x = col * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                            abs_y = row * TILE_SIZE + TILE_SIZE // 2

                            too_close_to_player = self.player and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 3
                            too_close_to_other_item = False
                            temp_rect_sprite = pygame.sprite.Sprite()
                            temp_rect_sprite.rect = pygame.Rect(0,0,TILE_SIZE, TILE_SIZE)
                            temp_rect_sprite.rect.center = (abs_x, abs_y)

                            for item_group in [self.rings, self.power_ups, self.core_fragments, self.vault_logs, self.glyph_tablets]:
                                if pygame.sprite.spritecollide(temp_rect_sprite, item_group, False):
                                    too_close_to_other_item = True
                                    break
                            if too_close_to_player or too_close_to_other_item:
                                continue

                            terminal = AncientAlienTerminal(abs_x, abs_y, assets_path="assets/images/world/")
                            terminal.item_id = terminal_unique_id
                            self.alien_terminals_group.add(terminal)
                            print(f"GameController: Spawned Ancient Alien Terminal '{terminal.item_id}' at ({abs_x}, {abs_y}) on level {self.level}")
                            spawned_terminal = True
                            break
                        if not spawned_terminal:
                            print(f"GameController: Could not find suitable distinct spawn for Ancient Alien Terminal on level {self.level}.")
                    else:
                        print(f"GameController: No path cells to spawn Ancient Alien Terminal on level {self.level}.")
            else:
                print(f"GameController: Terminal '{terminal_unique_id}' already solved, not spawning.")
        elif self.alien_terminals_group:
             terminals_to_remove = [t for t in self.alien_terminals_group if getattr(t, 'item_id', '').startswith(f"level_{target_level_for_terminal}_")]
             for t in terminals_to_remove: t.kill()


        if initial_setup:
            self._try_spawn_powerup_item()

    def _spawn_lore_collectibles_for_level(self):
        if not self.maze: return

        log_id_to_spawn = "GRX-23"
        lore_entry_id_for_log = "race_greys"
        # Define the filename for the GRX-23 log icon
        grx23_icon_filename = "vault_log_grx23_icon.png" # Ensure this file exists in assets/images/collectibles/

        if self.level == 2 and not self.drone_system.has_unlocked_lore(lore_entry_id_for_log):
            already_spawned = any(getattr(log, 'log_id', None) == log_id_to_spawn for log in self.vault_logs)
            if not already_spawned:
                spawn_pos = self._get_random_valid_fragment_tile_internal(set())
                if spawn_pos:
                    col, row = spawn_pos
                    abs_x = col * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = row * TILE_SIZE + TILE_SIZE // 2
                    # Pass the icon_filename to VaultLogItem constructor
                    self.vault_logs.add(VaultLogItem(abs_x, abs_y, log_id_to_spawn, icon_filename=grx23_icon_filename))
                    print(f"GameController: Spawned Vault Log '{log_id_to_spawn}' with icon '{grx23_icon_filename}' at ({abs_x}, {abs_y}) on level {self.level}")

        tablet_alpha_id = "alpha"
        lore_for_tablet_alpha = "tech_glyph_tablet_alpha"
        if self.level == 4 and \
           not self.drone_system.has_unlocked_lore(lore_for_tablet_alpha) and \
           tablet_alpha_id not in self.drone_system.get_collected_glyph_tablet_ids():
            already_spawned_alpha = any(getattr(t, 'tablet_id', None) == tablet_alpha_id for t in self.glyph_tablets)
            if not already_spawned_alpha:
                spawn_pos_tablet = self._get_random_valid_fragment_tile_internal(set())
                if spawn_pos_tablet:
                    col, row = spawn_pos_tablet
                    abs_x = col * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = row * TILE_SIZE + TILE_SIZE // 2
                    self.glyph_tablets.add(GlyphTabletItem(abs_x, abs_y, tablet_alpha_id))
                    print(f"GameController: Spawned Glyph Tablet '{tablet_alpha_id}' at ({abs_x}, {abs_y}) on level {self.level}")

        tablet_beta_id = "beta"
        lore_for_tablet_beta = "tech_glyph_tablet_beta"
        if self.level == 6 and \
           not self.drone_system.has_unlocked_lore(lore_for_tablet_beta) and \
           tablet_beta_id not in self.drone_system.get_collected_glyph_tablet_ids():
            already_spawned_beta = any(getattr(t, 'tablet_id', None) == tablet_beta_id for t in self.glyph_tablets)
            if not already_spawned_beta:
                spawn_pos_tablet = self._get_random_valid_fragment_tile_internal(set())
                if spawn_pos_tablet:
                    col, row = spawn_pos_tablet
                    abs_x = col * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = row * TILE_SIZE + TILE_SIZE // 2
                    self.glyph_tablets.add(GlyphTabletItem(abs_x, abs_y, tablet_beta_id))
                    print(f"GameController: Spawned Glyph Tablet '{tablet_beta_id}' at ({abs_x}, {abs_y}) on level {self.level}")

        tablet_gamma_id = "gamma"
        lore_for_tablet_gamma = "tech_glyph_tablet_gamma"
        if self.level == 8 and \
           not self.drone_system.has_unlocked_lore(lore_for_tablet_gamma) and \
           tablet_gamma_id not in self.drone_system.get_collected_glyph_tablet_ids():
            already_spawned_gamma = any(getattr(t, 'tablet_id', None) == tablet_gamma_id for t in self.glyph_tablets)
            if not already_spawned_gamma:
                spawn_pos_tablet = self._get_random_valid_fragment_tile_internal(set())
                if spawn_pos_tablet:
                    col, row = spawn_pos_tablet
                    abs_x = col * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = row * TILE_SIZE + TILE_SIZE // 2
                    self.glyph_tablets.add(GlyphTabletItem(abs_x, abs_y, tablet_gamma_id))
                    print(f"GameController: Spawned Glyph Tablet '{tablet_gamma_id}' at ({abs_x}, {abs_y}) on level {self.level}")

    def _spawn_core_fragments_for_level_internal(self):
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        occupied_fragment_tiles_this_level = set()
        for frag_key, details in CORE_FRAGMENT_DETAILS.items():
            if not details or not isinstance(details, dict): continue
            
            spawn_info = details.get("spawn_info")
            fragment_id = details.get("id")

            if spawn_info and spawn_info.get("level") == self.level and \
               fragment_id and not self.drone_system.has_collected_fragment(fragment_id):
                if details.get("reward_level") is None: 
                    random_tile_coords_rel = self._get_random_valid_fragment_tile_internal(occupied_fragment_tiles_this_level)
                    if random_tile_coords_rel:
                        tile_c_rel, tile_r_rel = random_tile_coords_rel
                        abs_x = tile_c_rel * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                        abs_y = tile_r_rel * TILE_SIZE + TILE_SIZE // 2
                        self.core_fragments.add(CoreFragmentItem(abs_x, abs_y, fragment_id, details))
                        occupied_fragment_tiles_this_level.add(random_tile_coords_rel)
                        print(f"GameController: Spawned standard fragment '{fragment_id}' at start of level {self.level}")


    def _get_random_valid_fragment_tile_internal(self, existing_fragment_tiles_rel):
        if not self.maze or not self.maze.grid: return None
        available_path_tiles_rel = []
        for r_idx in range(self.maze.actual_maze_rows):
            for c_idx in range(self.maze.actual_maze_cols):
                if self.maze.grid[r_idx][c_idx] == 0 and (c_idx, r_idx) not in existing_fragment_tiles_rel:
                    available_path_tiles_rel.append((c_idx, r_idx))
        if not available_path_tiles_rel:
            return None
        return random.choice(available_path_tiles_rel)

    def handle_main_menu_input(self, key_event):
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
                self.scene_manager.set_game_state(GAME_STATE_GAME_INTRO_SCROLL)
            elif action == "Select Drone":
                self.scene_manager.set_game_state(GAME_STATE_DRONE_SELECT)
            elif action == "Codex":
                self.scene_manager.set_game_state(GAME_STATE_CODEX)
            elif action == "Settings":
                self.scene_manager.set_game_state(GAME_STATE_SETTINGS)
            elif action == "Leaderboard":
                self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif action == "Quit":
                self.quit_game()

    def handle_codex_input(self, key_event):
        self.play_sound('ui_select', 0.6)

        if self.codex_current_view == "categories":
            if key_event == pygame.K_UP:
                self.codex_selected_category_index = (self.codex_selected_category_index - 1 + len(self.codex_categories_list)) % len(self.codex_categories_list) if self.codex_categories_list else 0
            elif key_event == pygame.K_DOWN:
                self.codex_selected_category_index = (self.codex_selected_category_index + 1) % len(self.codex_categories_list) if self.codex_categories_list else 0
            elif key_event == pygame.K_RETURN:
                if self.codex_categories_list:
                    self.codex_current_category_name = self.codex_categories_list[self.codex_selected_category_index]
                    self.codex_current_view = "entries"
                    self.codex_selected_entry_index_in_category = 0
                    self.codex_entries_in_category_list = []
                    unlocked_ids = self.drone_system.get_unlocked_lore_ids()
                    all_lore = self.drone_system.get_all_loaded_lore_entries()
                    for entry_id in unlocked_ids:
                        entry_data = all_lore.get(entry_id)
                        if entry_data and entry_data.get("category", "Misc") == self.codex_current_category_name:
                            self.codex_entries_in_category_list.append(entry_data)
                    self.codex_entries_in_category_list.sort(key=lambda e: e.get("title", "Untitled"))
            elif key_event == pygame.K_ESCAPE:
                self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

        elif self.codex_current_view == "entries":
            if key_event == pygame.K_UP:
                self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category - 1 + len(self.codex_entries_in_category_list)) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
            elif key_event == pygame.K_DOWN:
                self.codex_selected_entry_index_in_category = (self.codex_selected_entry_index_in_category + 1) % len(self.codex_entries_in_category_list) if self.codex_entries_in_category_list else 0
            elif key_event == pygame.K_RETURN:
                if self.codex_entries_in_category_list and 0 <= self.codex_selected_entry_index_in_category < len(self.codex_entries_in_category_list):
                    selected_entry_data = self.codex_entries_in_category_list[self.codex_selected_entry_index_in_category]
                    self.codex_selected_entry_id = selected_entry_data.get("id")
                    self.codex_current_view = "content"
                    self.codex_content_scroll_offset = 0
            elif key_event == pygame.K_ESCAPE:
                self.codex_current_view = "categories"
                self.codex_current_category_name = None
                self.codex_selected_entry_id = None
                self.codex_content_scroll_offset = 0

        elif self.codex_current_view == "content":
            if key_event == pygame.K_UP:
                self.codex_content_scroll_offset = max(0, self.codex_content_scroll_offset - 1)
            elif key_event == pygame.K_DOWN:
                if self.codex_current_entry_total_lines > 0:
                    max_scroll = self.codex_current_entry_total_lines - (self.ui_manager.codex_max_visible_lines_content if self.ui_manager.codex_max_visible_lines_content > 0 else 1)
                    max_scroll = max(0, max_scroll)
                    if self.codex_content_scroll_offset < max_scroll:
                        self.codex_content_scroll_offset += 1
                else:
                    self.codex_content_scroll_offset += 1
            elif key_event == pygame.K_ESCAPE:
                self.codex_current_view = "entries"
                self.codex_selected_entry_id = None
                self.codex_content_scroll_offset = 0

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
                if self.drone_system.set_selected_drone_id(selected_id):
                    self.play_sound('ui_confirm')
                    self.ui_manager.update_player_life_icon_surface()
                    self.drone_system.check_and_unlock_lore_entries(event_trigger=f"drone_selected_{selected_id}")
            else:
                unlocked_status, reason = self.drone_system.attempt_unlock_drone_with_cores(selected_id)
                if unlocked_status == True and reason == "unlocked":
                    self.play_sound('ui_confirm')
                    if selected_id == "PHANTOM":
                        self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB02")
                        self.trigger_story_beat("story_beat_SB02")
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
                gs.reset_all_settings_to_default()
                if self.screen_flags != (pygame.FULLSCREEN if gs.get_game_setting("FULLSCREEN_MODE") else 0):
                    self.screen_flags = pygame.FULLSCREEN if gs.get_game_setting("FULLSCREEN_MODE") else 0
                self.play_sound('ui_confirm')
        elif key_event == pygame.K_LEFT or key_event == pygame.K_RIGHT:
            if current_setting_item["type"] != "action":
                self.play_sound('ui_select', 0.7)
                current_val = gs.get_game_setting(setting_key)
                direction = 1 if key_event == pygame.K_RIGHT else -1
                if current_setting_item["type"] == "numeric":
                    step = current_setting_item["step"]
                    new_val = current_val + step * direction
                    new_val = max(current_setting_item["min"], min(current_setting_item["max"], new_val))
                    if isinstance(step, float) or isinstance(current_val, float): new_val = float(new_val)
                    else: new_val = int(new_val)
                    gs.set_game_setting(setting_key, new_val)
                elif current_setting_item["type"] == "choice":
                    choices = current_setting_item.get("choices", [])
                    if choices:
                        try:
                            current_choice_idx = choices.index(current_val)
                            new_choice_idx = (current_choice_idx + direction + len(choices)) % len(choices)
                            gs.set_game_setting(setting_key, choices[new_choice_idx])
                        except ValueError:
                            gs.set_game_setting(setting_key, choices[0])
        elif key_event == pygame.K_ESCAPE:
            self.play_sound('ui_select')
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def handle_pause_menu_input(self, key_event, game_state_when_paused):
        if key_event == pygame.K_l and game_state_when_paused == GAME_STATE_PLAYING:
            self.unpause_and_set_state(GAME_STATE_LEADERBOARD)
        elif key_event == pygame.K_m:
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_event == pygame.K_q:
            self.quit_game()
        elif key_event == pygame.K_ESCAPE and game_state_when_paused.startswith("architect_vault"):
            self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_event == pygame.K_p:
            self.toggle_pause()

    def handle_game_over_input(self, key_event):
        settings_were_modified = gs.SETTINGS_MODIFIED
        can_submit_score = not settings_were_modified
        is_actually_a_new_high_score_and_submittable = can_submit_score and leaderboard.is_high_score(self.score, self.level)

        if is_actually_a_new_high_score_and_submittable:
            if key_event in [pygame.K_r, pygame.K_l, pygame.K_m, pygame.K_q, pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE]: # Any key basically
                self.scene_manager.set_game_state(GAME_STATE_ENTER_NAME)
                return # Consume the event

        if key_event == pygame.K_r:
            self.scene_manager.set_game_state(GAME_STATE_GAME_INTRO_SCROLL)
        elif key_event == pygame.K_l and not is_actually_a_new_high_score_and_submittable :
            self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
        elif key_event == pygame.K_m:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        elif key_event == pygame.K_q:
            self.quit_game()

    def submit_leaderboard_name(self, name_cache_from_event_manager):
        if leaderboard.add_score(name_cache_from_event_manager, self.score, self.level):
            self.play_sound('ui_confirm')
        else:
            self.play_sound('ui_denied')
        self.leaderboard_scores = leaderboard.load_scores()
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)

    def update_player_name_input_display(self, name_cache_from_event_manager):
        self.player_name_input_display_cache = name_cache_from_event_manager

    def try_activate_vault_terminal(self, terminal_idx_pressed):
        if not (0 <= terminal_idx_pressed < len(self.architect_vault_puzzle_terminals_activated)):
            print(f"GameController: Invalid terminal index {terminal_idx_pressed} attempted.")
            return
        target_terminal_sprite = None
        for t_sprite in self.architect_vault_terminals:
            if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx_pressed:
                target_terminal_sprite = t_sprite
                break
        if not target_terminal_sprite or (hasattr(target_terminal_sprite, 'is_active') and target_terminal_sprite.is_active):
            self.play_sound('ui_denied')
            return

        fragment_keys_for_puzzle = [k for k, v in CORE_FRAGMENT_DETAILS.items() if v.get("spawn_info")]
        fragment_keys_for_puzzle.sort() 

        required_fragment_id = None
        required_fragment_name = "a specific Core Fragment"
        if terminal_idx_pressed < len(fragment_keys_for_puzzle):
            frag_details_key = fragment_keys_for_puzzle[terminal_idx_pressed]
            frag_details = CORE_FRAGMENT_DETAILS[frag_details_key]
            if frag_details and "id" in frag_details:
                required_fragment_id = frag_details["id"]
                required_fragment_name = frag_details.get("name", required_fragment_name)

        if required_fragment_id and self.drone_system.has_collected_fragment(required_fragment_id):
            self.architect_vault_puzzle_terminals_activated[terminal_idx_pressed] = True
            if hasattr(target_terminal_sprite, 'is_active'): target_terminal_sprite.is_active = True
            if hasattr(target_terminal_sprite, 'image'): target_terminal_sprite.image.fill(GREEN) 
            self.play_sound('vault_barrier_disable')
            self.architect_vault_message = f"Terminal {terminal_idx_pressed+1} ({required_fragment_name}) activated!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            if all(self.architect_vault_puzzle_terminals_activated):
                self.architect_vault_message = "All terminals active. Lockdown disengaged. Prepare for Gauntlet!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 4000
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        else:
            self.architect_vault_message = f"Terminal {terminal_idx_pressed+1} requires {required_fragment_name}."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            self.play_sound('ui_denied')

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            print("GameController: Game Paused.")
            pygame.mixer.music.pause()
        else:
            print("GameController: Game Resumed.")
            pygame.mixer.music.unpause()
            current_time = pygame.time.get_ticks()
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state == GAME_STATE_PLAYING:
                self.level_timer_start_ticks = current_time - (gs.get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif current_game_state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction":
                 self.architect_vault_phase_timer_start = current_time - (gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - self.level_time_remaining_ms)
            elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING:
                self.bonus_level_timer_start = current_time - (self.bonus_level_duration_ms - self.level_time_remaining_ms)

    def unpause_and_set_state(self, new_state):
        if self.paused: self.toggle_pause()
        self.scene_manager.set_game_state(new_state)

    def quit_game(self):
        print("GameController: Quitting game.")
        if self.drone_system: self.drone_system._save_unlocks()
        pygame.quit()
        sys.exit()

    def _draw_game_world(self):
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state.startswith("architect_vault"):
            self.screen.fill(ARCHITECT_VAULT_BG_COLOR)
            if self.maze: self.maze.draw_architect_vault(self.screen)
        else:
            self.screen.fill(BLACK)
            if self.maze: self.maze.draw(self.screen)

        self.rings.draw(self.screen)
        self.power_ups.draw(self.screen)
        self.core_fragments.draw(self.screen)
        self.vault_logs.draw(self.screen)
        self.glyph_tablets.draw(self.screen)
        self.alien_terminals_group.draw(self.screen)
        self.escape_zone_group.draw(self.screen)

        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_terminals.draw(self.screen)

        if hasattr(self, 'enemy_manager'):
            self.enemy_manager.draw_all(self.screen)

        if self.boss_active and self.maze_guardian:
            self.maze_guardian.draw(self.screen)

        if self.player:
            self.player.draw(self.screen)

        self.explosion_particles.draw(self.screen)

    def run(self):
        current_fullscreen_setting = gs.get_game_setting("FULLSCREEN_MODE")
        required_flags = pygame.FULLSCREEN if current_fullscreen_setting else 0
        if self.screen_flags != required_flags: 
            self.screen_flags = required_flags
            self.screen = pygame.display.set_mode((gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")), self.screen_flags)

        while True:
            self.event_manager.process_events()
            self.update()

            current_game_state = self.scene_manager.get_current_state()

            if current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
                self.ui_manager.draw_game_intro_scroll()
            elif current_game_state == GAME_STATE_RING_PUZZLE:
                if self.ring_puzzle_active_flag and self.current_ring_puzzle:
                    self.screen.fill(gs.DARK_GREY)
                    self.current_ring_puzzle.draw(self.screen)
            elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                 current_game_state.startswith("architect_vault"):
                self._draw_game_world()
                self.ui_manager.draw_current_scene_ui()
            else: 
                self.ui_manager.draw_current_scene_ui()

            pygame.display.flip()
            self.clock.tick(gs.get_game_setting("FPS"))
