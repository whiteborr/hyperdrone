import sys
import random
import math
import os

import pygame

import leaderboard
from player import Drone
from enemy import Enemy
from maze import Maze
from game_settings import (
    WIDTH, HEIGHT, FPS, TILE_SIZE,
    BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE,
    POWERUP_SIZE, POWERUP_TYPES, POWERUP_SPAWN_CHANCE, MAX_POWERUPS_ON_SCREEN,
    ENEMY_BULLET_DAMAGE, WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME,
    WEAPON_MODE_NAMES, 
    GAME_STATE_PLAYING, GAME_STATE_GAME_OVER, GAME_STATE_LEADERBOARD,
    GAME_STATE_ENTER_NAME, GAME_STATE_MAIN_MENU, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    DEFAULT_SETTINGS, set_game_setting, get_game_setting,
    WEAPON_MODES_SEQUENCE, 
    PLAYER_BULLET_COLOR, MISSILE_COLOR
)
from drone_system import DroneSystem
from drone_configs import DRONE_DISPLAY_ORDER, DRONE_DATA

# --- Collectible Classes ---
class Collectible(pygame.sprite.Sprite):
    """Base class for collectible items with a pulsing shine effect."""
    def __init__(self, x, y, base_color, size, thickness=3, icon_surface=None):
        super().__init__()
        self.surface_size = int(size * 2.5) 
        self.image = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.icon_surface = icon_surface 
        self.collected = False
        self.expired = False
        self.base_color = base_color
        self.current_color = base_color
        self.size = float(size) 
        self.thickness = thickness
        self.current_radius = float(self.size) 

        self.pulse_speed = 0.005 
        self.pulse_magnitude_radius = float(self.size * 0.15) 
        self.pulse_magnitude_alpha = 90 
        self.pulse_offset = random.uniform(0, 2 * math.pi) 

        self._render_to_image() 

    def _render_to_image(self):
        """Renders the collectible (circle and icon) to its self.image surface."""
        self.image.fill((0,0,0,0)) 
        surface_center_x = self.surface_size // 2
        surface_center_y = self.surface_size // 2
        pygame.draw.circle(self.image, self.current_color,
                           (surface_center_x, surface_center_y),
                           int(self.current_radius), self.thickness)
        if self.icon_surface:
            icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
            self.image.blit(self.icon_surface, icon_rect)

    def update_shine_and_render(self):
        """Updates the pulsing shine effect (radius and alpha) and re-renders."""
        time_ticks = pygame.time.get_ticks()
        pulse_wave = math.sin(time_ticks * self.pulse_speed + self.pulse_offset)
        alpha_change = (pulse_wave + 1) / 2 
        alpha = int(160 + alpha_change * self.pulse_magnitude_alpha)
        alpha = max(100, min(255, alpha)) 
        self.current_radius = self.size + pulse_wave * self.pulse_magnitude_radius
        self.current_radius = max(self.size * 0.8, self.current_radius) 
        rgb_base = self.base_color[:3] if len(self.base_color) == 4 else self.base_color
        self.current_color = (*rgb_base, alpha)
        self._render_to_image() 

    def base_update(self, item_lifetime_constant):
        if self.collected or self.expired:
            return True 
        current_time = pygame.time.get_ticks()
        if hasattr(self, 'creation_time') and current_time - self.creation_time > item_lifetime_constant:
            self.expired = True
            self.kill() 
            return True
        self.update_shine_and_render() 
        return False

class Ring(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y, base_color=GOLD, size=TILE_SIZE // 4, thickness=3, icon_surface=None)
    def update(self):
        if self.collected: 
            return
        self.update_shine_and_render() 

class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "weapon_upgrade" 
        details = POWERUP_TYPES[self.powerup_type]
        loaded_icon = None
        if "image_filename" in details: 
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                raw_icon = pygame.image.load(image_path).convert_alpha()
                icon_display_size = int(POWERUP_SIZE * 1.5) 
                loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{image_path}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()

    def update(self):
        return self.base_update(WEAPON_UPGRADE_ITEM_LIFETIME)
    
    def apply_effect(self, player):
        player.cycle_weapon_state(force_cycle=True) 


class ShieldItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "shield"
        details = POWERUP_TYPES[self.powerup_type]
        loaded_icon = None
        if "image_filename" in details:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                raw_icon = pygame.image.load(image_path).convert_alpha()
                icon_display_size = int(POWERUP_SIZE * 1.5)
                loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{image_path}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration = get_game_setting("SHIELD_POWERUP_DURATION")

    def update(self):
        return self.base_update(POWERUP_ITEM_LIFETIME)
    
    def apply_effect(self, player):
        player.activate_shield(self.effect_duration)


class SpeedBoostItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "speed_boost"
        details = POWERUP_TYPES[self.powerup_type]
        loaded_icon = None
        if "image_filename" in details:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                raw_icon = pygame.image.load(image_path).convert_alpha()
                icon_display_size = int(POWERUP_SIZE * 1.5)
                loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{image_path}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()
        self.effect_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.multiplier = details["multiplier"]

    def update(self):
        return self.base_update(POWERUP_ITEM_LIFETIME)
    
    def apply_effect(self, player):
        player.arm_speed_boost(self.effect_duration, self.multiplier)
# --- End of Collectible Classes ---

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init() 
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Drone Maze Combat")
        self.clock = pygame.time.Clock()
        self.drone_system = DroneSystem() 
        self.UI_PANEL_WIDTH = 280 
        self.UI_PANEL_COLOR = BLACK
        self.ui_panel_padding = 15
        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf") 
        self.font_size_ui = 28
        self.font_size_ui_values = 30
        self.font_size_small = 24
        self.font_size_medium = 48
        self.font_size_large = 74
        self.font_size_input = 50
        self.font_size_menu = 60
        self.font_size_title = 90
        self.font_drone_select_name = 36
        self.font_drone_select_desc = 22
        self.font_drone_select_unlock = 20
        try: 
            self.font_ui_icons = pygame.font.Font(self.font_path_emoji, self.font_size_ui)
            self.font_ui_text = pygame.font.Font(self.font_path_emoji, self.font_size_ui)
            self.font_ui_values = pygame.font.Font(self.font_path_emoji, self.font_size_ui_values)
            self.font = pygame.font.Font(self.font_path_emoji, self.font_size_ui) 
            self.small_font = pygame.font.Font(self.font_path_emoji, self.font_size_small)
            self.medium_font = pygame.font.Font(self.font_path_emoji, self.font_size_medium)
            self.large_font = pygame.font.Font(self.font_path_emoji, self.font_size_large)
            self.input_font = pygame.font.Font(self.font_path_emoji, self.font_size_input)
            self.menu_font = pygame.font.Font(self.font_path_emoji, self.font_size_menu)
            self.title_font = pygame.font.Font(self.font_path_emoji, self.font_size_title)
            self.timer_display_font = self.font_ui_values 
            self.font_drone_name = pygame.font.Font(self.font_path_emoji, self.font_drone_select_name)
            self.font_drone_desc = pygame.font.Font(self.font_path_emoji, self.font_drone_select_desc)
            self.font_drone_unlock = pygame.font.Font(self.font_path_emoji, self.font_drone_select_unlock)
        except pygame.error as e: 
            print(f"Warning: Font loading error ('{self.font_path_emoji}'): {e}. Using fallbacks.")
            font_size_map = {
                'ui_icons': self.font_size_ui, 'ui_text': self.font_size_ui,
                'ui_values': self.font_size_ui_values, 'font': self.font_size_ui,
                'small_font': self.font_size_small, 'medium_font': self.font_size_medium,
                'large_font': self.font_size_large, 'input_font': self.font_size_input,
                'menu_font': self.font_size_menu, 'title_font': self.font_size_title,
                'timer_display_font': self.font_size_ui_values,
                'font_drone_name': self.font_drone_select_name,
                'font_drone_desc': self.font_drone_select_desc,
                'font_drone_unlock': self.font_drone_select_unlock
            }
            for attr_name, size in font_size_map.items():
                setattr(self, attr_name, pygame.font.Font(None, size))
        self.menu_options = ["Start Game", "Select Drone", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0
        self.game_state = None 
        self.menu_music_path = os.path.join("assets", "sounds", "menu_logo.wav")
        self.gameplay_music_path = os.path.join("assets", "sounds", "background_music.wav")
        self.current_music_context = None 
        self.level = 1
        self.score = 0
        self.lives = get_game_setting("PLAYER_LIVES") 
        self.maze = None
        self.player = None
        self.enemies = pygame.sprite.Group()
        self.rings = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group() 
        self.collected_rings = 0
        self.total_rings_per_level = 5 
        self.paused = False
        self.player_name_input = "" 
        self.leaderboard_scores = leaderboard.load_scores()
        self.sounds = {} 
        self.menu_background_image = None
        self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")
        self.current_drone_life_icon_surface = None 
        self.ring_ui_icon = None 
        self.ring_ui_icon_empty = None 
        self.ui_icon_size_lives = (25, 25)
        self.ui_icon_size_rings = (20, 20)
        self.animating_rings = [] 
        self.ring_ui_target_pos = (0,0) 
        self.drone_select_options = DRONE_DISPLAY_ORDER 
        self.selected_drone_preview_index = 0
        self.drone_icons_cache = {} 
        self._load_drone_icons_for_select_menu()
        self.update_player_life_icon() 
        try: 
            ring_icon_path = os.path.join("assets", "images", "ring_ui_icon.png")
            raw_ring_icon = pygame.image.load(ring_icon_path).convert_alpha()
            self.ring_ui_icon = pygame.transform.smoothscale(raw_ring_icon, self.ui_icon_size_rings)
            if self.ring_ui_icon:
                self.ring_ui_icon_empty = self.ring_ui_icon.copy()
                self.ring_ui_icon_empty.set_alpha(80) 
        except pygame.error as e:
            print(f"ERROR loading 'ring_ui_icon.png': {e}. Ring UI will be basic.")
        self._initialize_settings_menu()
        self.load_menu_assets()
        self.load_sfx()
        self.menu_stars = []
        self._initialize_menu_stars()
        self.level_cleared_pending_animation = False 
        self.all_enemies_killed_this_level = False # New flag for weapon upgrade condition
        self.set_game_state(GAME_STATE_MAIN_MENU) 
        print("Game initialized. Default drone from DroneSystem will be used.")

    def _create_fallback_icon(self, size=(80,80), text="?", color=GREY, text_color=WHITE, font_to_use=None):
        if font_to_use is None:
            font_to_use = self.medium_font 
        surface = pygame.Surface(size, pygame.SRCALPHA) 
        surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2) 
        if text:
            text_surf = font_to_use.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
            surface.blit(text_surf, text_rect)
        return surface

    def _load_drone_icons_for_select_menu(self):
        for drone_id, data in DRONE_DATA.items():
            icon_display_size = (80, 80) 
            if "icon_path" in data and data["icon_path"]:
                try:
                    raw_icon = pygame.image.load(data["icon_path"]).convert_alpha()
                    self.drone_icons_cache[drone_id] = pygame.transform.smoothscale(raw_icon, icon_display_size)
                except pygame.error as e:
                    print(f"Error loading icon for {drone_id} ('{data['icon_path']}'): {e}. Creating fallback.")
                    initials = data.get("name", "?")[:2].upper()
                    self.drone_icons_cache[drone_id] = self._create_fallback_icon(
                        size=icon_display_size, text=initials, font_to_use=self.font_drone_name
                    )
            else: 
                initials = data.get("name", "?")[:2].upper()
                self.drone_icons_cache[drone_id] = self._create_fallback_icon(
                    size=icon_display_size, text=initials, font_to_use=self.font_drone_name
                )

    def update_player_life_icon(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        if drone_config and drone_config.get("icon_path"):
            try:
                raw_icon = pygame.image.load(drone_config["icon_path"]).convert_alpha()
                self.current_drone_life_icon_surface = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_lives)
            except pygame.error as e:
                print(f"Error loading life icon for {selected_drone_id} ('{drone_config['icon_path']}'): {e}. Using fallback.")
                self.current_drone_life_icon_surface = self._create_fallback_icon(
                    size=self.ui_icon_size_lives, text="♥", color=CYAN, font_to_use=self.small_font
                )
        else: 
            self.current_drone_life_icon_surface = self._create_fallback_icon(
                size=self.ui_icon_size_lives, text="♥", color=CYAN, font_to_use=self.small_font
            )

    def _initialize_menu_stars(self, num_stars=150):
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            speed = random.uniform(0.2, 1.0) 
            size = random.randint(1, 3) 
            self.menu_stars.append([x, y, speed, size])

    def _initialize_settings_menu(self):
        self.settings_items = [
            {"label": "Base Max Health", "key": "PLAYER_MAX_HEALTH", "type": "numeric", "min": 50, "max": 200, "step": 10, "note": "Original Drone base, others vary"},
            {"label": "Starting Lives", "key": "PLAYER_LIVES", "type": "numeric", "min": 1, "max": 9, "step": 1},
            {"label": "Base Speed", "key": "PLAYER_SPEED", "type": "numeric", "min": 1, "max": 10, "step": 1, "note": "Original Drone base, others vary"},
            {"label": "Initial Weapon", "key": "INITIAL_WEAPON_MODE", "type": "choice", "choices": WEAPON_MODES_SEQUENCE, "get_display": lambda val: WEAPON_MODE_NAMES.get(val, "Unknown")},
            {"label": "Bullet Speed", "key": "PLAYER_BULLET_SPEED", "type": "numeric", "min": 2, "max": 15, "step": 1},
            {"label": "Bullet Lifetime (frames)", "key": "PLAYER_BULLET_LIFETIME", "type": "numeric", "min": 30, "max": 300, "step": 10},
            {"label": "Base Shoot Cooldown (ms)", "key": "PLAYER_BASE_SHOOT_COOLDOWN", "type": "numeric", "min":100, "max":1000, "step":50},
            {"label": "Base Rapid Cooldown (ms)", "key": "PLAYER_RAPID_FIRE_COOLDOWN", "type": "numeric", "min":50, "max":500, "step":25},
            {"label": "Missile Speed", "key": "MISSILE_SPEED", "type": "numeric", "min": 1.0, "max": 20.0, "step": 0.5},
            {"label": "Missile Lifetime (frames)", "key": "MISSILE_LIFETIME", "type": "numeric", "min": 30, "max": 600, "step": 20},
            {"label": "Base Missile Cooldown (ms)", "key": "MISSILE_COOLDOWN", "type": "numeric", "min":1000, "max":10000, "step":500},
            {"label": "Missile Damage", "key": "MISSILE_DAMAGE", "type": "numeric", "min": 10, "max": 100, "step": 5},
            {"label": "Lightning Cooldown (ms)", "key": "LIGHTNING_COOLDOWN", "type": "numeric", "min": 200, "max": 2000, "step": 50},
            {"label": "Lightning Damage", "key": "LIGHTNING_DAMAGE", "type": "numeric", "min": 5, "max": 50, "step": 1},
            {"label": "Enemy Speed", "key": "ENEMY_SPEED", "type": "numeric", "min": 0.5, "max": 5, "step": 0.5},
            {"label": "Enemy Health", "key": "ENEMY_HEALTH", "type": "numeric", "min": 25, "max": 300, "step": 25},
            {"label": "Timer (sec)", "key": "LEVEL_TIMER_DURATION", "type": "numeric", "min": 60, "max": 300, "step": 15, "is_ms_to_sec": True},
            {"label": "Shield Duration (sec)", "key": "SHIELD_POWERUP_DURATION", "type": "numeric", "min": 10, "max": 60, "step": 5, "is_ms_to_sec": True},
            {"label": "Speed Duration (sec)", "key": "SPEED_BOOST_POWERUP_DURATION", "type": "numeric", "min": 5, "max": 30, "step": 2, "is_ms_to_sec": True},
            {"label": "Reset to Defaults", "key": "RESET_SETTINGS", "type": "action"},
        ]
        self.selected_setting_index = 0

    def _reset_all_settings_to_default(self):
        import game_settings 
        for key, default_value in game_settings.DEFAULT_SETTINGS.items():
            if any(item['key'] == key for item in self.settings_items if item['type'] != 'action'):
                 set_game_setting(key, default_value) 
        if hasattr(game_settings, 'SETTINGS_MODIFIED'):
            game_settings.SETTINGS_MODIFIED = False

    def _reset_level_timer(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")

    def load_menu_assets(self):
        try:
            self.menu_background_image = pygame.image.load(os.path.join("assets", "images", "menu_logo.png")).convert_alpha()
        except pygame.error as e:
            print(f"Error loading menu image: {e}")

    def load_sfx(self):
        sound_paths = {
            'collect_ring': "assets/sounds/collect_ring.wav",
            'weapon_upgrade_collect': "assets/sounds/collect_powerup.wav", 
            'crash': "assets/sounds/crash.wav", 
            'shoot': "assets/sounds/shoot.wav", 
            'missile_launch': "assets/sounds/missile_launch.wav",
            'level_up': "assets/sounds/level_up.wav",
            'player_death': "assets/sounds/player_death.wav",
            'enemy_shoot': "assets/sounds/enemy_shoot.wav",
            'timer_out': "assets/sounds/timer_warning.wav", 
            'ui_select': "assets/sounds/ui_select.wav", 
            'ui_confirm': "assets/sounds/ui_confirm.wav", 
            'ui_denied': "assets/sounds/ui_denied.wav" 
        }
        for name, path_str in sound_paths.items():
            try:
                self.sounds[name] = pygame.mixer.Sound(os.path.join(*path_str.split('/')))
            except pygame.error as e:
                print(f"Warning: Sound load error '{path_str}': {e}")

    def _play_music(self, music_path, context_label, volume=0.5, loops=-1):
        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=loops)
            self.current_music_context = context_label
        except pygame.error as e:
            print(f"Error playing music '{music_path}': {e}")

    def set_game_state(self, new_state):
        if self.game_state == new_state and not (new_state == GAME_STATE_PLAYING and self.paused):
            return 
        self.game_state = new_state
        music_map = {
            GAME_STATE_MAIN_MENU: "menu", GAME_STATE_PLAYING: "gameplay",
            GAME_STATE_LEADERBOARD: "menu", GAME_STATE_ENTER_NAME: "menu",
            GAME_STATE_GAME_OVER: "menu", GAME_STATE_SETTINGS: "menu",
            GAME_STATE_DRONE_SELECT: "menu"
        }
        target_music_context = music_map.get(self.game_state)
        if target_music_context:
            music_path_to_play = self.menu_music_path if target_music_context == "menu" else self.gameplay_music_path
            if self.current_music_context != target_music_context: 
                self._play_music(music_path_to_play, target_music_context)
            elif self.game_state == GAME_STATE_PLAYING and self.paused: 
                 pygame.mixer.music.unpause() 
        if self.game_state == GAME_STATE_DRONE_SELECT:
            current_selected_id = self.drone_system.get_selected_drone_id()
            try:
                self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
            except ValueError: 
                self.selected_drone_preview_index = 0

    def initialize_game_session(self):
        self.level = 1
        self.lives = get_game_setting("PLAYER_LIVES")
        self.score = 0
        new_unlocks_level = self.drone_system.set_player_level(self.level) 
        if new_unlocks_level:
            print(f"New drones unlocked by reaching level 1 (default check): {new_unlocks_level}")
        self.level_cleared_pending_animation = False
        self.all_enemies_killed_this_level = False # Reset for new game session
        self.maze = Maze(game_area_x_offset=self.UI_PANEL_WIDTH)
        player_start_pos = self.get_safe_spawn_point()
        selected_drone_id = self.drone_system.get_selected_drone_id()
        drone_config = self.drone_system.get_drone_config(selected_drone_id) 
        effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id) 
        self.player = Drone(player_start_pos[0], player_start_pos[1],
                            drone_id=selected_drone_id,
                            drone_stats=effective_drone_stats,
                            drone_sprite_path=drone_config.get("sprite_path"),
                            crash_sound=self.sounds.get('crash'),
                            drone_system=self.drone_system) 
        self.update_player_life_icon() 
        self.enemies.empty()
        self.spawn_enemies()
        if self.player: 
            self.player.bullets_group.empty()
            self.player.missiles_group.empty()
        self.rings.empty()
        self.power_ups.empty()
        self.collected_rings = 0
        self.total_rings_per_level = 5 
        self.paused = False
        self.player_name_input = "" 
        self.animating_rings.clear()
        self.place_collectibles(initial_setup=True) 
        self._reset_level_timer()
        self.set_game_state(GAME_STATE_PLAYING)

    def get_safe_spawn_point(self):
        path_cells_relative = self.maze.get_path_cells() 
        path_cells_absolute = [(x + self.UI_PANEL_WIDTH, y) for x,y in path_cells_relative]
        return random.choice(path_cells_absolute) if path_cells_absolute else \
               (self.UI_PANEL_WIDTH + WIDTH // 4, HEIGHT // 2) 

    def play_sound(self, name, volume=1.0):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()

    def spawn_enemies(self):
        self.enemies.empty()
        num_enemies = min(self.level + 1, 6) 
        path_cells_relative = self.maze.get_path_cells()
        enemy_shoot_sound = self.sounds.get('enemy_shoot')
        for _ in range(num_enemies):
            if not path_cells_relative: break 
            spawn_attempts = 0
            spawned = False
            while spawn_attempts < 10 and not spawned: 
                rel_x, rel_y = random.choice(path_cells_relative)
                abs_x, abs_y = rel_x + self.UI_PANEL_WIDTH, rel_y
                if self.player and math.hypot(abs_x - self.player.x, abs_y - self.player.y) < TILE_SIZE * 5:
                    spawn_attempts += 1; continue
                if any(math.hypot(abs_x - e.x, abs_y - e.y) < TILE_SIZE * 2 for e in self.enemies):
                    spawn_attempts +=1; continue
                self.enemies.add(Enemy(abs_x, abs_y, shoot_sound=enemy_shoot_sound))
                spawned = True
            if not spawned and path_cells_relative: 
                rel_fx, rel_fy = random.choice(path_cells_relative)
                abs_fx, abs_fy = rel_fx + self.UI_PANEL_WIDTH, rel_fy
                self.enemies.add(Enemy(abs_fx, abs_fy, shoot_sound=enemy_shoot_sound))

    def place_collectibles(self, initial_setup=False):
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return
        if initial_setup: 
            self.rings.empty()
            shuffled_path_cells_relative = random.sample(path_cells_relative, len(path_cells_relative))
            for i in range(min(self.total_rings_per_level, len(shuffled_path_cells_relative))):
                rel_x, rel_y = shuffled_path_cells_relative[i]
                abs_x, abs_y = rel_x + self.UI_PANEL_WIDTH, rel_y
                self.rings.add(Ring(abs_x, abs_y))
        self.try_spawn_powerup() 

    def try_spawn_powerup(self):
        if len(self.power_ups) < MAX_POWERUPS_ON_SCREEN: 
            path_cells_relative = self.maze.get_path_cells()
            if not path_cells_relative: return
            existing_coords_abs = set(r.rect.center for r in self.rings)
            for p_up in self.power_ups: existing_coords_abs.add(p_up.rect.center)
            available_cells_abs = [
                (rcx + self.UI_PANEL_WIDTH, rcy) for rcx, rcy in path_cells_relative
                if (rcx + self.UI_PANEL_WIDTH, rcy) not in existing_coords_abs
            ]
            if not available_cells_abs: return 
            abs_x, abs_y = random.choice(available_cells_abs) 
            chosen_type_key = random.choice(["weapon_upgrade", "shield", "speed_boost"])
            new_powerup = None
            if chosen_type_key == "weapon_upgrade": new_powerup = WeaponUpgradeItem(abs_x, abs_y)
            elif chosen_type_key == "shield": new_powerup = ShieldItem(abs_x, abs_y)
            elif chosen_type_key == "speed_boost": new_powerup = SpeedBoostItem(abs_x, abs_y)
            if new_powerup:
                self.power_ups.add(new_powerup)

    def draw_main_menu(self):
        if self.menu_background_image:
            self.screen.blit(pygame.transform.scale(self.menu_background_image, (WIDTH, HEIGHT)), (0, 0))
        else:
            self.screen.fill(BLACK) 
        menu_item_start_y = HEIGHT // 2 - 80
        item_spacing = 75
        for i, option_text in enumerate(self.menu_options):
            is_selected = (i == self.selected_menu_option)
            text_color = GOLD if is_selected else WHITE
            font_render_size = self.font_size_menu + 8 if is_selected else self.font_size_menu
            try:
                active_menu_font = pygame.font.Font(self.font_path_emoji if os.path.exists(self.font_path_emoji) else None, font_render_size)
            except: 
                active_menu_font = pygame.font.Font(None, font_render_size)
            text_surf = active_menu_font.render(option_text, True, text_color)
            text_rect = text_surf.get_rect()
            button_width = text_rect.width + 60
            button_height = text_rect.height + 25
            button_surface_rect = pygame.Rect(0,0,button_width,button_height)
            button_surface_rect.center = (WIDTH//2, menu_item_start_y + i * item_spacing)
            button_bg_surface = pygame.Surface(button_surface_rect.size, pygame.SRCALPHA)
            current_bg_color = (70,70,70,220) if is_selected else (50,50,50,180) 
            pygame.draw.rect(button_bg_surface, current_bg_color, button_bg_surface.get_rect(), border_radius=15)
            if is_selected: 
                pygame.draw.rect(button_bg_surface, GOLD, button_bg_surface.get_rect(), 3, border_radius=15)
            button_bg_surface.blit(text_surf, text_surf.get_rect(center=(button_width//2,button_height//2)))
            self.screen.blit(button_bg_surface, button_surface_rect.topleft)
        instr_surf = self.font.render("Use UP/DOWN keys, ENTER to select.", True, CYAN)
        instr_bg_box=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA)
        instr_bg_box.fill((30,30,30,150))
        instr_bg_box.blit(instr_surf,instr_surf.get_rect(center=(instr_bg_box.get_width()//2,instr_bg_box.get_height()//2)))
        self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH//2, HEIGHT-100)))
        if get_game_setting("SETTINGS_MODIFIED"):
            warning_surf = self.small_font.render("Custom settings active: Leaderboard disabled.", True, YELLOW)
            self.screen.blit(warning_surf, warning_surf.get_rect(center=(WIDTH//2, HEIGHT-50)))

    def draw_drone_select_menu(self):
        self.screen.fill(BLACK) 
        if self.menu_stars: 
            for star_params in self.menu_stars:
                pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])
        title_surf = self.title_font.render("Select Drone", True, GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 80)))
        item_width = 220; item_height = 280; padding = 20
        items_per_row = max(1, (WIDTH - 2 * padding) // (item_width + padding)) 
        start_x = (WIDTH - (items_per_row * (item_width + padding) - padding)) // 2 
        start_y = title_surf.get_rect().bottom + 50
        for i, drone_id in enumerate(self.drone_select_options):
            row = i // items_per_row
            col = i % items_per_row
            item_x = start_x + col * (item_width + padding)
            item_y = start_y + row * (item_height + padding)
            item_rect = pygame.Rect(item_x, item_y, item_width, item_height)
            is_selected_preview = (i == self.selected_drone_preview_index) 
            is_currently_equipped = (drone_id == self.drone_system.get_selected_drone_id()) 
            is_unlocked = self.drone_system.is_drone_unlocked(drone_id)
            box_color = (60,60,60,220) if is_selected_preview else (40,40,40,200)
            if not is_unlocked: box_color = (30,30,30, 180) 
            pygame.draw.rect(self.screen, box_color, item_rect, border_radius=15)
            border_color = GOLD if is_selected_preview else (GREEN if is_currently_equipped else WHITE)
            border_thickness = 3 if is_selected_preview or is_currently_equipped else 1
            pygame.draw.rect(self.screen, border_color, item_rect, border_thickness, border_radius=15)
            icon_surf = self.drone_icons_cache.get(drone_id)
            current_y_offset = item_rect.top + 15 
            if icon_surf:
                icon_rect_pos_x = item_rect.centerx - icon_surf.get_width() // 2
                icon_rect_pos_y = current_y_offset
                display_icon = icon_surf
                if not is_unlocked: 
                    display_icon = icon_surf.copy(); display_icon.set_alpha(100)
                self.screen.blit(display_icon, (icon_rect_pos_x, icon_rect_pos_y))
                current_y_offset += icon_surf.get_height() + 10
            drone_config = DRONE_DATA.get(drone_id, {})
            name_text = drone_config.get("name", "N/A")
            name_color = WHITE if is_unlocked else GREY
            name_surf = self.font_drone_name.render(name_text, True, name_color)
            self.screen.blit(name_surf, name_surf.get_rect(centerx=item_rect.centerx, top=current_y_offset))
            current_y_offset += name_surf.get_height() + 10
            desc_text = drone_config.get("description", "")
            desc_color = (200,200,200) if is_unlocked else (100,100,100)
            words = desc_text.split(' ')
            lines = []; current_line = ""
            for word in words: 
                test_line = current_line + word + " "
                if self.font_drone_desc.size(test_line)[0] < item_rect.width - 20: 
                    current_line = test_line
                else:
                    lines.append(current_line.strip()); current_line = word + " "
            lines.append(current_line.strip()) 
            for line_text in lines:
                if current_y_offset + self.font_drone_desc.get_height() > item_rect.bottom - 30: break 
                line_surf = self.font_drone_desc.render(line_text, True, desc_color)
                self.screen.blit(line_surf, line_surf.get_rect(centerx=item_rect.centerx, top=current_y_offset))
                current_y_offset += self.font_drone_desc.get_height() + 2
            unlock_y_pos = item_rect.bottom - 30
            if not is_unlocked:
                condition_text = drone_config.get("unlock_condition", {}).get("description", "Locked")
                condition_surf = self.font_drone_unlock.render(condition_text, True, YELLOW)
                self.screen.blit(condition_surf, condition_surf.get_rect(centerx=item_rect.centerx, bottom=unlock_y_pos))
            elif is_currently_equipped:
                equipped_surf = self.font_drone_unlock.render("EQUIPPED", True, GREEN)
                self.screen.blit(equipped_surf, equipped_surf.get_rect(centerx=item_rect.centerx, bottom=unlock_y_pos))
            elif is_selected_preview: 
                select_surf = self.font_drone_unlock.render("Press ENTER to Select", True, CYAN)
                self.screen.blit(select_surf, select_surf.get_rect(centerx=item_rect.centerx, bottom=unlock_y_pos))
        instr_surf = self.small_font.render("UP/DOWN/LEFT/RIGHT: Navigate | ENTER: Select/Unlock | ESC: Back", True, CYAN)
        instr_bg=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA)
        instr_bg.fill((20,20,20,180))
        instr_bg.blit(instr_surf,(10,5))
        self.screen.blit(instr_bg, instr_bg.get_rect(center=(WIDTH//2,HEIGHT-50)))
        cores_surf = self.font_ui_text.render(f"Player Cores: {self.drone_system.get_player_cores()} 💠", True, GOLD) 
        self.screen.blit(cores_surf, cores_surf.get_rect(right=WIDTH-20, bottom=HEIGHT-20))

    def draw_settings_menu(self):
        self.screen.fill(BLACK)
        if self.menu_stars: 
            for star_params in self.menu_stars:
                pygame.draw.circle(self.screen,WHITE,(int(star_params[0]),int(star_params[1])),star_params[3])
        title_surf=self.title_font.render("Settings",True,GOLD)
        title_bg=pygame.Surface((title_surf.get_width()+30,title_surf.get_height()+15),pygame.SRCALPHA)
        title_bg.fill((20,20,20,180)) 
        title_bg.blit(title_surf,title_surf.get_rect(center=(title_bg.get_width()//2,title_bg.get_height()//2)))
        self.screen.blit(title_bg,title_bg.get_rect(center=(WIDTH//2,80)))
        item_y_start=180
        item_line_height=self.font.get_height()+15
        max_items_on_screen=(HEIGHT-item_y_start-100)//item_line_height 
        view_start_index = max(0, min(
            self.selected_setting_index - max_items_on_screen + 1 if self.selected_setting_index >= max_items_on_screen else 0,
            len(self.settings_items) - max_items_on_screen if self.settings_items else 0
        ))
        view_end_index = min(view_start_index + max_items_on_screen, len(self.settings_items) if self.settings_items else 0)
        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)):
            item = self.settings_items[list_idx]
            y_pos = item_y_start + i_display * item_line_height
            color = YELLOW if list_idx == self.selected_setting_index else WHITE
            label_surf = self.font.render(item["label"], True, color)
            label_bg_rect = pygame.Rect(WIDTH//4-105,y_pos-5,label_surf.get_width()+10,label_surf.get_height()+10)
            pygame.draw.rect(self.screen,(30,30,30,160),label_bg_rect,border_radius=5) 
            self.screen.blit(label_surf, (WIDTH//4-100, y_pos))
            if "note" in item and list_idx == self.selected_setting_index:
                note_surf = self.small_font.render(item["note"], True, LIGHT_BLUE)
                self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right+10, centery=label_bg_rect.centery))
            if item["type"] != "action":
                current_value = get_game_setting(item["key"])
                display_value = ""
                if item["type"] == "numeric":
                    display_value = f"{current_value/1000:.0f}s" if item.get("is_ms_to_sec") else \
                                    (f"{current_value:.1f}" if isinstance(current_value,float) else str(current_value))
                elif item["type"] == "choice":
                    display_value = item["get_display"](current_value)
                value_surf = self.font.render(display_value, True, color)
                value_bg_rect = pygame.Rect(WIDTH//2+195,y_pos-5,value_surf.get_width()+10,value_surf.get_height()+10)
                pygame.draw.rect(self.screen,(30,30,30,160),value_bg_rect,border_radius=5) 
                self.screen.blit(value_surf, (WIDTH//2+200, y_pos))
                if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]:
                    self.screen.blit(self.small_font.render("*",True,RED),(WIDTH//2+180,y_pos))
            elif list_idx == self.selected_setting_index: 
                 action_hint_surf = self.font.render("<ENTER>", True, YELLOW)
                 action_hint_bg_rect=pygame.Rect(WIDTH//2+195,y_pos-5,action_hint_surf.get_width()+10,action_hint_surf.get_height()+10)
                 pygame.draw.rect(self.screen,(30,30,30,160),action_hint_bg_rect,border_radius=5)
                 self.screen.blit(action_hint_surf,(WIDTH//2+200,y_pos))
        instr_surf = self.small_font.render("UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back", True, CYAN)
        instr_bg=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA)
        instr_bg.fill((20,20,20,180))
        instr_bg.blit(instr_surf,(10,5))
        self.screen.blit(instr_bg,instr_bg.get_rect(center=(WIDTH//2,HEIGHT-70)))
        if get_game_setting("SETTINGS_MODIFIED"):
            warning_surf = self.small_font.render("Settings changed. Leaderboard will be disabled.", True, YELLOW)
            warning_bg=pygame.Surface((warning_surf.get_width()+10,warning_surf.get_height()+5),pygame.SRCALPHA)
            warning_bg.fill((20,20,20,180))
            warning_bg.blit(warning_surf,(5,2))
            self.screen.blit(warning_bg,warning_bg.get_rect(center=(WIDTH//2,HEIGHT-35)))

    def handle_events(self):
        current_time = pygame.time.get_ticks() 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
            if event.type == pygame.KEYDOWN:
                if self.game_state == GAME_STATE_MAIN_MENU:
                    if event.key == pygame.K_UP:
                        self.selected_menu_option = (self.selected_menu_option - 1 + len(self.menu_options)) % len(self.menu_options)
                        self.play_sound('ui_select')
                    elif event.key == pygame.K_DOWN:
                        self.selected_menu_option = (self.selected_menu_option + 1) % len(self.menu_options)
                        self.play_sound('ui_select')
                    elif event.key == pygame.K_RETURN:
                        self.play_sound('ui_confirm')
                        action = self.menu_options[self.selected_menu_option]
                        if action == "Start Game": self.initialize_game_session()
                        elif action == "Select Drone": self.set_game_state(GAME_STATE_DRONE_SELECT)
                        elif action == "Settings": self.set_game_state(GAME_STATE_SETTINGS)
                        elif action == "Leaderboard":
                            self.leaderboard_scores = leaderboard.load_scores() 
                            self.set_game_state(GAME_STATE_LEADERBOARD)
                        elif action == "Quit": self.quit_game()
                elif self.game_state == GAME_STATE_DRONE_SELECT:
                    num_options = len(self.drone_select_options)
                    items_per_row = max(1, (WIDTH - 2*20)//(220+20)) 
                    if event.key == pygame.K_UP:
                        if self.selected_drone_preview_index >= items_per_row:
                            self.selected_drone_preview_index -= items_per_row
                            self.play_sound('ui_select')
                    elif event.key == pygame.K_DOWN:
                        if self.selected_drone_preview_index + items_per_row < num_options:
                            self.selected_drone_preview_index += items_per_row
                            self.play_sound('ui_select')
                    elif event.key == pygame.K_LEFT:
                        if self.selected_drone_preview_index > 0:
                            self.selected_drone_preview_index -= 1
                            self.play_sound('ui_select')
                    elif event.key == pygame.K_RIGHT:
                        if self.selected_drone_preview_index < num_options - 1:
                            self.selected_drone_preview_index += 1
                            self.play_sound('ui_select')
                    elif event.key == pygame.K_RETURN:
                        selected_id = self.drone_select_options[self.selected_drone_preview_index]
                        if self.drone_system.is_drone_unlocked(selected_id):
                            if self.drone_system.set_selected_drone_id(selected_id): 
                                self.play_sound('ui_confirm')
                                self.update_player_life_icon() 
                                self.set_game_state(GAME_STATE_MAIN_MENU)
                        else: 
                            drone_cfg = self.drone_system.get_drone_config(selected_id)
                            if drone_cfg and drone_cfg["unlock_condition"]["type"] == "cores":
                                if self.drone_system.attempt_unlock_drone_with_cores(selected_id):
                                    self.play_sound('ui_confirm') 
                                    self.drone_system.set_selected_drone_id(selected_id) 
                                    self.update_player_life_icon()
                                else: self.play_sound('ui_denied') 
                            else: self.play_sound('ui_denied') 
                    elif event.key == pygame.K_ESCAPE:
                        self.play_sound('ui_select'); self.set_game_state(GAME_STATE_MAIN_MENU)
                elif self.game_state == GAME_STATE_SETTINGS:
                    setting_item = self.settings_items[self.selected_setting_index]
                    if event.key == pygame.K_UP:
                        self.selected_setting_index = (self.selected_setting_index - 1 + len(self.settings_items)) % len(self.settings_items)
                        self.play_sound('ui_select')
                    elif event.key == pygame.K_DOWN:
                        self.selected_setting_index = (self.selected_setting_index + 1) % len(self.settings_items)
                        self.play_sound('ui_select')
                    elif event.key == pygame.K_RETURN:
                        if setting_item["type"] == "action" and setting_item["key"] == "RESET_SETTINGS":
                            self._reset_all_settings_to_default()
                            self.play_sound('ui_confirm')
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                        if setting_item["type"] != "action": 
                            self.play_sound('ui_select',0.7) 
                            key_to_set = setting_item["key"]
                            current_val = get_game_setting(key_to_set)
                            direction = 1 if event.key == pygame.K_RIGHT else -1
                            if setting_item["type"] == "numeric":
                                new_val = current_val
                                step = setting_item["step"]
                                if setting_item.get("is_ms_to_sec"): 
                                    new_val = int(round(max(setting_item["min"], min(setting_item["max"], current_val/1000 + step*direction)))*1000)
                                else:
                                    new_val = round(max(setting_item["min"], min(setting_item["max"], current_val + step*direction)), 2 if isinstance(step,float) else 0)
                                    if not isinstance(step,float): new_val = int(new_val) 
                                set_game_setting(key_to_set, new_val)
                            elif setting_item["type"] == "choice":
                                current_choice_idx = setting_item["choices"].index(current_val)
                                new_choice_idx = (current_choice_idx + direction + len(setting_item["choices"])) % len(setting_item["choices"])
                                set_game_setting(key_to_set, setting_item["choices"][new_choice_idx])
                    elif event.key == pygame.K_ESCAPE:
                        self.play_sound('ui_select'); self.set_game_state(GAME_STATE_MAIN_MENU)
                elif self.game_state == GAME_STATE_PLAYING:
                    if event.key == pygame.K_p: 
                        self.paused = not self.paused
                        if self.paused:
                            pygame.mixer.music.pause() if self.current_music_context == "gameplay" else None
                        else: 
                            pygame.mixer.music.unpause() if self.current_music_context == "gameplay" else None
                            self.level_timer_start_ticks = pygame.time.get_ticks() - \
                                ( (get_game_setting("LEVEL_TIMER_DURATION")) - self.level_time_remaining_ms)
                    if not self.paused and self.player and self.player.alive:
                        if event.key == pygame.K_UP: 
                            self.player.moving_forward = True
                            self.player.attempt_speed_boost_activation() 
                        elif event.key == pygame.K_DOWN: 
                            self.player.moving_forward = False
                    elif self.paused: 
                        if event.key == pygame.K_l: 
                            self.leaderboard_scores = leaderboard.load_scores()
                            self.set_game_state(GAME_STATE_LEADERBOARD)
                        elif event.key == pygame.K_m: 
                            self.paused=False 
                            pygame.mixer.music.unpause() if self.current_music_context == "gameplay" else None
                            self.set_game_state(GAME_STATE_MAIN_MENU)
                        elif event.key == pygame.K_q: self.quit_game()
                elif self.game_state == GAME_STATE_GAME_OVER:
                    can_submit_score = not get_game_setting("SETTINGS_MODIFIED")
                    is_new_high = can_submit_score and leaderboard.is_high_score(self.score, self.level)
                    if is_new_high and event.key in [pygame.K_r, pygame.K_l, pygame.K_m, pygame.K_q, pygame.K_RETURN, pygame.K_SPACE]:
                        self.set_game_state(GAME_STATE_ENTER_NAME); return 
                    if event.key == pygame.K_r: self.initialize_game_session()
                    elif event.key == pygame.K_l and can_submit_score :
                        self.leaderboard_scores = leaderboard.load_scores()
                        self.set_game_state(GAME_STATE_LEADERBOARD)
                    elif event.key == pygame.K_m: self.set_game_state(GAME_STATE_MAIN_MENU)
                    elif event.key == pygame.K_q: self.quit_game()
                elif self.game_state == GAME_STATE_ENTER_NAME:
                    if event.key == pygame.K_RETURN and self.player_name_input:
                        leaderboard.add_score(self.player_name_input.upper(), self.score, self.level)
                        self.leaderboard_scores = leaderboard.load_scores() 
                        self.set_game_state(GAME_STATE_LEADERBOARD)
                        self.player_name_input = "" 
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name_input = self.player_name_input[:-1]
                    elif len(self.player_name_input) < 6 and event.unicode.isalpha(): 
                        self.player_name_input += event.unicode.upper()
                elif self.game_state == GAME_STATE_LEADERBOARD:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                        self.play_sound('ui_select')
                        self.set_game_state(GAME_STATE_MAIN_MENU)
                    elif event.key == pygame.K_q: self.quit_game()

        if self.game_state == GAME_STATE_PLAYING and not self.paused and self.player and self.player.alive:
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys, current_time) 
            if keys[pygame.K_SPACE]: 
                self.player.shoot(sound=self.sounds.get('shoot'),
                                  missile_sound=self.sounds.get('missile_launch'),
                                  maze=self.maze,
                                  enemies_group=self.enemies)

    def update(self):
        current_game_ticks = pygame.time.get_ticks()
        if self.game_state == GAME_STATE_PLAYING and not self.paused:
            if not self.player or not self.maze: 
                self.set_game_state(GAME_STATE_MAIN_MENU); return
            if not self.level_cleared_pending_animation:
                current_level_timer_duration = get_game_setting("LEVEL_TIMER_DURATION")
                elapsed_time_current_level_ms = current_game_ticks - self.level_timer_start_ticks
                self.level_time_remaining_ms = current_level_timer_duration - elapsed_time_current_level_ms
                if self.level_time_remaining_ms <= 0: 
                    self.play_sound('timer_out')
                    self.lives -= 1
                    if self.player: self.player.reset_active_powerups() 
                    if self.lives <= 0: 
                        self.drone_system.set_player_level(self.level) 
                        self.drone_system._save_unlocks() 
                        if not get_game_setting("SETTINGS_MODIFIED") and leaderboard.is_high_score(self.score, self.level):
                            self.set_game_state(GAME_STATE_ENTER_NAME)
                        else:
                            self.set_game_state(GAME_STATE_GAME_OVER)
                    else: 
                        self.reset_player_after_death()
                        self._reset_level_timer()
                    return 
                if self.player.alive:
                    self.player.update(current_game_ticks, self.maze, self.enemies, self.UI_PANEL_WIDTH)
                for enemy_obj in list(self.enemies): 
                    if self.player: 
                        enemy_obj.update(self.player.get_position(), self.maze, current_game_ticks)
                    else: 
                        enemy_obj.update((0,0), self.maze, current_game_ticks)
                    if not enemy_obj.alive and not enemy_obj.bullets: 
                        enemy_obj.kill() 
                self.rings.update()
                self.power_ups.update() 
                self.check_collisions() 
                if FPS > 0 and random.random() < (POWERUP_SPAWN_CHANCE / FPS):
                    self.try_spawn_powerup()
                if self.player and not self.player.alive:
                    self.play_sound('player_death')
                    self.lives -= 1
                    if self.lives <= 0: 
                        self.drone_system.set_player_level(self.level) 
                        self.drone_system._save_unlocks()
                        if not get_game_setting("SETTINGS_MODIFIED") and leaderboard.is_high_score(self.score, self.level):
                            self.set_game_state(GAME_STATE_ENTER_NAME)
                        else:
                            self.set_game_state(GAME_STATE_GAME_OVER)
                    else: 
                        self.reset_player_after_death()
                        self._reset_level_timer()
                    return
            for ring_anim in list(self.animating_rings):
                dx = ring_anim['target_pos'][0] - ring_anim['pos'][0]
                dy = ring_anim['target_pos'][1] - ring_anim['pos'][1]
                dist = math.hypot(dx,dy)
                if dist < ring_anim['speed']: 
                    self.animating_rings.remove(ring_anim)
                else: 
                    ring_anim['pos'][0] += (dx/dist) * ring_anim['speed']
                    ring_anim['pos'][1] += (dy/dist) * ring_anim['speed']
            if self.level_cleared_pending_animation and not self.animating_rings:
                self.level_up()
                self.level_cleared_pending_animation = False 
        elif self.game_state in [GAME_STATE_SETTINGS, GAME_STATE_LEADERBOARD, GAME_STATE_DRONE_SELECT, GAME_STATE_MAIN_MENU]:
            for star in self.menu_stars:
                star[0] -= star[2] 
                if star[0] < 0: 
                    star[0] = WIDTH
                    star[1] = random.randint(0, HEIGHT)

    def check_for_level_clear_condition(self):
        if self.player and self.collected_rings >= self.total_rings_per_level:
            if not self.level_cleared_pending_animation:
                self.player.moving_forward = False 
                self.level_cleared_pending_animation = True 

    def check_collisions(self):
        if not self.player or not self.player.alive: return
        if not self.level_cleared_pending_animation:
            collided_rings_sprites = pygame.sprite.spritecollide(self.player, self.rings, True, pygame.sprite.collide_rect_ratio(0.7))
            for ring_sprite in collided_rings_sprites:
                self.score += 10
                self.play_sound('collect_ring')
                self.collected_rings += 1
                self.drone_system.add_player_cores(5) 
                anim_ring_surf = None
                if hasattr(ring_sprite, 'image'): 
                    try:
                        anim_ring_surf = pygame.transform.smoothscale(ring_sprite.image.copy(), (15,15))
                    except: 
                        anim_ring_surf = self._create_fallback_icon((15,15),"",GOLD)
                if anim_ring_surf:
                    self.animating_rings.append({
                        'pos': list(ring_sprite.rect.center),
                        'target_pos': self.ring_ui_target_pos, 
                        'speed': 15, 
                        'surface': anim_ring_surf,
                        'alpha': 255
                    })
                self.check_for_level_clear_condition() 
                if self.level_cleared_pending_animation: 
                    break
        collided_powerups = pygame.sprite.spritecollide(self.player, self.power_ups, True, pygame.sprite.collide_rect_ratio(0.7))
        for item in collided_powerups:
            if hasattr(item, 'apply_effect'):
                item.apply_effect(self.player)
                self.play_sound('weapon_upgrade_collect') 
                self.score += 25 
        if self.player.alive: 
            enemy_collisions = pygame.sprite.spritecollide(self.player, self.enemies, False, pygame.sprite.collide_rect_ratio(0.7))
            for enemy_obj in enemy_collisions:
                if enemy_obj.alive: 
                    self.player.take_damage(34, self.sounds.get('crash')) 
                if not self.player.alive: break 
        player_projectiles = pygame.sprite.Group()
        if self.player: 
            player_projectiles.add(self.player.bullets_group) 
            player_projectiles.add(self.player.missiles_group) 
        for projectile in list(player_projectiles): 
            if not projectile.alive: continue 
            hit_enemies = pygame.sprite.spritecollide(projectile, self.enemies, False, pygame.sprite.collide_rect_ratio(0.8))
            for enemy_obj in hit_enemies:
                if enemy_obj.alive:
                    enemy_obj.take_damage(projectile.damage)
                    projectile.alive = False 
                    projectile.kill() 
                    if not enemy_obj.alive: 
                        self.score += 50
                        self.drone_system.add_player_cores(25) 
                        # Check if all enemies are now defeated
                        if all(not e.alive for e in self.enemies):
                            self.all_enemies_killed_this_level = True
                            print("DEBUG: All enemies defeated this level!")
                    break 
        for enemy_obj in self.enemies:
            for bullet_obj in list(enemy_obj.bullets): 
                if self.player.alive and bullet_obj.rect.colliderect(self.player.rect):
                    self.player.take_damage(ENEMY_BULLET_DAMAGE, self.sounds.get('crash'))
                    bullet_obj.alive = False
                    bullet_obj.kill()
                if not bullet_obj.alive and bullet_obj in enemy_obj.bullets: 
                    enemy_obj.bullets.remove(bullet_obj)

    def draw_ui(self):
        if not self.player: return
        panel_surface = pygame.Surface((self.UI_PANEL_WIDTH, HEIGHT))
        panel_surface.fill(self.UI_PANEL_COLOR)
        self.screen.blit(panel_surface, (0, 0))
        
        padding = self.ui_panel_padding
        icon_text_gap = 5 # Used for spacing between icon and bar
        element_spacing = 10
        bar_max_width = self.UI_PANEL_WIDTH - (2 * padding) # Original max width available for elements
        bar_height = 18
        
        current_time = pygame.time.get_ticks()
        current_y_top = padding

        # --- Score, Level, Cores, Time (remain as before) ---
        score_text = f"🏆 Score: {self.score}"
        score_surf = self.font_ui_text.render(score_text, True, GOLD)
        self.screen.blit(score_surf, (padding, current_y_top))
        current_y_top += score_surf.get_height() + element_spacing // 2

        level_text = f"🎯 Level: {self.level}"
        level_surf = self.font_ui_text.render(level_text, True, CYAN)
        self.screen.blit(level_surf, (padding, current_y_top))
        current_y_top += level_surf.get_height() + element_spacing

        cores_text = f"💠 Cores: {self.drone_system.get_player_cores()}"
        cores_surf = self.font_ui_text.render(cores_text, True, GOLD)
        self.screen.blit(cores_surf, (padding, current_y_top))
        current_y_top += cores_surf.get_height() + element_spacing

        time_left_s = max(0, self.level_time_remaining_ms // 1000)
        mins = time_left_s // 60
        secs = time_left_s % 60
        timer_str = f"⏱️ Time: {mins:02d}:{secs:02d}"
        timer_color = WHITE if time_left_s > 30 else (RED if (current_time // 250) % 2 == 0 else DARK_RED)
        timer_surf = self.font_ui_text.render(timer_str, True, timer_color)
        self.screen.blit(timer_surf, (padding, current_y_top))
        current_y_top += timer_surf.get_height() + element_spacing * 2

        # --- Indicator Bars with Icons ---
        # Define total width for the "icon + gap + bar" element.
        # Adjust the 0.85 factor (85%) as needed.
        total_indicator_width = bar_max_width # Uses the full available space
        min_bar_segment_width = 20 # Minimum pixel width for the bar segment itself

        current_y_bottom = HEIGHT - padding
        current_y_bottom -= bar_height 

        # --- Health Bar ---
        health_bar_y = current_y_bottom
        health_icon_char = "❤️" 
        health_icon_surf = self.font_ui_text.render(health_icon_char, True, RED) # Red heart
        health_icon_width = health_icon_surf.get_width()
        health_icon_height = health_icon_surf.get_height()

        self.screen.blit(health_icon_surf, (padding, health_bar_y + (bar_height - health_icon_height) // 2))
        
        bar_drawing_start_x_health = padding + health_icon_width + icon_text_gap
        bar_segment_width_health = total_indicator_width - health_icon_width - icon_text_gap
        if bar_segment_width_health < min_bar_segment_width: bar_segment_width_health = min_bar_segment_width

        health_percentage = self.player.health / self.player.max_health if self.player.max_health > 0 else 0
        health_bar_width_fill = int(bar_segment_width_health * health_percentage)
        health_fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED
        
        pygame.draw.rect(self.screen, (50,50,50), (bar_drawing_start_x_health, health_bar_y, bar_segment_width_health, bar_height))
        if health_bar_width_fill > 0:
            pygame.draw.rect(self.screen, health_fill_color, (bar_drawing_start_x_health, health_bar_y, health_bar_width_fill, bar_height))
        pygame.draw.rect(self.screen, WHITE, (bar_drawing_start_x_health, health_bar_y, bar_segment_width_health, bar_height), 2)

        current_y_bottom -= element_spacing
        current_y_bottom -= bar_height

        # --- Weapon Charge Bar ---
        weapon_charge_bar_y = current_y_bottom
        weapon_icon_char = "💥" 
        weapon_icon_surf = self.font_ui_text.render(weapon_icon_char, True, YELLOW) # Yellow/Orange for weapon
        weapon_icon_width = weapon_icon_surf.get_width()
        weapon_icon_height = weapon_icon_surf.get_height()

        self.screen.blit(weapon_icon_surf, (padding, weapon_charge_bar_y + (bar_height - weapon_icon_height) // 2))

        bar_drawing_start_x_weapon = padding + weapon_icon_width + icon_text_gap
        bar_segment_width_weapon = total_indicator_width - weapon_icon_width - icon_text_gap
        if bar_segment_width_weapon < min_bar_segment_width: bar_segment_width_weapon = min_bar_segment_width
        
        charge_fill_pct = 0.0
        weapon_ready_color = PLAYER_BULLET_COLOR # Fallback
        charge_bar_fill_color = CYAN # Fallback
        if self.player.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER"):
            weapon_ready_color = MISSILE_COLOR
            time_since_last_shot = current_time - self.player.last_missile_shot_time
            cooldown_duration = self.player.current_missile_cooldown
        else:
            if self.player.current_weapon_mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
                weapon_ready_color = get_game_setting("LIGHTNING_COLOR")
            time_since_last_shot = current_time - self.player.last_shot_time
            cooldown_duration = self.player.current_shoot_cooldown
        if cooldown_duration > 0:
            charge_fill_pct = min(1.0, time_since_last_shot / cooldown_duration)
        else:
            charge_fill_pct = 1.0
        
        charge_bar_fill_color = weapon_ready_color if charge_fill_pct >= 1.0 else CYAN # Use weapon color when ready

        weapon_charge_bar_width_fill = int(bar_segment_width_weapon * charge_fill_pct)
        
        pygame.draw.rect(self.screen, (50,50,50), (bar_drawing_start_x_weapon, weapon_charge_bar_y, bar_segment_width_weapon, bar_height))
        if weapon_charge_bar_width_fill > 0:
            pygame.draw.rect(self.screen, charge_bar_fill_color, (bar_drawing_start_x_weapon, weapon_charge_bar_y, weapon_charge_bar_width_fill, bar_height))
        pygame.draw.rect(self.screen, WHITE, (bar_drawing_start_x_weapon, weapon_charge_bar_y, bar_segment_width_weapon, bar_height), 2)

        current_y_bottom -= element_spacing
        current_y_bottom -= bar_height

        # --- Power-up Bar ---
        powerup_bar_y = current_y_bottom
        active_powerup_for_ui = self.player.active_powerup_type
        powerup_bar_width_fill = 0
        powerup_icon_char = ""
        powerup_icon_color = WHITE # Default
        
        if active_powerup_for_ui == "shield" and self.player.shield_active:
            powerup_icon_char = "🛡️"
            powerup_icon_color = POWERUP_TYPES["shield"]["color"]
            remaining_time = self.player.shield_end_time - current_time
            if self.player.shield_duration > 0 and remaining_time > 0:
                 # Temp render to get width for bar calculation BEFORE main render
                temp_icon_surf = self.font_ui_text.render(powerup_icon_char, True, WHITE)
                temp_icon_width = temp_icon_surf.get_width()
                bar_segment_width_powerup = total_indicator_width - temp_icon_width - icon_text_gap
                if bar_segment_width_powerup < min_bar_segment_width: bar_segment_width_powerup = min_bar_segment_width
                powerup_bar_width_fill = int(bar_segment_width_powerup * (remaining_time / self.player.shield_duration))
        elif active_powerup_for_ui == "speed_boost" and self.player.speed_boost_active:
            powerup_icon_char = "💨"
            powerup_icon_color = POWERUP_TYPES["speed_boost"]["color"]
            remaining_time = self.player.speed_boost_end_time - current_time
            if self.player.speed_boost_duration > 0 and remaining_time > 0:
                temp_icon_surf = self.font_ui_text.render(powerup_icon_char, True, WHITE)
                temp_icon_width = temp_icon_surf.get_width()
                bar_segment_width_powerup = total_indicator_width - temp_icon_width - icon_text_gap
                if bar_segment_width_powerup < min_bar_segment_width: bar_segment_width_powerup = min_bar_segment_width
                powerup_bar_width_fill = int(bar_segment_width_powerup * (remaining_time / self.player.speed_boost_duration))

        if powerup_icon_char: # Only draw if there's an active power-up
            powerup_icon_surf = self.font_ui_text.render(powerup_icon_char, True, WHITE) # Draw icon in white
            powerup_icon_width = powerup_icon_surf.get_width()
            powerup_icon_height = powerup_icon_surf.get_height()
            
            self.screen.blit(powerup_icon_surf, (padding, powerup_bar_y + (bar_height - powerup_icon_height) // 2))

            bar_drawing_start_x_powerup = padding + powerup_icon_width + icon_text_gap
            # Use the bar_segment_width calculated when determining fill, or recalculate if needed
            # This assumes bar_segment_width_powerup was set if powerup_icon_char is true
            # For safety, let's ensure bar_segment_width_powerup is always defined before use here:
            current_bar_segment_width_powerup = total_indicator_width - powerup_icon_width - icon_text_gap
            if current_bar_segment_width_powerup < min_bar_segment_width: current_bar_segment_width_powerup = min_bar_segment_width

            pygame.draw.rect(self.screen, (50,50,50), (bar_drawing_start_x_powerup, powerup_bar_y, current_bar_segment_width_powerup, bar_height))
            if powerup_bar_width_fill > 0: # Fill color is the powerup_icon_color
                pygame.draw.rect(self.screen, powerup_icon_color, (bar_drawing_start_x_powerup, powerup_bar_y, powerup_bar_width_fill, bar_height))
            pygame.draw.rect(self.screen, WHITE, (bar_drawing_start_x_powerup, powerup_bar_y, current_bar_segment_width_powerup, bar_height), 2)

        # --- Lives and Rings (remain as before) ---
        current_y_bottom -= element_spacing
        ui_icon_lives_h = self.ui_icon_size_lives[1] if self.current_drone_life_icon_surface else self.small_font.get_height()
        current_y_bottom -= ui_icon_lives_h
        lives_y_pos = current_y_bottom
        if self.current_drone_life_icon_surface:
            for i in range(self.lives):
                icon_x = padding + i * (self.ui_icon_size_lives[0] + icon_text_gap // 2)
                if icon_x + self.ui_icon_size_lives[0] <= self.UI_PANEL_WIDTH - padding:
                    self.screen.blit(self.current_drone_life_icon_surface, (icon_x, lives_y_pos))
                else: break
        else:
            self.screen.blit(self.small_font.render(f"Lives: {self.lives}", True, WHITE),
                             (padding, lives_y_pos + (ui_icon_lives_h - self.small_font.get_height())//2 ))

        current_y_bottom -= element_spacing
        ring_icon_h = self.ui_icon_size_rings[1] if self.ring_ui_icon else self.small_font.get_height()
        current_y_bottom -= ring_icon_h
        ring_ui_y_pos = current_y_bottom
        ring_current_x_offset = padding
        next_ring_slot_x_abs = padding
        for i in range(self.total_rings_per_level):
            current_icon_width = self.ui_icon_size_rings[0] if self.ring_ui_icon else 0
            if ring_current_x_offset + current_icon_width > self.UI_PANEL_WIDTH - padding: break
            icon_to_draw = self.ring_ui_icon if i < self.collected_rings else \
                           (self.ring_ui_icon_empty if self.ring_ui_icon_empty else None)
            if icon_to_draw:
                self.screen.blit(icon_to_draw, (ring_current_x_offset, ring_ui_y_pos))
            elif not self.ring_ui_icon :
                pygame.draw.circle(self.screen,GREY,(ring_current_x_offset+self.ui_icon_size_rings[0]//2,
                                   ring_ui_y_pos+self.ui_icon_size_rings[1]//2),self.ui_icon_size_rings[0]//2,1)
            if i == self.collected_rings:
                next_ring_slot_x_abs = ring_current_x_offset
            ring_current_x_offset += current_icon_width + (icon_text_gap // 2)
        self.ring_ui_target_pos = (
            next_ring_slot_x_abs + (self.ui_icon_size_rings[0]//2 if self.ring_ui_icon else 0),
            ring_ui_y_pos + (self.ui_icon_size_rings[1]//2 if self.ring_ui_icon else 0)
        )
        for ring_anim in self.animating_rings:
            if 'surface' in ring_anim and ring_anim['surface']:
                self.screen.blit(ring_anim['surface'], (int(ring_anim['pos'][0]), int(ring_anim['pos'][1])))

    def draw_overlay(self):
        if self.game_state == GAME_STATE_GAME_OVER:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,180)) 
            self.screen.blit(overlay, (0,0))
            go_text = self.large_font.render("GAME OVER", True, RED)
            sc_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            self.screen.blit(go_text, go_text.get_rect(center=(WIDTH//2, HEIGHT//2-100)))
            self.screen.blit(sc_text, sc_text.get_rect(center=(WIDTH//2, HEIGHT//2-20)))
            can_submit_score = not get_game_setting("SETTINGS_MODIFIED")
            is_new_high = can_submit_score and leaderboard.is_high_score(self.score, self.level)
            prompt_y_offset = HEIGHT//2 + 40
            if not can_submit_score:
                no_lb_text = self.font.render("Leaderboard disabled (custom settings).", True, YELLOW)
                self.screen.blit(no_lb_text, no_lb_text.get_rect(center=(WIDTH//2, prompt_y_offset)))
                prompt_y_offset += self.font.get_height() + 10
            prompt_str = "R: Restart  M: Menu  Q: Quit"
            prompt_clr = WHITE
            if can_submit_score and is_new_high:
                prompt_str = "New High Score! Press any key to enter name."
                prompt_clr = GOLD
            elif can_submit_score:
                prompt_str = "R: Restart  L: Leaderboard  M: Menu  Q: Quit"
            prompt_surf = self.font.render(prompt_str, True, prompt_clr)
            self.screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH//2, prompt_y_offset)))
        elif self.game_state == GAME_STATE_ENTER_NAME:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            self.screen.blit(overlay, (0,0))
            self.screen.blit(self.large_font.render("New High Score!", True, GOLD),
                             self.large_font.render("New High Score!", True, GOLD).get_rect(center=(WIDTH//2, HEIGHT//2-150)))
            self.screen.blit(self.font.render(f"Your Score: {self.score} (Level: {self.level})", True, WHITE),
                             self.font.render(f"Your Score: {self.score} (Level: {self.level})", True, WHITE).get_rect(center=(WIDTH//2, HEIGHT//2-80)))
            self.screen.blit(self.font.render("Enter Name (6 chars, A-Z):", True, WHITE),
                             self.font.render("Enter Name (6 chars, A-Z):", True, WHITE).get_rect(center=(WIDTH//2, HEIGHT//2-20)))
            input_box = pygame.Rect(WIDTH//2-125, HEIGHT//2+30, 250, 50)
            pygame.draw.rect(self.screen, WHITE, input_box, 2) 
            self.screen.blit(self.input_font.render(self.player_name_input, True, WHITE),
                             self.input_font.render(self.player_name_input, True, WHITE).get_rect(center=input_box.center))
            self.screen.blit(self.font.render("Press ENTER to submit.", True, CYAN),
                             self.font.render("Press ENTER to submit.", True, CYAN).get_rect(center=(WIDTH//2, HEIGHT//2+120)))
        elif self.game_state == GAME_STATE_LEADERBOARD:
            self.screen.fill(BLACK) 
            if self.menu_stars: 
                for star_params in self.menu_stars:
                    pygame.draw.circle(self.screen,WHITE,(int(star_params[0]),int(star_params[1])),star_params[3])
            title_surf=self.large_font.render("Leaderboard",True,GOLD)
            title_bg=pygame.Surface((title_surf.get_width()+30,title_surf.get_height()+15),pygame.SRCALPHA)
            title_bg.fill((20,20,20,180))
            title_bg.blit(title_surf,title_surf.get_rect(center=(title_bg.get_width()//2,title_bg.get_height()//2)))
            self.screen.blit(title_bg,title_bg.get_rect(center=(WIDTH//2,HEIGHT//2-300)))
            scores_to_display = leaderboard.get_top_scores()
            score_item_y_start = HEIGHT//2 - 200
            header_y = HEIGHT//2 - 250
            item_line_height = self.font.get_height() + 10
            if not scores_to_display:
                no_scores_surf = self.font.render("No scores yet!", True, WHITE)
                no_scores_bg=pygame.Surface((no_scores_surf.get_width()+20,no_scores_surf.get_height()+10),pygame.SRCALPHA)
                no_scores_bg.fill((30,30,30,160))
                no_scores_bg.blit(no_scores_surf,(10,5))
                self.screen.blit(no_scores_bg,no_scores_bg.get_rect(center=(WIDTH//2,HEIGHT//2)))
            else:
                cols = {"Rank":WIDTH//2-350, "Name":WIDTH//2-250, "Level":WIDTH//2+50, "Score":WIDTH//2+200}
                for col_name, x_pos in cols.items():
                    header_surf = self.font.render(col_name, True, WHITE)
                    header_bg=pygame.Surface((header_surf.get_width()+10,header_surf.get_height()+5),pygame.SRCALPHA)
                    header_bg.fill((40,40,40,170))
                    header_bg.blit(header_surf,(5,2))
                    self.screen.blit(header_bg,(x_pos,header_y))
                for i, entry in enumerate(scores_to_display):
                    y_pos = score_item_y_start + i * item_line_height
                    texts_to_draw = [
                        (f"{i+1}.",WHITE,cols["Rank"]),
                        (entry.get('name','N/A'),CYAN,cols["Name"]),
                        (str(entry.get('level','-')),GREEN,cols["Level"]),
                        (str(entry.get('score',0)),GOLD,cols["Score"])
                    ]
                    for text_str, color, x_coord in texts_to_draw:
                        text_surf = self.font.render(text_str, True, color)
                        item_bg=pygame.Surface((text_surf.get_width()+8,text_surf.get_height()+4),pygame.SRCALPHA)
                        item_bg.fill((30,30,30,150)) 
                        item_bg.blit(text_surf,(4,2))
                        self.screen.blit(item_bg,(x_coord,y_pos))
            menu_prompt_surf = self.font.render("ESC: Main Menu | Q: Quit", True, WHITE)
            prompt_bg=pygame.Surface((menu_prompt_surf.get_width()+20,menu_prompt_surf.get_height()+10),pygame.SRCALPHA)
            prompt_bg.fill((20,20,20,180))
            prompt_bg.blit(menu_prompt_surf,(10,5))
            self.screen.blit(prompt_bg,prompt_bg.get_rect(center=(WIDTH//2,HEIGHT-100)))
        elif self.game_state == GAME_STATE_PLAYING and self.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,128)) 
            self.screen.blit(overlay,(0,0))
            self.screen.blit(self.large_font.render("PAUSED", True, WHITE),
                             self.large_font.render("PAUSED", True, WHITE).get_rect(center=(WIDTH//2, HEIGHT//2-40)))
            self.screen.blit(self.font.render("P: Continue, L: Leaderboard, M: Menu, Q: Quit", True, WHITE),
                             self.font.render("P: Continue, L: Leaderboard, M: Menu, Q: Quit", True, WHITE).get_rect(center=(WIDTH//2, HEIGHT//2+40)))

    def draw(self):
        self.screen.fill(BLACK) 
        if self.game_state == GAME_STATE_MAIN_MENU:
            self.draw_main_menu()
        elif self.game_state == GAME_STATE_DRONE_SELECT:
            self.draw_drone_select_menu()
        elif self.game_state == GAME_STATE_SETTINGS:
            self.draw_settings_menu()
        elif self.game_state == GAME_STATE_LEADERBOARD: 
            self.draw_overlay() 
        elif self.game_state in [GAME_STATE_PLAYING, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME]:
            if self.maze: self.maze.draw(self.screen)
            self.rings.draw(self.screen)
            self.power_ups.draw(self.screen)
            if self.player: self.player.draw(self.screen) 
            for enemy_obj in self.enemies: enemy_obj.draw(self.screen) 
            self.draw_ui() 
            if self.game_state != GAME_STATE_PLAYING or self.paused:
                self.draw_overlay()
        pygame.display.flip() 

    def check_level_progression(self): 
        if self.player and self.collected_rings >= self.total_rings_per_level:
            if not self.level_cleared_pending_animation:
                self.player.moving_forward = False
                self.level_cleared_pending_animation = True

    def level_up(self):
        self.level += 1
        self.collected_rings = 0 
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15) 
        newly_unlocked = self.drone_system.set_player_level(self.level) 
        if newly_unlocked:
            print(f"New drones unlocked by reaching level {self.level}: {newly_unlocked}")
        
        if self.player:
            # Conditional weapon upgrade
            if self.all_enemies_killed_this_level:
                self.player.cycle_weapon_state(force_cycle=False) 
                print(f"DEBUG: Level {self.level-1} cleared with all enemies killed. Weapon upgraded.")
            else:
                print(f"DEBUG: Level {self.level-1} cleared, but not all enemies killed. Weapon not upgraded.")
            
            self.player.health = min(self.player.health + 25, self.player.max_health) 
            self.player.reset_active_powerups() 
        
        self.all_enemies_killed_this_level = False # Reset flag for the new level
        self.maze = Maze(game_area_x_offset=self.UI_PANEL_WIDTH)
        self.spawn_enemies()
        self.place_collectibles(initial_setup=True)
        self._reset_level_timer()
        self.play_sound('level_up')
        self.animating_rings.clear() 
        if self.player:
            self.player.moving_forward = False 
        # print(f"Starting Level {self.level}. Player moving_forward: {self.player.moving_forward if self.player else 'N/A'}")

    def reset_player_after_death(self):
        spawn_point = self.get_safe_spawn_point()
        if self.player:
            current_drone_id = self.player.drone_id 
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id)
            self.player.reset(spawn_point[0], spawn_point[1],
                              drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, 
                              drone_sprite_path=drone_config.get("sprite_path"),
                              health_override=None 
                             )
        self.animating_rings.clear() 
        self.level_cleared_pending_animation = False 

    def restart_game(self):
        self.initialize_game_session()

    def quit_game(self):
        print("Quitting game.")
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
