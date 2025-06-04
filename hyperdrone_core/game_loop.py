# hyperdrone_core/game_loop.py

import sys
import os
import random
import math
import json

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
    DEFAULT_SETTINGS, get_game_setting, set_game_setting, reset_all_settings_to_default,
    WIDTH, BOTTOM_PANEL_HEIGHT, GAME_PLAY_AREA_HEIGHT, HEIGHT, FPS
)

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
            try: self.fonts[name] = pygame.font.Font(path, size)
            except pygame.error as e: print(f"Font Error: {name}, {e}"); self.fonts[name] = pygame.font.Font(None, size)

    def _get_settings_menu_items_data_structure(self):
        return [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice", "choices":WEAPON_MODES_SEQUENCE, "get_display":lambda val:WEAPON_MODE_NAMES.get(val,"Unknown")},
            {"label":"Missile Damage","key":"MISSILE_DAMAGE","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","type":"numeric","min":0.5,"max":5,"step":0.5},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","type":"numeric","min":25,"max":300,"step":25},
            {"label":"Level Timer (sec)","key":"LEVEL_TIMER_DURATION","type":"numeric","min":60000,"max":300000,"step":15000, "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","type":"numeric","min":5000,"max":60000,"step":5000, "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Speed Boost Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","type":"numeric","min":3000,"max":30000,"step":2000, "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label": "Invincibility", "key": "PLAYER_INVINCIBILITY", "type": "choice", "choices": [False, True], "get_display": lambda val: "ON" if val else "OFF", "note": "Player does not take damage."},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ]

    def _load_intro_data_from_json_internal(self):
        fallback_data = [
            {"text": "The Architect — creator of the Vault\nand all drone intelligence — has vanished.\n\nNo warning. No trace. Only silence.", "image_path": "assets/images/lore/scene1.png"},
            {"text": "In their absence, the Vault has shifted.\n\nIts corridors twisted into cryptic mazes,\nteeming with automated defences.", "image_path": "assets/images/lore/scene2.png"},
            {"text": "You are a pilot. An explorer.\n\nEntering the Vault to unravel the AI’s enigma —\n\nand stop a system-wide fail-safe\nbefore it activates.", "image_path": "assets/images/lore/scene3.png"},
            {"text": "The Architect’s secrets lie ahead.\n\nSolve the puzzles. Survive the machines.\n\nOr be erased with everything else.", "image_path": "assets/images/lore/scene4.png"}
        ]
        intro_file_path = os.path.join("data", "intro.json")
        try:
            if os.path.exists(intro_file_path):
                with open(intro_file_path, 'r') as f: data = json.load(f)
                if isinstance(data, list) and all(isinstance(i, dict) and "text" in i and "image_path" in i for i in data):
                    return data
            return fallback_data
        except Exception: return fallback_data

    def _create_fallback_image_surface(self, size=(200,200), text="?", color=(80,80,80), text_color=WHITE, font_key="large_text"):
        surface = pygame.Surface(size, pygame.SRCALPHA); surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2)
        font_to_use = self.fonts.get(font_key, pygame.font.Font(None, size[1]//2))
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e: print(f"Fallback image render error: {e}")
        return surface

    def _load_drone_main_display_images(self):
        self.drone_main_display_cache = {} 
        display_size = (200, 200)
        for drone_id, data in DRONE_DATA.items():
            image_surface = None; path_to_try = data.get("sprite_path")
            if not path_to_try or not os.path.exists(path_to_try): path_to_try = data.get("icon_path")
            if path_to_try and os.path.exists(path_to_try):
                try:
                    loaded_image = pygame.image.load(path_to_try).convert_alpha()
                    image_surface = pygame.transform.smoothscale(loaded_image, display_size)
                except pygame.error: pass
            if image_surface is None:
                initials = data.get("name", "?")[:2].upper()
                image_surface = self._create_fallback_image_surface(size=display_size, text=initials, font_key="large_text")
            self.drone_main_display_cache[drone_id] = image_surface

    def load_sfx(self):
        sound_files = {
            'collect_ring': "collect_ring.wav", 'weapon_upgrade_collect': "collect_powerup.wav",
            'collect_fragment': "collect_fragment.wav", 'crash': "crash.wav",
            'shoot': "shoot.wav", 'missile_launch': "missile_launch.wav",
            'level_up': "level_up.wav", 'player_death': "player_death.wav",
            'enemy_shoot': "enemy_shoot.wav", 'timer_out': "timer_warning.wav",
            'ui_select': "ui_select.wav", 'ui_confirm': "ui_confirm.wav", 'ui_denied': "ui_denied.wav",
            'cloak_activate': "cloak_on.wav", 'vault_alarm': "vault_alarm.wav",
            'vault_barrier_disable': "vault_barrier_disable.wav",
            'prototype_drone_explode': "prototype_drone_explode.wav",
            'boss_intro': "boss_intro.wav", 'laser_charge': "laser_charge.wav",
            'laser_fire': "laser_fire.wav", 'shield_activate': "shield_activate.wav",
            'minion_spawn': "minion_spawn.wav", 'wall_shift': "wall_shift.wav",
            'boss_hit': "boss_hit.wav", 'boss_death': "boss_death.wav",
            'lore_unlock': "ui_confirm.wav", 'collect_log': "collect_fragment.wav",
            'reactor_hit_placeholder': "enemy_shoot.wav", 'reactor_destroyed_placeholder': "boss_death.wav",
            'turret_place_placeholder': "ui_select.wav", 'turret_shoot_placeholder': "shoot.wav"
        }
        sound_dir = os.path.join("assets", "sounds")
        for name, filename in sound_files.items():
            path = os.path.join(sound_dir, filename)
            if os.path.exists(path):
                try: self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e: print(f"SFX Load Error: {name}, {e}")
            else: print(f"SFX Missing: {path}")
            
    def play_sound(self, name, volume_multiplier=0.7):
        if name in self.sounds and self.sounds[name]:
            effective_volume = volume_multiplier * gs.get_game_setting("SFX_VOLUME_MULTIPLIER", 0.7)
            self.sounds[name].set_volume(effective_volume); self.sounds[name].play()

    def set_story_message(self, message, duration=None):
        self.story_message = message; self.story_message_active = True

    def trigger_story_beat(self, beat_id):
        if beat_id not in self.triggered_story_beats:
            if self.drone_system.has_unlocked_lore(beat_id):
                lore_entry = self.drone_system.get_lore_entry_details(beat_id)
                if lore_entry:
                    self.set_story_message(lore_entry.get("content", f"Event: {lore_entry.get('title', beat_id)}"))
                    self.triggered_story_beats.add(beat_id); self.play_sound('lore_unlock', 0.6)
                    return True
        return False

    def _create_explosion(self, x, y, num_particles=20, specific_sound='prototype_drone_explode'):
        colors = [ORANGE, YELLOW, RED, DARK_RED, GREY]
        for _ in range(num_particles):
            particle = Particle(x, y, colors, 1, 4, 2, 5, 0.05, 0.1, random.randint(20,40))
            self.explosion_particles_group.add(particle)
        if specific_sound: self.play_sound(specific_sound)

    def handle_scene_transition(self, new_state, old_state, **kwargs):
        print(f"GameController: Handling scene transition from '{old_state}' to '{new_state}'")
        pygame.mouse.set_visible(False) 

        if new_state == GAME_STATE_MAIN_MENU:
            self.ui_flow_controller.initialize_main_menu()
        elif new_state == GAME_STATE_GAME_INTRO_SCROLL:
            self.ui_flow_controller.initialize_game_intro(self._load_intro_data_from_json_internal())
            self._prepare_current_intro_screen_surfaces() 
        elif new_state == GAME_STATE_PLAYING:
            if old_state == GAME_STATE_GAME_INTRO_SCROLL or old_state == GAME_STATE_MAIN_MENU:
                 self.initialize_specific_game_mode("standard_play")
        elif new_state == GAME_STATE_DRONE_SELECT:
            self.ui_flow_controller.initialize_drone_select()
            if self.player and self.ui_manager: self.ui_manager.update_player_life_icon_surface()
        elif new_state == GAME_STATE_SETTINGS:
            self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure())
        elif new_state == GAME_STATE_LEADERBOARD:
            self.ui_flow_controller.initialize_leaderboard()
        elif new_state == GAME_STATE_CODEX:
            self.ui_flow_controller.initialize_codex()
        elif new_state == GAME_STATE_GAME_OVER:
            self.handle_game_over_scene_entry() 
        elif new_state == GAME_STATE_ENTER_NAME:
            self.ui_flow_controller.initialize_enter_name()
        elif new_state == GAME_STATE_MAZE_DEFENSE:
            self.initialize_specific_game_mode("maze_defense")
            pygame.mouse.set_visible(True) 
        elif new_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            self.initialize_specific_game_mode("architect_vault_entry") 
        elif new_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.initialize_architect_vault_session_phases("entry_puzzle")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET:
            self.initialize_architect_vault_session_phases("gauntlet_intro")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT:
            self.initialize_architect_vault_session_phases("architect_vault_boss_fight")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION:
            self.initialize_architect_vault_session_phases("extraction")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS:
            self.handle_architect_vault_success_scene() 
        elif new_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            self.handle_architect_vault_failure_scene() 
        elif new_state == GAME_STATE_RING_PUZZLE:
            triggering_terminal = kwargs.get('triggering_terminal')
            if triggering_terminal and self.puzzle_controller:
                self.puzzle_controller.start_ring_puzzle(triggering_terminal)
            else: 
                print("GameController: Warning - Could not start ring puzzle. Missing terminal or puzzle controller.")
                self.scene_manager.set_game_state(GAME_STATE_PLAYING if old_state != GAME_STATE_MAIN_MENU else GAME_STATE_MAIN_MENU) 
        elif new_state == GAME_STATE_BONUS_LEVEL_START:
            self.bonus_level_start_display_end_time = pygame.time.get_ticks() + 2000 
            self.combat_controller.enemy_manager.reset_all() 
            self.collectible_rings_group.empty() 
            self._place_collectibles_for_bonus_level()
            self._reset_level_timer_internal() 
            self.level_time_remaining_ms = self.bonus_level_duration_ms 
            self.bonus_level_timer_start = pygame.time.get_ticks()

    def _prepare_current_intro_screen_surfaces(self):
        ui_flow_ctrl = self.ui_flow_controller
        # Ensure intro_screens_data is populated in ui_flow_ctrl before this is called
        if not ui_flow_ctrl.intro_screens_data or ui_flow_ctrl.current_intro_screen_index >= len(ui_flow_ctrl.intro_screens_data):
            ui_flow_ctrl.intro_sequence_finished = True # Mark finished if no data or index out of bounds
            self.current_intro_image_surface = None
            self.intro_screen_text_surfaces_current = []
            return

        if ui_flow_ctrl.intro_sequence_finished: # If already marked finished by UIFlowController
            self.current_intro_image_surface = None
            self.intro_screen_text_surfaces_current = []
            return
            
        screen_data = ui_flow_ctrl.intro_screens_data[ui_flow_ctrl.current_intro_screen_index]
        text_content = screen_data["text"]; image_path = screen_data["image_path"]
        
        # Load/cache image
        if image_path not in self.ui_manager.codex_image_cache:
            if os.path.exists(image_path):
                try: self.ui_manager.codex_image_cache[image_path] = pygame.image.load(image_path).convert_alpha()
                except pygame.error: self.ui_manager.codex_image_cache[image_path] = None
            else: self.ui_manager.codex_image_cache[image_path] = None
        self.current_intro_image_surface = self.ui_manager.codex_image_cache.get(image_path)

        # Render text surfaces
        self.intro_screen_text_surfaces_current = []
        font = self.fonts.get(self.intro_font_key, pygame.font.Font(None, 36))
        raw_lines = text_content.split('\n')
        for raw_line in raw_lines:
            if not raw_line.strip(): self.intro_screen_text_surfaces_current.append(font.render(" ", True, GOLD))
            else: self.intro_screen_text_surfaces_current.append(font.render(raw_line, True, GOLD))

    def initialize_specific_game_mode(self, mode_type="standard_play"):
        print(f"GameController: Initializing game mode: {mode_type}. Current state before init: {self.scene_manager.get_current_state()}") 
        pygame.mouse.set_visible(False); self.paused = False
        
        self.collectible_rings_group.empty(); self.power_ups_group.empty(); self.core_fragments_group.empty()
        self.vault_logs_group.empty(); self.glyph_tablets_group.empty(); self.architect_echoes_group.empty()
        self.alien_terminals_group.empty(); self.architect_vault_puzzle_terminals_group.empty()
        self.explosion_particles_group.empty(); self.escape_zone_group.empty()
        self.reactor_group.empty(); self.turrets_group.empty()

        self.combat_controller.reset_combat_state()
        self.puzzle_controller.reset_puzzles_state()
        
        self.score = 0; self.lives = gs.get_game_setting("PLAYER_LIVES")
        if mode_type == "standard_play": self.level = 1 
        self.drone_system.set_player_level(self.level) 
        self.triggered_story_beats.clear()
        self.level_cleared_pending_animation = False; self.all_enemies_killed_this_level = False
        self.level_clear_fragment_spawned_this_level = False
        self.animating_rings_to_hud.clear(); self.animating_fragments_to_hud.clear()

        target_scene_state_after_init = None

        if mode_type == "standard_play":
            self.drone_system.reset_collected_fragments_in_storage()
            self.drone_system.reset_architect_vault_status()
            if hasattr(self.drone_system, 'unlock_data'):
                self.drone_system.unlock_data["collected_glyph_tablet_ids"] = []
                self.drone_system.unlock_data["solved_puzzle_terminals"] = []
            self.drone_system._save_unlocks()

            self.maze = Maze(game_area_x_offset=0, maze_type="standard")
            player_start_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            self._create_or_reset_player(player_start_pos, is_vault=False)
            
            self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
            self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
            
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, alien_terminals_group=self.alien_terminals_group)

            self._place_collectibles_for_level(initial_setup=True)
            self._reset_level_timer_internal()
            target_scene_state_after_init = GAME_STATE_PLAYING

        elif mode_type == "maze_defense":
            self.maze = MazeChapter2(game_area_x_offset=0, maze_type="chapter2_tilemap")
            self.player = None 
            reactor_spawn_pos = self.maze.get_core_reactor_spawn_position_abs()
            core_reactor_entity = None
            if reactor_spawn_pos:
                reactor_health = gs.get_game_setting("DEFENSE_REACTOR_HEALTH", 1000)
                core_reactor_entity = CoreReactor(reactor_spawn_pos[0], reactor_spawn_pos[1], health=reactor_health)
                self.reactor_group.add(core_reactor_entity)
            else: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return

            self.combat_controller.set_active_entities(
                player=None, maze=self.maze, core_reactor=core_reactor_entity, 
                turrets_group=self.turrets_group, explosion_particles_group=self.explosion_particles_group
            )
            self.combat_controller.wave_manager.start_first_build_phase()
            if self.ui_manager.build_menu: self.ui_manager.build_menu.activate()
            target_scene_state_after_init = GAME_STATE_MAZE_DEFENSE

        elif mode_type == "architect_vault_entry":
            self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault")
            player_start_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
            self._create_or_reset_player(player_start_pos, is_vault=True)
            
            self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(
                player=self.player, drone_system=self.drone_system, scene_manager=self.scene_manager,
                architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group
            )
            # This will call initialize_architect_vault_session_phases("intro") via handle_scene_transition
            target_scene_state_after_init = GAME_STATE_ARCHITECT_VAULT_INTRO 
        
        if target_scene_state_after_init and self.scene_manager.get_current_state() != target_scene_state_after_init:
            print(f"GameController: initialize_specific_game_mode for '{mode_type}' is now setting state to '{target_scene_state_after_init}'")
            self.scene_manager.set_game_state(target_scene_state_after_init)
        elif not target_scene_state_after_init:
             print(f"Warning: Unknown mode_type '{mode_type}' in initialize_specific_game_mode, state not set.")


    def _create_or_reset_player(self, position, is_vault=False, preserve_weapon_on_reset=False):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=is_vault)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_sprite_path = drone_config.get("ingame_sprite_path")
        if self.player is None:
            self.player = PlayerDrone(position[0], position[1], drone_id=selected_drone_id, drone_stats=effective_stats,
                                      drone_sprite_path=player_sprite_path, crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        else:
            self.player.reset(position[0], position[1], drone_id=selected_drone_id, drone_stats=effective_stats,
                              drone_sprite_path=player_sprite_path, preserve_weapon=preserve_weapon_on_reset)
        if self.ui_manager: self.ui_manager.update_player_life_icon_surface()
        if self.combat_controller: self.combat_controller.player = self.player
        if self.puzzle_controller: self.puzzle_controller.player = self.player

    def initialize_architect_vault_session_phases(self, phase):
        self.architect_vault_current_phase = phase
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
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
            try: wave_num = int(wave_num_str)
            except ValueError: wave_num = 1 
            self.combat_controller.architect_vault_gauntlet_current_wave = wave_num
            num_drones_this_wave = gs.ARCHITECT_VAULT_DRONES_PER_WAVE[wave_num -1] if wave_num-1 < len(gs.ARCHITECT_VAULT_DRONES_PER_WAVE) else gs.ARCHITECT_VAULT_DRONES_PER_WAVE[-1]
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
            self._spawn_escape_zone(); self.level_time_remaining_ms = gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS")
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        
        self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
        self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group)

    def handle_architect_vault_success_scene(self):
        self.ui_flow_controller.initialize_architect_vault_result_screen(success=True)
        if self.drone_system:
            self.drone_system.mark_architect_vault_completed(True)
            self.score += 2500; self.drone_system.add_player_cores(500)
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB05")
            self.trigger_story_beat("story_beat_SB05")
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.set_story_message("Architect's Vault conquered! Entering defensive perimeter...", 5000)
        self.initialize_specific_game_mode("maze_defense") 

    def handle_architect_vault_failure_scene(self):
        self.ui_flow_controller.initialize_architect_vault_result_screen(success=False, failure_reason=self.architect_vault_failure_reason)
        self.drone_system.mark_architect_vault_completed(False)
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()

    def handle_game_over_scene_entry(self):
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.drone_system.set_player_level(self.level); self.drone_system._save_unlocks()

    def handle_maze_defense_victory(self):
        self.set_story_message("CORE REACTOR SECURED! ALL WAVES DEFEATED!", 10000)
        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) 

    def update(self, delta_time_ms):
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_game_state)

        # Continuously prepare intro screen surfaces if in that state and not finished
        if current_game_state == GAME_STATE_GAME_INTRO_SCROLL and not self.ui_flow_controller.intro_sequence_finished:
            self._prepare_current_intro_screen_surfaces()

        if current_game_state == GAME_STATE_RING_PUZZLE:
            self.puzzle_controller.update(current_time_ms, current_game_state)
        elif current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_standard_playing_state(current_time_ms, delta_time_ms)
        elif current_game_state == GAME_STATE_MAZE_DEFENSE and not self.paused:
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.player and self.player.alive: self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused:
            self._update_bonus_level_state(current_time_ms)
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state_machine(current_time_ms, delta_time_ms)
            if self.player and self.player.alive: self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
        
        self._update_hud_animations()
        if self.scene_manager: self.scene_manager.update()

    def _update_standard_playing_state(self, current_time_ms, delta_time_ms):
        if not self.player or not self.maze: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
        if not self.level_cleared_pending_animation:
            elapsed_time_current_level_ms = current_time_ms - self.level_timer_start_ticks
            self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION") - elapsed_time_current_level_ms
            if self.level_time_remaining_ms <= 0:
                self.play_sound('timer_out'); self._handle_player_death_or_life_loss("Time Ran Out!"); return
            if self.player.alive:
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
            else: self._handle_player_death_or_life_loss("Drone Destroyed!"); return
            
            self.combat_controller.update(current_time_ms, delta_time_ms) 

            self.collectible_rings_group.update(); self.core_fragments_group.update()
            self.vault_logs_group.update(); self.glyph_tablets_group.update()
            self.architect_echoes_group.update(); self.alien_terminals_group.update()
            self._handle_collectible_collisions()
            if not self.level_clear_fragment_spawned_this_level and \
               self.collected_rings_count >= self.total_rings_per_level and \
               self.all_enemies_killed_this_level: 
                if self._attempt_level_clear_fragment_spawn(): self.level_clear_fragment_spawned_this_level = True
        if self.level_cleared_pending_animation and not self.animating_rings_to_hud and not self.animating_fragments_to_hud:
            self._prepare_for_next_level(); self.level_cleared_pending_animation = False

    def _update_architect_vault_state_machine(self, current_time_ms, delta_time_ms):
        if not self.player or not self.maze: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
        if not self.player.alive:
            self.architect_vault_failure_reason = "Drone critically damaged."
            if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
        
        current_phase = self.architect_vault_current_phase
        if current_phase == "intro":
            if current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        elif current_phase == "entry_puzzle":
            if all(self.puzzle_controller.architect_vault_terminals_activated):
                 if current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        elif current_phase == "gauntlet_intro":
            if current_time_ms > self.architect_vault_message_timer: self.initialize_architect_vault_session_phases(f"gauntlet_wave_1")
        elif current_phase and current_phase.startswith("gauntlet_wave"):
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
                current_wave_num = self.combat_controller.architect_vault_gauntlet_current_wave
                if current_wave_num >= gs.ARCHITECT_VAULT_GAUNTLET_WAVES: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT)
                else:
                    next_wave_num = current_wave_num + 1
                    self.initialize_architect_vault_session_phases(f"gauntlet_wave_{next_wave_num}")
        elif current_phase == "architect_vault_boss_fight":
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if not self.combat_controller.boss_active and self.combat_controller.maze_guardian_defeat_processed:
                if current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif current_phase == "extraction":
            self.combat_controller.update(current_time_ms, delta_time_ms) 
            time_elapsed_extraction = current_time_ms - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - time_elapsed_extraction)
            if self.escape_zone_group.sprite and self.player.rect.colliderect(self.escape_zone_group.sprite.rect):
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS); return
            if self.level_time_remaining_ms <= 0:
                self.architect_vault_failure_reason = "Extraction Failed: Time Expired."
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
            if random.random() < 0.008 : 
                 if self.combat_controller.enemy_manager.get_active_enemies_count() < 3: 
                     self.combat_controller.enemy_manager.spawn_prototype_drones(1)

    def _update_bonus_level_state(self, current_time_ms):
        if not self.player or not self.player.alive: self._end_bonus_level(completed=False); return
        self.player.update(current_time_ms, self.maze, None, self.maze.game_area_x_offset if self.maze else 0)
        elapsed_bonus_time = current_time_ms - self.bonus_level_timer_start
        self.level_time_remaining_ms = max(0, self.bonus_level_duration_ms - elapsed_bonus_time)
        if self.level_time_remaining_ms <= 0: self._end_bonus_level(completed=True); return
        self.explosion_particles_group.update()

    def _update_hud_animations(self):
        for ring_anim in list(self.animating_rings_to_hud):
            dx = ring_anim['target_pos'][0] - ring_anim['pos'][0]; dy = ring_anim['target_pos'][1] - ring_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < ring_anim['speed']:
                self.animating_rings_to_hud.remove(ring_anim); self.displayed_collected_rings_count += 1
                self.displayed_collected_rings_count = min(self.displayed_collected_rings_count, self.collected_rings_count)
            else: ring_anim['pos'][0] += (dx / dist) * ring_anim['speed']; ring_anim['pos'][1] += (dy / dist) * ring_anim['speed']
        for frag_anim in list(self.animating_fragments_to_hud):
            dx = frag_anim['target_pos'][0] - frag_anim['pos'][0]; dy = frag_anim['target_pos'][1] - frag_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < frag_anim['speed']:
                self.animating_fragments_to_hud.remove(frag_anim)
                if 'id' in frag_anim: self.hud_displayed_fragments.add(frag_anim['id'])
            else: frag_anim['pos'][0] += (dx / dist) * frag_anim['speed']; frag_anim['pos'][1] += (dy / dist) * frag_anim['speed']

    def _handle_collectible_collisions(self):
        if not self.player or not self.player.alive: return
        collided_rings = pygame.sprite.spritecollide(self.player, self.collectible_rings_group, True, pygame.sprite.collide_rect_ratio(0.7))
        for ring_sprite in collided_rings:
            self.score += 10; self.play_sound('collect_ring'); self.collected_rings_count += 1
            self.drone_system.add_player_cores(5)
            anim_surf = None
            if hasattr(ring_sprite, 'image') and self.ui_manager.ui_assets.get("ring_icon"):
                try: anim_surf = pygame.transform.smoothscale(self.ui_manager.ui_assets["ring_icon"], (15,15))
                except Exception: pass
            if anim_surf: self.animating_rings_to_hud.append({'pos': list(ring_sprite.rect.center), 'target_pos': self.ring_ui_target_pos, 'speed': 15, 'surface': anim_surf})
            self._check_level_clear_condition();
            if self.level_cleared_pending_animation: break
        collided_fragments = pygame.sprite.spritecollide(self.player, self.core_fragments_group, True, pygame.sprite.collide_rect_ratio(0.7))
        for frag_sprite in collided_fragments:
            if hasattr(frag_sprite, 'apply_effect') and frag_sprite.apply_effect(self.player, self):
                self.play_sound('collect_fragment'); self.score += 100
                frag_id = getattr(frag_sprite, 'fragment_id', None)
                if frag_id and self.drone_system:
                    unlocked_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{frag_id}")
                    if unlocked_lore: self.set_story_message(f"Lore: {self.drone_system.get_lore_entry_details(unlocked_lore[0]).get('title', 'New Data')}")
                if frag_id and hasattr(self.ui_manager, 'get_scaled_fragment_icon'):
                    is_animating = any(anim.get('id') == frag_id for anim in self.animating_fragments_to_hud)
                    if frag_id not in self.hud_displayed_fragments and not is_animating:
                        icon_surf = self.ui_manager.get_scaled_fragment_icon(frag_id); target_pos = self.fragment_ui_target_positions.get(frag_id)
                        if icon_surf and target_pos: self.animating_fragments_to_hud.append({'pos': list(frag_sprite.rect.center), 'target_pos': target_pos, 'speed': 12, 'surface': icon_surf, 'id': frag_id})
                if self.drone_system and self.drone_system.are_all_core_fragments_collected():
                    self.architect_vault_message = "All Core Fragments Acquired! Vault Access Imminent!"; self.architect_vault_message_timer = pygame.time.get_ticks() + 4000
                self._check_level_clear_condition()
        for item_group, sound_name, score_val, lore_prefix in [(self.vault_logs_group, 'collect_log', 50, "collect_log_"), (self.glyph_tablets_group, 'collect_log', 75, "collect_glyph_tablet_"), (self.architect_echoes_group, 'collect_fragment', 150, "collect_echo_")]:
            collided_items = pygame.sprite.spritecollide(self.player, item_group, True, pygame.sprite.collide_rect_ratio(0.7))
            for item in collided_items:
                item_id_attr = 'log_id' if item_group == self.vault_logs_group else 'tablet_id' if item_group == self.glyph_tablets_group else 'echo_id' if item_group == self.architect_echoes_group else None
                item_id_val = getattr(item, item_id_attr, None)
                if hasattr(item, 'apply_effect') and item.apply_effect(self.player, self):
                    self.play_sound(sound_name); self.score += score_val
                    if item_group == self.glyph_tablets_group and item_id_val:
                        self.drone_system.add_collected_glyph_tablet(item_id_val)
                        all_tablets_lore_check = self.drone_system.check_and_unlock_lore_entries()
                        if "race_nordics" in all_tablets_lore_check:
                             nordic_lore_details = self.drone_system.get_lore_entry_details("race_nordics")
                             nordic_title = nordic_lore_details.get("title", "NORDIC Preservers") if nordic_lore_details else "NORDIC Preservers"
                             self.set_story_message(f"All Glyphs Collected! Lore Unlocked: {nordic_title}")
        collided_alien_terminal = pygame.sprite.spritecollideany(self.player, self.alien_terminals_group)
        if collided_alien_terminal and isinstance(collided_alien_terminal, AncientAlienTerminal):
            if not collided_alien_terminal.interacted:
                self.scene_manager.set_game_state(GAME_STATE_RING_PUZZLE, triggering_terminal=collided_alien_terminal)

    def _handle_player_death_or_life_loss(self, reason=""):
        if self.player: self.player.reset_active_powerups()
        self.lives -= 1
        if self.lives <= 0:
            if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
            self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
        else:
            if self.player: self._reset_player_after_death_internal()
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state == GAME_STATE_PLAYING or \
               (current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and self.player):
                self._reset_level_timer_internal()

    def _check_level_clear_condition(self):
        if self.player and self.collected_rings_count >= self.total_rings_per_level and \
           self.all_enemies_killed_this_level and not self.level_cleared_pending_animation:
            if not self.level_clear_fragment_spawned_this_level:
                if self._attempt_level_clear_fragment_spawn(): self.level_clear_fragment_spawned_this_level = True; return
            if self.player: self.player.moving_forward = False
            self.level_cleared_pending_animation = True

    def _attempt_level_clear_fragment_spawn(self):
        fragment_id_to_spawn = None; fragment_details_to_spawn = None
        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details.get("reward_level") == self.level:
                fragment_id_to_spawn = details.get("id"); fragment_details_to_spawn = details; break
        if fragment_id_to_spawn and fragment_details_to_spawn:
            if self.drone_system and not self.drone_system.has_collected_fragment(fragment_id_to_spawn) and \
               not any(getattr(frag, 'fragment_id', None) == fragment_id_to_spawn for frag in self.core_fragments_group):
                spawn_pos = self._get_safe_spawn_point(TILE_SIZE, TILE_SIZE)
                if spawn_pos:
                    self.core_fragments_group.add(CoreFragmentItem(spawn_pos[0], spawn_pos[1], fragment_id_to_spawn, fragment_details_to_spawn))
                    self.play_sound('collect_fragment', 0.8); return True
        return False

    def _prepare_for_next_level(self, from_bonus_level_completion=False):
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.level_clear_fragment_spawned_this_level = False
        if self.player and not self.player.alive and self.lives > 0:
            self.player.health = self.player.max_health; self.player.alive = True
        all_frags_collected = self.drone_system.are_all_core_fragments_collected() if self.drone_system else False
        vault_not_done = not self.drone_system.has_completed_architect_vault() if self.drone_system else True
        if not from_bonus_level_completion and all_frags_collected and vault_not_done and \
           not self.scene_manager.get_current_state().startswith("architect_vault"):
            self.initialize_specific_game_mode("architect_vault_entry"); return
        if not from_bonus_level_completion: self.level += 1
        self.collected_rings_count = 0; self.displayed_collected_rings_count = 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15)
        if self.drone_system: self.drone_system.set_player_level(self.level)
        if self.level == 7 and "story_beat_SB03" not in self.triggered_story_beats: 
            if self.drone_system: self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB03")
            self.trigger_story_beat("story_beat_SB03")
        if self.level == 10 and self.drone_system and self.drone_system.has_completed_architect_vault() and \
           "story_beat_SB04" not in self.triggered_story_beats:
            self.drone_system.check_and_unlock_lore_entries(event_trigger="story_beat_trigger_SB04")
            self.trigger_story_beat("story_beat_SB04")
        new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        self._create_or_reset_player(new_player_pos, is_vault=False, preserve_weapon_on_reset=True)
        self.all_enemies_killed_this_level = False
        self.maze = Maze(game_area_x_offset=0, maze_type="standard")
        self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
        self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
        self.core_fragments_group.empty(); self.vault_logs_group.empty(); self.glyph_tablets_group.empty()
        self.alien_terminals_group.empty(); self.architect_echoes_group.empty()
        self._place_collectibles_for_level(initial_setup=True)
        self._reset_level_timer_internal(); self.play_sound('level_up')
        self.animating_rings_to_hud.clear(); self.animating_fragments_to_hud.clear()
        if self.player: self.player.moving_forward = False
        self.scene_manager.set_game_state(GAME_STATE_PLAYING)

    def _reset_player_after_death_internal(self):
        if not self.player: return
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.level_clear_fragment_spawned_this_level = False
        new_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        is_vault = self.scene_manager.get_current_state().startswith("architect_vault")
        self._create_or_reset_player(new_pos, is_vault=is_vault, preserve_weapon_on_reset=False)
        if is_vault and self.architect_vault_current_phase not in ["intro", "entry_puzzle"]:
            self.architect_vault_failure_reason = "Drone destroyed mid-mission."
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
        self.animating_rings_to_hud.clear(); self.animating_fragments_to_hud.clear()
        self.level_cleared_pending_animation = False

    def _reset_level_timer_internal(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level(self, completed=True):
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.level_clear_fragment_spawned_this_level = False
        if completed: self.score += 500;
        if self.drone_system: self.drone_system.add_player_cores(250); self.drone_system._save_unlocks()
        self._prepare_for_next_level(from_bonus_level_completion=True)

    def _get_safe_spawn_point(self, entity_width, entity_height):
        if not self.maze: return (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)
        path_cells_abs = []
        if hasattr(self.maze, 'get_path_cells_abs'): path_cells_abs = self.maze.get_path_cells_abs()
        elif hasattr(self.maze, 'get_path_cells'):
            path_cells_rel = self.maze.get_path_cells()
            path_cells_abs = [(x + self.maze.game_area_x_offset, y) for x,y in path_cells_rel]
        if not path_cells_abs: return (getattr(self.maze, 'game_area_x_offset', 0) + TILE_SIZE//2, TILE_SIZE//2)
        random.shuffle(path_cells_abs)
        for abs_x, abs_y in path_cells_abs:
            if self.player and hasattr(self.player, 'x') and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 4: continue
            if not self.maze.is_wall(abs_x, abs_y, entity_width, entity_height): return (abs_x, abs_y)
        return path_cells_abs[0] if path_cells_abs else (getattr(self.maze, 'game_area_x_offset', 0) + TILE_SIZE // 2, TILE_SIZE // 2)

    def _spawn_architect_vault_puzzle_terminals(self):
        self.architect_vault_puzzle_terminals_group.empty()
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        path_cells_abs = self.maze.get_path_cells_abs() if hasattr(self.maze, 'get_path_cells_abs') else []
        frag_ids_for_terminals = ["cf_alpha", "cf_beta", "cf_gamma"]
        num_to_spawn = len(frag_ids_for_terminals)
        if len(path_cells_abs) < num_to_spawn: num_to_spawn = len(path_cells_abs)
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

    def _spawn_escape_zone(self):
        if self.maze and self.player:
            spawn_pos = self._get_safe_spawn_point(TILE_SIZE * 1.5, TILE_SIZE * 1.5)
            if spawn_pos: self.escape_zone_group.add(EscapeZone(spawn_pos[0], spawn_pos[1]))

    def _place_collectibles_for_level(self, initial_setup=False):
        if not self.maze or not self.player: return
        path_cells_abs = self.maze.get_path_cells_abs() if hasattr(self.maze, 'get_path_cells_abs') else []
        if not path_cells_abs: return
        if initial_setup:
            self.collectible_rings_group.empty()
            num_rings = min(self.total_rings_per_level, len(path_cells_abs))
            if num_rings > 0:
                ring_spawns = random.sample(path_cells_abs, k=num_rings)
                for x,y in ring_spawns: self.collectible_rings_group.add(CollectibleRing(x,y))
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
                if spawn_pos: self.vault_logs_group.add(VaultLogItem(spawn_pos[0], spawn_pos[1], "GRX-23", "vault_log_grx23_icon.png")); occupied_tiles.add(spawn_pos)
        terminal_id = f"level_5_element115_terminal"
        if self.level == 5 and self.drone_system and not self.drone_system.has_puzzle_terminal_been_solved(terminal_id):
            if not any(getattr(t, 'item_id', '') == terminal_id for t in self.alien_terminals_group):
                spawn_pos = self._get_random_valid_collectible_spawn_abs(path_cells_abs, occupied_tiles, min_dist_player=TILE_SIZE*3)
                if spawn_pos:
                    term = AncientAlienTerminal(spawn_pos[0], spawn_pos[1]); term.item_id = terminal_id
                    self.alien_terminals_group.add(term); occupied_tiles.add(spawn_pos)

    def _place_collectibles_for_bonus_level(self):
        """Spawns collectibles for the bonus level."""
        print("GameController: Placing collectibles for Bonus Level.")
        if not self.maze or not self.player:
            print("GameController: Cannot place bonus collectibles - maze or player missing.")
            return

        path_cells_abs = []
        if hasattr(self.maze, 'get_path_cells_abs'):
            path_cells_abs = self.maze.get_path_cells_abs()
        elif hasattr(self.maze, 'get_path_cells'): 
            path_cells_rel = self.maze.get_path_cells()
            path_cells_abs = [(x + self.maze.game_area_x_offset, y) for x,y in path_cells_rel]

        if not path_cells_abs:
            print("GameController: No path cells to spawn bonus rings.")
            return
        
        self.collectible_rings_group.empty() # Clear existing rings before spawning new ones
        num_bonus_rings = gs.get_game_setting("BONUS_LEVEL_NUM_RINGS", 50) # Get from settings
        
        if len(path_cells_abs) < num_bonus_rings:
            num_bonus_rings = len(path_cells_abs) 
        
        if num_bonus_rings > 0:
            ring_spawn_points_abs = random.sample(path_cells_abs, k=num_bonus_rings)
            for x,y in ring_spawn_points_abs:
                self.collectible_rings_group.add(CollectibleRing(x,y))
        print(f"GameController: Spawned {num_bonus_rings} rings for bonus level.")
        
        # Optionally spawn other bonus items like temporary score multipliers or power-ups
        # For example, spawn a few weapon upgrade items
        # num_bonus_powerups = 3
        # if len(path_cells_abs) > num_bonus_rings + num_bonus_powerups: # Ensure enough unique spots
        #     available_spots_for_powerups = [cell for cell in path_cells_abs if cell not in ring_spawn_points_abs]
        #     if len(available_spots_for_powerups) >= num_bonus_powerups:
        #         powerup_spawns = random.sample(available_spots_for_powerups, k=num_bonus_powerups)
        #         for x,y in powerup_spawns:
        #             self.power_ups_group.add(WeaponUpgradeItem(x,y)) # Example
        #         print(f"GameController: Spawned {num_bonus_powerups} power-ups for bonus level.")


    def _get_random_valid_collectible_spawn_abs(self, available_path_cells_abs, occupied_coords_abs, min_dist_player=TILE_SIZE*2):
        if not available_path_cells_abs: return None
        potential_spawns = [
            cell for cell in available_path_cells_abs 
            if cell not in occupied_coords_abs and 
               (not self.player or math.hypot(cell[0] - self.player.x, cell[1] - self.player.y) > min_dist_player)
        ]
        return random.choice(potential_spawns) if potential_spawns else None

    def submit_leaderboard_name(self, name_from_ui_flow):
        if leaderboard.add_score(name_from_ui_flow, self.score, self.level): self.play_sound('ui_confirm')
        else: self.play_sound('ui_denied')
        self.ui_flow_controller.leaderboard_scores = leaderboard.load_scores()
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD) 

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused: pygame.mixer.music.pause()
        else: 
            pygame.mixer.music.unpause()
            current_time = pygame.time.get_ticks(); current_state = self.scene_manager.get_current_state()
            if current_state == GAME_STATE_PLAYING: self.level_timer_start_ticks = current_time - (gs.get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif current_state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction": self.architect_vault_phase_timer_start = current_time - (gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - self.level_time_remaining_ms)
            elif current_state == GAME_STATE_BONUS_LEVEL_PLAYING: self.bonus_level_timer_start = current_time - (self.bonus_level_duration_ms - self.level_time_remaining_ms)

    def unpause_and_set_state(self, new_state):
        if self.paused: self.toggle_pause()
        self.scene_manager.set_game_state(new_state) 

    def quit_game(self):
        if self.drone_system: self.drone_system._save_unlocks()
        pygame.quit(); sys.exit()

    def _draw_game_world(self):
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state.startswith("architect_vault"): self.screen.fill(ARCHITECT_VAULT_BG_COLOR)
        elif current_game_state == GAME_STATE_MAZE_DEFENSE: self.screen.fill(gs.DARK_GREY)
        else: self.screen.fill(BLACK)
        if self.maze: self.maze.draw(self.screen)
        if current_game_state != GAME_STATE_MAZE_DEFENSE:
            self.collectible_rings_group.draw(self.screen); self.core_fragments_group.draw(self.screen)
            self.vault_logs_group.draw(self.screen); self.glyph_tablets_group.draw(self.screen)
            self.architect_echoes_group.draw(self.screen); self.alien_terminals_group.draw(self.screen)
        self.power_ups_group.draw(self.screen); self.escape_zone_group.draw(self.screen)
        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: self.architect_vault_puzzle_terminals_group.draw(self.screen)
        if current_game_state == GAME_STATE_MAZE_DEFENSE:
            self.reactor_group.draw(self.screen); self.turrets_group.draw(self.screen)
            if self.player and self.player.alive: self.player.draw(self.screen)
        if self.combat_controller and self.combat_controller.enemy_manager: self.combat_controller.enemy_manager.draw_all(self.screen)
        if self.combat_controller and self.combat_controller.boss_active and self.combat_controller.maze_guardian: self.combat_controller.maze_guardian.draw(self.screen)
        if self.player and current_game_state != GAME_STATE_MAZE_DEFENSE:
             if self.player.alive or self.player.bullets_group or self.player.missiles_group or self.player.lightning_zaps_group: self.player.draw(self.screen)
        self.explosion_particles_group.draw(self.screen)

    def is_current_score_a_high_score(self): 
        return leaderboard.is_high_score(self.score, self.level)

    def check_and_apply_screen_settings_change(self):
        current_fullscreen_setting = gs.get_game_setting("FULLSCREEN_MODE")
        required_flags = pygame.FULLSCREEN if current_fullscreen_setting else 0
        if self.screen_flags != required_flags:
            print("GameController: Screen mode changed, reinitializing display.")
            self.screen_flags = required_flags
            current_w = gs.get_game_setting("WIDTH"); current_h = gs.get_game_setting("HEIGHT")
            self.screen = pygame.display.set_mode((current_w, current_h), self.screen_flags)

    def run(self):
        self.check_and_apply_screen_settings_change() 
        while True:
            delta_time_ms = self.clock.tick(FPS)
            self.event_manager.process_events()
            self.update(delta_time_ms)
            current_game_state = self.scene_manager.get_current_state()

            if current_game_state == GAME_STATE_GAME_INTRO_SCROLL:
                self.ui_manager.draw_current_scene_ui()
            elif current_game_state == GAME_STATE_RING_PUZZLE:
                self.screen.fill(gs.DARK_GREY)
                self.puzzle_controller.draw_active_puzzle(self.screen)
            elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE] or \
                 current_game_state.startswith("architect_vault"):
                self._draw_game_world()
                self.ui_manager.draw_current_scene_ui()
            else: 
                self.ui_manager.draw_current_scene_ui()
            pygame.display.flip()

