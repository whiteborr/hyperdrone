# game_loop.py
import pygame
import sys
import os
import random
import math

# New Module Imports
from scene_manager import SceneManager
from event_manager import EventManager
from ui import UIManager 
from player_actions import PlayerActions
from collectibles import Ring, WeaponUpgradeItem, ShieldItem, SpeedBoostItem, CoreFragmentItem 

# Existing Game Logic Imports (these will be instantiated/managed by GameController)
from drone_system import DroneSystem
from player import Drone 
from enemy import Enemy
from maze import Maze
from game_settings import (
    WIDTH, HEIGHT, FPS, TILE_SIZE, MAZE_ROWS, 
    BLACK, # For default screen fill
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_BONUS_LEVEL_PLAYING, 
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, 
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    ARCHITECT_VAULT_BG_COLOR, # For vault background
    POWERUP_SPAWN_CHANCE, 
    WEAPON_MODES_SEQUENCE, WEAPON_MODE_NAMES, POWERUP_TYPES, 
    get_game_setting, set_game_setting, 
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED, 
    ARCHITECT_VAULT_DRONES_PER_WAVE, ARCHITECT_VAULT_GAUNTLET_WAVES, 
    PROTOTYPE_DRONE_HEALTH, PROTOTYPE_DRONE_SPEED, PROTOTYPE_DRONE_SHOOT_COOLDOWN, PROTOTYPE_DRONE_SPRITE_PATH,
    ARCHITECT_VAULT_EXTRACTION_TIMER_MS, DEFAULT_SETTINGS, ENEMY_BULLET_DAMAGE,
    PLAYER_DEFAULT_BULLET_SIZE 
)
import leaderboard
from drone_configs import DRONE_DISPLAY_ORDER, DRONE_DATA # Added DRONE_DATA for image loading


class GameController:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0)
        pygame.display.set_caption("HYPERDRONE")
        self.clock = pygame.time.Clock()

        self.drone_system = DroneSystem()
        
        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf")
        self.font_path_neuropol = os.path.join("assets", "fonts", "neuropol.otf")
        self.fonts = {} 
        self._initialize_fonts()

        self.scene_manager = SceneManager(self)
        self.event_manager = EventManager(self, self.scene_manager)
        self.ui_manager = UIManager(self.screen, self.fonts, self, self.scene_manager, self.drone_system)
        self.player_actions = PlayerActions(self) 

        self.player = None 
        self.maze = None
        self.enemies = pygame.sprite.Group()
        self.rings = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group()
        self.core_fragments = pygame.sprite.Group()
        self.architect_vault_terminals = pygame.sprite.Group()
        self.architect_vault_hazards = pygame.sprite.Group() 

        self.score = 0
        self.level = 1
        self.lives = get_game_setting("PLAYER_LIVES")
        self.paused = False
        
        self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")
        self.bonus_level_timer_start = 0 
        self.bonus_level_duration_ms = 60000 
        
        self.collected_rings = 0
        self.displayed_collected_rings = 0 
        self.total_rings_per_level = 5 
        self.animating_rings = [] 
        self.ring_ui_target_pos = (0,0) 

        self.all_enemies_killed_this_level = False
        self.level_cleared_pending_animation = False

        self.architect_vault_current_phase = None
        self.architect_vault_phase_timer_start = 0
        self.architect_vault_gauntlet_current_wave = 0
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self.architect_vault_message = ""
        self.architect_vault_message_timer = 0

        self.menu_options = ["Start Game", "Select Drone", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.player_name_input_display_cache = "" 
        self.leaderboard_scores = leaderboard.load_scores()
        
        self.drone_select_options = DRONE_DISPLAY_ORDER 
        self.selected_drone_preview_index = 0
        self.drone_grid_icons_cache = {} 
        self.drone_main_display_cache = {}
        self._load_drone_grid_icons() # Call image loading methods
        self._load_drone_main_display_images() # Call image loading methods


        self.sounds = {}
        self.load_sfx() 

        self.menu_stars = []
        self._initialize_menu_stars()
        
        self._initialize_settings_menu_items() 

        self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)


    def _initialize_fonts(self):
        font_sizes = {
            "ui_text": 28, "ui_values": 30, "ui_emoji_general": 32, "ui_emoji_small": 20,
            "small_text": 24, "medium_text": 48, "large_text": 74, "input_text": 50,
            "menu_text": 60, "title_text": 90, "drone_name_grid": 36, "drone_desc_grid": 22,
            "drone_unlock_grid": 20, "drone_name_cycle": 42, "drone_stats_label_cycle": 26,
            "drone_stats_value_cycle": 28, "drone_desc_cycle": 22, "drone_unlock_cycle": 20,
            "vault_message": 36, "vault_timer": 48, "leaderboard_header": 32, "leaderboard_entry": 28,
            "arrow_font_key": 60 
        }
        for name, size in font_sizes.items():
            font_file = self.font_path_neuropol if "emoji" not in name and name != "arrow_font_key" else self.font_path_emoji
            try:
                self.fonts[name] = pygame.font.Font(font_file, size)
            except pygame.error as e:
                print(f"Warning: Font loading error for '{name}' ({font_file}, size {size}): {e}. Using fallback.")
                self.fonts[name] = pygame.font.Font(None, size)

    def _initialize_menu_stars(self, num_stars=150):
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, WIDTH); y = random.randint(0, HEIGHT)
            speed = random.uniform(0.2, 1.0); size = random.randint(1, 3)
            self.menu_stars.append([x, y, speed, size])

    def _initialize_settings_menu_items(self):
        self.settings_items_data = [ 
            {"label":"Base Max Health","key":"PLAYER_MAX_HEALTH","type":"numeric","min":50,"max":200,"step":10,"note":"Original Drone base, others vary"},
            {"label":"Starting Lives","key":"PLAYER_LIVES","type":"numeric","min":1,"max":9,"step":1},
            {"label":"Base Speed","key":"PLAYER_SPEED","type":"numeric","min":1,"max":10,"step":1,"note":"Original Drone base, others vary"},
            {"label":"Initial Weapon","key":"INITIAL_WEAPON_MODE","type":"choice","choices":WEAPON_MODES_SEQUENCE,"get_display":lambda val:WEAPON_MODE_NAMES.get(val,"Unknown")},
            {"label":"Bullet Speed","key":"PLAYER_BULLET_SPEED","type":"numeric","min":2,"max":15,"step":1},
            {"label":"Bullet Lifetime (frames)","key":"PLAYER_BULLET_LIFETIME","type":"numeric","min":30,"max":300,"step":10},
            {"label":"Base Shoot Cooldown (ms)","key":"PLAYER_BASE_SHOOT_COOLDOWN","type":"numeric","min":100,"max":1000,"step":50},
            {"label":"Base Rapid Cooldown (ms)","key":"PLAYER_RAPID_FIRE_COOLDOWN","type":"numeric","min":50,"max":500,"step":25},
            {"label":"Missile Speed","key":"MISSILE_SPEED","type":"numeric","min":1.0,"max":20.0,"step":0.5},
            {"label":"Missile Lifetime (frames)","key":"MISSILE_LIFETIME","type":"numeric","min":30,"max":600,"step":20},
            {"label":"Base Missile Cooldown (ms)","key":"MISSILE_COOLDOWN","type":"numeric","min":1000,"max":10000,"step":500},
            {"label":"Missile Damage","key":"MISSILE_DAMAGE","type":"numeric","min":10,"max":100,"step":5},
            {"label":"Lightning Cooldown (ms)","key":"LIGHTNING_COOLDOWN","type":"numeric","min":200,"max":2000,"step":50},
            {"label":"Lightning Damage","key":"LIGHTNING_DAMAGE","type":"numeric","min":5,"max":50,"step":1},
            {"label":"Enemy Speed","key":"ENEMY_SPEED","type":"numeric","min":0.5,"max":5,"step":0.5},
            {"label":"Enemy Health","key":"ENEMY_HEALTH","type":"numeric","min":25,"max":300,"step":25},
            {"label":"Timer (sec)","key":"LEVEL_TIMER_DURATION","type":"numeric","min":60,"max":300,"step":15,"is_ms_to_sec":True},
            {"label":"Shield Duration (sec)","key":"SHIELD_POWERUP_DURATION","type":"numeric","min":10,"max":60,"step":5,"is_ms_to_sec":True},
            {"label":"Speed Duration (sec)","key":"SPEED_BOOST_POWERUP_DURATION","type":"numeric","min":5,"max":30,"step":2,"is_ms_to_sec":True},
            {"label":"Reset to Defaults","key":"RESET_SETTINGS","type":"action"},
        ]
        self.selected_setting_index = 0

    def _create_fallback_icon_surface(self, size=(80,80), text="?", color=(100,100,100), text_color=(255,255,255), font_key="medium_text"): # Added method to GameController
        """Creates a fallback surface for an icon if the image fails to load."""
        font_to_use = self.fonts.get(font_key)
        if not font_to_use: # Fallback if the specific font key isn't found
            font_to_use = pygame.font.Font(None, size[1]-4 if size[1]>10 else 10)

        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2) # Border
        if text and font_to_use:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e:
                print(f"Error rendering fallback icon text '{text}' with font '{font_key}': {e}")
        return surface

    def _load_drone_grid_icons(self): # Added method to GameController
        for drone_id, data in DRONE_DATA.items():
            icon_display_size = (80, 80) # Standard size for grid icons
            if "icon_path" in data and data["icon_path"] and os.path.exists(data["icon_path"]):
                try:
                    raw_icon = pygame.image.load(data["icon_path"]).convert_alpha()
                    self.drone_grid_icons_cache[drone_id] = pygame.transform.smoothscale(raw_icon, icon_display_size)
                except pygame.error as e:
                    print(f"Error loading grid icon for {drone_id} ('{data['icon_path']}'): {e}. Using fallback.")
                    initials = data.get("name", "?")[:2].upper()
                    self.drone_grid_icons_cache[drone_id] = self._create_fallback_icon_surface(
                        size=icon_display_size, text=initials, font_key="drone_name_grid"
                    )
            else:
                if "icon_path" in data and data["icon_path"]: print(f"Warning: Grid icon path not found: {data['icon_path']}")
                initials = data.get("name", "?")[:2].upper()
                self.drone_grid_icons_cache[drone_id] = self._create_fallback_icon_surface(
                    size=icon_display_size, text=initials, font_key="drone_name_grid"
                )
    
    def _load_drone_main_display_images(self): # Added method to GameController
        display_size = (200, 200) # Standard size for main preview image
        for drone_id, data in DRONE_DATA.items():
            image_surface = None
            # Prefer sprite_path for main display, fallback to icon_path if sprite_path is missing/invalid
            path_to_try = data.get("sprite_path") 
            if not path_to_try or not os.path.exists(path_to_try):
                path_to_try = data.get("icon_path") # Fallback to icon_path

            if path_to_try and os.path.exists(path_to_try):
                try:
                    loaded_image = pygame.image.load(path_to_try).convert_alpha()
                    image_surface = pygame.transform.smoothscale(loaded_image, display_size)
                except pygame.error as e:
                    print(f"Error loading main display image for {drone_id} ('{path_to_try}'): {e}. Using fallback.")
                    # Fallback handled below if image_surface is still None
            else:
                 if path_to_try: print(f"Warning: Main display image path not found: {path_to_try}")
            
            if image_surface is None: # If loading failed or path was invalid
                initials = data.get("name", "?")[:2].upper()
                image_surface = self._create_fallback_icon_surface(
                    size=display_size, text=initials, font_key="large_text"
                )
            self.drone_main_display_cache[drone_id] = image_surface


    def load_sfx(self):
        sound_paths = {
            'collect_ring':"assets/sounds/collect_ring.wav", 'weapon_upgrade_collect':"assets/sounds/collect_powerup.wav",
            'collect_fragment':"assets/sounds/collect_fragment.wav", 'crash':"assets/sounds/crash.wav",
            'shoot':"assets/sounds/shoot.wav", 'missile_launch':"assets/sounds/missile_launch.wav",
            'level_up':"assets/sounds/level_up.wav", 'player_death':"assets/sounds/player_death.wav",
            'enemy_shoot':"assets/sounds/enemy_shoot.wav", 'timer_out':"assets/sounds/timer_warning.wav",
            'ui_select':"assets/sounds/ui_select.wav", 'ui_confirm':"assets/sounds/ui_confirm.wav",
            'ui_denied':"assets/sounds/ui_denied.wav",
            'vault_alarm': "assets/sounds/vault_alarm.wav", 
            'vault_barrier_disable': "assets/sounds/vault_barrier_disable.wav", 
            'prototype_drone_explode': "assets/sounds/prototype_drone_explode.wav"
        }
        for name, path_str in sound_paths.items():
            try: self.sounds[name] = pygame.mixer.Sound(os.path.join(*path_str.split('/')))
            except pygame.error as e: print(f"Warning: Sound load error '{path_str}': {e}")
    
    def play_sound(self, name, volume=1.0): 
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume); self.sounds[name].play()

    def get_game_setting(self, key): 
        return get_game_setting(key)

    def set_game_setting(self, key, value): 
        set_game_setting(key, value)

    # --- Scene Initialization Methods (called by SceneManager) ---
    def initialize_main_menu_scene(self):
        self.selected_menu_option = 0 

    def initialize_drone_select_scene(self):
        current_selected_id = self.drone_system.get_selected_drone_id()
        try: 
            self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
        except ValueError: 
            self.selected_drone_preview_index = 0
        # Images are loaded once in GameController.__init__ now.
        # UIManager will access self.game_controller.drone_main_display_cache
        if hasattr(self.ui_manager, 'update_player_life_icon_surface'): # Ensure UIManager updates its own cache if needed
            self.ui_manager.update_player_life_icon_surface()


    def initialize_settings_scene(self):
        self.selected_setting_index = 0 

    def initialize_leaderboard_scene(self):
        self.leaderboard_scores = leaderboard.load_scores()

    def initialize_enter_name_scene(self):
        self.player_name_input_display_cache = "" 

    def initialize_game_session(self): 
        self.level = 1
        self.lives = self.get_game_setting("PLAYER_LIVES") 
        self.score = 0
        self.drone_system.set_player_level(self.level) 
        self.level_cleared_pending_animation = False
        self.all_enemies_killed_this_level = False
        
        self.maze = Maze(game_area_x_offset=0, maze_type="standard") 
        player_start_pos = self._get_safe_spawn_point(TILE_SIZE * 0.8, TILE_SIZE * 0.8)
        
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=False)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite = drone_config.get("ingame_sprite_path")

        self.player = Drone(player_start_pos[0], player_start_pos[1], drone_id=selected_drone_id,
                            drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite,
                            crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        
        if hasattr(self.ui_manager, 'update_player_life_icon_surface'): 
            self.ui_manager.update_player_life_icon_surface()
        
        self.enemies.empty(); self._spawn_enemies() 
        if self.player: self.player.bullets_group.empty(); self.player.missiles_group.empty()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.collected_rings = 0; self.displayed_collected_rings = 0; self.total_rings_per_level = 5
        self.paused = False; self.player_name_input_display_cache = ""; self.animating_rings.clear()
        
        self._place_collectibles(initial_setup=True)
        self._reset_level_timer_internal() 
        # SceneManager set_game_state to PLAYING is called by the menu action.

    def initialize_architect_vault_session(self):
        print("--- GameController: Initializing Architect's Vault! ---")
        self.maze = Maze(game_area_x_offset=0, maze_type="architect_vault") 
        
        prev_weapon_mode_index = -1
        prev_current_weapon_mode = -1

        if self.player: 
            safe_spawn = self._get_safe_spawn_point(TILE_SIZE*0.8, TILE_SIZE*0.8)
            current_drone_id = self.player.drone_id
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=True)
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            
            prev_weapon_mode_index = self.player.weapon_mode_index
            prev_current_weapon_mode = self.player.current_weapon_mode

            self.player.reset(safe_spawn[0], safe_spawn[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite)
        else: 
            selected_drone_id = self.drone_system.get_selected_drone_id()
            effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=True)
            drone_config = self.drone_system.get_drone_config(selected_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            safe_spawn = self._get_safe_spawn_point(TILE_SIZE*0.8, TILE_SIZE*0.8)
            self.player = Drone(safe_spawn[0], safe_spawn[1], drone_id=selected_drone_id,
                                drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite,
                                crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)

        if prev_weapon_mode_index != -1 and self.player: # Ensure player exists before setting attributes
            self.player.weapon_mode_index = prev_weapon_mode_index
            self.player.current_weapon_mode = prev_current_weapon_mode
            self.player._update_weapon_attributes() 

        if self.player: # Ensure player exists before these operations
            self.player.reset_active_powerups() 
            self.player.alive = True 
            self.player.health = self.player.max_health 
            self.player.moving_forward = False 
            
            if hasattr(self.player, 'activate_shield'):
                self.player.activate_shield(1500, is_from_speed_boost=False) # 1.5 second shield
                print("Activated temporary spawn shield for Architect's Vault.")

        self.enemies.empty() 
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty() 
        self.architect_vault_terminals.empty(); self.architect_vault_hazards.empty()

        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.level_time_remaining_ms = 0 

    # --- Methods called by SceneManager for specific vault phases ---
    def start_architect_vault_intro(self):
        self.architect_vault_current_phase = "intro"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.architect_vault_message = "The Architect's Vault... Entry protocol initiated."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000 

    def start_architect_vault_entry_puzzle(self):
        self.architect_vault_current_phase = "entry_puzzle"
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
        self._spawn_architect_vault_terminals() 
        self.architect_vault_message = "Activate terminals with Core Fragments."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000

    def start_architect_vault_gauntlet(self):
        self.architect_vault_current_phase = "gauntlet_intro" 
        self.architect_vault_gauntlet_current_wave = 0
        self.enemies.empty() 
        self.architect_vault_message = "Security systems online. Prepare for hostiles."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 3000

    def start_architect_vault_extraction(self):
        self.architect_vault_current_phase = "extraction"
        self.architect_vault_phase_timer_start = pygame.time.get_ticks() 
        self.play_sound('vault_alarm', 0.7)
        self.architect_vault_message = "SELF-DESTRUCT SEQUENCE ACTIVATED! ESCAPE NOW!"
        self.architect_vault_message_timer = pygame.time.get_ticks() + ARCHITECT_VAULT_EXTRACTION_TIMER_MS
        self.level_time_remaining_ms = ARCHITECT_VAULT_EXTRACTION_TIMER_MS 

    def handle_architect_vault_success(self):
        self.architect_vault_message = "Vault Conquered! Blueprint Acquired!"
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        self.drone_system.mark_architect_vault_completed(True)
        self.score += 2500 
        self.drone_system.add_player_cores(500) 
        self.drone_system._save_unlocks() 

    def handle_architect_vault_failure(self):
        self.architect_vault_message = "Vault Mission Failed. Returning to base..."
        self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        self.drone_system.mark_architect_vault_completed(False) 
    
    def handle_game_over(self):
        self.drone_system.set_player_level(self.level) 
        self.drone_system._save_unlocks() 
        # UIManager will draw the game over screen. EventManager handles input for next state.

    # --- Update method for the main game loop ---
    def update(self):
        current_game_state = self.scene_manager.get_current_state()
        current_time = pygame.time.get_ticks()

        if current_game_state == GAME_STATE_PLAYING and not self.paused:
            self._update_playing_state(current_time)
        elif current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused: # Old bonus
            self._update_bonus_level_state(current_time) 
        elif current_game_state.startswith("architect_vault") and not self.paused:
            self._update_architect_vault_state(current_time) 
        elif current_game_state in [GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, 
                                    GAME_STATE_DRONE_SELECT, GAME_STATE_MAIN_MENU]:
            if hasattr(self, 'menu_stars'):
                for star in self.menu_stars:
                    star[0] -= star[2]
                    if star[0] < 0: star[0] = WIDTH; star[1] = random.randint(0, HEIGHT)
        
        if hasattr(self.scene_manager, 'update'):
            self.scene_manager.update()


    # --- State-specific update methods ---
    def _update_playing_state(self, current_time):
        if not self.player or not self.maze: 
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return

        if not self.level_cleared_pending_animation:
            elapsed_time_current_level_ms = current_time - self.level_timer_start_ticks
            self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION") - elapsed_time_current_level_ms
            if self.level_time_remaining_ms <= 0:
                self.play_sound('timer_out'); self.lives -= 1
                if self.player: self.player.reset_active_powerups()
                if self.lives <= 0: self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
                else: self._reset_player_after_death(); self._reset_level_timer_internal()
                return
            
            if self.player.alive: self.player.update(current_time, self.maze, self.enemies, 0) 
            
            for enemy_obj in list(self.enemies): 
                enemy_obj.update(self.player.get_position() if self.player else (0,0), self.maze, current_time)
                if not enemy_obj.alive and (not hasattr(enemy_obj, 'bullets') or not enemy_obj.bullets): enemy_obj.kill() 
            
            for p_up in list(self.power_ups): 
                if p_up.update(): p_up.kill() 
            for fragment in list(self.core_fragments): fragment.update()
            self.rings.update(); self._check_collisions_playing() 
            
            if FPS > 0 and random.random() < (get_game_setting("POWERUP_SPAWN_CHANCE") / FPS): self._try_spawn_powerup() 
            
            if self.player and not self.player.alive: 
                self.play_sound('player_death'); self.lives -= 1
                if self.lives <= 0: self.scene_manager.set_game_state(GAME_STATE_GAME_OVER)
                else: self._reset_player_after_death(); self._reset_level_timer_internal()
                return
        
        for ring_anim in list(self.animating_rings): 
            dx = ring_anim['target_pos'][0]-ring_anim['pos'][0]; dy = ring_anim['target_pos'][1]-ring_anim['pos'][1]
            dist = math.hypot(dx,dy)
            if dist < ring_anim['speed']:
                self.animating_rings.remove(ring_anim); self.displayed_collected_rings += 1
                self.displayed_collected_rings = min(self.displayed_collected_rings,self.collected_rings)
            else: ring_anim['pos'][0]+=(dx/dist)*ring_anim['speed']; ring_anim['pos'][1]+=(dy/dist)*ring_anim['speed']

        if self.level_cleared_pending_animation and not self.animating_rings:
            self._level_up_logic(); self.level_cleared_pending_animation = False 

    def _update_bonus_level_state(self, current_time): # Old bonus
        if not self.player or not self.player.alive:
            self._end_bonus_level_logic(completed=False); return 
        self.player.update(current_time, self.maze, None, 0)
        elapsed_bonus_time = current_time - self.bonus_level_timer_start 
        bonus_duration = getattr(self, 'bonus_level_duration_ms', 60000) 
        self.level_time_remaining_ms = max(0, bonus_duration - elapsed_bonus_time)
        if self.level_time_remaining_ms <= 0:
            self._end_bonus_level_logic(completed=True); return

    def _update_architect_vault_state(self, current_time):
        if not self.player or not self.maze:
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU); return 
        if not self.player.alive: # Check if player died during a vault phase
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return
        if self.paused: return 

        self.player.update(current_time, self.maze, self.enemies, 0) 

        if self.architect_vault_current_phase == "intro":
            if current_time > self.architect_vault_message_timer: 
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        elif self.architect_vault_current_phase == "entry_puzzle":
            if hasattr(self.architect_vault_terminals, 'update'): self.architect_vault_terminals.update() 
            # Puzzle solved transitions are handled by try_activate_vault_terminal via EventManager
        elif self.architect_vault_current_phase == "gauntlet_intro":
            if current_time > self.architect_vault_message_timer:
                self.architect_vault_gauntlet_current_wave = 1
                self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                self._spawn_prototype_drones(ARCHITECT_VAULT_DRONES_PER_WAVE[0])
                self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif self.architect_vault_current_phase and self.architect_vault_current_phase.startswith("gauntlet_wave"):
            self.enemies.update(self.player.get_position() if self.player else (0,0), self.maze, current_time)
            self._check_collisions_architect_vault() 
            if not self.enemies: 
                self.play_sound('level_up') 
                self.architect_vault_gauntlet_current_wave += 1
                if self.architect_vault_gauntlet_current_wave > ARCHITECT_VAULT_GAUNTLET_WAVES:
                    self.architect_vault_message = "Gauntlet cleared. Accessing core..."
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                    self.architect_vault_current_phase = "gauntlet_cleared_transition" 
                    self.architect_vault_phase_timer_start = current_time 
                else:
                    self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                    num_drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[self.architect_vault_gauntlet_current_wave - 1]
                    self._spawn_prototype_drones(num_drones_this_wave)
                    self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        elif self.architect_vault_current_phase == "gauntlet_cleared_transition":
             if current_time - self.architect_vault_phase_timer_start > 2000: 
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)
        elif self.architect_vault_current_phase == "extraction":
            time_elapsed_extraction = current_time - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, ARCHITECT_VAULT_EXTRACTION_TIMER_MS - time_elapsed_extraction)
            if self.level_time_remaining_ms <= 0:
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS) 
            if random.random() < 0.005 : 
                 if len(self.enemies) < 2: self._spawn_prototype_drones(1) 
            self.enemies.update(self.player.get_position() if self.player else (0,0), self.maze, current_time) 
            self._check_collisions_architect_vault()

    # --- Helper methods for game logic (internal to GameController) ---
    def _get_random_valid_fragment_tile(self, maze_grid, maze_cols, maze_rows, existing_fragment_tiles=None):
        """ Helper to find a random valid tile for fragment spawning. """
        if existing_fragment_tiles is None:
            existing_fragment_tiles = set()
        available_path_tiles = []
        for r_idx in range(maze_rows): # Use different loop var name
            for c_idx in range(maze_cols): # Use different loop var name
                if 0 <= r_idx < len(maze_grid) and 0 <= c_idx < len(maze_grid[r_idx]):
                    if maze_grid[r_idx][c_idx] == 0 and (c_idx, r_idx) not in existing_fragment_tiles:
                        available_path_tiles.append((c_idx, r_idx))
        if not available_path_tiles:
            return None
        return random.choice(available_path_tiles)

    def _spawn_core_fragments_for_level(self):
        """Spawns core fragments in REGULAR levels based on conditions."""
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        occupied_fragment_tiles_this_level = set()
        for frag_key, details in CORE_FRAGMENT_DETAILS.items():
            if not details: continue 
            spawn_info = details.get("spawn_info", {})
            if spawn_info.get("level") == self.level and not self.drone_system.has_collected_fragment(details["id"]):
                random_tile = self._get_random_valid_fragment_tile( # Call internal helper
                    self.maze.grid, self.maze.actual_maze_cols, self.maze.actual_maze_rows, # Use maze attributes
                    occupied_fragment_tiles_this_level
                )
                if random_tile:
                    tile_x, tile_y = random_tile
                    # game_area_x_offset is 0 for GameController's direct maze interaction
                    abs_x = tile_x * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset 
                    abs_y = tile_y * TILE_SIZE + TILE_SIZE // 2
                    self.core_fragments.add(CoreFragmentItem(abs_x, abs_y, details["id"], details))
                    occupied_fragment_tiles_this_level.add(random_tile)

    def _get_safe_spawn_point(self, drone_check_width, drone_check_height):
        if not self.maze: return (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2) 
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return (WIDTH // 4, GAME_PLAY_AREA_HEIGHT // 2)
        
        path_cells_absolute = [(x + self.maze.game_area_x_offset, y) for x, y in path_cells_relative]
        random.shuffle(path_cells_absolute)
        for spawn_x, spawn_y in path_cells_absolute:
            if not self.maze.is_wall(spawn_x, spawn_y, drone_check_width, drone_check_height):
                return (spawn_x, spawn_y)
        return path_cells_absolute[0] 

    def _spawn_enemies(self): # For regular levels
        self.enemies.empty()
        num_enemies = min(self.level + 1, 6) 
        path_cells_relative = self.maze.get_path_cells() if self.maze else []
        enemy_shoot_sound = self.sounds.get('enemy_shoot')
        # Get PLAYER_DEFAULT_BULLET_SIZE once to pass to Enemy constructor
        player_bullet_size_from_settings = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

        for _ in range(num_enemies):
            if not path_cells_relative: break
            spawn_attempts = 0; spawned = False
            while spawn_attempts < 10 and not spawned:
                rel_x, rel_y = random.choice(path_cells_relative)
                abs_x, abs_y = rel_x + self.maze.game_area_x_offset, rel_y
                if self.player and math.hypot(abs_x-self.player.x,abs_y-self.player.y) < TILE_SIZE*5:
                    spawn_attempts+=1; continue
                if any(math.hypot(abs_x-e.x,abs_y-e.y) < TILE_SIZE*2 for e in self.enemies):
                    spawn_attempts+=1; continue
                self.enemies.add(Enemy(abs_x,abs_y, player_bullet_size_from_settings, shoot_sound=enemy_shoot_sound)); spawned=True # Pass player_bullet_size
            if not spawned and path_cells_relative: 
                rel_fx,rel_fy = random.choice(path_cells_relative)
                abs_fx,abs_fy = rel_fx + self.maze.game_area_x_offset, rel_fy
                self.enemies.add(Enemy(abs_fx,abs_fy, player_bullet_size_from_settings, shoot_sound=enemy_shoot_sound)) # Pass player_bullet_size
    
    def _spawn_prototype_drones(self, count): # For Architect's Vault
        if not self.maze or not self.player: return
        path_cells_rel = self.maze.get_path_cells()
        enemy_shoot_sound = self.sounds.get('enemy_shoot') 
        player_bullet_size_from_settings = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")


        for _ in range(count):
            if not path_cells_rel: break
            spawn_attempts = 0; spawned = False
            while spawn_attempts < 10 and not spawned:
                rel_x, rel_y = random.choice(path_cells_rel)
                abs_x, abs_y = rel_x + self.maze.game_area_x_offset, rel_y
                if math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 7:
                    spawn_attempts += 1; continue
                if any(math.hypot(abs_x - e.x, abs_y - e.y) < TILE_SIZE * 3 for e in self.enemies):
                    spawn_attempts += 1; continue
                
                proto_drone = Enemy(abs_x, abs_y, player_bullet_size_from_settings, shoot_sound=enemy_shoot_sound, sprite_path=PROTOTYPE_DRONE_SPRITE_PATH) # Pass player_bullet_size
                proto_drone.health = PROTOTYPE_DRONE_HEALTH
                proto_drone.max_health = PROTOTYPE_DRONE_HEALTH
                proto_drone.speed = PROTOTYPE_DRONE_SPEED
                proto_drone.shoot_cooldown = PROTOTYPE_DRONE_SHOOT_COOLDOWN
                self.enemies.add(proto_drone)
                spawned = True
            if not spawned and path_cells_rel: 
                rel_fx,rel_fy = random.choice(path_cells_rel)
                abs_fx,abs_fy = rel_fx + self.maze.game_area_x_offset, rel_fy
                proto_drone = Enemy(abs_fx,abs_fy, player_bullet_size_from_settings, shoot_sound=enemy_shoot_sound, sprite_path=PROTOTYPE_DRONE_SPRITE_PATH) # Pass player_bullet_size
                proto_drone.health = PROTOTYPE_DRONE_HEALTH; proto_drone.max_health = PROTOTYPE_DRONE_HEALTH
                proto_drone.speed = PROTOTYPE_DRONE_SPEED; proto_drone.shoot_cooldown = PROTOTYPE_DRONE_SHOOT_COOLDOWN
                self.enemies.add(proto_drone)

    def _spawn_architect_vault_terminals(self): # Renamed from Game
        self.architect_vault_terminals.empty()
        if not self.maze: return
        path_cells = self.maze.get_path_cells()
        if len(path_cells) < TOTAL_CORE_FRAGMENTS_NEEDED: 
            print("Warning: Not enough path cells to spawn all vault terminals.")
            return

        for i in range(TOTAL_CORE_FRAGMENTS_NEEDED):
            if not path_cells: break
            pos_rel = random.choice(path_cells)
            path_cells.remove(pos_rel) 
            abs_x = pos_rel[0] + self.maze.game_area_x_offset
            abs_y = pos_rel[1]
            terminal = pygame.sprite.Sprite()
            terminal.image = pygame.Surface([TILE_SIZE*0.5, TILE_SIZE*0.5])
            terminal.image.fill(PURPLE) 
            terminal.rect = terminal.image.get_rect(center=(abs_x, abs_y))
            terminal.terminal_id = i 
            terminal.is_active = False 
            self.architect_vault_terminals.add(terminal)

    def _try_spawn_powerup(self): # Renamed from Game
        if len(self.power_ups) < get_game_setting("MAX_POWERUPS_ON_SCREEN"): # Use getter
            path_cells_relative = self.maze.get_path_cells() if self.maze else []
            if not path_cells_relative: return
            existing_coords_abs = set(r.rect.center for r in self.rings)
            for p_up in self.power_ups: existing_coords_abs.add(p_up.rect.center)
            for frag in self.core_fragments: existing_coords_abs.add(frag.rect.center)
            
            available_cells_abs = [(rcx+self.maze.game_area_x_offset,rcy) for rcx,rcy in path_cells_relative if (rcx+self.maze.game_area_x_offset,rcy) not in existing_coords_abs]
            if not available_cells_abs: return
            
            abs_x, abs_y = random.choice(available_cells_abs)
            chosen_type_key = random.choice(["weapon_upgrade","shield","speed_boost"])
            new_powerup = None
            if chosen_type_key=="weapon_upgrade": new_powerup=WeaponUpgradeItem(abs_x,abs_y)
            elif chosen_type_key=="shield": new_powerup=ShieldItem(abs_x,abs_y)
            elif chosen_type_key=="speed_boost": new_powerup=SpeedBoostItem(abs_x,abs_y)
            if new_powerup: self.power_ups.add(new_powerup)

    def _place_collectibles(self, initial_setup=False): # Renamed from Game
        path_cells_relative = self.maze.get_path_cells() if self.maze else []
        if initial_setup and path_cells_relative:
            self.rings.empty()
            shuffled_path_cells_relative = random.sample(path_cells_relative, len(path_cells_relative))
            for i in range(min(self.total_rings_per_level, len(shuffled_path_cells_relative))):
                rel_x, rel_y = shuffled_path_cells_relative[i]
                abs_x = rel_x + self.maze.game_area_x_offset; abs_y = rel_y
                self.rings.add(Ring(abs_x, abs_y))
        
        self._spawn_core_fragments_for_level() # Renamed
        self._try_spawn_powerup() 

    def _check_collisions_playing(self): # Renamed from Game.check_collisions
        if not self.player or not self.player.alive: return
        
        if not self.level_cleared_pending_animation: 
            collided_rings_sprites = pygame.sprite.spritecollide(self.player,self.rings,True,pygame.sprite.collide_rect_ratio(0.7))
            for ring_sprite in collided_rings_sprites:
                self.score += 10; self.play_sound('collect_ring'); self.collected_rings += 1
                self.drone_system.add_player_cores(5) 
                
                anim_ring_surf = None
                if hasattr(ring_sprite,'image'):
                    try: anim_ring_surf = pygame.transform.smoothscale(ring_sprite.image.copy(), (15,15))
                    except: anim_ring_surf = self.ui_manager._create_fallback_icon((15,15),"",GOLD, font_key="ui_emoji_small") # Use UIManager's helper
                if anim_ring_surf: self.animating_rings.append({'pos':list(ring_sprite.rect.center),'target_pos':self.ring_ui_target_pos,'speed':15,'surface':anim_ring_surf,'alpha':255})
                
                self._check_for_level_clear_condition() # Renamed
                if self.level_cleared_pending_animation: break 
        
        collided_powerups = pygame.sprite.spritecollide(self.player,self.power_ups,False,pygame.sprite.collide_rect_ratio(0.7))
        for item in collided_powerups:
            if not item.collected and not item.expired and hasattr(item,'apply_effect'):
                item.apply_effect(self.player); item.collected=True; item.kill()
                self.play_sound('weapon_upgrade_collect'); self.score+=25
        
        collided_fragments = pygame.sprite.spritecollide(self.player,self.core_fragments,False,pygame.sprite.collide_rect_ratio(0.7))
        for fragment in collided_fragments:
            if not fragment.collected and fragment.apply_effect(self.player,self): 
                self.play_sound('collect_fragment'); fragment.kill(); self.score+=100
                if self.drone_system.are_all_core_fragments_collected():
                    self.architect_vault_message = "All Fragments Acquired! Vault Access Imminent!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 4000

        if self.player.alive:
            player_projectiles = pygame.sprite.Group()
            player_projectiles.add(self.player.bullets_group); player_projectiles.add(self.player.missiles_group)
            for projectile in list(player_projectiles):
                if not projectile.alive: continue
                hit_enemies = pygame.sprite.spritecollide(projectile,self.enemies,False,pygame.sprite.collide_rect_ratio(0.8))
                for enemy_obj in hit_enemies:
                    if enemy_obj.alive:
                        enemy_obj.take_damage(projectile.damage)
                        if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                             projectile.pierces_done +=1
                        else:
                             projectile.alive=False; projectile.kill()
                        if not enemy_obj.alive:
                            self.score+=50; self.drone_system.add_player_cores(25)
                            if all(not e.alive for e in self.enemies): self.all_enemies_killed_this_level=True
                        if not projectile.alive: break 
            
            for enemy_obj in self.enemies:
                if hasattr(enemy_obj, 'bullets'): 
                    for bullet_obj in list(enemy_obj.bullets):
                        if self.player.alive and bullet_obj.rect.colliderect(self.player.rect):
                            self.player.take_damage(ENEMY_BULLET_DAMAGE, self.sounds.get('crash'))
                            bullet_obj.alive=False; bullet_obj.kill()
                        if not bullet_obj.alive and bullet_obj in enemy_obj.bullets:
                            enemy_obj.bullets.remove(bullet_obj) 
            
            enemy_collisions = pygame.sprite.spritecollide(self.player,self.enemies,False,pygame.sprite.collide_rect_ratio(0.7))
            for enemy_obj in enemy_collisions:
                if enemy_obj.alive: self.player.take_damage(34, self.sounds.get('crash')) 
                if not self.player.alive: break
    
    def _check_collisions_architect_vault(self): # Renamed from Game
        if not self.player or not self.player.alive: return

        player_projectiles = pygame.sprite.Group()
        if self.player:
            player_projectiles.add(self.player.bullets_group)
            player_projectiles.add(self.player.missiles_group)

        for projectile in list(player_projectiles):
            if not projectile.alive: continue
            hit_enemies = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.7))
            for enemy_obj in hit_enemies:
                if enemy_obj.alive:
                    enemy_obj.take_damage(projectile.damage)
                    if hasattr(projectile, 'max_pierces') and projectile.pierces_done < projectile.max_pierces:
                        projectile.pierces_done +=1
                    else:
                        projectile.alive = False; projectile.kill() 
                    
                    if not enemy_obj.alive:
                        self.score += 75 
                        self.drone_system.add_player_cores(10) 
                        self.play_sound('prototype_drone_explode') 
                    if not projectile.alive: break 

        for enemy_obj in self.enemies:
            if not enemy_obj.alive: continue
            if hasattr(enemy_obj, 'bullets'):
                for bullet_obj in list(enemy_obj.bullets): 
                    if self.player.alive and bullet_obj.rect.colliderect(self.player.rect): 
                        self.player.take_damage(get_game_setting("ENEMY_BULLET_DAMAGE") * 1.2, self.sounds.get('crash')) 
                        bullet_obj.alive = False; bullet_obj.kill()
                    if not bullet_obj.alive and bullet_obj in enemy_obj.bullets: 
                        enemy_obj.bullets.remove(bullet_obj)
        
        if self.player.alive:
            enemy_collisions = pygame.sprite.spritecollide(self.player, self.enemies, False, pygame.sprite.collide_rect_ratio(0.6))
            for enemy_obj in enemy_collisions:
                if enemy_obj.alive:
                    self.player.take_damage(40, self.sounds.get('crash')) 
                if not self.player.alive: break

    def _check_for_level_clear_condition(self): # Renamed from Game
        if self.player and self.collected_rings >= self.total_rings_per_level and not self.level_cleared_pending_animation:
            self.player.moving_forward = False; self.level_cleared_pending_animation = True

    def _level_up_logic(self, from_bonus_level_completion=False): # Renamed from Game.level_up
        prev_weapon_mode_index = -1
        prev_current_weapon_mode = -1
        if self.player:
            prev_weapon_mode_index = self.player.weapon_mode_index
            prev_current_weapon_mode = self.player.current_weapon_mode

        if self.drone_system.are_all_core_fragments_collected() and not self.drone_system.has_completed_architect_vault():
            self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_INTRO)
            return

        if not from_bonus_level_completion: self.level += 1
        
        self.collected_rings = 0; self.displayed_collected_rings = 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15)
        self.drone_system.set_player_level(self.level) 
        
        if self.player:
            if self.all_enemies_killed_this_level: self.player.cycle_weapon_state(force_cycle=False)
            self.player.health = min(self.player.health + 25, self.player.max_health)
            self.player.reset_active_powerups()
        
        self.all_enemies_killed_this_level = False
        self.maze = Maze(game_area_x_offset=0, maze_type="standard")
        new_player_pos = self._get_safe_spawn_point(TILE_SIZE*0.8, TILE_SIZE*0.8)
        
        if self.player:
            current_drone_id = self.player.drone_id
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) 
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite)
            if prev_weapon_mode_index != -1:
                self.player.weapon_mode_index = prev_weapon_mode_index
                self.player.current_weapon_mode = prev_current_weapon_mode
                self.player._update_weapon_attributes()
        
        self._spawn_enemies(); self.core_fragments.empty(); self._place_collectibles(initial_setup=True)
        self._reset_level_timer_internal(); self.play_sound('level_up')
        self.animating_rings.clear()
        if self.player: self.player.moving_forward = False
        
        if not self.scene_manager.get_current_state().startswith("architect_vault"):
            self.scene_manager.set_game_state(GAME_STATE_PLAYING)

    def _reset_player_after_death(self): # Renamed from Game
        prev_weapon_mode_index = -1
        prev_current_weapon_mode = -1
        if self.player:
            prev_weapon_mode_index = self.player.weapon_mode_index
            prev_current_weapon_mode = self.player.current_weapon_mode

        new_player_pos = self._get_safe_spawn_point(TILE_SIZE*0.8, TILE_SIZE*0.8)
        if self.player:
            current_drone_id = self.player.drone_id
            in_vault = self.scene_manager.get_current_state().startswith("architect_vault")
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=in_vault) 
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite,
                              health_override=None) 
            if prev_weapon_mode_index != -1:
                self.player.weapon_mode_index = prev_weapon_mode_index
                self.player.current_weapon_mode = prev_current_weapon_mode
                self.player._update_weapon_attributes()
        self.animating_rings.clear(); self.level_cleared_pending_animation = False

    def _reset_level_timer_internal(self): # Renamed from Game._reset_level_timer
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")

    def _end_bonus_level_logic(self, completed=True): # Renamed from Game.end_bonus_level
        print(f"--- Old Bonus Level Ended. Completed: {completed} ---")
        if completed: self.score += 500; self.drone_system.add_player_cores(250)
        self.drone_system._save_unlocks() 
        self._level_up_logic(from_bonus_level_completion=True) 

    def try_activate_vault_terminal(self, terminal_idx): # Moved from Game, called by EventManager
        if not (0 <= terminal_idx < len(self.architect_vault_puzzle_terminals_activated)): return

        target_terminal_sprite = None
        for t_sprite in self.architect_vault_terminals:
            if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx:
                target_terminal_sprite = t_sprite; break
        
        if not target_terminal_sprite or (hasattr(target_terminal_sprite, 'is_active') and target_terminal_sprite.is_active): return

        collected_fragment_ids = self.drone_system.get_collected_fragments_ids()
        required_fragment_id = None
        if CORE_FRAGMENT_DETAILS: 
            frag_keys = list(CORE_FRAGMENT_DETAILS.keys())
            if terminal_idx < len(frag_keys) and CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]]: # Check details exist
                required_fragment_id = CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]].get("id")

        if required_fragment_id and required_fragment_id in collected_fragment_ids:
            self.architect_vault_puzzle_terminals_activated[terminal_idx] = True
            if hasattr(target_terminal_sprite, 'is_active'): target_terminal_sprite.is_active = True
            if hasattr(target_terminal_sprite, 'image'): target_terminal_sprite.image.fill(GREEN) 
            self.play_sound('vault_barrier_disable')
            self.architect_vault_message = f"Terminal {terminal_idx+1} ({CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]].get('name', '')}) activated!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000

            if all(self.architect_vault_puzzle_terminals_activated):
                self.architect_vault_message = "All terminals active. Lockdown disengaged."
                self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                self.scene_manager.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        else:
            frag_name_required = "specific fragment"
            if required_fragment_id and CORE_FRAGMENT_DETAILS:
                for k,v in CORE_FRAGMENT_DETAILS.items():
                    if v and v.get("id") == required_fragment_id:
                        frag_name_required = v.get("name", "specific fragment")
                        break
            self.architect_vault_message = f"Terminal {terminal_idx+1} requires {frag_name_required}."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            self.play_sound('ui_denied')
            
    # --- Input Handlers (called by EventManager) ---
    def handle_main_menu_input(self, key):
        if key == pygame.K_UP: self.selected_menu_option=(self.selected_menu_option-1+len(self.menu_options))%len(self.menu_options); self.play_sound('ui_select')
        elif key == pygame.K_DOWN: self.selected_menu_option=(self.selected_menu_option+1)%len(self.menu_options); self.play_sound('ui_select')
        elif key == pygame.K_RETURN:
            self.play_sound('ui_confirm'); action=self.menu_options[self.selected_menu_option]
            if action=="Start Game": self.initialize_game_session(); self.scene_manager.set_game_state(GAME_STATE_PLAYING) # Ensure state change
            elif action=="Select Drone": self.scene_manager.set_game_state(GAME_STATE_DRONE_SELECT)
            elif action=="Settings": self.scene_manager.set_game_state(GAME_STATE_SETTINGS)
            elif action=="Leaderboard": self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
            elif action=="Quit": self.quit_game()

    def handle_drone_select_input(self, key):
        num_options=len(self.drone_select_options)
        if num_options>0: 
            if key==pygame.K_LEFT: self.selected_drone_preview_index=(self.selected_drone_preview_index-1+num_options)%num_options; self.play_sound('ui_select')
            elif key==pygame.K_RIGHT: self.selected_drone_preview_index=(self.selected_drone_preview_index+1)%num_options; self.play_sound('ui_select')
            elif key==pygame.K_RETURN:
                selected_id=self.drone_select_options[self.selected_drone_preview_index]
                if self.drone_system.is_drone_unlocked(selected_id):
                    if self.drone_system.set_selected_drone_id(selected_id): self.play_sound('ui_confirm'); 
                    if hasattr(self.ui_manager, 'update_player_life_icon_surface'): self.ui_manager.update_player_life_icon_surface()
                else: 
                    if self.drone_system.attempt_unlock_drone_with_cores(selected_id): self.play_sound('ui_confirm')
                    else: self.play_sound('ui_denied')
        if key==pygame.K_ESCAPE: self.play_sound('ui_select'); self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def handle_settings_input(self, key):
        if not self.settings_items_data: return
        setting_item = self.settings_items_data[self.selected_setting_index]
        if key == pygame.K_UP: self.selected_setting_index=(self.selected_setting_index-1+len(self.settings_items_data))%len(self.settings_items_data); self.play_sound('ui_select')
        elif key == pygame.K_DOWN: self.selected_setting_index=(self.selected_setting_index+1)%len(self.settings_items_data); self.play_sound('ui_select')
        elif key == pygame.K_RETURN:
            if setting_item["type"]=="action" and setting_item["key"]=="RESET_SETTINGS": self._reset_all_settings_to_default(); self.play_sound('ui_confirm')
        elif key==pygame.K_LEFT or key==pygame.K_RIGHT:
            if setting_item["type"]!="action":
                self.play_sound('ui_select',0.7); key_to_set=setting_item["key"]; current_val=get_game_setting(key_to_set); direction=1 if key==pygame.K_RIGHT else -1
                if setting_item["type"]=="numeric":
                    new_val=current_val; step=setting_item["step"]
                    if setting_item.get("is_ms_to_sec"): new_val=int(round(max(setting_item["min"],min(setting_item["max"],current_val/1000+step*direction)))*1000)
                    else: new_val=round(max(setting_item["min"],min(setting_item["max"],current_val+step*direction)),2 if isinstance(step,float) else 0);
                    if not isinstance(step,float) and not isinstance(new_val, float): new_val=int(new_val) 
                    elif isinstance(step, float): new_val = float(new_val) 
                    set_game_setting(key_to_set,new_val)
                elif setting_item["type"]=="choice":
                    choices = setting_item.get("choices", [])
                    if choices: 
                        try:
                            current_choice_idx=choices.index(current_val)
                            new_choice_idx=(current_choice_idx+direction+len(choices))%len(choices)
                            set_game_setting(key_to_set,choices[new_choice_idx])
                        except ValueError: 
                            set_game_setting(key_to_set, choices[0])
        elif key==pygame.K_ESCAPE: self.play_sound('ui_select'); self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)

    def handle_pause_menu_input(self, key, current_game_state_when_paused):
        # current_game_state_when_paused is the state game was in when P was pressed
        if key==pygame.K_l and current_game_state_when_paused==GAME_STATE_PLAYING: 
            self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
        elif key==pygame.K_m: 
            self.toggle_pause() # Unpause before changing state
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        elif key==pygame.K_q: self.quit_game()
        elif key==pygame.K_ESCAPE and current_game_state_when_paused.startswith("architect_vault"):
            self.toggle_pause() # Unpause
            self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU) # Exit vault to main menu

    def handle_game_over_input(self, key):
        can_submit_score=not get_game_setting("SETTINGS_MODIFIED")
        is_new_high=can_submit_score and leaderboard.is_high_score(self.score,self.level)
        if is_new_high and key in [pygame.K_r,pygame.K_l,pygame.K_m,pygame.K_q,pygame.K_RETURN,pygame.K_SPACE]: 
            self.scene_manager.set_game_state(GAME_STATE_ENTER_NAME); return
        if key==pygame.K_r: self.initialize_game_session(); self.scene_manager.set_game_state(GAME_STATE_PLAYING)
        elif key==pygame.K_l and can_submit_score: self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
        elif key==pygame.K_m: self.scene_manager.set_game_state(GAME_STATE_MAIN_MENU)
        # Q is handled globally by EventManager for this state

    def submit_leaderboard_name(self, name_cache):
        leaderboard.add_score(name_cache, self.score, self.level)
        self.scene_manager.set_game_state(GAME_STATE_LEADERBOARD)
        # player_name_input_cache is cleared by EventManager

    def update_player_name_input_display(self, name_cache):
        # This method is for EventManager to update the cache that UIManager will read for display
        self.player_name_input_display_cache = name_cache
        # UIManager will access self.game_controller.player_name_input_display_cache to draw

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
            current_game_state = self.scene_manager.get_current_state()
            # Adjust timer if unpausing a timed state
            if current_game_state == GAME_STATE_PLAYING:
                self.level_timer_start_ticks = pygame.time.get_ticks() - (get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
            elif current_game_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION:
                 self.architect_vault_phase_timer_start = pygame.time.get_ticks() - (ARCHITECT_VAULT_EXTRACTION_TIMER_MS - self.level_time_remaining_ms)
            # Old bonus level timer might also need adjustment if it's kept

    def unpause_and_set_state(self, new_state): # Helper for exiting pause to a new state
        self.paused = False
        pygame.mixer.music.unpause()
        self.scene_manager.set_game_state(new_state)

    def quit_game(self):
        print("GameController: Quitting game.")
        if self.drone_system: self.drone_system._save_unlocks() 
        pygame.quit()
        sys.exit()

    def run(self):
        """Main game loop."""
        is_fullscreen = get_game_setting("FULLSCREEN_MODE")
        if isinstance(is_fullscreen, bool) and is_fullscreen : 
             self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else: 
             self.screen = pygame.display.set_mode((WIDTH, HEIGHT), 0)

        # Game world drawing method
        # This method will be responsible for drawing the maze, player, enemies, collectibles etc.
        # based on the current game state.
        # UIManager.draw_current_scene_ui() will then draw menus, HUD, overlays on top.
        
        while True:
            self.event_manager.process_events()
            self.update()
            
            # --- Main Drawing Logic ---
            current_game_state = self.scene_manager.get_current_state()
            
            # 1. Draw Game World (if applicable)
            if current_game_state == GAME_STATE_PLAYING or \
               current_game_state == GAME_STATE_BONUS_LEVEL_PLAYING or \
               current_game_state.startswith("architect_vault"):
                self._draw_game_world() # New method to draw game elements
            
            # 2. Draw UI (Menus, HUD, Overlays)
            self.ui_manager.draw_current_scene_ui()
            
            pygame.display.flip()
            self.clock.tick(FPS)

    def _draw_game_world(self):
        """Draws the core game elements like maze, player, enemies, collectibles."""
        current_game_state = self.scene_manager.get_current_state()

        # Set background color based on state
        if current_game_state.startswith("architect_vault"):
            self.screen.fill(ARCHITECT_VAULT_BG_COLOR)
            if self.maze: self.maze.draw_architect_vault(self.screen)
        else: # Regular playing state or old bonus level
            self.screen.fill(BLACK) # Default background for gameplay
            if self.maze: self.maze.draw(self.screen)
        
        # Draw collectibles
        self.rings.draw(self.screen)
        self.power_ups.draw(self.screen)
        self.core_fragments.draw(self.screen)

        # Draw Architect's Vault specific elements (like terminals if in puzzle phase)
        if current_game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_terminals.draw(self.screen)
        # Could add self.architect_vault_hazards.draw(self.screen) here if they exist

        # Draw enemies and player
        if self.enemies: self.enemies.draw(self.screen) # Handles both regular and prototype
        if self.player: self.player.draw(self.screen)
        # Player bullets are drawn as part of player.draw() if they are in player's groups
        # Enemy bullets are drawn as part of enemy.draw()

