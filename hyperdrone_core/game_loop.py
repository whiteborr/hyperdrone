# hyperdrone_core/game_loop.py
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
from story import StoryManager, Chapter, Objective 

from entities import PlayerDrone, CoreReactor, Turret, LightningZap, Missile, Particle
from entities import MazeGuardian, SentinelDrone, EscapeZone, Maze, MazeChapter2, Bullet
from entities.collectibles import (
    Ring as CollectibleRing, WeaponUpgradeItem, ShieldItem, SpeedBoostItem,
    CoreFragmentItem, GlyphTabletItem, AncientAlienTerminal, 
    ArchitectEchoItem, CorruptedLogItem
)
from drone_management import DroneSystem, DRONE_DATA
from settings_manager import get_setting, set_setting, save_settings
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
        
        self.state_manager = StateManager(self)
        
        self.player = None
        self.maze = None
        self.camera = None
        
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
        self.corrupted_logs_group = pygame.sprite.Group() # New group for logs

        from .item_manager import ItemManager
        self.item_manager = ItemManager(self, self.asset_manager)
        
        self.ui_manager.state_manager = self.state_manager
        
        self.ui_flow_controller.set_dependencies(self.state_manager, self.ui_manager, self.drone_system)
        
        self.event_manager = EventManager(self, self.state_manager, self.combat_controller, self.puzzle_controller, self.ui_flow_controller)
        
        self.lives = get_setting("gameplay", "PLAYER_LIVES", 3)
        self.paused = False
        self.is_build_phase = False
        
        self.level_manager = LevelManager(self)
        
        from hyperdrone_core.game_events import EnemyDefeatedEvent
        self.event_manager.register_listener(EnemyDefeatedEvent, self.on_enemy_defeated_effects)
        
        self.hud_displayed_fragments = set()
        self.animating_fragments_to_hud = []
        self.fragment_ui_target_positions = {}
        
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
        
        self.story_message = ""
        self.story_message_active = False
        self.story_message_end_time = 0
        self.STORY_MESSAGE_DURATION = 5000
        self.triggered_story_beats = set()
        
        self.current_intro_image_asset_key = None
        self.intro_screen_text_surfaces_current = []
        self.intro_font_key = "codex_category_font"
        
        self.story_manager = StoryManager(state_manager_ref=self.state_manager)

        ch1_obj1 = Objective(objective_id="c1_collect_rings", description="Gather energy signatures (Collect 5 Rings)", obj_type="collect_all", target="rings")
        ch1_obj2 = Objective(objective_id="c1_clear_hostiles", description="Neutralize initial defense drones", obj_type="kill_all", target="standard_enemies")
        chapter1 = Chapter(chapter_id="chapter_1", title="Chapter 1: The Anomaly", 
                           description="A strange energy signature requires investigation. Enter the Vault and assess the situation.", 
                           objectives=[ch1_obj1, ch1_obj2], 
                           next_state_id="PlayingState")

        ch2_obj1 = Objective(objective_id="c2_defeat_guardian", description="Decommission the Vault's primary Guardian", obj_type="kill", target="MAZE_GUARDIAN")
        chapter2 = Chapter(chapter_id="chapter_2", title="Chapter 2: The Guardian", 
                           description="The Vault's defenses are active and hostile. A formidable Guardian blocks the path forward.", 
                           objectives=[ch2_obj1], 
                           next_state_id="BossFightState")

        ch3_obj1 = Objective(objective_id="c3_find_log_alpha", description="Find Corrupted Log Alpha", obj_type="collect", target="log_alpha")
        ch3_obj2 = Objective(objective_id="c3_find_log_beta", description="Access secure data with VANTIS drone", obj_type="collect", target="log_beta")
        chapter3 = Chapter(chapter_id="chapter_3", title="Chapter 3: The Corrupted Sector", 
                           description="This sector is unstable. Find out why the Vault is failing.", 
                           objectives=[ch3_obj1, ch3_obj2], 
                           next_state_id="CorruptedSectorState")

        self.story_manager.add_chapter(chapter1)
        self.story_manager.add_chapter(chapter2)
        self.story_manager.add_chapter(chapter3)
        
        self.story_manager.start_story()

        self.STORY_FONT_TITLE = pygame.font.Font(None, 48)
        self.STORY_FONT_BODY = pygame.font.Font(None, 28)
        self.STORY_TEXT_COLOR = (220, 220, 220)
        self.STORY_TITLE_COLOR = (255, 255, 255)
        
        self.player = None
        
        self.state_manager.set_state("MainMenuState")
        
        logger_gc.info("GameController initialized successfully.")

    def _preload_all_assets(self):
        self.asset_manager.preload_game_assets()
        logger_gc.info("GameController: All assets preloaded via AssetManager.")
    
    def run(self):
        while True:
            delta_time_ms = self.clock.tick(get_setting("display", "FPS", 60))
            
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.quit_game()
            
            current_state = self.state_manager.get_current_state()
            if current_state:
                current_state.handle_events(events)
            
            if current_state and not self.paused:
                current_state.update(delta_time_ms)
            
            current_time_ms = pygame.time.get_ticks()
            if current_state:
                self.ui_flow_controller.update(current_time_ms, delta_time_ms, current_state.get_state_id())
            
            if self.story_message_active and current_time_ms > self.story_message_end_time:
                self.story_message_active = False
                self.story_message = ""
            
            self.state_manager.update()
            
            if current_state:
                current_state.draw(self.screen)
            
            self.ui_manager.draw_current_scene_ui()
            self._draw_story_overlay(self.screen)

            pygame.display.flip()

    def handle_state_transition(self, new_state, old_state, **kwargs):
        self.paused = False
        
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
            self.ui_flow_controller.initialize_game_intro(self._load_intro_data_from_json_internal())

    def toggle_pause(self):
        self.paused = not self.paused
        logger_gc.info(f"Game {'paused' if self.paused else 'resumed'}.")
        self.state_manager._update_music()

    def quit_game(self):
        if self.drone_system: 
            self.drone_system._save_unlocks()
        pygame.quit()
        sys.exit()
        
    def play_sound(self, key, vol=0.7):
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
    
    def _get_settings_menu_items_data_structure(self):
        weapon_modes_sequence = get_setting("weapon_modes", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3])
        
        weapon_mode_names_dict = get_setting("weapon_modes", "WEAPON_MODE_NAMES", {})
        weapon_mode_names = {int(k): v for k, v in weapon_mode_names_dict.items()} if weapon_mode_names_dict else {
            0: "Standard", 1: "Spread", 2: "Rapid", 3: "Missile"
        }
        
        return [
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","category":"gameplay","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","category":"gameplay","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","category":"gameplay","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","category":"gameplay","type":"choice",
             "choices":weapon_modes_sequence, "get_display":lambda val:weapon_mode_names.get(val,"Unknown")},
            {"label":"Missile Damage","key":"weapons","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","category":"enemies","type":"numeric","min":0.5,"max":5,"step":0.5},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","category":"enemies","type":"numeric","min":25,"max":300,"step":25},
            {"label":"Level Timer (sec)","key":"LEVEL_TIMER_DURATION","category":"progression","type":"numeric","min":60000,"max":300000,"step":15000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","category":"powerups","type":"numeric","min":5000,"max":60000,"step":5000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label":"Speed Boost Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","category":"powerups","type":"numeric","min":3000,"max":30000,"step":2000,
             "is_ms_to_sec":True, "display_format": "{:.0f}s"},
            {"label": "Invincibility", "key": "PLAYER_INVINCIBILITY","category":"gameplay", "type": "choice",
             "choices": [False, True], "get_display": lambda val: "ON" if val else "OFF",
             "note": "Player does not take damage."},
            {"label":"Fullscreen", "key":"FULLSCREEN_MODE","category":"display", "type":"choice", "choices":[False,True], "get_display":lambda v: "ON" if v else "OFF", "note":"Restart may be needed"},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS_ACTION","type":"action"},
        ]
    
    def _get_safe_spawn_point(self, width, height):
        if self.maze and hasattr(self.maze, 'get_walkable_tiles_abs'):
            walkable = self.maze.get_walkable_tiles_abs()
            if walkable:
                return random.choice(walkable)
        return (200, 200)

    def _handle_player_death_or_life_loss(self, reason=""):
        self.player.alive = False 
        self._create_explosion(self.player.x, self.player.y, 6, 'crash')
        self.lives -= 1
        
        if self.lives > 0:
            self.set_story_message(f"Lives remaining: {self.lives}", 2000)
            self.state_manager.set_state(self.state_manager.get_current_state_id()) 
        else:
            self.state_manager.set_state("GameOverState")
    
    def _create_explosion(self, x, y, num_particles=20, specific_sound_key=None, is_enemy=False):
        orange_color = get_setting("colors", "ORANGE", (255, 165, 0))
        yellow_color = get_setting("colors", "YELLOW", (255, 255, 0))
        red_color = get_setting("colors", "RED", (255, 0, 0))
        white_color = get_setting("colors", "WHITE", (255, 255, 255))
        
        flash_size = random.uniform(3.0, 5.0) if is_enemy else 8.0
        self.explosion_particles_group.add(
            Particle(x, y, [white_color, yellow_color], 
                    min_speed=0.5, max_speed=1.0, 
                    min_size=flash_size*0.8, max_size=flash_size, 
                    gravity=0, shrink_rate=0.2, 
                    lifetime_frames=10 if is_enemy else 12)
        )
        
        if is_enemy:
            colors = [red_color, orange_color, yellow_color]
            particle_count = 15
            gravity = 0.01
            spread_angle = 15
            
            for _ in range(particle_count):
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
                            gravity=gravity, shrink_rate=0.08, 
                            lifetime_frames=lifetime,
                            base_angle_deg=angle, spread_angle_deg=spread_angle)
                )
        else:
            colors = [orange_color, yellow_color, red_color]
            for _ in range(num_particles):
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
            
    def on_enemy_defeated_effects(self, event):
        self._create_explosion(event.position[0], event.position[1], 15, None, True)
    
    def check_for_all_enemies_killed(self):
        if self.combat_controller.enemy_manager.get_active_enemies_count() == 0:
            self.level_manager.all_enemies_killed_this_level = True
    
    def _draw_game_world(self):
        black_color = get_setting("colors", "BLACK", (0, 0, 0))
        self.screen.fill(black_color)
        if self.maze:
            self.maze.draw(self.screen, self.camera)
        
        for item_group in [self.collectible_rings_group, self.power_ups_group, 
                          self.core_fragments_group, self.vault_logs_group,
                          self.glyph_tablets_group, self.architect_echoes_group,
                          self.corrupted_logs_group]: # Add new group to drawing
            for item in item_group:
                item.draw(self.screen, self.camera)
        
        self.explosion_particles_group.update()
        self.explosion_particles_group.draw(self.screen) 

        if self.player:
            self.player.draw(self.screen)
            
        current_game_state = self.state_manager.get_current_state_id()
        game_state_maze_defense = get_setting("game_states", "GAME_STATE_MAZE_DEFENSE", "maze_defense_mode")
        if current_game_state == game_state_maze_defense and hasattr(self, 'tower_defense_manager'):
            self.tower_defense_manager.draw(self.screen, self.camera)
            
        if self.combat_controller:
            self.combat_controller.enemy_manager.draw_all(self.screen, self.camera)
            
        if self.turrets_group:
            for turret in self.turrets_group:
                turret.draw(self.screen, self.camera)
                
        if self.reactor_group:
            for reactor in self.reactor_group:
                reactor.draw(self.screen, self.camera)
                
        ring_icon = self.asset_manager.get_image("ring_ui_icon")
        self.level_manager.draw_ring_animations(self.screen, ring_icon)
    
    def _handle_collectible_collisions(self):
        if not self.player or not hasattr(self.player, 'rect'):
            return
            
        for ring in pygame.sprite.spritecollide(self.player, self.collectible_rings_group, True):
            self.level_manager.collect_ring(ring.rect.center)
            self.play_sound('collect_ring')
            
        for powerup in pygame.sprite.spritecollide(self.player, self.power_ups_group, True):
            if isinstance(powerup, WeaponUpgradeItem):
                powerup.apply_effect(self.player)
                self.play_sound('weapon_upgrade_collect')
                if hasattr(self.ui_manager, 'update_weapon_icon_surface'):
                    self.ui_manager.update_weapon_icon_surface(self.player.current_weapon_mode)
            elif isinstance(powerup, (ShieldItem, SpeedBoostItem)):
                powerup.apply_effect(self.player)
                self.play_sound('collect_ring')
                
        for fragment in pygame.sprite.spritecollide(self.player, self.core_fragments_group, True):
            self.drone_system.collect_core_fragment(fragment.fragment_id)
            self.play_sound('collect_fragment')
            self.set_story_message(f"Core Fragment collected!", 2000)
            from .game_events import ItemCollectedEvent
            event = ItemCollectedEvent(item_id=fragment.fragment_id, item_type='core_fragment')
            self.event_manager.dispatch(event)

        # Handle Corrupted Log collisions
        for log in pygame.sprite.spritecollide(self.player, self.corrupted_logs_group, True):
            if hasattr(log, 'apply_effect'):
                log.apply_effect(self.player, self) # Pass game_controller instance
    
    def _check_level_clear_condition(self):
        return self.level_manager.check_level_clear_condition()
        
    def set_story_message(self, message, duration=5000):
        self.story_message = message
        self.story_message_active = True
        self.story_message_end_time = pygame.time.get_ticks() + duration
    
    def _draw_story_overlay(self, surface):
        current_chapter = self.story_manager.get_current_chapter()

        if not current_chapter:
            return

        title_surface = self.STORY_FONT_TITLE.render(current_chapter.title, True, self.STORY_TITLE_COLOR)
        surface.blit(title_surface, (20, 20))

        desc_surface = self.STORY_FONT_BODY.render(current_chapter.description, True, self.STORY_TEXT_COLOR)
        surface.blit(desc_surface, (20, 80))

        obj_y_pos = 150
        for obj in current_chapter.objectives:
            status = "[X]" if obj.is_complete else "[ ]"
            obj_text = f"{status} {obj.description}"
            
            obj_surface = self.STORY_FONT_BODY.render(obj_text, True, self.STORY_TEXT_COLOR)
            surface.blit(obj_surface, (40, obj_y_pos))
            obj_y_pos += 40
