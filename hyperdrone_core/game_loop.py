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
from hyperdrone_core.camera import Camera

logger_gc = logging.getLogger(__name__)

class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        try:
            info = pygame.display.Info()
            detected_width, detected_height = info.current_w, info.current_h
            final_width = max(1920, detected_width)
            final_height = max(1080, detected_height)
            gs.set_game_setting("WIDTH", final_width)
            gs.set_game_setting("HEIGHT", final_height)
            logger_gc.info(f"Screen resolution set to: {final_width}x{final_height}")
        except pygame.error as e:
            logger_gc.error(f"Could not detect screen size: {e}. Using default 1920x1080.")

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
        self.camera = None

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
        self.ring_ui_target_pos = (gs.get_game_setting("WIDTH") - 50, gs.get_game_setting("HEIGHT") - gs.get_game_setting("BOTTOM_PANEL_HEIGHT") + 50)
        self.hud_displayed_fragments = set()
        self.animating_fragments_to_hud = []
        self.fragment_ui_target_positions = {}

        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False
        self.level_clear_fragment_spawned_this_level = False
        
        self.story_message = ""
        self.story_message_active = False
        self.story_message_end_time = 0
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

        self.scene_manager.set_game_state(gs.GAME_STATE_MAIN_MENU)
        logger_gc.info("GameController initialized successfully.")

    def _preload_all_assets(self):
        asset_manifest = {
            "images": {
                "ring_ui_icon": {"path": "images/collectibles/ring_ui_icon.png"},
                "ring_ui_icon_empty": {"path": "images/collectibles/ring_ui_icon_empty.png"},
                "menu_logo_hyperdrone": {"path": "images/ui/menu_logo_hyperdrone.png"},
                "core_fragment_empty_icon": {"path": "images/collectibles/fragment_ui_icon_empty.png"},
                "reactor_hud_icon_key": {"path": "images/level_elements/reactor_icon.png"},
                "core_reactor_image": {"path": "images/level_elements/core_reactor.png", "alpha": True},
                "shield_powerup_icon": {"path": "images/powerups/shield_icon.png"},
                "speed_boost_powerup_icon": {"path": "images/powerups/speed_icon.png"},
                "weapon_upgrade_powerup_icon": {"path": "images/powerups/weapon_icon.png"},
                "regular_enemy_sprite_key": {"path": gs.REGULAR_ENEMY_SPRITE_PATH.replace("assets/", ""), "alpha": True},
                "prototype_drone_sprite_key": {"path": gs.PROTOTYPE_DRONE_SPRITE_PATH.replace("assets/", ""), "alpha": True},
                "sentinel_drone_sprite_key": {"path": gs.SENTINEL_DRONE_SPRITE_PATH.replace("assets/", ""), "alpha": True},
                "maze_guardian_sprite_key": {"path": gs.MAZE_GUARDIAN_SPRITE_PATH.replace("assets/", ""), "alpha": True},
                "defense_drone_1_sprite_key": {"path": "images/enemies/defense_drone_1.png", "alpha": True},
                "defense_drone_2_sprite_key": {"path": "images/enemies/defense_drone_2.png", "alpha": True},
                "defense_drone_3_sprite_key": {"path": "images/enemies/defense_drone_3.png", "alpha": True},
                "defense_drone_4_sprite_key": {"path": "images/enemies/defense_drone_4.png", "alpha": True},
                "defense_drone_5_sprite_key": {"path": "images/enemies/defense_drone_5.png", "alpha": True},
                "images/lore/scene1.png": {"path": "images/lore/scene1.png", "alpha": True},
                "images/lore/scene2.png": {"path": "images/lore/scene2.png", "alpha": True},
                "images/lore/scene3.png": {"path": "images/lore/scene3.png", "alpha": True},
                "images/lore/scene4.png": {"path": "images/lore/scene4.png", "alpha": True},
            },
            "sounds": {
                'collect_ring': "sounds/collect_ring.wav",
                'weapon_upgrade_collect': "sounds/weapon_upgrade_collect.wav",
                'collect_fragment': "sounds/collect_fragment.wav",
                'shoot': "sounds/shoot.wav",
                'enemy_shoot': "sounds/enemy_shoot.wav",
                'crash': "sounds/crash.wav",
                'level_up': "sounds/level_up.wav",
                'ui_select': "sounds/ui_select.wav",
                'ui_confirm': "sounds/ui_confirm.wav",
                'missile_launch': "sounds/missile_launch.wav",
            },
            "fonts": {
                "ui_text": {"path": "fonts/neuropol.otf", "sizes": [28, 24, 20, 16, 32]},
                "ui_values": {"path": "fonts/neuropol.otf", "sizes": [30]},
                "small_text": {"path": "fonts/neuropol.otf", "sizes": [24]},
                "medium_text": {"path": "fonts/neuropol.otf", "sizes": [48, 36]},
                "large_text": {"path": "fonts/neuropol.otf", "sizes": [74, 52, 48]},
                "title_text": {"path": "fonts/neuropol.otf", "sizes": [90]},
            },
            "music": {
                "menu_theme": "sounds/menu_music.wav",
                "gameplay_theme": "sounds/gameplay_music.wav",
                "defense_theme": "sounds/defense_mode_music.wav"
            }
        }
        
        if gs.CORE_FRAGMENT_DETAILS:
            for _, details in gs.CORE_FRAGMENT_DETAILS.items():
                if details and "id" in details and "icon_filename" in details:
                    asset_manifest["images"][f"fragment_{details['id']}_icon"] = {"path": details['icon_filename']}

        for drone_id, config in DRONE_DATA.items():
            if config.get("ingame_sprite_path"): 
                asset_manifest["images"][f"drone_{drone_id}_ingame_sprite"] = {"path": config["ingame_sprite_path"].replace("assets/", ""), "alpha": True}
            if config.get("icon_path"):
                 asset_manifest["images"][f"drone_{drone_id}_hud_icon"] = {"path": config["icon_path"].replace("assets/", ""), "alpha": True}

        for weapon_path in gs.WEAPON_MODE_ICONS.values():
            if weapon_path and isinstance(weapon_path, str):
                asset_key = weapon_path.replace("assets/", "").replace("\\", "/")
                asset_manifest["images"][asset_key] = {"path": asset_key, "alpha": True}
        
        self.asset_manager.preload_manifest(asset_manifest)
        logger_gc.info("GameController: All assets preloaded via AssetManager.")
    
    def run(self):
        while True:
            delta_time_ms = self.clock.tick(gs.get_game_setting("FPS", 60))
            self.event_manager.process_events()
            self.update(delta_time_ms)
            
            current_game_state = self.scene_manager.get_current_state()
            if current_game_state in [gs.GAME_STATE_PLAYING, gs.GAME_STATE_MAZE_DEFENSE] or current_game_state.startswith("architect_vault"):
                self._draw_game_world()
            
            self.ui_manager.draw_current_scene_ui()
            pygame.display.flip()

    def update(self, delta_time_ms):
        current_time_ms = pygame.time.get_ticks()
        current_game_state = self.scene_manager.get_current_state()
        self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_game_state)

        if self.story_message_active and current_time_ms > self.story_message_end_time:
            self.story_message_active = False
            self.story_message = ""

        if current_game_state == gs.GAME_STATE_GAME_INTRO_SCROLL:
            if self.ui_flow_controller.intro_sequence_finished:
                self.scene_manager.set_game_state(gs.GAME_STATE_PLAYING)
        
        elif current_game_state == gs.GAME_STATE_PLAYING and not self.paused:
            self._update_standard_playing_state(current_time_ms, delta_time_ms)
        
        elif current_game_state == gs.GAME_STATE_MAZE_DEFENSE and not self.paused:
            self.combat_controller.update(current_time_ms, delta_time_ms)
            if self.camera:
                if hasattr(self.ui_manager, 'build_menu') and self.ui_manager.build_menu:
                    self.ui_manager.build_menu.update(pygame.mouse.get_pos(), current_game_state, self.camera)
        
        if self.scene_manager: self.scene_manager.update()

    def set_story_message(self, message, duration_ms=None):
        self.story_message = message
        self.story_message_active = True
        duration_to_use = duration_ms if duration_ms is not None else self.STORY_MESSAGE_DURATION
        self.story_message_end_time = pygame.time.get_ticks() + duration_to_use
        logger_gc.info(f"Setting story message: '{message}' for {duration_to_use}ms")

    def _create_explosion(self, x, y, num_particles=20, specific_sound_key=None):
        """Creates a particle explosion at a given coordinate."""
        for _ in range(num_particles):
            self.explosion_particles_group.add(Particle(x, y, [gs.ORANGE, gs.YELLOW, gs.RED], 1, 4, 2, 8, gravity=0.1, shrink_rate=0.2, lifetime_frames=30))
        if specific_sound_key:
            self.play_sound(specific_sound_key)

    def handle_scene_transition(self, new_state, old_state, **kwargs):
        self.paused = False
        if new_state == gs.GAME_STATE_MAIN_MENU:
            self.ui_flow_controller.initialize_main_menu()
        elif new_state == gs.GAME_STATE_DRONE_SELECT:
            self.ui_flow_controller.initialize_drone_select()
        elif new_state == gs.GAME_STATE_SETTINGS:
            self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure())
        elif new_state == gs.GAME_STATE_LEADERBOARD:
            self.ui_flow_controller.initialize_leaderboard()
        elif new_state == gs.GAME_STATE_CODEX:
            self.ui_flow_controller.initialize_codex()
        elif new_state == gs.GAME_STATE_ENTER_NAME:
            self.ui_flow_controller.initialize_enter_name()
        elif new_state == gs.GAME_STATE_GAME_INTRO_SCROLL:
            self.ui_flow_controller.initialize_game_intro(self._load_intro_data_from_json_internal())
        elif new_state == gs.GAME_STATE_PLAYING:
            self.initialize_specific_game_mode(gs.GAME_STATE_PLAYING, old_state, **kwargs)
        elif new_state == gs.GAME_STATE_MAZE_DEFENSE:
            self.initialize_specific_game_mode(gs.GAME_STATE_MAZE_DEFENSE, old_state, **kwargs)

    def initialize_specific_game_mode(self, mode_type, old_state, **kwargs):
        self.combat_controller.reset_combat_state()
        self.puzzle_controller.reset_puzzles_state()
        self.level = 1
        self.score = 0
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        
        if mode_type == gs.GAME_STATE_MAZE_DEFENSE:
            self.maze = MazeChapter2(game_area_x_offset=300) 
            self.camera = Camera(self.maze.actual_maze_cols * gs.TILE_SIZE, self.maze.actual_maze_rows * gs.TILE_SIZE)
            reactor_pos = self.maze.get_core_reactor_spawn_position_abs()
            if reactor_pos:
                self.core_reactor = CoreReactor(reactor_pos[0], reactor_pos[1], self.asset_manager, health=gs.DEFENSE_REACTOR_HEALTH)
                self.reactor_group.add(self.core_reactor)
            self.combat_controller.set_active_entities(player=None, maze=self.maze, core_reactor=self.core_reactor, turrets_group=self.turrets_group)
            self.combat_controller.wave_manager.start_first_build_phase()
        else: 
            self.maze = Maze()
            self.camera = None
            spawn_x, spawn_y = self._get_safe_spawn_point(gs.TILE_SIZE * 0.7, gs.TILE_SIZE * 0.7)
            drone_id = self.drone_system.get_selected_drone_id()
            drone_stats = self.drone_system.get_drone_stats(drone_id)
            sprite_key = f"drone_{drone_id}_ingame_sprite"
            self.player = PlayerDrone(spawn_x, spawn_y, drone_id, drone_stats, self.asset_manager, sprite_key, 'crash', self.drone_system)
            self.combat_controller.set_active_entities(player=self.player, maze=self.maze, power_ups_group=self.power_ups_group)
            self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level)
            self.puzzle_controller.set_active_entities(player=self.player, drone_system=self.drone_system, scene_manager=self.scene_manager)

    def _update_standard_playing_state(self, current_time_ms, delta_time_ms):
        if not self.player: return
        self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.player_actions, self.maze.game_area_x_offset if self.maze else 0)
        self.combat_controller.update(current_time_ms, delta_time_ms)

    def _draw_game_world(self):
        self.screen.fill(gs.BLACK)
        if self.maze:
            self.maze.draw(self.screen, self.camera)
        
        self.explosion_particles_group.draw(self.screen) 

        if self.player:
            self.player.draw(self.screen)
        if self.combat_controller:
            self.combat_controller.enemy_manager.draw_all(self.screen, self.camera)
        if self.reactor_group:
            self.reactor_group.draw(self.screen, self.camera)
        if self.turrets_group:
            for turret in self.turrets_group:
                turret.draw(self.screen, self.camera)

    def quit_game(self):
        if self.drone_system: self.drone_system._save_unlocks()
        pygame.quit()
        sys.exit()

    def _get_settings_menu_items_data_structure(self):
        return [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice",
             "choices":gs.WEAPON_MODES_SEQUENCE, "get_display":lambda val:gs.WEAPON_MODE_NAMES.get(val,"Unknown")},
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
        fallback_data = [{"text": "The Architect has vanished.", "image_path_key": "images/lore/scene1.png"}]
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
                            new_item["image_path_key"] = original_path.replace("assets/", "").replace("\\", "/")
                            transformed_data.append(new_item)
                        return transformed_data
            except Exception as e:
                logger_gc.error(f"Error loading intro.json: {e}. Using fallback.")
        return fallback_data
    
    def _get_safe_spawn_point(self, w, h):
        if self.maze and hasattr(self.maze, 'get_walkable_tiles_abs'):
            walkable = self.maze.get_walkable_tiles_abs()
            if walkable:
                return random.choice(walkable)
        return (200, 200)

    def check_and_apply_screen_settings_change(self): pass
    def play_sound(self, key, vol=0.7): pass
    def check_for_all_enemies_killed(self): pass
    def _check_level_clear_condition(self): pass
    def _attempt_level_clear_fragment_spawn(self): return False
    def _handle_collectible_collisions(self): pass
    def _handle_player_death_or_life_loss(self, reason=""): pass