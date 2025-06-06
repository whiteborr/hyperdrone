# hyperdrone_core/game_loop.py
import sys
import os
import random
import math
import json
import logging

import pygame

from .scene_manager import SceneManager
from .event_manager import EventManager
from .player_actions import PlayerActions
from . import leaderboard
from .combat_controller import CombatController
from .puzzle_controller import PuzzleController
from .ui_flow_controller import UIFlowController
from ui import UIManager
from .asset_manager import AssetManager

from entities import (
    PlayerDrone, Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    CoreFragmentItem, VaultLogItem, GlyphTabletItem, AncientAlienTerminal,
    ArchitectEchoItem, CoreReactor, Turret, LightningZap, Missile, Particle,
    MazeGuardian, SentinelDrone, EscapeZone, Maze, MazeChapter2, Bullet
)
from drone_management import DroneSystem, DRONE_DATA
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

logger_gc = logging.getLogger(__name__)

if not hasattr(gs, 'GAME_STATE_MAZE_DEFENSE'):
    gs.GAME_STATE_MAZE_DEFENSE = "maze_defense_mode"
GAME_STATE_MAZE_DEFENSE = gs.GAME_STATE_MAZE_DEFENSE

class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen_flags = pygame.FULLSCREEN if gs.get_game_setting("FULLSCREEN_MODE") else 0
        self.screen = pygame.display.set_mode((gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")), self.screen_flags)
        pygame.display.set_caption("HYPERDRONE")

        self.asset_manager = AssetManager(base_asset_folder_name="assets")
        self.drone_system = DroneSystem()
        
        self._preload_all_assets()

        self.clock = pygame.time.Clock()
        self.scene_manager = SceneManager(self)
        self.player_actions = PlayerActions(self)
        self.combat_controller = CombatController(self, self.asset_manager)
        self.puzzle_controller = PuzzleController(self, self.asset_manager)
        self.ui_flow_controller = UIFlowController(self)
        self.ui_manager = UIManager(self.screen, self.asset_manager, self, self.scene_manager, self.drone_system)
        
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

        self.current_intro_image_asset_key = None
        self.intro_screen_text_surfaces_current = []
        self.intro_font_key = "codex_category_font"

        if self.drone_system:
            self.drone_system.unlock_lore_entry_by_id("architect_legacy_intro")
            self.drone_system.check_and_unlock_lore_entries(event_trigger="game_start")
            
        if self.ui_flow_controller:
            self.ui_flow_controller.settings_items_data = self._get_settings_menu_items_data_structure()
            self.ui_flow_controller.intro_screens_data = self._load_intro_data_from_json_internal()

        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        logger_gc.info("GameController initialized successfully with AssetManager.")

    def _preload_all_assets(self):
        asset_manifest = {
            "images": { "ring_ui_icon": {"path": "images/collectibles/ring_ui_icon.png"}, "ring_ui_icon_empty": {"path": "images/collectibles/ring_ui_icon_empty.png"}, "menu_logo_hyperdrone": {"path": "images/ui/menu_logo_hyperdrone.png"}, "core_fragment_empty_icon": {"path": "images/collectibles/fragment_ui_icon_empty.png"}, "reactor_hud_icon_key": {"path": "images/ui/reactor_icon.png"}, },
            "sounds": { 'collect_ring': "sounds/collect_ring.wav", 'weapon_upgrade_collect': "sounds/weapon_upgrade_collect.wav", 'collect_fragment': "sounds/collect_fragment.wav", 'collect_log': "sounds/collect_log.wav", 'shoot': "sounds/shoot.wav", 'enemy_shoot': "sounds/enemy_shoot.wav", 'crash': "sounds/crash.wav", 'timer_out': "sounds/timer_out.wav", 'level_up': "sounds/level_up.wav", 'boss_intro': "sounds/boss_intro.wav", 'boss_hit': "sounds/boss_hit.wav", 'boss_death': "sounds/boss_death.wav", 'cloak_activate': "sounds/cloak_activate.wav", 'missile_launch': "sounds/missile_launch.wav", 'ui_select': "sounds/ui_select.wav", 'ui_confirm': "sounds/ui_confirm.wav", 'ui_denied': "sounds/ui_denied.wav", 'lore_unlock': "sounds/lore_unlock.wav", 'vault_alarm': "sounds/vault_alarm.wav", 'prototype_drone_explode': "sounds/prototype_drone_explode.wav", 'vault_barrier_disable': "sounds/vault_barrier_disable.wav", 'turret_place_placeholder': "sounds/turret_place.wav",  'reactor_hit_placeholder': "sounds/reactor_hit.wav",    'reactor_destroyed_placeholder': "sounds/reactor_destroyed.wav",  'turret_shoot_placeholder': "sounds/turret_shoot.wav"  },
            "fonts": {
                # This format tells the AssetManager to load ONE font file and create MULTIPLE sizes from it.
                "ui_text": {"path": "fonts/neuropol.otf", "sizes": [28, 24, 16]},
                "ui_values": {"path": "fonts/neuropol.otf", "sizes": [30]},
                # --- START FIX ---
                # Added size 24 to the manifest for the emoji font.
                "ui_emoji_general": {"path": "fonts/seguiemj.ttf", "sizes": [32, 28, 24, 19]},
                # --- END FIX ---
                "ui_emoji_small": {"path": "fonts/seguiemj.ttf", "sizes": [20, 26]},
                "small_text": {"path": "fonts/neuropol.otf", "sizes": [24]},
                "medium_text": {"path": "fonts/neuropol.otf", "sizes": [48]},
                "large_text": {"path": "fonts/neuropol.otf", "sizes": [74]},
                "input_text": {"path": "fonts/neuropol.otf", "sizes": [50]},
                "menu_text": {"path": "fonts/neuropol.otf", "sizes": [60, 54, 48]},
                "title_text": {"path": "fonts/neuropol.otf", "sizes": [90]},
                "drone_name_grid": {"path": "fonts/neuropol.otf", "sizes": [36]},
                "drone_desc_grid": {"path": "fonts/neuropol.otf", "sizes": [22]},
                "drone_unlock_grid": {"path": "fonts/neuropol.otf", "sizes": [20]},
                "drone_name_cycle": {"path": "fonts/neuropol.otf", "sizes": [42]},
                "drone_stats_label_cycle": {"path": "fonts/neuropol.otf", "sizes": [26]},
                "drone_stats_value_cycle": {"path": "fonts/neuropol.otf", "sizes": [28]},
                "drone_desc_cycle": {"path": "fonts/neuropol.otf", "sizes": [22]},
                "drone_unlock_cycle": {"path": "fonts/neuropol.otf", "sizes": [20]},
                "vault_message": {"path": "fonts/neuropol.otf", "sizes": [36]},
                "vault_timer": {"path": "fonts/neuropol.otf", "sizes": [48]},
                "leaderboard_header": {"path": "fonts/neuropol.otf", "sizes": [32]},
                "leaderboard_entry": {"path": "fonts/neuropol.otf", "sizes": [28]},
                "arrow_font_key": {"path": "fonts/seguiemj.ttf", "sizes": [60]},
                "story_message_font": {"path": "fonts/neuropol.otf", "sizes": [26]},
                "codex_title_font": {"path": "fonts/neuropol.otf", "sizes": [60]},
                "codex_category_font": {"path": "fonts/neuropol.otf", "sizes": [38]},
                "codex_entry_font": {"path": "fonts/neuropol.otf", "sizes": [30]},
                "codex_content_font": {"path": "fonts/neuropol.otf", "sizes": [24]},
            },
            "music": { "menu_theme": "sounds/menu_music.wav", "gameplay_theme": "sounds/gameplay_music.wav", "architect_vault_theme": "sounds/architect_vault_theme.wav", "defense_theme": "sounds/defense_mode_music.wav" }
        }
        
        if CORE_FRAGMENT_DETAILS:
            for _, details in CORE_FRAGMENT_DETAILS.items():
                if details and "id" in details and "icon_filename" in details: asset_manifest["images"][f"fragment_{details['id']}_icon"] = {"path": f"images/collectibles/{details['icon_filename']}"}
        for drone_id, config in DRONE_DATA.items():
            if config.get("sprite_path"): asset_manifest["images"][f"drone_{drone_id}_select_preview"] = {"path": config["sprite_path"].replace("assets/", ""), "alpha": True}
            if config.get("icon_path"): asset_manifest["images"][f"drone_{drone_id}_hud_icon"] = {"path": config["icon_path"].replace("assets/", ""), "alpha": True}
            if config.get("ingame_sprite_path"): asset_manifest["images"][f"drone_{drone_id}_ingame_sprite"] = {"path": config["ingame_sprite_path"].replace("assets/", ""), "alpha": True}
        entity_sprite_key_map = { "regular_enemy_sprite_key": gs.REGULAR_ENEMY_SPRITE_PATH, "prototype_drone_sprite_key": gs.PROTOTYPE_DRONE_SPRITE_PATH, "sentinel_drone_sprite_key": gs.SENTINEL_DRONE_SPRITE_PATH, "maze_guardian_sprite_key": gs.MAZE_GUARDIAN_SPRITE_PATH, }
        for key, path_val in entity_sprite_key_map.items():
            if path_val: asset_manifest["images"][key] = {"path": path_val.replace("assets/", ""), "alpha": True}
        if 'shield' in POWERUP_TYPES and 'image_filename' in POWERUP_TYPES['shield']: asset_manifest["images"]["shield_powerup_icon"] = {"path": f"images/powerups/{POWERUP_TYPES['shield']['image_filename']}"}
        if 'speed_boost' in POWERUP_TYPES and 'image_filename' in POWERUP_TYPES['speed_boost']: asset_manifest["images"]["speed_boost_powerup_icon"] = {"path": f"images/powerups/{POWERUP_TYPES['speed_boost']['image_filename']}"}
        if 'weapon_upgrade' in POWERUP_TYPES and 'image_filename' in POWERUP_TYPES['weapon_upgrade']: asset_manifest["images"]["weapon_upgrade_powerup_icon"] = {"path": f"images/powerups/{POWERUP_TYPES['weapon_upgrade']['image_filename']}"}
        ring_puzzle_image_keys = { "ring_puzzle_ring1_img": "images/puzzles/ring1.png", "ring_puzzle_ring2_img": "images/puzzles/ring2.png", "ring_puzzle_ring3_img": "images/puzzles/ring3.png" }
        for key, path in ring_puzzle_image_keys.items(): asset_manifest["images"][key] = {"path": path, "alpha": True}
        asset_manifest["images"]["ancient_terminal_sprite_img"] = {"path": "images/world/ancient_terminal.png", "alpha": True}
        turret_image_path_map = { "turret_default_base_img": "level_elements/turret1.png", "turret_trishot_base_img": "level_elements/turret2.png", "turret_seeker_base_img": "level_elements/turret3.png", "turret_lightning_base_img": "level_elements/turret4.png", }
        for key, rel_path in turret_image_path_map.items():
            if rel_path: asset_manifest["images"][key] = {"path": f"images/{rel_path}", "alpha": True}
        intro_data = self._load_intro_data_from_json_internal()
        for screen in intro_data:
            key = screen.get("image_path_key")
            if key: asset_manifest["images"][key] = {"path": key, "alpha": True}
        if hasattr(self.drone_system, 'all_lore_entries'):
            for lore_id_val, lore_entry_val in self.drone_system.all_lore_entries.items():
                if lore_entry_val and "image_path" in lore_entry_val and lore_entry_val["image_path"]:
                    relative_lore_path = lore_entry_val["image_path"].replace("assets/", "", 1)
                    asset_manifest["images"][f"lore_{lore_id_val}_image"] = {"path": relative_lore_path, "alpha": True}
        self.asset_manager.preload_manifest(asset_manifest)
        logger_gc.info("GameController: All assets preloaded via AssetManager.")

    # --- ALL OTHER GameController methods are included below ---
    # ... (omitting for brevity, but the full code is in the Canvas)
    def play_sound(self, sound_asset_key, volume_multiplier=0.7):
        sound = self.asset_manager.get_sound(sound_asset_key)
        if sound:
            try:
                base_sfx_volume = gs.get_game_setting("SFX_VOLUME_MULTIPLIER", 0.7)
                sound.set_volume(base_sfx_volume * volume_multiplier)
                sound.play()
            except pygame.error as e:
                logger_gc.error(f"Error playing sound '{sound_asset_key}': {e}")
        else:
            logger_gc.debug(f"Sound with key '{sound_asset_key}' not found. Play attempt skipped.")
            
    def _create_or_reset_player(self, position, is_vault=False, preserve_weapon_on_reset=False):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=is_vault)
        player_sprite_asset_key = f"drone_{selected_drone_id}_ingame_sprite"
        
        if self.player is None: 
            self.player = PlayerDrone(position[0], position[1], drone_id=selected_drone_id, 
                                      drone_stats=effective_stats, asset_manager=self.asset_manager, 
                                      sprite_asset_key=player_sprite_asset_key, crash_sound_key='crash', 
                                      drone_system=self.drone_system)
        else: 
            self.player.reset(position[0], position[1], drone_id=selected_drone_id, 
                              drone_stats=effective_stats, asset_manager=self.asset_manager,
                              sprite_asset_key=player_sprite_asset_key,
                              preserve_weapon=preserve_weapon_on_reset)
        
        if self.ui_manager: self.ui_manager.update_player_life_icon_surface()
        if self.combat_controller: self.combat_controller.player = self.player 
        if self.puzzle_controller: self.puzzle_controller.player = self.player

    def _create_explosion(self, x, y, num_particles=20, specific_sound_key='prototype_drone_explode'):
        colors = [ORANGE, YELLOW, RED, DARK_RED, GREY] 
        for _ in range(num_particles):
            self.explosion_particles_group.add(Particle(x, y, colors, 1, 4, 2, 5, 0.05, 0.1, random.randint(20,40)))
        if specific_sound_key: self.play_sound(specific_sound_key)

    def _get_settings_menu_items_data_structure(self):
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
            {"label":"Fullscreen", "key":"FULLSCREEN_MODE", "type":"choice", "choices":[False,True], "get_display":lambda v: "ON" if v else "OFF", "note":"Restart may be needed"},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ]

    def _load_intro_data_from_json_internal(self):
        fallback_data = [
            {"text": "The Architect — creator of the Vault\nand all drone intelligence — has vanished.\n\nNo warning. No trace. Only silence.", "image_path_key": "images/lore/scene1.png"},
            {"text": "In his absence, the Vault has become corrupted.\n\nIts corridors twisted into a cryptic maze,\nteeming with A.I defences.", "image_path_key": "images/lore/scene2.png"},
            {"text": "You are a pilot. An explorer.\n\nEntering the Vault to unravel the AI's enigma -\n\nand stop a system-wide fail-safe\nbefore it activates.", "image_path_key": "images/lore/scene3.png"},
            {"text": "The Architect's secrets lie ahead.\n\nSolve the puzzles. Survive the machines.\n\nOr be erased with everything else.", "image_path_key": "images/lore/scene4.png"},
        ]
        intro_file_path = os.path.join("data", "intro.json") 
        if os.path.exists(intro_file_path):
            try:
                with open(intro_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, list) and all("text" in item and "image_path" in item for item in loaded_data):
                        transformed_data = []
                        for item in loaded_data:
                            new_item = item.copy()
                            original_path = new_item.pop("image_path")
                            new_item["image_path_key"] = original_path.replace("assets/", "", 1)
                            transformed_data.append(new_item)
                        logger_gc.info(f"Successfully loaded and transformed {len(transformed_data)} intro screens.")
                        return transformed_data
                    else: logger_gc.warning("Intro.json format incorrect. Using fallback.")
            except (IOError, json.JSONDecodeError) as e:
                logger_gc.error(f"Error loading intro.json: {e}. Using fallback.")
        else: logger_gc.info("intro.json not found. Using fallback.")
        
        for item in fallback_data:
            if "image_path" in item: item["image_path_key"] = item.pop("image_path").replace("assets/", "", 1)
        return fallback_data

    def _prepare_current_intro_screen_surfaces(self):
        ui_flow_ctrl = self.ui_flow_controller
        if not ui_flow_ctrl.intro_screens_data or ui_flow_ctrl.current_intro_screen_index >= len(ui_flow_ctrl.intro_screens_data):
            ui_flow_ctrl.intro_sequence_finished = True
            self.current_intro_image_asset_key, self.intro_screen_text_surfaces_current = None, []
            return
        if ui_flow_ctrl.intro_sequence_finished:
            self.current_intro_image_asset_key, self.intro_screen_text_surfaces_current = None, []
            return
        screen_data = ui_flow_ctrl.intro_screens_data[ui_flow_ctrl.current_intro_screen_index]
        self.current_intro_image_asset_key = screen_data.get("image_path_key")
        self.intro_screen_text_surfaces_current = []
        font = self.asset_manager.get_font("codex_category_font", 38) or pygame.font.Font(None, 36)
        for raw_line in screen_data["text"].split('\n'):
            self.intro_screen_text_surfaces_current.append(font.render(raw_line or " ", True, GOLD))

    def set_story_message(self, message, duration=None): 
        self.story_message, self.story_message_active = message, True
        logger_gc.info(f"Story message set: {message}")

    def trigger_story_beat(self, beat_id):
        if beat_id not in self.triggered_story_beats:
            unlocked = self.drone_system.check_and_unlock_lore_entries(event_trigger=beat_id)
            if unlocked and (lore := self.drone_system.get_lore_entry_details(unlocked[0])):
                msg = lore.get("story_beat_message", lore.get("title", "New Intel Acquired"))
                self.set_story_message(f"Update: {msg}")
                self.triggered_story_beats.add(beat_id); self.play_sound('lore_unlock', 0.6)
                logger_gc.info(f"Story beat '{beat_id}' triggered, unlocking: {unlocked}.")
                return True
        return False

    def handle_scene_transition(self, new_state, old_state, **kwargs):
        logger_gc.info(f"Transition from '{old_state}' to '{new_state}'")
        is_menu_state = new_state in [GAME_STATE_MAIN_MENU, GAME_STATE_DRONE_SELECT, GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_CODEX, GAME_STATE_ENTER_NAME, GAME_STATE_GAME_OVER, GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE, GAME_STATE_MAZE_DEFENSE]
        pygame.mouse.set_visible(is_menu_state)
        menu_states = {
            GAME_STATE_MAIN_MENU: self.ui_flow_controller.initialize_main_menu,
            GAME_STATE_DRONE_SELECT: self.ui_flow_controller.initialize_drone_select,
            GAME_STATE_SETTINGS: lambda: self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure()),
            GAME_STATE_LEADERBOARD: self.ui_flow_controller.initialize_leaderboard,
            GAME_STATE_CODEX: self.ui_flow_controller.initialize_codex,
            GAME_STATE_ENTER_NAME: self.ui_flow_controller.initialize_enter_name,
            GAME_STATE_GAME_OVER: self.handle_game_over_scene_entry,
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: self.handle_architect_vault_success_scene,
            GAME_STATE_ARCHITECT_VAULT_FAILURE: self.handle_architect_vault_failure_scene
        }
        if new_state in menu_states: menu_states[new_state]()
        elif new_state == GAME_STATE_GAME_INTRO_SCROLL: self.ui_flow_controller.initialize_game_intro(self.ui_flow_controller.intro_screens_data)
        elif new_state == GAME_STATE_PLAYING: self.initialize_specific_game_mode("standard_play", old_state, **kwargs)
        elif new_state == GAME_STATE_BONUS_LEVEL_START: self.initialize_specific_game_mode("bonus_level_start", old_state)
        elif new_state == GAME_STATE_ARCHITECT_VAULT_INTRO: self.initialize_specific_game_mode("architect_vault_entry", old_state, phase_to_start="intro")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: self.initialize_architect_vault_session_phases("entry_puzzle")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET: self.initialize_architect_vault_session_phases("gauntlet_intro")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT: self.initialize_architect_vault_session_phases("architect_vault_boss_fight")
        elif new_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION: self.initialize_architect_vault_session_phases("extraction")
        elif new_state == GAME_STATE_RING_PUZZLE:
            if (terminal := kwargs.get('triggering_terminal')) and self.puzzle_controller: self.puzzle_controller.start_ring_puzzle(terminal)
        elif new_state == GAME_STATE_MAZE_DEFENSE: self.initialize_specific_game_mode("maze_defense", old_state)

    def _draw_game_world(self):
        state = self.scene_manager.get_current_state()
        bg_color = BLACK
        if state.startswith("architect_vault"): bg_color = ARCHITECT_VAULT_BG_COLOR
        elif state == GAME_STATE_MAZE_DEFENSE: bg_color = gs.DARK_GREY
        self.screen.fill(bg_color)
        if self.maze: self.maze.draw(self.screen)
        if state != GAME_STATE_MAZE_DEFENSE:
            for group in [self.collectible_rings_group, self.core_fragments_group, self.vault_logs_group, self.glyph_tablets_group, self.architect_echoes_group, self.alien_terminals_group]:
                group.draw(self.screen)
        self.power_ups_group.draw(self.screen); self.escape_zone_group.draw(self.screen); self.explosion_particles_group.draw(self.screen)
        if state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: self.architect_vault_puzzle_terminals_group.draw(self.screen)
        if state == GAME_STATE_MAZE_DEFENSE:
            self.reactor_group.draw(self.screen)
            for turret in self.turrets_group: turret.draw(self.screen)
            if self.player and self.player.alive: self.player.draw(self.screen)
        if self.combat_controller:
            if self.combat_controller.enemy_manager: self.combat_controller.enemy_manager.draw_all(self.screen)
            if self.combat_controller.boss_active and self.combat_controller.maze_guardian: self.combat_controller.maze_guardian.draw(self.screen)
        if self.player and (state != GAME_STATE_MAZE_DEFENSE or (self.player and self.player.alive)):
             if self.player.alive or any(getattr(self.player, g, None) for g in ['bullets_group', 'missiles_group', 'lightning_zaps_group']):
                 self.player.draw(self.screen)
    
    def run(self):
        self.check_and_apply_screen_settings_change()
        while True:
            delta_time_ms = self.clock.tick(gs.get_game_setting("FPS", 60))
            self.event_manager.process_events()
            self.update(delta_time_ms)
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state == GAME_STATE_GAME_INTRO_SCROLL: self.ui_manager.draw_current_scene_ui()
            elif current_game_state == GAME_STATE_RING_PUZZLE:
                self.screen.fill(gs.DARK_GREY); self.puzzle_controller.draw_active_puzzle(self.screen)
            elif current_game_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING, GAME_STATE_MAZE_DEFENSE] or current_game_state.startswith("architect_vault"):
                self._draw_game_world(); self.ui_manager.draw_current_scene_ui() 
            else: self.ui_manager.draw_current_scene_ui()
            pygame.display.flip()
            
    def update(self, delta_time_ms):
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_game_state)
        if current_game_state == GAME_STATE_GAME_INTRO_SCROLL and not self.ui_flow_controller.intro_sequence_finished:
            self._prepare_current_intro_screen_surfaces()
        if current_game_state == GAME_STATE_RING_PUZZLE:
            self.puzzle_controller.update(current_time_ms, current_game_state)
        elif current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_standard_playing_state(current_time_ms, delta_time_ms)
        elif current_game_state == GAME_STATE_MAZE_DEFENSE and not self.paused:
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.player and self.player.alive:
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
            if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu and self.ui_manager.build_menu.is_active:
                self.ui_manager.build_menu.update(pygame.mouse.get_pos(), current_game_state)
        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused:
            self._update_bonus_level_state(current_time_ms)
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state_machine(current_time_ms, delta_time_ms)
            if self.player and self.player.alive:
                self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
        self._update_hud_animations()
        if self.scene_manager: self.scene_manager.update()

    def _update_standard_playing_state(self, current_time_ms, delta_time_ms):
        if not self.player: logger_gc.error("Player is None."); return
        if not self.level_cleared_pending_animation:
            self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION") - (current_time_ms - self.level_timer_start_ticks)
            if self.level_time_remaining_ms <= 0: self.play_sound('timer_out'); self._handle_player_death_or_life_loss("Time Ran Out!"); return
            if self.player.alive: self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.maze.game_area_x_offset if self.maze else 0)
            else: self._handle_player_death_or_life_loss("Drone Destroyed!"); return
            self.combat_controller.update(current_time_ms, delta_time_ms)
            self.collectible_rings_group.update(); self.core_fragments_group.update(); self.vault_logs_group.update()
            self.glyph_tablets_group.update(); self.architect_echoes_group.update(); self.alien_terminals_group.update()
            self._handle_collectible_collisions()
            if not self.level_clear_fragment_spawned_this_level and self.collected_rings_count >= self.total_rings_per_level and self.all_enemies_killed_this_level:
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
        if current_phase == "intro" and current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        elif current_phase == "entry_puzzle" and all(self.puzzle_controller.architect_vault_terminals_activated) and current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        elif current_phase == "gauntlet_intro" and current_time_ms > self.architect_vault_message_timer: self.initialize_architect_vault_session_phases(f"gauntlet_wave_1")
        elif current_phase and current_phase.startswith("gauntlet_wave"):
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
                current_wave_num = self.combat_controller.architect_vault_gauntlet_current_wave
                if current_wave_num >= ARCHITECT_VAULT_GAUNTLET_WAVES: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_BOSS_FIGHT)
                else: self.initialize_architect_vault_session_phases(f"gauntlet_wave_{current_wave_num + 1}")
        elif current_phase == "architect_vault_boss_fight":
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if not self.combat_controller.boss_active and self.combat_controller.maze_guardian_defeat_processed and current_time_ms > self.architect_vault_message_timer: self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif current_phase == "extraction":
            self.combat_controller.update(current_time_ms, delta_time_ms)
            self.level_time_remaining_ms = max(0, gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - (current_time_ms - self.architect_vault_phase_timer_start))
            if self.escape_zone_group.sprite and self.player.rect.colliderect(self.escape_zone_group.sprite.rect): self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS); return
            if self.level_time_remaining_ms <= 0: self.architect_vault_failure_reason = "Extraction Failed: Time Expired."; self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
            if random.random() < 0.008 and self.combat_controller.enemy_manager.get_active_enemies_count() < 3: self.combat_controller.enemy_manager.spawn_prototype_drones(1)

    def _update_bonus_level_state(self, current_time_ms):
        if not self.player or not self.player.alive: self._end_bonus_level(completed=False); return
        self.player.update(current_time_ms, self.maze, None, self.maze.game_area_x_offset if self.maze else 0)
        self.level_time_remaining_ms = max(0, self.bonus_level_duration_ms - (current_time_ms - self.bonus_level_timer_start))
        if self.level_time_remaining_ms <= 0: self._end_bonus_level(completed=True); return
        self.explosion_particles_group.update()

    def _update_hud_animations(self):
        for ring_anim in list(self.animating_rings_to_hud):
            dx, dy = ring_anim['target_pos'][0] - ring_anim['pos'][0], ring_anim['target_pos'][1] - ring_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < ring_anim['speed']: self.animating_rings_to_hud.remove(ring_anim); self.displayed_collected_rings_count = min(self.displayed_collected_rings_count + 1, self.collected_rings_count)
            else: ring_anim['pos'][0] += (dx / dist) * ring_anim['speed']; ring_anim['pos'][1] += (dy / dist) * ring_anim['speed']
        for frag_anim in list(self.animating_fragments_to_hud):
            dx, dy = frag_anim['target_pos'][0] - frag_anim['pos'][0], frag_anim['target_pos'][1] - frag_anim['pos'][1]
            dist = math.hypot(dx, dy)
            if dist < frag_anim['speed']: self.animating_fragments_to_hud.remove(frag_anim); self.hud_displayed_fragments.add(frag_anim.get('id'))
            else: frag_anim['pos'][0] += (dx / dist) * frag_anim['speed']; frag_anim['pos'][1] += (dy / dist) * frag_anim['speed']

    def _handle_collectible_collisions(self):
        if not self.player or not self.player.alive: return
        for ring_sprite in pygame.sprite.spritecollide(self.player, self.collectible_rings_group, True, pygame.sprite.collide_rect_ratio(0.7)):
            self.score += 10; self.play_sound('collect_ring'); self.collected_rings_count += 1; self.drone_system.add_player_cores(5)
            anim_surf = self.asset_manager.get_image("ring_ui_icon", scale_to_size=(15, 15))
            if anim_surf: self.animating_rings_to_hud.append({'pos': list(ring_sprite.rect.center), 'target_pos': self.ring_ui_target_pos, 'speed': 15, 'surface': anim_surf})
            self._check_level_clear_condition();
            if self.level_cleared_pending_animation: break
        for frag_sprite in pygame.sprite.spritecollide(self.player, self.core_fragments_group, True, pygame.sprite.collide_rect_ratio(0.7)):
            if hasattr(frag_sprite, 'apply_effect') and frag_sprite.apply_effect(self.player, self):
                self.play_sound('collect_fragment'); self.score += 100
                self.player.is_cruising = False
                frag_id = getattr(frag_sprite, 'fragment_id', None)
                if frag_id and self.drone_system:
                    unlocked_lore = self.drone_system.check_and_unlock_lore_entries(event_trigger=f"collect_fragment_{frag_id}")
                    if unlocked_lore: self.set_story_message(f"Lore: {self.drone_system.get_lore_entry_details(unlocked_lore[0]).get('title', 'New Data')}")
                if frag_id and not any(a.get('id') == frag_id for a in self.animating_fragments_to_hud) and frag_id not in self.hud_displayed_fragments:
                    icon_surf = self.asset_manager.get_image(f"fragment_{frag_id}_icon", scale_to_size=(28,28)); target_pos = self.fragment_ui_target_positions.get(frag_id)
                    if icon_surf and target_pos: self.animating_fragments_to_hud.append({'pos': list(frag_sprite.rect.center), 'target_pos': target_pos, 'speed': 12, 'surface': icon_surf, 'id': frag_id})
                if self.drone_system and self.drone_system.are_all_core_fragments_collected(): self.set_story_message("All Core Fragments Acquired! Vault Access Imminent!", 4000)
                self._check_level_clear_condition()
        for item_group, sound_key, score_val, lore_prefix in [(self.vault_logs_group, 'collect_log', 50, "collect_log_"), (self.glyph_tablets_group, 'collect_log', 75, "collect_glyph_tablet_"), (self.architect_echoes_group, 'collect_fragment', 150, "collect_echo_")]:
            for item in pygame.sprite.spritecollide(self.player, item_group, True, pygame.sprite.collide_rect_ratio(0.7)):
                item_id_val = getattr(item, {'VaultLogItem':'log_id', 'GlyphTabletItem':'tablet_id', 'ArchitectEchoItem':'echo_id'}.get(type(item).__name__), None)
                if hasattr(item, 'apply_effect') and item.apply_effect(self.player, self):
                    self.play_sound(sound_key); self.score += score_val; self.player.is_cruising = False
                    if isinstance(item, GlyphTabletItem) and item_id_val:
                        self.drone_system.add_collected_glyph_tablet(item_id_val)
                        if "race_nordics" in self.drone_system.check_and_unlock_lore_entries(event_trigger="collect_all_architect_glyph_tablets"):
                            lore = self.drone_system.get_lore_entry_details("race_nordics"); title = lore.get("title", "NORDIC Preservers") if lore else "NORDIC Preservers"
                            self.set_story_message(f"All Glyphs Collected! Lore Unlocked: {title}")
                    elif item_id_val: self.drone_system.check_and_unlock_lore_entries(event_trigger=f"{lore_prefix}{item_id_val}")
        if (terminal := pygame.sprite.spritecollideany(self.player, self.alien_terminals_group)) and isinstance(terminal, AncientAlienTerminal) and not terminal.interacted:
            self.player.is_cruising = False
            terminal.interact(self)

    def _handle_player_death_or_life_loss(self, reason=""):
        if self.player: self.player.reset_active_powerups()
        self.lives -= 1
        logger_gc.info(f"Player lost a life. Reason: {reason}. Lives remaining: {self.lives}")
        if self.lives <= 0:
            if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
            self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
        else:
            if self.player: self._reset_player_after_death_internal()
            state = self.scene_manager.get_current_state()
            if state == GAME_STATE_PLAYING or (state == GAME_STATE_BONUS_LEVEL_PLAYING and self.player): self._reset_level_timer_internal()

    def check_and_apply_screen_settings_change(self):
        fullscreen = gs.get_game_setting("FULLSCREEN_MODE")
        flags = pygame.FULLSCREEN if fullscreen else 0
        w, h = gs.get_game_setting("WIDTH"), gs.get_game_setting("HEIGHT")
        current_w, current_h = self.screen.get_size()
        if self.screen_flags != flags or current_w != w or current_h != h:
            logger_gc.info(f"Screen settings changed. Reinitializing display.")
            self.screen_flags = flags
            try:
                self.screen = pygame.display.set_mode((w, h), self.screen_flags)
                if hasattr(self.ui_manager, 'on_screen_resize'): self.ui_manager.on_screen_resize(self.screen)
            except pygame.error as e: logger_gc.error(f"Failed to reinitialize display: {e}")

    def handle_pause_menu_input(self, key_pressed, current_game_state):
        if key_pressed == pygame.K_p: self.toggle_pause()
        elif key_pressed == pygame.K_m: self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_pressed == pygame.K_q: self.quit_game()
        elif key_pressed == pygame.K_l and current_game_state == GAME_STATE_PLAYING: self.unpause_and_set_state(GAME_STATE_LEADERBOARD)
        elif key_pressed == pygame.K_ESCAPE and current_game_state.startswith("architect_vault"): self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
        elif key_pressed == pygame.K_m and current_game_state == GAME_STATE_MAZE_DEFENSE: self.unpause_and_set_state(GAME_STATE_MAIN_MENU)
    
    def _check_level_clear_condition(self):
        if self.player and self.collected_rings_count >= self.total_rings_per_level and \
           self.all_enemies_killed_this_level and not self.level_cleared_pending_animation:
            
            # Attempt to spawn a reward fragment.
            fragment_spawned = self._attempt_level_clear_fragment_spawn()

            if fragment_spawned:
                # If a fragment was spawned, mark it and wait for collection.
                self.level_clear_fragment_spawned_this_level = True
            else:
                # If no fragment was spawned (because none was defined for this level),
                # immediately trigger the level clear animation sequence.
                if self.player: 
                    self.player.moving_forward = False
                    self.player.is_cruising = False
                self.level_cleared_pending_animation = True

    def _attempt_level_clear_fragment_spawn(self):
        fragment_id_to_spawn, fragment_details_to_spawn = None, None
        
        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details and details.get("reward_level") == self.level: 
                fragment_id_to_spawn, fragment_details_to_spawn = details.get("id"), details
                break
        
        if fragment_id_to_spawn and fragment_details_to_spawn:
            if self.drone_system and not self.drone_system.has_collected_fragment(fragment_id_to_spawn) and \
               not any(getattr(f, 'fragment_id', None) == fragment_id_to_spawn for f in self.core_fragments_group):
                
                spawn_pos = self._get_safe_spawn_point(TILE_SIZE, TILE_SIZE) 
                if spawn_pos:
                    self.core_fragments_group.add(CoreFragmentItem(spawn_pos[0], spawn_pos[1], fragment_id_to_spawn, fragment_details_to_spawn, asset_manager=self.asset_manager))
                    self.play_sound('collect_fragment', 0.8) 
                    logger_gc.info(f"Level clear fragment '{fragment_id_to_spawn}' spawned at {spawn_pos}.")
                    return True 
        return False 

    def _prepare_for_next_level(self, from_bonus_level_completion=False):
        logger_gc.info(f"Preparing for next level. Current level: {self.level}, From bonus: {from_bonus_level_completion}")
        self.explosion_particles_group.empty() 
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
        self.level_clear_fragment_spawned_this_level = False 

        if self.player and not self.player.alive and self.lives > 0: self.player.alive = True
        
        all_frags_collected = self.drone_system.are_all_core_fragments_collected() if self.drone_system else False
        vault_not_done = not self.drone_system.has_completed_architect_vault() if self.drone_system else True
        
        if not from_bonus_level_completion and all_frags_collected and vault_not_done and \
           not self.scene_manager.get_current_state().startswith("architect_vault"):
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_INTRO); return

        if not from_bonus_level_completion: self.level += 1 
        self.collected_rings_count, self.displayed_collected_rings_count = 0, 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15) 
        
        if self.drone_system: self.drone_system.set_player_level(self.level) 
        
        if self.level == 7: self.trigger_story_beat("story_beat_SB03")
        if self.level == 10 and self.drone_system and self.drone_system.has_completed_architect_vault(): self.trigger_story_beat("story_beat_SB04")
        
        new_player_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8) or (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)

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
        
        if self.player: self.player.moving_forward = False; self.player.is_cruising = False
        self.scene_manager.set_game_state(GAME_STATE_PLAYING)

    def _reset_player_after_death_internal(self):
        if not self.player: return
        self.explosion_particles_group.empty() 
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill() 
        self.level_clear_fragment_spawned_this_level = False 

        new_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8) or (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)
        is_vault = self.scene_manager.get_current_state().startswith("architect_vault")
        self._create_or_reset_player(new_pos, is_vault=is_vault, preserve_weapon_on_reset=False) 
        
        if is_vault and self.architect_vault_current_phase not in ["intro", "entry_puzzle"]:
            self.architect_vault_failure_reason = "Drone destroyed mid-mission."
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
        
        self.animating_rings_to_hud.clear(); self.animating_fragments_to_hud.clear(); self.level_cleared_pending_animation = False

    def _reset_level_timer_internal(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = gs.get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level(self, completed=True):
        self.explosion_particles_group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        self.level_clear_fragment_spawned_this_level = False
        if completed: self.score += 500 
        if self.drone_system: self.drone_system.add_player_cores(250); self.drone_system._save_unlocks() 
        self._prepare_for_next_level(from_bonus_level_completion=True)

    def _get_safe_spawn_point(self, entity_width, entity_height):
        if not self.maze: return (WIDTH // 2, GAME_PLAY_AREA_HEIGHT // 2) 
        path_cells_abs = getattr(self.maze, 'get_walkable_tiles_abs', lambda: [])()
        if not path_cells_abs: return (getattr(self.maze, 'game_area_x_offset', 0) + TILE_SIZE * 1.5, TILE_SIZE * 1.5)
        random.shuffle(path_cells_abs) 
        for abs_x, abs_y in path_cells_abs:
            if not self.maze.is_wall(abs_x, abs_y, entity_width, entity_height): return (abs_x, abs_y) 
        return path_cells_abs[0]

    def _spawn_architect_vault_puzzle_terminals(self):
        self.architect_vault_puzzle_terminals_group.empty() 
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        path_cells_abs = getattr(self.maze, 'get_walkable_tiles_abs', lambda: [])()
        frag_ids_for_terminals = ["cf_alpha", "cf_beta", "cf_gamma"] 
        num_to_spawn = min(len(frag_ids_for_terminals), len(path_cells_abs))
        if num_to_spawn == 0: return
        spawn_points = random.sample(path_cells_abs, k=num_to_spawn) 
        for i in range(num_to_spawn):
            term = AncientAlienTerminal(spawn_points[i][0], spawn_points[i][1], asset_manager=self.asset_manager)
            term.terminal_id, term.required_fragment_id, term.is_active = i, frag_ids_for_terminals[i], False 
            self.architect_vault_puzzle_terminals_group.add(term)
        logger_gc.info(f"Spawned {num_to_spawn} Architect Vault puzzle terminals.")

    def _spawn_escape_zone(self):
        if self.maze and self.player and (spawn_pos := self._get_safe_spawn_point(TILE_SIZE * 1.5, TILE_SIZE * 1.5)):
            self.escape_zone_group.add(EscapeZone(spawn_pos[0], spawn_pos[1]))
            logger_gc.info(f"Escape zone spawned at {spawn_pos}")

    def _place_collectibles_for_level(self, initial_setup=False):
        if not self.maze or not self.player: return
        walkable_tiles_abs = getattr(self.maze, 'get_walkable_tiles_abs', lambda: [])()
        if not walkable_tiles_abs: return
        if initial_setup:
            self.collectible_rings_group.empty()
            num_rings = min(self.total_rings_per_level, len(walkable_tiles_abs))
            if num_rings > 0:
                for x,y in random.sample(walkable_tiles_abs, k=num_rings): self.collectible_rings_group.add(CollectibleRing(x,y))
        occupied_tiles = set() 
        for key, details in CORE_FRAGMENT_DETAILS.items():
            if details and details.get("spawn_info", {}).get("level") == self.level and details.get("reward_level") is None and self.drone_system and not self.drone_system.has_collected_fragment(details["id"]) and not any(getattr(f,'fragment_id',None) == details["id"] for f in self.core_fragments_group):
                if spawn_pos := self._get_random_valid_collectible_spawn_abs(walkable_tiles_abs, occupied_tiles):
                    self.core_fragments_group.add(CoreFragmentItem(spawn_pos[0], spawn_pos[1], details["id"], details, asset_manager=self.asset_manager)); occupied_tiles.add(spawn_pos) 
        if self.level == 2 and self.drone_system and not self.drone_system.has_unlocked_lore("race_greys") and not any(getattr(log, 'log_id', None) == "GRX-23" for log in self.vault_logs_group):
            if spawn_pos := self._get_random_valid_collectible_spawn_abs(walkable_tiles_abs, occupied_tiles):
                self.vault_logs_group.add(VaultLogItem(spawn_pos[0], spawn_pos[1], "GRX-23", "vault_log_grx23_icon.png", asset_manager=self.asset_manager)); occupied_tiles.add(spawn_pos)
        terminal_id = f"level_5_element115_terminal" 
        if self.level == 5 and self.drone_system and not self.drone_system.has_puzzle_terminal_been_solved(terminal_id) and not any(getattr(t, 'item_id', '') == terminal_id for t in self.alien_terminals_group):
            if spawn_pos := self._get_random_valid_collectible_spawn_abs(walkable_tiles_abs, occupied_tiles, min_dist_player=TILE_SIZE*3):
                term = AncientAlienTerminal(spawn_pos[0], spawn_pos[1], asset_manager=self.asset_manager); term.item_id = terminal_id 
                self.alien_terminals_group.add(term); occupied_tiles.add(spawn_pos)
        echo_id_example, lore_id_for_echo = "echo_intro_01", "lore_architect_first_message"
        if self.level == 1 and not self.drone_system.has_unlocked_lore(lore_id_for_echo) and not any(getattr(e, 'echo_id', '') == echo_id_example for e in self.architect_echoes_group):
            if spawn_pos := self._get_random_valid_collectible_spawn_abs(walkable_tiles_abs, occupied_tiles):
                self.architect_echoes_group.add(ArchitectEchoItem(spawn_pos[0], spawn_pos[1], echo_id_example, lore_id_for_echo, asset_manager=self.asset_manager)); occupied_tiles.add(spawn_pos)

    def _place_collectibles_for_bonus_level(self):
        if not self.maze or not self.player: return
        walkable_tiles_abs = getattr(self.maze, 'get_walkable_tiles_abs', lambda: [])()
        if not walkable_tiles_abs: return
        self.collectible_rings_group.empty() 
        num_bonus_rings = min(gs.get_game_setting("BONUS_LEVEL_NUM_RINGS", 50), len(walkable_tiles_abs))
        if num_bonus_rings > 0:
            for x,y in random.sample(walkable_tiles_abs, k=num_bonus_rings): self.collectible_rings_group.add(CollectibleRing(x,y))
        logger_gc.info(f"Spawned {num_bonus_rings} rings for bonus level.")

    def _get_random_valid_collectible_spawn_abs(self, available_path_cells_abs, occupied_coords_abs, min_dist_player=TILE_SIZE*2):
        if not available_path_cells_abs: return None
        potential_spawns = [cell for cell in available_path_cells_abs if cell not in occupied_coords_abs and (not self.player or math.hypot(cell[0] - self.player.x, cell[1] - self.player.y) > min_dist_player)]
        return random.choice(potential_spawns) if potential_spawns else None

    def quit_game(self):
        logger_gc.info("Quitting game...");
        if self.drone_system: self.drone_system._save_unlocks()
        pygame.quit(); sys.exit()
    
    def handle_game_over_scene_entry(self):
        if self.escape_zone_group.sprite: 
            self.escape_zone_group.sprite.kill() 
        if self.drone_system:
            self.drone_system.set_player_level(self.level) 
            self.drone_system._save_unlocks()
    
    def handle_architect_vault_success_scene(self):
        self.ui_flow_controller.initialize_architect_vault_result_screen(success=True)
        if self.drone_system:
            self.drone_system.mark_architect_vault_completed(True) 
            self.score += 2500 
            self.drone_system.add_player_cores(500) 
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
            
    def is_current_score_a_high_score(self): return leaderboard.is_high_score(self.score, self.level)
    def submit_leaderboard_name(self, name):
        if leaderboard.add_score(name, self.score, self.level): self.play_sound('ui_confirm')
        else: self.play_sound('ui_denied')
        self.ui_flow_controller.leaderboard_scores = leaderboard.load_scores()
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
    def toggle_pause(self):
        self.paused = not self.paused; logger_gc.debug(f"Pause state: {self.paused}")
        if self.scene_manager: self.scene_manager._update_music()
        if not self.paused:
            t = pygame.time.get_ticks(); state = self.scene_manager.get_current_state()
            if state == GAME_STATE_PLAYING: self.level_timer_start_ticks = t - (gs.get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction": self.architect_vault_phase_timer_start = t - (gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS") - self.level_time_remaining_ms)
            elif state == GAME_STATE_BONUS_LEVEL_PLAYING: self.bonus_level_timer_start = t - (self.bonus_level_duration_ms - self.level_time_remaining_ms)
    def unpause_and_set_state(self, new_state):
        if self.paused: self.toggle_pause()
        self.scene_manager.set_game_state(new_state)
    def handle_maze_defense_victory(self):
        logger_gc.info("Maze Defense Victory!"); self.set_story_message("CORE REACTOR SECURED! ALL WAVES DEFEATED!", 10000)
        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
    def get_enemy_spawn_points_for_defense(self):
        if self.maze and hasattr(self.maze, 'get_enemy_spawn_points_abs'): return self.maze.get_enemy_spawn_points_abs()
        return []
    def initialize_architect_vault_session_phases(self, phase):
        self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
        self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group)
        self.architect_vault_current_phase, self.architect_vault_phase_timer_start = phase, pygame.time.get_ticks()
        logger_gc.info(f"Architect Vault Phase: {phase}")
        if phase == "intro": self.set_story_message("The Architect's Vault... Entry protocol initiated.", 5000); self.drone_system.check_and_unlock_lore_entries(event_trigger="architect_vault_entered")
        elif phase == "entry_puzzle": self.puzzle_controller.architect_vault_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED; self._spawn_architect_vault_puzzle_terminals(); self.set_story_message("Activate terminals with collected Core Fragments.", 5000)
        elif phase == "gauntlet_intro": self.combat_controller.architect_vault_gauntlet_current_wave, self.combat_controller.enemy_manager.reset_all(), self.set_story_message("Security systems online. Prepare for hostiles.", 3000)
        elif phase.startswith("gauntlet_wave_"):
            wave_num = int(phase.split("_")[-1]) if phase.split("_")[-1].isdigit() else 1
            self.combat_controller.architect_vault_gauntlet_current_wave = wave_num
            drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[min(wave_num - 1, len(ARCHITECT_VAULT_DRONES_PER_WAVE)-1)]
            self.combat_controller.enemy_manager.spawn_prototype_drones(drones_this_wave); self.set_story_message(f"Wave {wave_num} initiated!", 2000)
        elif phase == "architect_vault_boss_fight": self.set_story_message("MAZE GUARDIAN DETECTED. PREPARE FOR ENGAGEMENT!", 3000); self.combat_controller.spawn_maze_guardian()
        elif phase == "extraction": self.play_sound('vault_alarm', 0.7); self.set_story_message("SELF-DESTRUCT SEQUENCE ACTIVATED! REACH THE EXTRACTION POINT!", 5000); self._spawn_escape_zone(); self.level_time_remaining_ms = gs.get_game_setting("ARCHITECT_VAULT_EXTRACTION_TIMER_MS")
    def initialize_specific_game_mode(self, mode_type="standard_play", old_state=None, **kwargs): 
        logger_gc.info(f"Initializing mode: {mode_type}")
        for group in [self.collectible_rings_group, self.power_ups_group, self.core_fragments_group, self.vault_logs_group, self.glyph_tablets_group, self.architect_echoes_group, self.alien_terminals_group, self.architect_vault_puzzle_terminals_group, self.explosion_particles_group, self.reactor_group, self.turrets_group]: group.empty()
        if self.escape_zone_group.sprite: self.escape_zone_group.sprite.kill()
        if self.combat_controller: self.combat_controller.reset_combat_state()
        if self.puzzle_controller: self.puzzle_controller.reset_puzzles_state()
        if self.ui_flow_controller: self.ui_flow_controller.reset_ui_flow_states()
        self.player, self.maze, self.is_build_phase, self.paused = None, None, False, False
        if mode_type == "architect_vault_entry":
            if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            self.level = 1; self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault")
            if pos := self._get_safe_spawn_point(TILE_SIZE*0.8, TILE_SIZE*0.8): self._create_or_reset_player(pos, is_vault=True, preserve_weapon_on_reset=True)
            else: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
            self.combat_controller.set_active_entities(self.player, self.maze, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, architect_vault_terminals_group=self.architect_vault_puzzle_terminals_group)
            self.initialize_architect_vault_session_phases(kwargs.get('phase_to_start', 'intro'))
        elif mode_type == "maze_defense":
            self.level, self.score, self.lives = 1, 0, get_game_setting("PLAYER_LIVES")
            if self.drone_system: self.drone_system.reset_collected_fragments_in_storage(); self.drone_system.reset_architect_vault_status()
            self.maze, self.player = MazeChapter2(game_area_x_offset=0, maze_type="chapter2_tilemap"), None
            if pos := self.maze.get_core_reactor_spawn_position_abs(): self.reactor_group.add(CoreReactor(pos[0], pos[1], health=gs.get_game_setting("DEFENSE_REACTOR_HEALTH", 1000)))
            else: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
            self.combat_controller.set_active_entities(player=None, maze=self.maze, core_reactor=self.reactor_group.sprite, turrets_group=self.turrets_group, explosion_particles_group=self.explosion_particles_group)
            self.combat_controller.wave_manager.start_first_build_phase(); self.is_build_phase = True
            if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu: self.ui_manager.build_menu.activate()
        elif mode_type == "bonus_level_start":
            if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            self.maze = Maze(game_area_x_offset=0, maze_type="bonus")
            if pos := self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8): self._create_or_reset_player(pos, is_vault=False, preserve_weapon_on_reset=True)
            else: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
            self._place_collectibles_for_bonus_level()
            self.bonus_level_timer_start, self.level_time_remaining_ms = pygame.time.get_ticks(), self.bonus_level_duration_ms
            self.bonus_level_start_display_end_time = pygame.time.get_ticks() + 3000
            self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager)
        else: # standard_play
            if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu: self.ui_manager.build_menu.deactivate()
            self.level = kwargs.get('start_level', 1 if old_state == GAME_STATE_GAME_INTRO_SCROLL else self.level)
            if old_state == GAME_STATE_GAME_INTRO_SCROLL:
                self.score, self.lives = 0, get_game_setting("PLAYER_LIVES"); self.triggered_story_beats.clear()
                if self.drone_system: self.drone_system.reset_collected_fragments_in_storage(); self.drone_system.reset_architect_vault_status()
            self.collected_rings_count, self.displayed_collected_rings_count, self.total_rings_per_level = 0, 0, 5
            self.all_enemies_killed_this_level, self.animating_rings_to_hud, self.animating_fragments_to_hud, self.hud_displayed_fragments = False, [], [], set()
            self.maze = Maze(game_area_x_offset=0, maze_type="standard")
            if pos := self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8): self._create_or_reset_player(pos, is_vault=False, preserve_weapon_on_reset=(old_state == GAME_STATE_PLAYING))
            else: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return
            self.combat_controller.set_active_entities(self.player, self.maze, power_ups_group=self.power_ups_group, explosion_particles_group=self.explosion_particles_group)
            self.puzzle_controller.set_active_entities(self.player, self.drone_system, self.scene_manager, alien_terminals_group=self.alien_terminals_group)
            self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
            self._place_collectibles_for_level(initial_setup=True); self._reset_level_timer_internal()
            self.level_cleared_pending_animation, self.level_clear_fragment_spawned_this_level = False, False
        logger_gc.info(f"Finished init for {mode_type}.")
