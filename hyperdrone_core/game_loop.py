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
from .level_manager import LevelManager
from ui import UIManager
from .asset_manager import AssetManager

from entities import PlayerDrone, CoreReactor, Turret, LightningZap, Missile, Particle
from entities import MazeGuardian, SentinelDrone, EscapeZone, Maze, MazeChapter2, Bullet
from entities.collectibles import Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem
from entities.collectibles import CoreFragmentItem, VaultLogItem, GlyphTabletItem, AncientAlienTerminal, ArchitectEchoItem
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
        
        self.player = None
        self.maze = None
        self.camera = None
        
        # Add score attribute to fix game over restart
        self.score = 0
        self.level = 1

        # Initialize sprite groups first
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
        
        # Add item manager for collectibles and powerups after sprite groups are initialized
        from .item_manager import ItemManager
        self.item_manager = ItemManager(self, self.asset_manager)
        
        self.event_manager = EventManager(self, self.scene_manager, self.combat_controller, self.puzzle_controller, self.ui_flow_controller)
        self.ui_flow_controller.set_dependencies(self.scene_manager, self.ui_manager, self.drone_system)
        
        # Game state variables
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        self.paused = False
        self.is_build_phase = False
        
        # Create level manager
        self.level_manager = LevelManager(self)
        
        # Fragment collection variables
        self.hud_displayed_fragments = set()
        self.animating_fragments_to_hud = []
        self.fragment_ui_target_positions = {}
        
        # Timer variables
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
        
        # Initialize story message attributes
        self.story_message = ""
        self.story_message_active = False
        self.story_message_end_time = 0
        self.STORY_MESSAGE_DURATION = 5000
        self.triggered_story_beats = set()
        
        # UI and intro screen variables
        self.current_intro_image_asset_key = None
        self.intro_screen_text_surfaces_current = []
        self.intro_font_key = "codex_category_font"
        
    def _create_explosion(self, x, y, num_particles=6, specific_sound_key='prototype_drone_explode'):
        # Richer color range including whites and brighter tones for flash effect
        colors = [gs.WHITE, gs.YELLOW, gs.ORANGE, gs.RED]
        
        # Create a tiny bright flash at the center
        self.explosion_particles_group.add(
            Particle(x, y, [gs.WHITE, gs.YELLOW], 
                    min_speed=0.01, max_speed=0.05, 
                    min_size=0.01, max_size=0.05, 
                    gravity=0, shrink_rate=0.2, 
                    lifetime_frames=4)
        )
        
        # Create the main explosion particles - fewer and much smaller
        for _ in range(num_particles):
            # Calculate random angle for directional explosion
            angle = random.uniform(0, 360)
            speed = random.uniform(0.05, 0.2)  # Extremely low speed
            size = random.uniform(0.01, 0.05)  # Extremely small particles
            lifetime = random.randint(5, 10)   # Very short lifetime
            
            self.explosion_particles_group.add(
                Particle(x, y, colors, 
                        min_speed=speed*0.8, max_speed=speed, 
                        min_size=size*0.8, max_size=size, 
                        gravity=0.001, shrink_rate=0.05, 
                        lifetime_frames=lifetime,
                        base_angle_deg=angle, spread_angle_deg=5)
            )
            
        if specific_sound_key:
            self.play_sound(specific_sound_key)
        
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
        
        # Reset level manager
        self.level_manager.reset()
        
        self.hud_displayed_fragments = set()
        self.animating_fragments_to_hud = []
        self.fragment_ui_target_positions = {}
        
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
        # Use the new method in AssetManager to preload all game assets
        self.asset_manager.preload_game_assets()
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
        # Create explosion particles with varied colors and sizes
        colors = [gs.ORANGE, gs.YELLOW, gs.RED]
        
        # Create a bright flash at the center
        self.explosion_particles_group.add(
            Particle(x, y, [gs.WHITE, gs.YELLOW], 
                    min_speed=0.5, max_speed=1.0, 
                    min_size=5.0, max_size=8.0, 
                    gravity=0, shrink_rate=0.2, 
                    lifetime_frames=12)
        )
        
        # Create the main explosion particles
        for _ in range(num_particles):
            # Calculate random angle for directional explosion
            angle = random.uniform(0, 360)
            speed = random.uniform(2.0, 4.0)
            size = random.uniform(2.0, 4.0)
            lifetime = random.randint(20, 30)
            
            self.explosion_particles_group.add(
                Particle(x, y, colors, 
                        min_speed=speed*0.8, max_speed=speed, 
                        min_size=size*0.8, max_size=size, 
                        gravity=0.02, shrink_rate=0.08, 
                        lifetime_frames=lifetime,
                        base_angle_deg=angle, spread_angle_deg=20)
            )
        if specific_sound_key:
            self.play_sound(specific_sound_key)
            
    def _create_enemy_explosion(self, x, y):
        """Creates an explosion specifically for enemy deaths."""
        # Create a bright flash at the center
        flash_size = random.uniform(3.0, 5.0)
        self.explosion_particles_group.add(
            Particle(x, y, [gs.WHITE, gs.YELLOW], 
                     min_speed=0.5, max_speed=1.0, 
                     min_size=flash_size*0.8, max_size=flash_size, 
                     gravity=0, shrink_rate=0.2, 
                     lifetime_frames=10)
        )
        
        # Create outward expanding particles
        colors = [gs.RED, gs.ORANGE, gs.YELLOW]
        for _ in range(15):
            angle = random.uniform(0, 360)
            distance = random.uniform(2.0, 4.0)
            px = x + math.cos(math.radians(angle)) * distance
            py = y + math.sin(math.radians(angle)) * distance
            
            size = random.uniform(1.5, 3.0)
            speed = random.uniform(1.5, 3.0)
            lifetime = random.randint(15, 25)
            
            self.explosion_particles_group.add(
                Particle(px, py, colors, 
                         min_speed=speed*0.8, max_speed=speed, 
                         min_size=size*0.8, max_size=size, 
                         gravity=0.01, shrink_rate=0.08, 
                         lifetime_frames=lifetime,
                         base_angle_deg=angle, spread_angle_deg=15)
            )

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
        self.level_manager.reset()
        self.lives = gs.get_game_setting("PLAYER_LIVES")
        
        # Reset item manager for the new level
        if hasattr(self, 'item_manager'):
            self.item_manager.reset_for_level()
        
        if mode_type == gs.GAME_STATE_MAZE_DEFENSE:
            self.maze = MazeChapter2(game_area_x_offset=300) 
            self.camera = Camera(self.maze.actual_maze_cols * gs.TILE_SIZE, self.maze.actual_maze_rows * gs.TILE_SIZE)
            # Set initial zoom level to full zoom out if specified in maze
            if hasattr(self.maze, 'initial_zoom_level'):
                self.camera.zoom_level = self.maze.initial_zoom_level
            
            # Initialize tower defense manager
            from entities.tower_defense_manager import TowerDefenseManager
            self.tower_defense_manager = TowerDefenseManager(
                self.maze.actual_maze_cols, 
                self.maze.actual_maze_rows, 
                gs.TILE_SIZE, 
                self.maze.game_area_x_offset
            )
            # Set game controller reference
            self.tower_defense_manager.game_controller = self
            self.tower_defense_manager.initialize_from_maze(self.maze)
            
            reactor_pos = self.maze.get_core_reactor_spawn_position_abs()
            if reactor_pos:
                # Create the core reactor with the correct position
                self.core_reactor = CoreReactor(reactor_pos[0], reactor_pos[1], self.asset_manager, health=gs.DEFENSE_REACTOR_HEALTH)
                self.reactor_group.empty()  # Clear any existing reactors
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
            self.combat_controller.enemy_manager.spawn_enemies_for_level(self.level_manager.level)
            self.puzzle_controller.set_active_entities(player=self.player, drone_system=self.drone_system, scene_manager=self.scene_manager)

    def _update_standard_playing_state(self, current_time_ms, delta_time_ms):
        if not self.player: return
        self.player.update(current_time_ms, self.maze, self.combat_controller.enemy_manager.get_sprites(), self.player_actions, self.maze.game_area_x_offset if self.maze else 0)
        self.combat_controller.update(current_time_ms, delta_time_ms)
        
        # Update item manager to spawn collectibles and powerups
        if hasattr(self, 'item_manager'):
            self.item_manager.update(current_time_ms, self.maze)
            
        # Handle collectible collisions
        self._handle_collectible_collisions()
        
        # Check if level is cleared
        self._check_level_clear_condition()

    def _draw_game_world(self):
        self.screen.fill(gs.BLACK)
        if self.maze:
            self.maze.draw(self.screen, self.camera)
        
        # Draw collectibles and powerups
        for item_group in [self.collectible_rings_group, self.power_ups_group, 
                          self.core_fragments_group, self.vault_logs_group,
                          self.glyph_tablets_group, self.architect_echoes_group]:
            for item in item_group:
                item.draw(self.screen, self.camera)
        
        # Update and draw explosion particles
        self.explosion_particles_group.update()
        self.explosion_particles_group.draw(self.screen) 

        if self.player:
            self.player.draw(self.screen)
            
        # Draw tower defense elements if available
        current_game_state = self.scene_manager.get_current_state()
        if current_game_state == gs.GAME_STATE_MAZE_DEFENSE and hasattr(self, 'tower_defense_manager'):
            self.tower_defense_manager.draw(self.screen, self.camera)
            
        if self.combat_controller:
            self.combat_controller.enemy_manager.draw_all(self.screen, self.camera)
            
        if self.turrets_group:
            for turret in self.turrets_group:
                turret.draw(self.screen, self.camera)
                
        if self.reactor_group:
            for reactor in self.reactor_group:
                reactor.draw(self.screen, self.camera)
                
        # Draw animating rings using level manager
        ring_icon = self.asset_manager.get_image("ring_ui_icon")
        self.level_manager.draw_ring_animations(self.screen, ring_icon)

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
    def _check_level_clear_condition(self):
        """Check if the level has been cleared and progress to the next level if so"""
        return self.level_manager.check_level_clear_condition()
    def _attempt_level_clear_fragment_spawn(self): return False
    def _handle_collectible_collisions(self):
        """Handle collisions between player and collectible items"""
        if not self.player or not hasattr(self.player, 'rect'):
            return
            
        # Check for ring collisions
        for ring in pygame.sprite.spritecollide(self.player, self.collectible_rings_group, False):
            ring.collected = True
            self.level_manager.collect_ring(ring.rect.center)
            self.play_sound('collect_ring')
            
        # Check for powerup collisions
        for powerup in pygame.sprite.spritecollide(self.player, self.power_ups_group, False):
            if isinstance(powerup, WeaponUpgradeItem):
                powerup.apply_effect(self.player)
                powerup.collected = True
                self.play_sound('weapon_upgrade_collect')
            elif isinstance(powerup, ShieldItem):
                powerup.apply_effect(self.player)
                powerup.collected = True
                self.play_sound('collect_ring')
            elif isinstance(powerup, SpeedBoostItem):
                powerup.apply_effect(self.player)
                powerup.collected = True
                self.play_sound('collect_ring')
                
# Method removed - now handled by LevelManager
    def _handle_player_death_or_life_loss(self, reason=""):
        """Handle player death and respawn if lives remain."""
        self._create_explosion(self.player.x, self.player.y, 6, 'crash')
        self.lives -= 1
        
        if self.lives > 0:
            # Respawn player
            spawn_x, spawn_y = self._get_safe_spawn_point(gs.TILE_SIZE * 0.7, gs.TILE_SIZE * 0.7)
            drone_id = self.drone_system.get_selected_drone_id()
            drone_stats = self.drone_system.get_drone_stats(drone_id)
            sprite_key = f"drone_{drone_id}_ingame_sprite"
            
            self.player = PlayerDrone(spawn_x, spawn_y, drone_id, drone_stats, 
                                     self.asset_manager, sprite_key, 'crash', 
                                     self.drone_system)
            
            self.combat_controller.set_active_entities(
                player=self.player, 
                maze=self.maze, 
                power_ups_group=self.power_ups_group
            )
            
            self.set_story_message(f"Lives remaining: {self.lives}", 2000)
        else:
            # Game over
            self.scene_manager.set_game_state(gs.GAME_STATE_GAME_OVER)