# hyperdrone_core/game_loop_refactored.py
import sys
import os
import random
import math
import json
import logging

import pygame

from .state_manager import StateManager
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
from settings_manager import get_setting, set_setting, save_settings
import game_settings as gs  # Keep for compatibility during transition
from hyperdrone_core.camera import Camera

logger_gc = logging.getLogger(__name__)

class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Add reference to game_settings module for state classes to use during transition
        self.gs = gs

        try:
            info = pygame.display.Info()
            detected_width, detected_height = info.current_w, info.current_h
            final_width = max(1920, detected_width)
            final_height = max(1080, detected_height)
            set_setting("display", "WIDTH", final_width)
            set_setting("display", "HEIGHT", final_height)
            logger_gc.info(f"Screen resolution set to: {final_width}x{final_height}")
        except pygame.error as e:
            logger_gc.error(f"Could not detect screen size: {e}. Using default 1920x1080.")

        self.screen_flags = pygame.FULLSCREEN if get_setting("display", "FULLSCREEN_MODE", False) else 0
        self.screen = pygame.display.set_mode((get_setting("display", "WIDTH", 1920), 
                                              get_setting("display", "HEIGHT", 1080)), self.screen_flags)
        pygame.display.set_caption("HYPERDRONE")

        self.asset_manager = AssetManager(base_asset_folder_name="assets")
        self.drone_system = DroneSystem()
        
        self._preload_all_assets()

        self.clock = pygame.time.Clock()
        
        self.player_actions = PlayerActions(self)
        self.combat_controller = CombatController(self, self.asset_manager)
        self.puzzle_controller = PuzzleController(self, self.asset_manager)
        self.ui_flow_controller = UIFlowController(self)
        self.ui_manager = UIManager(self.screen, self.asset_manager, self, None, self.drone_system)
        
        # Use StateManager instead of SceneManager - initialize after ui_flow_controller
        self.state_manager = StateManager(self)
        
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
        
        # Update UI manager with state_manager reference
        self.ui_manager.state_manager = self.state_manager
        
        # Set dependencies for ui_flow_controller
        self.ui_flow_controller.set_dependencies(self.state_manager, self.ui_manager, self.drone_system)
        
        # Use state_manager instead of scene_manager in EventManager
        self.event_manager = EventManager(self, self.state_manager, self.combat_controller, self.puzzle_controller, self.ui_flow_controller)
        
        # Game state variables
        self.lives = get_setting("gameplay", "PLAYER_LIVES", 3)
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
        self.level_time_remaining_ms = get_setting("progression", "LEVEL_TIMER_DURATION", 120000)
        self.bonus_level_timer_start = 0
        self.bonus_level_duration_ms = get_setting("progression", "BONUS_LEVEL_DURATION_MS", 60000)
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
        
        # Initialize player to None
        self.player = None
        
        # Initialize with the main menu state
        self.state_manager.set_state("MainMenuState")
        
        logger_gc.info("GameController initialized successfully.")

    def _preload_all_assets(self):
        # Use the new method in AssetManager to preload all game assets
        self.asset_manager.preload_game_assets()
        logger_gc.info("GameController: All assets preloaded via AssetManager.")
    
    def run(self):
        while True:
            delta_time_ms = self.clock.tick(get_setting("display", "FPS", 60))
            
            # Process events
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.quit_game()
            
            # Let the current state handle events
            current_state = self.state_manager.get_current_state()
            if current_state and not self.paused:
                current_state.handle_events(events)
            
            # Update the current state
            if current_state and not self.paused:
                current_state.update(delta_time_ms)
            
            # Update UI flow controller
            current_time_ms = pygame.time.get_ticks()
            self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_state.get_state_id() if current_state else None)
            
            # Update story message
            if self.story_message_active and current_time_ms > self.story_message_end_time:
                self.story_message_active = False
                self.story_message = ""
            
            # Update state manager
            self.state_manager.update()
            
            # Draw the current state
            if current_state:
                current_state.draw(self.screen)
            
            # Draw UI
            self.ui_manager.draw_current_scene_ui()
            
            # Update display
            pygame.display.flip()

    def handle_state_transition(self, new_state, old_state, **kwargs):
        """Handle state transitions for UI flow controller"""
        self.paused = False
        
        # Map state IDs to UI flow controller initialization methods
        if new_state == "MainMenuState":
            self.ui_flow_controller.initialize_main_menu()
        elif new_state == "DroneSelectState":
            self.ui_flow_controller.initialize_drone_select()
        elif new_state == "SettingsState":
            self.ui_flow_controller.initialize_settings(self._get_settings_menu_items_data_structure())
        elif new_state == "LeaderboardState":
            self.ui_flow_controller.initialize_leaderboard()
        elif new_state == "CodexState":
            self.ui_flow_controller.initialize_codex()
        elif new_state == "EnterNameState":
            self.ui_flow_controller.initialize_enter_name()
        elif new_state == "GameIntroScrollState":
            self.ui_flow_controller.initialize_game_intro(self._load_intro_data())

    def toggle_pause(self):
        """Toggle the game's paused state"""
        self.paused = not self.paused
        if self.paused:
            print("Game paused")
        else:
            print("Game resumed")
        
        # Update music based on pause state
        self.state_manager._update_music()

    def quit_game(self):
        """Quit the game and save any necessary data"""
        if self.drone_system: 
            self.drone_system._save_unlocks()
        pygame.quit()
        sys.exit()
        
    def play_sound(self, key, vol=0.7):
        """Play a sound effect with the given key and volume."""
        if not hasattr(self, 'asset_manager'):
            return
            
        sound = self.asset_manager.get_sound(key)
        if sound:
            try:
                sound.set_volume(vol * get_setting("display", "SFX_VOLUME_MULTIPLIER", 0.7))
                sound.play()
            except Exception as e:
                logger_gc.error(f"Error playing sound '{key}': {e}")
        else:
            logger_gc.warning(f"Sound '{key}' not found")
            
    # Other methods remain the same as in the original GameController
    def _load_intro_data(self):
        """Load intro screen data from a JSON file."""
        try:
            with open("data/intro.json", "r") as file:
                intro_data = json.load(file)
                # Convert image_path to image_path_key for asset manager
                for scene in intro_data:
                    if "image_path" in scene:
                        # Extract just the filename from the path
                        image_key = scene["image_path"].split('/')[-1]
                        # Map to the preloaded asset keys
                        if "scene1.png" in scene["image_path"]:
                            scene["image_path_key"] = "images/lore/scene1.png"
                        elif "scene2.png" in scene["image_path"]:
                            scene["image_path_key"] = "images/lore/scene2.png"
                        elif "scene3.png" in scene["image_path"]:
                            scene["image_path_key"] = "images/lore/scene3.png"
                        elif "scene4.png" in scene["image_path"]:
                            scene["image_path_key"] = "images/lore/scene4.png"
                return intro_data
        except Exception as e:
            logger_gc.error(f"Error loading intro data: {e}")
            # Fallback data if file can't be loaded
            return [{"text": "Error loading intro data", "image_path_key": None}]
    def _get_settings_menu_items_data_structure(self):
        """Return the settings menu items data structure"""
        from constants import WEAPON_MODE_NAMES
        
        # Define weapon modes sequence
        weapon_modes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # WEAPON_MODE_DEFAULT through WEAPON_MODE_LIGHTNING
        
        return [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice",
             "choices":weapon_modes, "get_display":lambda val:WEAPON_MODE_NAMES.get(val,"Unknown")},
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
            {"label":"Fullscreen", "key":"FULLSCREEN_MODE","type":"choice", "choices":[False,True], "get_display":lambda v: "ON" if v else "OFF", "note":"Restart may be needed"},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ]
    def _get_safe_spawn_point(self, width, height):
        """Get a safe spawn point for the player that doesn't collide with walls"""
        # Default spawn point in the center of the screen
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        spawn_x = width // 2
        spawn_y = height // 2
        
        # If maze exists, find a safe spawn point
        if hasattr(self, 'maze') and self.maze:
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            # Try to find an empty cell
            for r in range(1, self.maze.actual_maze_rows - 1):
                for c in range(1, self.maze.actual_maze_cols - 1):
                    if self.maze.grid[r][c] == 0:  # 0 means empty path
                        # Convert maze coordinates to screen coordinates
                        spawn_x = c * tile_size + tile_size // 2
                        spawn_y = r * tile_size + tile_size // 2
                        return spawn_x, spawn_y
        
        return spawn_x, spawn_y
    def _handle_player_death_or_life_loss(self, message=""):
        """Handle player death or life loss."""
        if self.lives > 0:
            self.lives -= 1
            if self.lives <= 0:
                self.state_manager.set_state("GameOverState")
            else:
                # Respawn player
                self.set_story_message(f"{message} Lives remaining: {self.lives}", 3000)
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                spawn_x, spawn_y = self._get_safe_spawn_point(tile_size * 0.7, tile_size * 0.7)
                drone_id = self.drone_system.get_selected_drone_id()
                drone_stats = self.drone_system.get_drone_stats(drone_id)
                sprite_key = f"drone_{drone_id}_ingame_sprite"
                
                from entities import PlayerDrone
                self.player = PlayerDrone(
                    spawn_x, spawn_y, drone_id, drone_stats,
                    self.asset_manager, sprite_key, 'crash',
                    self.drone_system
                )
                
                # Reset player's weapon mode to default
                while self.player.current_weapon_mode != 0:
                    self.player.cycle_weapon_state()
                
                # Update combat controller with new player
                self.combat_controller.set_active_entities(
                    player=self.player,
                    maze=self.maze,
                    power_ups_group=self.power_ups_group
                )
        else:
            self.state_manager.set_state("GameOverState")
    
    def _create_enemy_explosion(self, x, y):
        """Create an explosion effect at the given position."""
        for _ in range(10):
            particle = Particle(
                x, y,
                random.uniform(-2, 2), random.uniform(-2, 2),
                random.choice([(255, 100, 0), (255, 165, 0), (255, 215, 0)]),
                random.randint(5, 10), random.randint(20, 40)
            )
            self.explosion_particles_group.add(particle)
        self.play_sound('prototype_drone_explode', 0.5)
    
    def check_for_all_enemies_killed(self):
        """Check if all enemies have been killed."""
        if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
            self.level_manager.all_enemies_killed_this_level = True
    
    def set_story_message(self, message, duration=5000):
        """Display a story message for the given duration."""
        self.story_message = message
        self.story_message_active = True
        self.story_message_end_time = pygame.time.get_ticks() + duration
    
    def trigger_story_beat(self, beat_id):
        """Trigger a story beat."""
        if beat_id not in self.triggered_story_beats:
            self.triggered_story_beats.add(beat_id)
            # Add any specific story beat handling here
    
    def _handle_collectible_collisions(self):
        """Handle collisions with collectible items."""
        if not self.player or not self.player.alive:
            return
            
        # Check for ring collisions
        player_group = pygame.sprite.GroupSingle(self.player)
        collision_func = pygame.sprite.collide_rect_ratio(0.7)
        
        # Collectible rings
        if self.collectible_rings_group:
            ring_hits = pygame.sprite.groupcollide(player_group, self.collectible_rings_group, False, True, collision_func)
            for player, rings_hit in ring_hits.items():
                for ring in rings_hit:
                    self.level_manager.collect_ring(ring.rect.center)
                    self.play_sound('collect_ring')
        
        # Core fragments
        if self.core_fragments_group:
            fragment_hits = pygame.sprite.groupcollide(player_group, self.core_fragments_group, False, False, collision_func)
            for player, fragments_hit in fragment_hits.items():
                for fragment in fragments_hit:
                    if not fragment.collected:
                        fragment.collected = True
                        fragment.kill()
                        self.play_sound('collect_fragment')
                        self.level_manager.add_score(500)
                        
                        # Add fragment to player's collection
                        if hasattr(fragment, 'fragment_id') and self.drone_system:
                            if self.drone_system.collect_core_fragment(fragment.fragment_id):
                                fragment_details = self.gs.CORE_FRAGMENT_DETAILS.get(f"fragment_{fragment.fragment_id}")
                                if fragment_details:
                                    self.set_story_message(f"Core Fragment Collected: {fragment_details.get('name', 'Unknown Fragment')}")
        
        # Check for other collectibles like vault logs, glyph tablets, etc.
        # (Implementation would be similar to the above)
    
    def _check_level_clear_condition(self):
        """Check if the level has been cleared."""
        self.level_manager.check_level_clear_condition()
