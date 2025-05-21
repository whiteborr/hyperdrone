import sys
import random
import math
import os

import pygame

import leaderboard
from player import Drone
from enemy import Enemy # Will use this for prototype drones initially
from maze import Maze
from game_settings import (
    WIDTH, HEIGHT, FPS, TILE_SIZE,
    BLACK, GOLD, WHITE, GREEN, CYAN, RED, DARK_RED, GREY, YELLOW, LIGHT_BLUE, ORANGE, PURPLE,
    DARK_GREY, DARK_PURPLE, # Vault colors
    BOTTOM_PANEL_HEIGHT, GAME_PLAY_AREA_HEIGHT,
    POWERUP_SIZE, POWERUP_TYPES, POWERUP_SPAWN_CHANCE, MAX_POWERUPS_ON_SCREEN,
    ENEMY_BULLET_DAMAGE, WEAPON_UPGRADE_ITEM_LIFETIME, POWERUP_ITEM_LIFETIME,
    WEAPON_MODE_NAMES,
    GAME_STATE_MAIN_MENU, GAME_STATE_PLAYING, GAME_STATE_GAME_OVER,
    GAME_STATE_LEADERBOARD, GAME_STATE_ENTER_NAME, GAME_STATE_SETTINGS, GAME_STATE_DRONE_SELECT,
    GAME_STATE_BONUS_LEVEL_TRANSITION, GAME_STATE_BONUS_LEVEL_START, GAME_STATE_BONUS_LEVEL_PLAYING, # Existing bonus
    GAME_STATE_ARCHITECT_VAULT_INTRO, GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE, # New Vault States
    GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION,
    GAME_STATE_ARCHITECT_VAULT_SUCCESS, GAME_STATE_ARCHITECT_VAULT_FAILURE,
    DEFAULT_SETTINGS, set_game_setting, get_game_setting,
    WEAPON_MODES_SEQUENCE,
    PLAYER_BULLET_COLOR, MISSILE_COLOR, LIGHTNING_COLOR,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING,
    WEAPON_MODE_ICONS,
    CORE_FRAGMENT_DETAILS, TOTAL_CORE_FRAGMENTS_NEEDED,
    ARCHITECT_VAULT_EXTRACTION_TIMER_MS, ARCHITECT_VAULT_GAUNTLET_WAVES,
    ARCHITECT_VAULT_DRONES_PER_WAVE,
    PROTOTYPE_DRONE_HEALTH, PROTOTYPE_DRONE_SPEED, PROTOTYPE_DRONE_COLOR, # Prototype drone stats
    PROTOTYPE_DRONE_SHOOT_COOLDOWN, PROTOTYPE_DRONE_BULLET_SPEED, PROTOTYPE_DRONE_SPRITE_PATH,
    ARCHITECT_VAULT_BG_COLOR, ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR,
    ARCHITECT_REWARD_BLUEPRINT_ID, ARCHITECT_REWARD_LORE_ID
)
from drone_system import DroneSystem
from drone_configs import DRONE_DATA, DRONE_DISPLAY_ORDER

# --- Helper Function for Dynamic Fragment Spawning ---
def get_random_valid_fragment_tile(maze_grid, maze_cols, maze_rows, existing_fragment_tiles=None):
    """
    Returns a random (tile_x, tile_y) that is a path cell (0) in the maze_grid.
    Avoids tiles already occupied by other fragments in the current spawning session.
    """
    if existing_fragment_tiles is None:
        existing_fragment_tiles = set()

    available_path_tiles = []
    for r in range(maze_rows):
        for c in range(maze_cols):
            if 0 <= r < len(maze_grid) and 0 <= c < len(maze_grid[r]):
                if maze_grid[r][c] == 0 and (c, r) not in existing_fragment_tiles:
                    available_path_tiles.append((c, r))
    
    if not available_path_tiles:
        return None
    
    return random.choice(available_path_tiles)

# --- Collectible Classes ---
class Collectible(pygame.sprite.Sprite):
    """Base class for collectible items with a pulsing shine effect."""
    def __init__(self, x, y, base_color, size, thickness=3, icon_surface=None):
        super().__init__()
        self.surface_size = int(size * 2.5) # Increased surface size for better pulse visibility
        self.image = pygame.Surface((self.surface_size, self.surface_size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.icon_surface = icon_surface
        self.collected = False
        self.expired = False # For timed items
        self.base_color = base_color
        self.current_color = base_color
        self.size = float(size) # Actual visual size of the circle/icon
        self.thickness = thickness
        self.current_radius = float(self.size) # Radius for drawing the circle
        self.pulse_speed = 0.005 # Radians per tick for sin wave
        self.pulse_magnitude_radius = float(self.size * 0.15) # How much radius changes
        self.pulse_magnitude_alpha = 90 # How much alpha changes (from base 160 up to 250)
        self.pulse_offset = random.uniform(0, 2 * math.pi) # Randomize start of pulse
        self._render_to_image() # Initial render

    def _render_to_image(self):
        self.image.fill((0,0,0,0)) # Clear previous render
        surface_center_x = self.surface_size // 2
        surface_center_y = self.surface_size // 2
        # Draw the pulsing circle
        pygame.draw.circle(self.image, self.current_color,
                           (surface_center_x, surface_center_y),
                           int(self.current_radius), self.thickness)
        # Blit the icon on top if it exists
        if self.icon_surface:
            icon_rect = self.icon_surface.get_rect(center=(surface_center_x, surface_center_y))
            self.image.blit(self.icon_surface, icon_rect)

    def update_shine_and_render(self):
        time_ticks = pygame.time.get_ticks()
        # Sin wave for pulsing effect, offset for variation
        pulse_wave = math.sin(time_ticks * self.pulse_speed + self.pulse_offset)
        # Alpha: 0 to 1 range from sin wave, then scaled
        alpha_change = (pulse_wave + 1) / 2 # Normalizes sin output to 0-1
        alpha = int(160 + alpha_change * self.pulse_magnitude_alpha) # Base alpha 160, pulses up to 250
        alpha = max(100, min(255, alpha)) # Clamp alpha
        # Radius: also pulses
        self.current_radius = self.size + pulse_wave * self.pulse_magnitude_radius
        self.current_radius = max(self.size * 0.8, self.current_radius) # Clamp radius
        # Update current color with new alpha
        rgb_base = self.base_color[:3] if len(self.base_color) == 4 else self.base_color
        self.current_color = (*rgb_base, alpha)
        # Re-render the image
        self._render_to_image()

    def base_update(self, item_lifetime_constant): # For timed items
        if self.collected or self.expired:
            return True # Indicates it should be removed or ignored
        current_time = pygame.time.get_ticks()
        if hasattr(self, 'creation_time') and current_time - self.creation_time > item_lifetime_constant:
            self.expired = True
            return True
        self.update_shine_and_render()
        return False

class Ring(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y, base_color=GOLD, size=TILE_SIZE // 4, thickness=3, icon_surface=None)
    def update(self):
        if self.collected:
            return True # Already collected, do nothing
        self.update_shine_and_render()
        return False

class WeaponUpgradeItem(Collectible):
    def __init__(self, x, y):
        self.powerup_type = "weapon_upgrade"
        details = POWERUP_TYPES[self.powerup_type]
        loaded_icon = None
        if "image_filename" in details:
            try:
                image_path = os.path.join("assets", "images", "powerups", details["image_filename"])
                raw_icon = pygame.image.load(image_path).convert_alpha()
                icon_display_size = int(POWERUP_SIZE * 1.5) # Icon slightly larger than base powerup size
                loaded_icon = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
            except pygame.error as e:
                print(f"Error loading icon for {self.powerup_type} ('{image_path}'): {e}")
        super().__init__(x, y, base_color=details["color"], size=POWERUP_SIZE, thickness=4, icon_surface=loaded_icon)
        self.creation_time = pygame.time.get_ticks()

    def update(self):
        if self.base_update(WEAPON_UPGRADE_ITEM_LIFETIME): # True if collected or expired
            self.kill() # Remove from sprite groups

    def apply_effect(self, player):
        player.cycle_weapon_state(force_cycle=True) # Force cycle to ensure upgrade

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
        if self.base_update(POWERUP_ITEM_LIFETIME):
            self.kill()

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
        if self.base_update(POWERUP_ITEM_LIFETIME):
            self.kill()

    def apply_effect(self, player):
        player.arm_speed_boost(self.effect_duration, self.multiplier)

CORE_FRAGMENT_VISUAL_SIZE = TILE_SIZE // 2.5 # Visual size of the fragment item

class CoreFragmentItem(Collectible):
    def __init__(self, x, y, fragment_id, fragment_config):
        self.fragment_id = fragment_id
        self.fragment_name = fragment_config.get("name", "Core Fragment")
        self.description = fragment_config.get("description", "") # Not directly used in-game yet
        base_color = PURPLE # Default color for fragments
        icon_surface = None
        icon_filename = fragment_config.get("icon_filename")
        if icon_filename:
            try:
                # Check primary and alternative paths for icons
                primary_path = os.path.join("assets", "images", "collectibles", icon_filename)
                alt_path = os.path.join("assets", "drones", icon_filename) # Some icons might be in drone folder
                image_path_to_load = None
                if os.path.exists(primary_path): image_path_to_load = primary_path
                elif os.path.exists(alt_path): image_path_to_load = alt_path

                if image_path_to_load:
                    raw_icon = pygame.image.load(image_path_to_load).convert_alpha()
                    icon_display_size = int(CORE_FRAGMENT_VISUAL_SIZE * 0.8) # Icon smaller than the pulsing circle
                    icon_surface = pygame.transform.smoothscale(raw_icon, (icon_display_size, icon_display_size))
                else: print(f"CoreFragment icon not found: {icon_filename}")
            except pygame.error as e: print(f"Error loading icon for CF '{self.fragment_name}': {e}")
        
        super().__init__(x, y, base_color=base_color, size=CORE_FRAGMENT_VISUAL_SIZE, thickness=3, icon_surface=icon_surface)
        self.creation_time = pygame.time.get_ticks() # Fragments don't expire, but good to have

    def update(self):
        if self.collected: return True # Already collected
        self.update_shine_and_render()
        return False # Not collected yet

    def apply_effect(self, player, game_instance): # Game instance needed to access drone_system
        if not self.collected:
            if game_instance.drone_system.collect_core_fragment(self.fragment_id):
                self.collected = True
                # game_instance.play_sound('collect_fragment') # Sound played in Game.check_collisions
                return True
        return False
# --- End of Collectible Classes ---

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        # Use get_game_setting for fullscreen mode to allow it to be changed in settings later if desired
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if get_game_setting("FULLSCREEN_MODE") else 0)
        pygame.display.set_caption("HYPERDRONE")
        self.clock = pygame.time.Clock()
        self.drone_system = DroneSystem()
        self.UI_PANEL_WIDTH = 0 # Assuming UI panel is at the bottom, not side
        self.player_spawn_check_dimension = TILE_SIZE * 0.8 # For checking safe spawn, slightly smaller than tile

        # Font setup
        self.font_path_emoji = os.path.join("assets", "fonts", "seguiemj.ttf")
        self.font_path_neuropol = os.path.join("assets", "fonts", "neuropol.otf")
        self._initialize_fonts() # Moved font loading to a helper

        self.menu_options = ["Start Game", "Select Drone", "Settings", "Leaderboard", "Quit"]
        self.selected_menu_option = 0; self.game_state = None
        self.menu_music_path = os.path.join("assets", "sounds", "menu_logo.wav")
        self.gameplay_music_path = os.path.join("assets", "sounds", "background_music.wav")
        self.architect_vault_music_path = os.path.join("assets", "sounds", "architect_vault_theme.wav") # Placeholder

        self.current_music_context = None; self.level = 1; self.score = 0
        self.lives = get_game_setting("PLAYER_LIVES"); self.maze = None; self.player = None
        self.enemies = pygame.sprite.Group(); self.rings = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group(); self.core_fragments = pygame.sprite.Group()
        self.architect_vault_terminals = pygame.sprite.Group() # For entry puzzle
        self.architect_vault_hazards = pygame.sprite.Group() # For lasers, EMP traps

        self.collected_rings = 0; self.displayed_collected_rings = 0; self.total_rings_per_level = 5
        self.paused = False; self.player_name_input = ""
        self.leaderboard_scores = leaderboard.load_scores(); self.sounds = {}
        self.menu_background_image = None; self.level_timer_start_ticks = 0
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")
        
        self.current_drone_life_icon_surface = None; self.ring_ui_icon = None; self.ring_ui_icon_empty = None
        self.ui_icon_size_lives = (30, 30); self.ui_icon_size_rings = (20, 20)
        self.animating_rings = []; self.ring_ui_target_pos = (0,0)
        
        self.drone_select_options = DRONE_DISPLAY_ORDER # From drone_configs
        self.selected_drone_preview_index = 0
        self.drone_grid_icons_cache = {}; self.drone_main_display_cache = {}
        
        self._load_drone_grid_icons(); self._load_drone_main_display_images(); self.update_player_life_icon()
        self._load_ui_icons()
        self._initialize_settings_menu(); self.load_menu_assets(); self.load_sfx()
        self.menu_stars = []; self._initialize_menu_stars()
        
        self.level_cleared_pending_animation = False; self.all_enemies_killed_this_level = False
        
        # Architect's Vault specific attributes
        self.architect_vault_current_phase = None # e.g., "entry_puzzle", "gauntlet_wave_1", "extraction"
        self.architect_vault_phase_timer_start = 0
        self.architect_vault_gauntlet_current_wave = 0
        self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED # For 3 fragments
        self.architect_vault_message = "" # For displaying messages during vault
        self.architect_vault_message_timer = 0 
        
        self.played_bonus_level_after_fragments = False # Tracks if the *old* bonus was played
                                                        # Will be replaced by Architect's Vault logic

        self.set_game_state(GAME_STATE_MAIN_MENU)
        print("Game initialized.")

    def _initialize_fonts(self):
        # Define font sizes
        self.font_sizes = {
            "ui_text": 28, "ui_values": 30, "ui_emoji_general": 32, "ui_emoji_small": 20,
            "small_text": 24, "medium_text": 48, "large_text": 74, "input_text": 50,
            "menu_text": 60, "title_text": 90, "drone_name_grid": 36, "drone_desc_grid": 22,
            "drone_unlock_grid": 20, "drone_name_cycle": 42, "drone_stats_label_cycle": 26,
            "drone_stats_value_cycle": 28, "drone_desc_cycle": 22, "drone_unlock_cycle": 20,
            "vault_message": 36, "vault_timer": 48, "leaderboard_header": 32, "leaderboard_entry": 28,
            "arrow_font_key": 60 # Key for a large font suitable for arrows, potentially emoji font
        }
        # Load fonts
        self.fonts = {}
        for name, size in self.font_sizes.items():
            # Use emoji font for "arrow_font_key" and other emoji contexts
            if name == "arrow_font_key" or "emoji" in name:
                font_file = self.font_path_emoji
            else:
                font_file = self.font_path_neuropol
            
            try:
                self.fonts[name] = pygame.font.Font(font_file, size)
            except pygame.error as e:
                print(f"Warning: Font loading error for '{name}' ({font_file}, size {size}): {e}. Using fallback.")
                self.fonts[name] = pygame.font.Font(None, size) # Pygame's default font


    def _load_ui_icons(self):
        try:
            ring_icon_path = os.path.join("assets", "images", "ring_ui_icon.png")
            raw_ring_icon = pygame.image.load(ring_icon_path).convert_alpha()
            self.ring_ui_icon = pygame.transform.smoothscale(raw_ring_icon, self.ui_icon_size_rings)
            if self.ring_ui_icon:
                self.ring_ui_icon_empty = self.ring_ui_icon.copy(); self.ring_ui_icon_empty.set_alpha(80)
        except pygame.error as e: print(f"ERROR loading 'ring_ui_icon.png': {e}")


    def update_player_life_icon(self):
        selected_drone_id = self.drone_system.get_selected_drone_id()
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        icon_path = drone_config.get("icon_path") if drone_config else None
        
        if icon_path:
            try:
                raw_icon = pygame.image.load(icon_path).convert_alpha()
                self.current_drone_life_icon_surface = pygame.transform.smoothscale(raw_icon, self.ui_icon_size_lives)
            except pygame.error as e:
                print(f"Error loading life icon for {selected_drone_id} ('{icon_path}'): {e}. Using fallback.")
                self.current_drone_life_icon_surface = self._create_fallback_icon(
                    size=self.ui_icon_size_lives, text="♥", color=CYAN, font_to_use=self.fonts["ui_emoji_small"]
                )
        else:
            self.current_drone_life_icon_surface = self._create_fallback_icon(
                size=self.ui_icon_size_lives, text="♥", color=CYAN, font_to_use=self.fonts["ui_emoji_small"]
            )

    def _create_fallback_icon(self, size=(80,80), text="?", color=GREY, text_color=WHITE, font_to_use=None):
        if font_to_use is None: font_to_use = self.fonts["medium_text"] # Default if not specified
        surface = pygame.Surface(size, pygame.SRCALPHA); surface.fill(color)
        pygame.draw.rect(surface, WHITE, surface.get_rect(), 2)
        if text:
            try:
                text_surf = font_to_use.render(text, True, text_color)
                text_rect = text_surf.get_rect(center=(size[0] // 2, size[1] // 2))
                surface.blit(text_surf, text_rect)
            except Exception as e:
                print(f"Error rendering fallback icon text '{text}': {e}")
        return surface

    def _load_drone_grid_icons(self):
        for drone_id, data in DRONE_DATA.items():
            icon_display_size = (80, 80)
            if "icon_path" in data and data["icon_path"]:
                try:
                    raw_icon = pygame.image.load(data["icon_path"]).convert_alpha()
                    self.drone_grid_icons_cache[drone_id] = pygame.transform.smoothscale(raw_icon, icon_display_size)
                except pygame.error as e:
                    initials = data.get("name", "?")[:2].upper()
                    self.drone_grid_icons_cache[drone_id] = self._create_fallback_icon(
                        size=icon_display_size, text=initials, font_to_use=self.fonts["drone_name_grid"]
                    )
            else:
                initials = data.get("name", "?")[:2].upper()
                self.drone_grid_icons_cache[drone_id] = self._create_fallback_icon(
                    size=icon_display_size, text=initials, font_to_use=self.fonts["drone_name_grid"]
                )

    def _load_drone_main_display_images(self):
        display_size = (200, 200)
        for drone_id, data in DRONE_DATA.items():
            image_surface = None
            path_key = "sprite_path" if data.get("sprite_path") else "icon_path"
            image_path = data.get(path_key)
            if image_path and isinstance(image_path, str):
                try:
                    if os.path.exists(image_path):
                        loaded_image = pygame.image.load(image_path).convert_alpha()
                        image_surface = pygame.transform.smoothscale(loaded_image, display_size)
                except pygame.error as e: pass 
            
            if image_surface is None:
                initials = data.get("name", "?")[:2].upper()
                image_surface = self._create_fallback_icon(
                    size=display_size, text=initials, font_to_use=self.fonts["large_text"]
                )
            self.drone_main_display_cache[drone_id] = image_surface

    def _initialize_menu_stars(self, num_stars=150):
        self.menu_stars = []
        for _ in range(num_stars):
            x = random.randint(0, WIDTH); y = random.randint(0, HEIGHT)
            speed = random.uniform(0.2, 1.0); size = random.randint(1, 3)
            self.menu_stars.append([x, y, speed, size])

    def _initialize_settings_menu(self):
        # Full settings items list (ensure keys match game_settings.py for get_game_setting)
        self.settings_items = [
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


    def _reset_all_settings_to_default(self):
        import game_settings # Re-import to access the module-level DEFAULT_SETTINGS
        for key, default_value in game_settings.DEFAULT_SETTINGS.items():
            # Check if the key is actually one managed by the settings menu
            if any(item['key'] == key for item in self.settings_items if item['type'] != 'action'):
                 set_game_setting(key, default_value) # Use the global set_game_setting
        if hasattr(game_settings, 'SETTINGS_MODIFIED'): # Ensure the flag exists
            game_settings.SETTINGS_MODIFIED = False


    def _reset_level_timer(self):
        self.level_timer_start_ticks = pygame.time.get_ticks()
        self.level_time_remaining_ms = get_game_setting("LEVEL_TIMER_DURATION")

    def load_menu_assets(self):
        try:
            self.menu_background_image = pygame.image.load(os.path.join("assets", "images", "menu_logo.png")).convert_alpha()
        except pygame.error as e: print(f"Error loading menu image: {e}")

    def play_sound(self, name, volume=1.0):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume); self.sounds[name].play()

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

    def _play_music(self, music_path, context_label, volume=0.5, loops=-1):
        if not music_path or not os.path.exists(music_path):
            print(f"Music file not found or path is None: {music_path}. Skipping playback for context {context_label}.")
            if self.current_music_context == context_label: 
                pygame.mixer.music.stop()
                self.current_music_context = None
            return
            
        try:
            pygame.mixer.music.load(music_path); pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=loops); self.current_music_context = context_label
        except pygame.error as e: print(f"Error playing music '{music_path}': {e}")


    def set_game_state(self, new_state):
        is_playing_state = new_state in [GAME_STATE_PLAYING, GAME_STATE_BONUS_LEVEL_PLAYING] or \
                           new_state.startswith("architect_vault") 
        if self.game_state == new_state and not (is_playing_state and self.paused):
            return

        old_state = self.game_state # Store old state for conditional logic if needed
        self.game_state = new_state
        print(f"Game state changed from {old_state} to: {self.game_state}")

        music_map = {
            GAME_STATE_MAIN_MENU: (self.menu_music_path, "menu"),
            GAME_STATE_PLAYING: (self.gameplay_music_path, "gameplay"),
            GAME_STATE_LEADERBOARD: (self.menu_music_path, "menu"),
            GAME_STATE_ENTER_NAME: (self.menu_music_path, "menu"),
            GAME_STATE_GAME_OVER: (self.menu_music_path, "menu"),
            GAME_STATE_SETTINGS: (self.menu_music_path, "menu"),
            GAME_STATE_DRONE_SELECT: (self.menu_music_path, "menu"),
            GAME_STATE_BONUS_LEVEL_START: (self.gameplay_music_path, "gameplay"), # Old bonus
            GAME_STATE_BONUS_LEVEL_PLAYING: (self.gameplay_music_path, "gameplay"), # Old bonus
            GAME_STATE_ARCHITECT_VAULT_INTRO: (self.architect_vault_music_path, "architect_vault"),
            GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE: (self.architect_vault_music_path, "architect_vault"),
            GAME_STATE_ARCHITECT_VAULT_GAUNTLET: (self.architect_vault_music_path, "architect_vault_action"), 
            GAME_STATE_ARCHITECT_VAULT_EXTRACTION: (self.architect_vault_music_path, "architect_vault_action"), 
            GAME_STATE_ARCHITECT_VAULT_SUCCESS: (self.menu_music_path, "menu"), 
            GAME_STATE_ARCHITECT_VAULT_FAILURE: (self.menu_music_path, "menu")
        }
        
        music_info = music_map.get(self.game_state)
        if music_info:
            path, context = music_info
            if self.current_music_context != context or not pygame.mixer.music.get_busy():
                self._play_music(path, context)
            elif is_playing_state and self.paused and old_state == self.game_state : # Unpausing the same playing state
                 pygame.mixer.music.unpause()
        
        if self.game_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
            self.initialize_architect_vault_session() 
            self.architect_vault_current_phase = "intro"
            self.architect_vault_phase_timer_start = pygame.time.get_ticks()
            self.architect_vault_message = "The Architect's Vault... Entry protocol initiated."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000 
        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_current_phase = "entry_puzzle"
            self.architect_vault_puzzle_terminals_activated = [False] * TOTAL_CORE_FRAGMENTS_NEEDED
            self.spawn_architect_vault_terminals()
            self.architect_vault_message = "Activate terminals with Core Fragments."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_GAUNTLET:
            self.architect_vault_current_phase = "gauntlet_intro" 
            self.architect_vault_gauntlet_current_wave = 0
            self.enemies.empty() 
            self.architect_vault_message = "Security systems online. Prepare for hostiles."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_EXTRACTION:
            self.architect_vault_current_phase = "extraction"
            self.architect_vault_phase_timer_start = pygame.time.get_ticks() 
            self.play_sound('vault_alarm', 0.7)
            self.architect_vault_message = "SELF-DESTRUCT SEQUENCE ACTIVATED! ESCAPE NOW!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + ARCHITECT_VAULT_EXTRACTION_TIMER_MS
        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS:
            self.architect_vault_message = "Vault Conquered! Blueprint Acquired!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
            self.drone_system.mark_architect_vault_completed(True)
            self.score += 2500 
            self.drone_system.add_player_cores(500) 
            self.drone_system._save_unlocks() 
        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
            self.architect_vault_message = "Vault Mission Failed. Returning to base..."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 5000
            self.drone_system.mark_architect_vault_completed(False)

        if self.game_state == GAME_STATE_DRONE_SELECT:
            current_selected_id = self.drone_system.get_selected_drone_id()
            try: self.selected_drone_preview_index = self.drone_select_options.index(current_selected_id)
            except ValueError: self.selected_drone_preview_index = 0


    def spawn_core_fragments_for_level(self):
        if not self.maze or not CORE_FRAGMENT_DETAILS: return
        occupied_fragment_tiles_this_level = set()
        for frag_key, details in CORE_FRAGMENT_DETAILS.items():
            if not details: continue 
            spawn_info = details.get("spawn_info", {})
            if spawn_info.get("level") == self.level and not self.drone_system.has_collected_fragment(details["id"]):
                random_tile = get_random_valid_fragment_tile(
                    self.maze.grid, self.maze.actual_maze_cols, self.maze.actual_maze_rows,
                    occupied_fragment_tiles_this_level
                )
                if random_tile:
                    tile_x, tile_y = random_tile
                    abs_x = tile_x * TILE_SIZE + TILE_SIZE // 2 + self.maze.game_area_x_offset
                    abs_y = tile_y * TILE_SIZE + TILE_SIZE // 2
                    self.core_fragments.add(CoreFragmentItem(abs_x, abs_y, details["id"], details))
                    occupied_fragment_tiles_this_level.add(random_tile)

    def place_collectibles(self, initial_setup=False):
        path_cells_relative = self.maze.get_path_cells() if self.maze else []
        if initial_setup and path_cells_relative:
            self.rings.empty()
            shuffled_path_cells_relative = random.sample(path_cells_relative, len(path_cells_relative))
            for i in range(min(self.total_rings_per_level, len(shuffled_path_cells_relative))):
                rel_x, rel_y = shuffled_path_cells_relative[i]
                abs_x = rel_x + self.maze.game_area_x_offset; abs_y = rel_y
                self.rings.add(Ring(abs_x, abs_y))
        
        self.spawn_core_fragments_for_level() 
        self.try_spawn_powerup() 

    def initialize_game_session(self): 
        self.level = 1; self.lives = get_game_setting("PLAYER_LIVES"); self.score = 0
        self.drone_system.set_player_level(self.level) 
        self.level_cleared_pending_animation = False; self.all_enemies_killed_this_level = False
        
        self.maze = Maze(game_area_x_offset=self.UI_PANEL_WIDTH, maze_type="standard")
        player_start_pos = self.get_safe_spawn_point(self.player_spawn_check_dimension, self.player_spawn_check_dimension)
        
        selected_drone_id = self.drone_system.get_selected_drone_id()
        effective_drone_stats = self.drone_system.get_drone_stats(selected_drone_id, is_in_architect_vault=False)
        drone_config = self.drone_system.get_drone_config(selected_drone_id)
        player_ingame_sprite = drone_config.get("ingame_sprite_path")

        self.player = Drone(player_start_pos[0], player_start_pos[1], drone_id=selected_drone_id,
                            drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite,
                            crash_sound=self.sounds.get('crash'), drone_system=self.drone_system)
        self.update_player_life_icon()
        
        self.enemies.empty(); self.spawn_enemies() 
        if self.player: self.player.bullets_group.empty(); self.player.missiles_group.empty()
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty()
        self.collected_rings = 0; self.displayed_collected_rings = 0; self.total_rings_per_level = 5
        self.paused = False; self.player_name_input = ""; self.animating_rings.clear()
        
        self.place_collectibles(initial_setup=True)
        self._reset_level_timer()
        self.set_game_state(GAME_STATE_PLAYING)

    def initialize_architect_vault_session(self):
        print("--- Initializing Architect's Vault! ---")
        self.maze = Maze(game_area_x_offset=self.UI_PANEL_WIDTH, maze_type="architect_vault") 
        
        if self.player:
            safe_spawn = self.get_safe_spawn_point(self.player_spawn_check_dimension, self.player_spawn_check_dimension)
            current_drone_id = self.player.drone_id
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=True)
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            
            self.player.reset(safe_spawn[0], safe_spawn[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite)
            self.player.reset_active_powerups() 
        
        self.enemies.empty() 
        self.rings.empty(); self.power_ups.empty(); self.core_fragments.empty() 
        self.architect_vault_terminals.empty(); self.architect_vault_hazards.empty()

        self.architect_vault_current_phase = "intro" 
        self.architect_vault_phase_timer_start = pygame.time.get_ticks()
        self.level_time_remaining_ms = 0 

    def spawn_architect_vault_terminals(self):
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
            # Initial color based on whether it's considered "active" yet (all start inactive)
            terminal.image.fill(PURPLE) 
            terminal.rect = terminal.image.get_rect(center=(abs_x, abs_y))
            terminal.terminal_id = i 
            terminal.is_active = False # Custom attribute to track activation
            self.architect_vault_terminals.add(terminal)

    def spawn_prototype_drones(self, count):
        if not self.maze or not self.player: return
        path_cells_rel = self.maze.get_path_cells()
        enemy_shoot_sound = self.sounds.get('enemy_shoot') 

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
                
                proto_drone = Enemy(abs_x, abs_y, shoot_sound=enemy_shoot_sound, sprite_path=PROTOTYPE_DRONE_SPRITE_PATH)
                proto_drone.health = PROTOTYPE_DRONE_HEALTH
                proto_drone.max_health = PROTOTYPE_DRONE_HEALTH
                proto_drone.speed = PROTOTYPE_DRONE_SPEED
                proto_drone.shoot_cooldown = PROTOTYPE_DRONE_SHOOT_COOLDOWN
                self.enemies.add(proto_drone)
                spawned = True
            if not spawned and path_cells_rel: 
                rel_fx,rel_fy = random.choice(path_cells_rel)
                abs_fx,abs_fy = rel_fx + self.maze.game_area_x_offset, rel_fy
                proto_drone = Enemy(abs_fx,abs_fy,shoot_sound=enemy_shoot_sound, sprite_path=PROTOTYPE_DRONE_SPRITE_PATH)
                proto_drone.health = PROTOTYPE_DRONE_HEALTH; proto_drone.max_health = PROTOTYPE_DRONE_HEALTH
                proto_drone.speed = PROTOTYPE_DRONE_SPEED; proto_drone.shoot_cooldown = PROTOTYPE_DRONE_SHOOT_COOLDOWN
                self.enemies.add(proto_drone)


    def get_safe_spawn_point(self, drone_check_width, drone_check_height):
        if not self.maze: return (WIDTH // 4 + self.UI_PANEL_WIDTH, GAME_PLAY_AREA_HEIGHT // 2)
        path_cells_relative = self.maze.get_path_cells()
        if not path_cells_relative: return (WIDTH // 4 + self.UI_PANEL_WIDTH, GAME_PLAY_AREA_HEIGHT // 2)
        
        path_cells_absolute = [(x + self.maze.game_area_x_offset, y) for x, y in path_cells_relative]
        random.shuffle(path_cells_absolute)
        for spawn_x, spawn_y in path_cells_absolute:
            if not self.maze.is_wall(spawn_x, spawn_y, drone_check_width, drone_check_height):
                return (spawn_x, spawn_y)
        return path_cells_absolute[0] 

    def spawn_enemies(self): 
        self.enemies.empty()
        num_enemies = min(self.level + 1, 6) 
        path_cells_relative = self.maze.get_path_cells() if self.maze else []
        enemy_shoot_sound = self.sounds.get('enemy_shoot')
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
                self.enemies.add(Enemy(abs_x,abs_y,shoot_sound=enemy_shoot_sound)); spawned=True
            if not spawned and path_cells_relative: 
                rel_fx,rel_fy = random.choice(path_cells_relative)
                abs_fx,abs_fy = rel_fx + self.maze.game_area_x_offset, rel_fy
                self.enemies.add(Enemy(abs_fx,abs_fy,shoot_sound=enemy_shoot_sound))

    def try_spawn_powerup(self): 
        if len(self.power_ups) < MAX_POWERUPS_ON_SCREEN:
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


    def draw_main_menu(self):
        if self.menu_background_image:
            self.screen.blit(pygame.transform.scale(self.menu_background_image, (WIDTH, HEIGHT)), (0,0))
        else: self.screen.fill(BLACK)
        
        menu_item_start_y = HEIGHT // 2 - 80; item_spacing = 75
        for i, option_text in enumerate(self.menu_options):
            is_selected = (i == self.selected_menu_option); text_color = GOLD if is_selected else WHITE
            active_menu_font = self.fonts["menu_text"]
            if is_selected: # Make selected item slightly larger
                 try: active_menu_font = pygame.font.Font(self.font_path_neuropol, self.font_sizes["menu_text"] + 8)
                 except: active_menu_font = pygame.font.Font(None, self.font_sizes["menu_text"] + 8) # Fallback
            
            try:
                text_surf = active_menu_font.render(option_text, True, text_color)
                text_rect = text_surf.get_rect()
                button_width = text_rect.width + 60; button_height = text_rect.height + 25
                button_surface_rect = pygame.Rect(0,0,button_width, button_height)
                button_surface_rect.center = (WIDTH // 2, menu_item_start_y + i * item_spacing)
                
                button_bg_surface = pygame.Surface(button_surface_rect.size, pygame.SRCALPHA)
                current_bg_color = (70,70,70,220) if is_selected else (50,50,50,180)
                pygame.draw.rect(button_bg_surface, current_bg_color, button_bg_surface.get_rect(), border_radius=15)
                if is_selected: pygame.draw.rect(button_bg_surface, GOLD, button_bg_surface.get_rect(), 3, border_radius=15)
                
                button_bg_surface.blit(text_surf, text_surf.get_rect(center=(button_width//2, button_height//2)))
                self.screen.blit(button_bg_surface, button_surface_rect.topleft)
            except Exception as e:
                print(f"Error rendering menu item '{option_text}': {e}")
                # Optionally draw a placeholder if rendering fails
                pygame.draw.rect(self.screen, RED, (WIDTH // 2 - 100, menu_item_start_y + i * item_spacing - 20, 200, 40))


        try:
            instr_surf = self.fonts["small_text"].render("Use UP/DOWN keys, ENTER to select.", True, CYAN)
            instr_bg_box=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA); instr_bg_box.fill((30,30,30,150))
            instr_bg_box.blit(instr_surf,instr_surf.get_rect(center=(instr_bg_box.get_width()//2,instr_bg_box.get_height()//2)))
            self.screen.blit(instr_bg_box, instr_bg_box.get_rect(center=(WIDTH//2, HEIGHT-100)))
        except Exception as e: print(f"Error rendering menu instructions: {e}")

        if get_game_setting("SETTINGS_MODIFIED"):
            try:
                warning_surf = self.fonts["small_text"].render("Custom settings active: Leaderboard disabled.", True, YELLOW)
                self.screen.blit(warning_surf, warning_surf.get_rect(center=(WIDTH//2, HEIGHT-50)))
            except Exception as e: print(f"Error rendering settings warning: {e}")


    def draw_drone_select_menu(self):
        self.screen.fill(BLACK)
        if self.menu_stars:
            for star_params in self.menu_stars:
                pygame.draw.circle(self.screen, WHITE, (int(star_params[0]), int(star_params[1])), star_params[3])

        try:
            title_surf = self.fonts["title_text"].render("Select Drone", True, GOLD)
            title_rect = title_surf.get_rect(center=(WIDTH // 2, 70))
            self.screen.blit(title_surf, title_rect)
        except Exception as e:
            print(f"Error rendering drone select title: {e}")
            return 

        num_options = len(self.drone_select_options)
        if not self.drone_select_options:
            try:
                no_drones_surf = self.fonts["large_text"].render("NO DRONES AVAILABLE", True, RED)
                self.screen.blit(no_drones_surf, no_drones_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            except Exception as e: print(f"Error rendering 'no drones' message: {e}")
            return

        current_drone_id = self.drone_select_options[self.selected_drone_preview_index]
        drone_config = DRONE_DATA.get(current_drone_id, {})
        # Pass is_in_architect_vault=False as this is drone select, not in-game vault
        drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) 
        is_unlocked = self.drone_system.is_drone_unlocked(current_drone_id)
        is_currently_equipped = (current_drone_id == self.drone_system.get_selected_drone_id())

        # --- Card Layout Calculations ---
        display_area_center_x = WIDTH // 2
        drone_image_surf = self.drone_main_display_cache.get(current_drone_id)
        img_width = drone_image_surf.get_width() if drone_image_surf else 200
        img_height = drone_image_surf.get_height() if drone_image_surf else 200

        name_text = drone_config.get("name", "N/A")
        name_surf_temp = self.fonts["drone_name_cycle"].render(name_text, True, WHITE)
        name_height = name_surf_temp.get_height()

        # Stats
        hp_stat = drone_stats.get("hp")
        speed_stat = drone_stats.get("speed")
        turn_speed_stat = drone_stats.get("turn_speed")
        fire_rate_mult = drone_stats.get("fire_rate_multiplier", 1.0)
        special_ability_key = drone_stats.get("special_ability")

        hp_display = str(hp_stat) if hp_stat is not None else "N/A"
        speed_display = f"{speed_stat:.1f}" if isinstance(speed_stat, (int, float)) else str(speed_stat) if speed_stat is not None else "N/A"
        turn_speed_display = f"{turn_speed_stat:.1f}" if isinstance(turn_speed_stat, (int, float)) else str(turn_speed_stat) if turn_speed_stat is not None else "N/A"
        
        fire_rate_text = f"{1/fire_rate_mult:.1f}x" # Display as multiplier (e.g., 2x faster if mult is 0.5)
        if fire_rate_mult == 1.0: fire_rate_text += " (Normal)"
        elif fire_rate_mult < 1.0: fire_rate_text += " (Faster)" # fire_rate_multiplier < 1 means faster
        else: fire_rate_text += " (Slower)" # fire_rate_multiplier > 1 means slower

        special_ability_name = "None"
        if special_ability_key == "phantom_cloak": special_ability_name = "Phantom Cloak"
        elif special_ability_key == "omega_boost": special_ability_name = "Omega Boost"
        
        stats_data_tuples = [
            ("HP:", hp_display), ("Speed:", speed_display), ("Turn Speed:", turn_speed_display),
            ("Fire Rate:", fire_rate_text), ("Special:", special_ability_name)
        ]
        stats_content_surfaces = []
        max_stat_label_w = 0; max_stat_value_w = 0
        stat_line_h = self.fonts["drone_stats_label_cycle"].get_height() + 5

        for label_str, value_str in stats_data_tuples:
            label_s = self.fonts["drone_stats_label_cycle"].render(label_str, True, LIGHT_BLUE if is_unlocked else GREY)
            value_s = self.fonts["drone_stats_value_cycle"].render(value_str, True, WHITE if is_unlocked else GREY)
            stats_content_surfaces.append((label_s, value_s))
            max_stat_label_w = max(max_stat_label_w, label_s.get_width())
            max_stat_value_w = max(max_stat_value_w, value_s.get_width())

        stats_box_padding = 15 # Increased padding
        stats_box_visual_width = max_stat_label_w + max_stat_value_w + 3 * stats_box_padding
        stats_box_visual_height = (len(stats_content_surfaces) * stat_line_h) - (5 if stats_content_surfaces else 0) + 2 * stats_box_padding

        # Description
        desc_text = drone_config.get("description", "")
        desc_color_final = (200,200,200) if is_unlocked else (100,100,100)
        desc_max_width_for_card = WIDTH * 0.45 # Adjusted width
        desc_lines_surfs = []
        words = desc_text.split(' ')
        current_line_text_desc = ""
        for word in words:
            test_line = current_line_text_desc + word + " "
            if self.fonts["drone_desc_cycle"].size(test_line)[0] < desc_max_width_for_card:
                current_line_text_desc = test_line
            else:
                desc_lines_surfs.append(self.fonts["drone_desc_cycle"].render(current_line_text_desc.strip(), True, desc_color_final))
                current_line_text_desc = word + " "
        if current_line_text_desc:
            desc_lines_surfs.append(self.fonts["drone_desc_cycle"].render(current_line_text_desc.strip(), True, desc_color_final))
        
        total_desc_height = sum(s.get_height() for s in desc_lines_surfs) + (len(desc_lines_surfs)-1)*3 if desc_lines_surfs else 0

        # Unlock Info
        unlock_text_str = ""; unlock_text_color = WHITE
        unlock_condition = drone_config.get("unlock_condition",{})
        if not is_unlocked:
            condition_text_str = unlock_condition.get("description","Locked")
            unlock_cost_val = unlock_condition.get("value")
            type_is_cores_unlock = unlock_condition.get("type") == "cores"
            unlock_text_str = condition_text_str
            if type_is_cores_unlock and unlock_cost_val is not None and self.drone_system.get_player_cores() >= unlock_cost_val:
                unlock_text_str += f" (ENTER to Unlock: {unlock_cost_val} 💠)"; unlock_text_color = GREEN
            else: unlock_text_color = YELLOW
        elif is_currently_equipped:
            unlock_text_str = "EQUIPPED"; unlock_text_color = GREEN
        else:
            unlock_text_str = "Press ENTER to Select"; unlock_text_color = CYAN
        
        unlock_info_surf = self.fonts["drone_unlock_cycle"].render(unlock_text_str, True, unlock_text_color)
        unlock_info_height = unlock_info_surf.get_height() if unlock_info_surf else 0

        # Card Sizing & Positioning
        spacing_between_elements = 15; padding_inside_card = 25
        card_content_total_h = (img_height + spacing_between_elements + name_height +
                                spacing_between_elements + stats_box_visual_height +
                                spacing_between_elements + total_desc_height +
                                spacing_between_elements + unlock_info_height)
        
        max_content_width_for_card = max(
            img_width, name_surf_temp.get_width(), stats_box_visual_width,
            max(s.get_width() for s in desc_lines_surfs) if desc_lines_surfs else 0,
            unlock_info_surf.get_width() if unlock_info_surf else 0
        )
        card_w = max_content_width_for_card + 2*padding_inside_card
        card_w = min(card_w, WIDTH*0.6) # Max card width
        card_h = card_content_total_h + 2*padding_inside_card + 20 # Extra padding at bottom
        
        # Ensure title_rect is defined before use here
        title_bottom = 70 + self.fonts["title_text"].get_height() // 2 if "title_text" in self.fonts else 100

        main_card_x = display_area_center_x - card_w//2
        main_card_y = title_bottom + 40 # Position below title
        main_card_rect = pygame.Rect(main_card_x, main_card_y, card_w, card_h)

        # Draw Card Background
        pygame.draw.rect(self.screen, (25,30,40,230), main_card_rect, border_radius=20) # Slightly more opaque
        pygame.draw.rect(self.screen, GOLD, main_card_rect, 3, border_radius=20)

        # --- Draw Elements Inside Card ---
        current_y_in_card = main_card_rect.top + padding_inside_card

        # Drone Image
        if drone_image_surf:
            display_drone_image = drone_image_surf
            if not is_unlocked:
                temp_img = drone_image_surf.copy(); temp_img.set_alpha(100); display_drone_image = temp_img
            final_img_rect = display_drone_image.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(display_drone_image, final_img_rect)
            current_y_in_card = final_img_rect.bottom + spacing_between_elements
        else: # Fallback spacing if no image
            current_y_in_card += img_height + spacing_between_elements

        # Drone Name
        name_color_final = WHITE if is_unlocked else GREY
        name_surf_final = self.fonts["drone_name_cycle"].render(name_text, True, name_color_final)
        final_name_rect = name_surf_final.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
        self.screen.blit(name_surf_final, final_name_rect)
        current_y_in_card = final_name_rect.bottom + spacing_between_elements

        # Stats Box
        final_stats_box_draw_rect = pygame.Rect(main_card_rect.centerx-stats_box_visual_width//2, current_y_in_card, stats_box_visual_width, stats_box_visual_height)
        pygame.draw.rect(self.screen, (40,45,55,200), final_stats_box_draw_rect, border_radius=10) # More opaque
        pygame.draw.rect(self.screen, CYAN, final_stats_box_draw_rect, 1, border_radius=10)
        
        stat_y_pos_render = final_stats_box_draw_rect.top + stats_box_padding
        for i, (label_s, value_s) in enumerate(stats_content_surfaces):
            self.screen.blit(label_s, (final_stats_box_draw_rect.left+stats_box_padding, stat_y_pos_render))
            self.screen.blit(value_s, (final_stats_box_draw_rect.right-stats_box_padding-value_s.get_width(), stat_y_pos_render))
            stat_y_pos_render += max(label_s.get_height(), value_s.get_height()) + (5 if i < len(stats_content_surfaces)-1 else 0)
        current_y_in_card = final_stats_box_draw_rect.bottom + spacing_between_elements

        # Description
        desc_start_y_render = current_y_in_card
        for line_surf in desc_lines_surfs:
            self.screen.blit(line_surf, line_surf.get_rect(centerx=main_card_rect.centerx, top=desc_start_y_render))
            desc_start_y_render += line_surf.get_height() + 3
        current_y_in_card = desc_start_y_render + 5 # Small gap after description

        # Unlock Info
        if unlock_info_surf:
            unlock_info_rect = unlock_info_surf.get_rect(centerx=main_card_rect.centerx, top=current_y_in_card)
            self.screen.blit(unlock_info_surf, unlock_info_rect)

        # Navigation Arrows
        arrow_font = self.fonts.get("arrow_font_key", self.fonts["large_text"]) # Fallback to large_text if specific arrow_font not found
        left_arrow_surf = arrow_font.render("◀", True, WHITE if num_options > 1 else GREY)
        right_arrow_surf = arrow_font.render("▶", True, WHITE if num_options > 1 else GREY)
        arrow_y_center = main_card_rect.centery
        arrow_padding_from_card_edge = 40
        if num_options > 1:
            left_arrow_rect = left_arrow_surf.get_rect(centery=arrow_y_center, right=main_card_rect.left-arrow_padding_from_card_edge)
            right_arrow_rect = right_arrow_surf.get_rect(centery=arrow_y_center, left=main_card_rect.right+arrow_padding_from_card_edge)
            self.screen.blit(left_arrow_surf, left_arrow_rect)
            self.screen.blit(right_arrow_surf, right_arrow_rect)

        # Instructions & Cores Display (Bottom of screen)
        try:
            instr_surf = self.fonts["small_text"].render("LEFT/RIGHT: Cycle | ENTER: Select/Unlock | ESC: Back", True, CYAN)
            instr_bg_rect = pygame.Rect(0, HEIGHT - 70, WIDTH, 30) # Adjusted y for instructions
            instr_surf_rect = instr_surf.get_rect(center=instr_bg_rect.center)
            self.screen.blit(instr_surf, instr_surf_rect)

            cores_label_text_surf = self.fonts["ui_text"].render(f"Player Cores: ", True, GOLD)
            cores_value_text_surf = self.fonts["ui_values"].render(f"{self.drone_system.get_player_cores()}", True, GOLD)
            cores_emoji_surf = self.fonts["ui_emoji_general"].render(" 💠", True, GOLD)
            
            total_cores_display_width = cores_label_text_surf.get_width()+cores_value_text_surf.get_width()+cores_emoji_surf.get_width()
            cores_start_x = WIDTH - 20 - total_cores_display_width
            max_element_height_cores = max(cores_label_text_surf.get_height(), cores_value_text_surf.get_height(), cores_emoji_surf.get_height())
            cores_y_baseline = HEIGHT - 20 - max_element_height_cores # Position at bottom right

            self.screen.blit(cores_label_text_surf, (cores_start_x, cores_y_baseline+(max_element_height_cores-cores_label_text_surf.get_height())//2))
            current_x_offset_cores = cores_start_x + cores_label_text_surf.get_width()
            self.screen.blit(cores_value_text_surf, (current_x_offset_cores, cores_y_baseline+(max_element_height_cores-cores_value_text_surf.get_height())//2))
            current_x_offset_cores += cores_value_text_surf.get_width()
            self.screen.blit(cores_emoji_surf, (current_x_offset_cores, cores_y_baseline+(max_element_height_cores-cores_emoji_surf.get_height())//2))

        except Exception as e: print(f"Error rendering drone select bottom UI: {e}")


    def draw_settings_menu(self):
        self.screen.fill(BLACK)
        if self.menu_stars:
            for star_params in self.menu_stars: pygame.draw.circle(self.screen,WHITE,(int(star_params[0]),int(star_params[1])),star_params[3])
        
        try:
            title_surf=self.fonts["title_text"].render("Settings",True,GOLD)
            title_bg=pygame.Surface((title_surf.get_width()+30,title_surf.get_height()+15),pygame.SRCALPHA); title_bg.fill((20,20,20,180))
            title_bg.blit(title_surf,title_surf.get_rect(center=(title_bg.get_width()//2,title_bg.get_height()//2)))
            self.screen.blit(title_bg,title_bg.get_rect(center=(WIDTH//2,80)))
        except Exception as e: print(f"Error rendering settings title: {e}")

        item_y_start=180; item_line_height= (self.fonts["ui_text"].get_height() if "ui_text" in self.fonts else 30) + 15
        max_items_on_screen=(HEIGHT-item_y_start-100)//item_line_height
        
        view_start_index = 0
        if len(self.settings_items) > max_items_on_screen :
            view_start_index = max(0, self.selected_setting_index - max_items_on_screen // 2)
            view_start_index = min(view_start_index, len(self.settings_items) - max_items_on_screen)
        
        view_end_index = min(view_start_index+max_items_on_screen, len(self.settings_items))

        for i_display, list_idx in enumerate(range(view_start_index, view_end_index)):
            if list_idx >= len(self.settings_items): continue # Boundary check
            item = self.settings_items[list_idx]; y_pos = item_y_start + i_display * item_line_height
            color = YELLOW if list_idx == self.selected_setting_index else WHITE
            
            try:
                label_surf = self.fonts["ui_text"].render(item["label"], True, color)
                label_bg_rect = pygame.Rect(WIDTH//4-105,y_pos-5,label_surf.get_width()+10,label_surf.get_height()+10)
                pygame.draw.rect(self.screen,(30,30,30,160),label_bg_rect,border_radius=5)
                self.screen.blit(label_surf, (WIDTH//4-100, y_pos))

                if "note" in item and list_idx == self.selected_setting_index:
                    note_surf = self.fonts["small_text"].render(item["note"], True, LIGHT_BLUE)
                    self.screen.blit(note_surf, note_surf.get_rect(left=label_bg_rect.right+10, centery=label_bg_rect.centery))
                
                if item["type"] != "action":
                    current_value = get_game_setting(item["key"]); display_value = ""
                    if item["type"] == "numeric":
                        display_value = f"{current_value/1000:.0f}s" if item.get("is_ms_to_sec") else (f"{current_value:.1f}" if isinstance(current_value,float) else str(current_value))
                    elif item["type"] == "choice": display_value = item["get_display"](current_value)
                    
                    value_surf = self.fonts["ui_text"].render(display_value, True, color)
                    value_bg_rect = pygame.Rect(WIDTH//2+195,y_pos-5,value_surf.get_width()+10,value_surf.get_height()+10)
                    pygame.draw.rect(self.screen,(30,30,30,160),value_bg_rect,border_radius=5)
                    self.screen.blit(value_surf, (WIDTH//2+200, y_pos))
                    
                    if item["key"] in DEFAULT_SETTINGS and current_value != DEFAULT_SETTINGS[item["key"]]:
                        self.screen.blit(self.fonts["small_text"].render("*",True,RED),(WIDTH//2+180,y_pos))
                elif list_idx == self.selected_setting_index: # For "action" type items
                     action_hint_surf = self.fonts["ui_text"].render("<ENTER>", True, YELLOW)
                     action_hint_bg_rect=pygame.Rect(WIDTH//2+195,y_pos-5,action_hint_surf.get_width()+10,action_hint_surf.get_height()+10)
                     pygame.draw.rect(self.screen,(30,30,30,160),action_hint_bg_rect,border_radius=5)
                     self.screen.blit(action_hint_surf,(WIDTH//2+200,y_pos))
            except Exception as e:
                print(f"Error rendering settings item '{item.get('label', 'UNKNOWN')}': {e}")
                # Draw a red box as an error indicator for this item
                pygame.draw.rect(self.screen, RED, (WIDTH//4-100, y_pos, 400, item_line_height - 5))


        try:
            instr_surf = self.fonts["small_text"].render("UP/DOWN: Select | LEFT/RIGHT: Adjust | ENTER: Activate | ESC: Back", True, CYAN)
            instr_bg=pygame.Surface((instr_surf.get_width()+20,instr_surf.get_height()+10),pygame.SRCALPHA); instr_bg.fill((20,20,20,180))
            instr_bg.blit(instr_surf,(10,5)); self.screen.blit(instr_bg,instr_bg.get_rect(center=(WIDTH//2,HEIGHT-70)))
        except Exception as e: print(f"Error rendering settings instructions: {e}")
        
        if get_game_setting("SETTINGS_MODIFIED"):
            try:
                warning_surf = self.fonts["small_text"].render("Settings changed. Leaderboard will be disabled.", True, YELLOW)
                warning_bg=pygame.Surface((warning_surf.get_width()+10,warning_surf.get_height()+5),pygame.SRCALPHA); warning_bg.fill((20,20,20,180))
                warning_bg.blit(warning_surf,(5,2)); self.screen.blit(warning_bg,warning_bg.get_rect(center=(WIDTH//2,HEIGHT-35)))
            except Exception as e: print(f"Error rendering settings modified warning: {e}")


    def handle_events(self):
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.quit_game()
            if event.type == pygame.KEYDOWN:
                if self.game_state == GAME_STATE_MAIN_MENU:
                    if event.key == pygame.K_UP: self.selected_menu_option=(self.selected_menu_option-1+len(self.menu_options))%len(self.menu_options); self.play_sound('ui_select')
                    elif event.key == pygame.K_DOWN: self.selected_menu_option=(self.selected_menu_option+1)%len(self.menu_options); self.play_sound('ui_select')
                    elif event.key == pygame.K_RETURN:
                        self.play_sound('ui_confirm'); action=self.menu_options[self.selected_menu_option]
                        if action=="Start Game": self.initialize_game_session()
                        elif action=="Select Drone": self.set_game_state(GAME_STATE_DRONE_SELECT)
                        elif action=="Settings": self.set_game_state(GAME_STATE_SETTINGS)
                        elif action=="Leaderboard": self.leaderboard_scores=leaderboard.load_scores(); self.set_game_state(GAME_STATE_LEADERBOARD)
                        elif action=="Quit": self.quit_game()
                
                elif self.game_state == GAME_STATE_DRONE_SELECT:
                    num_options=len(self.drone_select_options)
                    if num_options>0: # Ensure there are drones to select
                        if event.key==pygame.K_LEFT: self.selected_drone_preview_index=(self.selected_drone_preview_index-1+num_options)%num_options; self.play_sound('ui_select')
                        elif event.key==pygame.K_RIGHT: self.selected_drone_preview_index=(self.selected_drone_preview_index+1)%num_options; self.play_sound('ui_select')
                        elif event.key==pygame.K_RETURN:
                            selected_id=self.drone_select_options[self.selected_drone_preview_index]
                            if self.drone_system.is_drone_unlocked(selected_id):
                                if self.drone_system.set_selected_drone_id(selected_id): self.play_sound('ui_confirm'); self.update_player_life_icon()
                            else: 
                                if self.drone_system.attempt_unlock_drone_with_cores(selected_id): self.play_sound('ui_confirm')
                                else: self.play_sound('ui_denied')
                    if event.key==pygame.K_ESCAPE: self.play_sound('ui_select'); self.set_game_state(GAME_STATE_MAIN_MENU)
                
                elif self.game_state == GAME_STATE_SETTINGS:
                    if not self.settings_items: return # Should not happen if initialized
                    setting_item = self.settings_items[self.selected_setting_index]
                    if event.key == pygame.K_UP: self.selected_setting_index=(self.selected_setting_index-1+len(self.settings_items))%len(self.settings_items); self.play_sound('ui_select')
                    elif event.key == pygame.K_DOWN: self.selected_setting_index=(self.selected_setting_index+1)%len(self.settings_items); self.play_sound('ui_select')
                    elif event.key == pygame.K_RETURN:
                        if setting_item["type"]=="action" and setting_item["key"]=="RESET_SETTINGS": self._reset_all_settings_to_default(); self.play_sound('ui_confirm')
                    elif event.key==pygame.K_LEFT or event.key==pygame.K_RIGHT:
                        if setting_item["type"]!="action":
                            self.play_sound('ui_select',0.7); key_to_set=setting_item["key"]; current_val=get_game_setting(key_to_set); direction=1 if event.key==pygame.K_RIGHT else -1
                            if setting_item["type"]=="numeric":
                                new_val=current_val; step=setting_item["step"]
                                if setting_item.get("is_ms_to_sec"): new_val=int(round(max(setting_item["min"],min(setting_item["max"],current_val/1000+step*direction)))*1000)
                                else: new_val=round(max(setting_item["min"],min(setting_item["max"],current_val+step*direction)),2 if isinstance(step,float) else 0);
                                if not isinstance(step,float) and not isinstance(new_val, float): new_val=int(new_val) # Ensure int if step is int
                                elif isinstance(step, float): new_val = float(new_val) # Ensure float if step is float
                                set_game_setting(key_to_set,new_val)
                            elif setting_item["type"]=="choice":
                                choices = setting_item.get("choices", [])
                                if choices: # Ensure choices exist
                                    try:
                                        current_choice_idx=choices.index(current_val)
                                        new_choice_idx=(current_choice_idx+direction+len(choices))%len(choices)
                                        set_game_setting(key_to_set,choices[new_choice_idx])
                                    except ValueError: # Current value not in choices, reset to first
                                        set_game_setting(key_to_set, choices[0])
                    elif event.key==pygame.K_ESCAPE: self.play_sound('ui_select'); self.set_game_state(GAME_STATE_MAIN_MENU)
                
                elif self.game_state == GAME_STATE_PLAYING or self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                        if self.paused: pygame.mixer.music.pause()
                        else: 
                            pygame.mixer.music.unpause()
                            if self.game_state == GAME_STATE_PLAYING:
                                self.level_timer_start_ticks = pygame.time.get_ticks() - (get_game_setting("LEVEL_TIMER_DURATION") - self.level_time_remaining_ms)
                    if not self.paused and self.player and self.player.alive:
                        if event.key == pygame.K_UP: self.player.moving_forward=True; self.player.attempt_speed_boost_activation()
                        elif event.key == pygame.K_DOWN: self.player.moving_forward=False
                    elif self.paused: 
                        if event.key==pygame.K_l and self.game_state==GAME_STATE_PLAYING: self.leaderboard_scores=leaderboard.load_scores(); self.set_game_state(GAME_STATE_LEADERBOARD)
                        elif event.key==pygame.K_m: self.paused=False; pygame.mixer.music.unpause(); self.set_game_state(GAME_STATE_MAIN_MENU)
                        elif event.key==pygame.K_q: self.quit_game()

                elif self.game_state.startswith("architect_vault"): # Handle pause for all vault states
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                        if self.paused: pygame.mixer.music.pause()
                        else: pygame.mixer.music.unpause() # Music context handles actual path
                    
                    if self.paused and event.key == pygame.K_ESCAPE: # Allow exiting vault to main menu from pause
                        self.paused = False; pygame.mixer.music.unpause()
                        self.set_game_state(GAME_STATE_MAIN_MENU)
                        return # Prevent further vault specific input handling this frame

                    if not self.paused: # Vault specific inputs if not paused
                        if self.game_state == GAME_STATE_ARCHITECT_VAULT_INTRO:
                            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE: 
                                self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
                        elif self.game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
                            # Example: Use number keys to activate terminals for testing
                            if event.key == pygame.K_1: self.try_activate_vault_terminal(0)
                            elif event.key == pygame.K_2: self.try_activate_vault_terminal(1)
                            elif event.key == pygame.K_3: self.try_activate_vault_terminal(2)
                        # Player movement input for gauntlet/extraction is handled by general key check later
                        if self.player and self.player.alive:
                             if event.key == pygame.K_UP: self.player.moving_forward=True; self.player.attempt_speed_boost_activation()
                             elif event.key == pygame.K_DOWN: self.player.moving_forward=False
                
                elif self.game_state == GAME_STATE_ARCHITECT_VAULT_SUCCESS or self.game_state == GAME_STATE_ARCHITECT_VAULT_FAILURE:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_m:
                        self.set_game_state(GAME_STATE_MAIN_MENU) 

                elif self.game_state == GAME_STATE_GAME_OVER:
                    can_submit_score=not get_game_setting("SETTINGS_MODIFIED"); is_new_high=can_submit_score and leaderboard.is_high_score(self.score,self.level)
                    if is_new_high and event.key in [pygame.K_r,pygame.K_l,pygame.K_m,pygame.K_q,pygame.K_RETURN,pygame.K_SPACE]: self.set_game_state(GAME_STATE_ENTER_NAME); return
                    if event.key==pygame.K_r: self.initialize_game_session()
                    elif event.key==pygame.K_l and can_submit_score: self.leaderboard_scores=leaderboard.load_scores(); self.set_game_state(GAME_STATE_LEADERBOARD)
                    elif event.key==pygame.K_m: self.set_game_state(GAME_STATE_MAIN_MENU)
                    elif event.key==pygame.K_q: self.quit_game()
                
                elif self.game_state == GAME_STATE_ENTER_NAME:
                    if event.key==pygame.K_RETURN and self.player_name_input: leaderboard.add_score(self.player_name_input.upper(),self.score,self.level); self.leaderboard_scores=leaderboard.load_scores(); self.set_game_state(GAME_STATE_LEADERBOARD); self.player_name_input=""
                    elif event.key==pygame.K_BACKSPACE: self.player_name_input=self.player_name_input[:-1]
                    elif len(self.player_name_input)<6 and event.unicode.isalpha(): self.player_name_input+=event.unicode.upper()
                
                elif self.game_state == GAME_STATE_LEADERBOARD:
                    if event.key==pygame.K_ESCAPE or event.key==pygame.K_m: self.play_sound('ui_select'); self.set_game_state(GAME_STATE_MAIN_MENU)
                    elif event.key==pygame.K_q: self.quit_game()

        is_active_combat_state = self.game_state in [
            GAME_STATE_PLAYING, GAME_STATE_ARCHITECT_VAULT_GAUNTLET, GAME_STATE_ARCHITECT_VAULT_EXTRACTION
        ]
        if is_active_combat_state and not self.paused and self.player and self.player.alive:
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys, current_time) 
            if keys[pygame.K_SPACE]:
                targetable_enemies = self.enemies # Same group for regular and vault enemies for now
                self.player.shoot(sound=self.sounds.get('shoot'), missile_sound=self.sounds.get('missile_launch'),
                                  maze=self.maze, enemies_group=targetable_enemies)


    def try_activate_vault_terminal(self, terminal_idx):
        if not (0 <= terminal_idx < len(self.architect_vault_puzzle_terminals_activated)): return

        # Find the specific terminal sprite
        target_terminal_sprite = None
        for t_sprite in self.architect_vault_terminals:
            if hasattr(t_sprite, 'terminal_id') and t_sprite.terminal_id == terminal_idx:
                target_terminal_sprite = t_sprite
                break
        
        if not target_terminal_sprite or (hasattr(target_terminal_sprite, 'is_active') and target_terminal_sprite.is_active):
            return # Terminal not found or already active

        # Simplified: Check if player has *any* of the required fragments.
        # A more complex puzzle would require specific fragments for specific terminals.
        # For now, let's assume activating terminals sequentially requires having collected that many fragments.
        collected_fragment_ids = self.drone_system.get_collected_fragments_ids()
        
        # This logic assumes fragments are cf_alpha, cf_beta, cf_gamma and terminals 0, 1, 2 correspond
        required_fragment_id = None
        if CORE_FRAGMENT_DETAILS: # Ensure details are loaded
            frag_keys = list(CORE_FRAGMENT_DETAILS.keys())
            if terminal_idx < len(frag_keys):
                required_fragment_id = CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]].get("id")

        if required_fragment_id and required_fragment_id in collected_fragment_ids:
            self.architect_vault_puzzle_terminals_activated[terminal_idx] = True
            if hasattr(target_terminal_sprite, 'is_active'): target_terminal_sprite.is_active = True
            target_terminal_sprite.image.fill(GREEN) # Visually mark as active
            self.play_sound('vault_barrier_disable')
            self.architect_vault_message = f"Terminal {terminal_idx+1} ({CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]].get('name', '')}) activated!"
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000

            if all(self.architect_vault_puzzle_terminals_activated):
                self.architect_vault_message = "All terminals active. Lockdown disengaged."
                self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                # Add a slight delay before state change using phase timer if desired
                # For now, direct transition:
                self.set_game_state(GAME_STATE_ARCHITECT_VAULT_GAUNTLET)
        else:
            self.architect_vault_message = f"Terminal {terminal_idx+1} requires {CORE_FRAGMENT_DETAILS[frag_keys[terminal_idx]].get('name', 'specific fragment')}."
            self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
            self.play_sound('ui_denied')


    def update_architect_vault(self):
        current_time = pygame.time.get_ticks()
        if not self.player or not self.maze:
            self.set_game_state(GAME_STATE_MAIN_MENU); return 

        if not self.player.alive:
            self.set_game_state(GAME_STATE_ARCHITECT_VAULT_FAILURE); return

        if self.paused: return 

        self.player.update(current_time, self.maze, self.enemies, self.UI_PANEL_WIDTH) 

        if self.architect_vault_current_phase == "intro":
            if current_time > self.architect_vault_message_timer: 
                self.set_game_state(GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE)
        
        elif self.architect_vault_current_phase == "entry_puzzle":
            self.architect_vault_terminals.update() 
            # Player interaction with terminals is mostly via key presses in handle_events for this version.
            # Collision with hazards (placeholder)
            # if pygame.sprite.spritecollide(self.player, self.architect_vault_hazards, False, pygame.sprite.collide_circle):
            # self.player.take_damage(10) # Example hazard damage
            pass # Puzzle progression handled by try_activate_vault_terminal

        elif self.architect_vault_current_phase == "gauntlet_intro":
            if current_time > self.architect_vault_message_timer:
                self.architect_vault_gauntlet_current_wave = 1
                self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                self.spawn_prototype_drones(ARCHITECT_VAULT_DRONES_PER_WAVE[0])
                self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                self.architect_vault_message_timer = pygame.time.get_ticks() + 2000

        elif self.architect_vault_current_phase and self.architect_vault_current_phase.startswith("gauntlet_wave"):
            self.enemies.update(self.player.get_position(), self.maze, current_time)
            self.check_collisions_architect_vault() 

            if not self.enemies: 
                self.play_sound('level_up') 
                self.architect_vault_gauntlet_current_wave += 1
                if self.architect_vault_gauntlet_current_wave > ARCHITECT_VAULT_GAUNTLET_WAVES:
                    self.architect_vault_message = "Gauntlet cleared. Accessing core..."
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 3000
                    # Short delay before extraction phase starts
                    self.architect_vault_current_phase = "gauntlet_cleared_transition" 
                    self.architect_vault_phase_timer_start = current_time # Timer for this transition
                else:
                    self.architect_vault_current_phase = f"gauntlet_wave_{self.architect_vault_gauntlet_current_wave}"
                    num_drones_this_wave = ARCHITECT_VAULT_DRONES_PER_WAVE[self.architect_vault_gauntlet_current_wave - 1]
                    self.spawn_prototype_drones(num_drones_this_wave)
                    self.architect_vault_message = f"Wave {self.architect_vault_gauntlet_current_wave} initiated!"
                    self.architect_vault_message_timer = pygame.time.get_ticks() + 2000
        
        elif self.architect_vault_current_phase == "gauntlet_cleared_transition":
             if current_time - self.architect_vault_phase_timer_start > 2000: # 2s delay
                self.set_game_state(GAME_STATE_ARCHITECT_VAULT_EXTRACTION)

        elif self.architect_vault_current_phase == "extraction":
            time_elapsed_extraction = current_time - self.architect_vault_phase_timer_start
            self.level_time_remaining_ms = max(0, ARCHITECT_VAULT_EXTRACTION_TIMER_MS - time_elapsed_extraction)

            if self.level_time_remaining_ms <= 0:
                self.set_game_state(GAME_STATE_ARCHITECT_VAULT_SUCCESS) 
            
            if random.random() < 0.005 : # Lower chance for chase drones
                 if len(self.enemies) < 2: # Max 2 chase drones
                    self.spawn_prototype_drones(1) 
            self.enemies.update(self.player.get_position(), self.maze, current_time) 
            self.check_collisions_architect_vault()


    def check_collisions_architect_vault(self):
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
            for bullet_obj in list(enemy_obj.bullets): # Ensure enemy_obj.bullets is iterable
                if self.player.alive and bullet_obj.rect.colliderect(self.player.rect): 
                    self.player.take_damage(get_game_setting("ENEMY_BULLET_DAMAGE") * 1.2, self.sounds.get('crash')) 
                    bullet_obj.alive = False; bullet_obj.kill()
                if not bullet_obj.alive and hasattr(enemy_obj, 'bullets') and bullet_obj in enemy_obj.bullets: 
                    enemy_obj.bullets.remove(bullet_obj)
        
        if self.player.alive:
            enemy_collisions = pygame.sprite.spritecollide(self.player, self.enemies, False, pygame.sprite.collide_rect_ratio(0.6))
            for enemy_obj in enemy_collisions:
                if enemy_obj.alive:
                    self.player.take_damage(40, self.sounds.get('crash')) 
                if not self.player.alive: break


    def update_bonus_level(self): # Old bonus level logic
        current_game_ticks = pygame.time.get_ticks()
        if not self.player or not self.player.alive:
            self.end_bonus_level(completed=False); return 
        
        self.player.update(current_game_ticks, self.maze, None, self.UI_PANEL_WIDTH) 
        
        elapsed_bonus_time = current_game_ticks - self.bonus_level_timer_start
        # Assuming bonus_level_duration_ms was set when bonus level started
        # Need to ensure self.bonus_level_duration_ms is initialized correctly for old bonus
        # For now, let's assume it was set to e.g. 60000ms
        bonus_duration = getattr(self, 'bonus_level_duration_ms', 60000) # Fallback
        self.level_time_remaining_ms = max(0, bonus_duration - elapsed_bonus_time)

        if self.level_time_remaining_ms <= 0:
            self.end_bonus_level(completed=True); return

    def end_bonus_level(self, completed=True): # For OLD bonus level
        print(f"--- Old Bonus Level Ended. Completed: {completed} ---")
        if completed: self.score += 500; self.drone_system.add_player_cores(250)
        self.drone_system._save_unlocks() 
        self.level_up(from_bonus_level_completion=True) 

    def update(self):
        current_game_ticks = pygame.time.get_ticks()
        
        if self.game_state == GAME_STATE_PLAYING and not self.paused:
            if not self.player or not self.maze: self.set_game_state(GAME_STATE_MAIN_MENU); return
            if not self.level_cleared_pending_animation:
                current_level_timer_duration = get_game_setting("LEVEL_TIMER_DURATION")
                elapsed_time_current_level_ms = current_game_ticks - self.level_timer_start_ticks
                self.level_time_remaining_ms = current_level_timer_duration - elapsed_time_current_level_ms
                if self.level_time_remaining_ms <= 0: 
                    self.play_sound('timer_out'); self.lives -= 1
                    if self.player: self.player.reset_active_powerups()
                    if self.lives <= 0:
                        self.drone_system.set_player_level(self.level); self.drone_system._save_unlocks()
                        if not get_game_setting("SETTINGS_MODIFIED") and leaderboard.is_high_score(self.score,self.level): self.set_game_state(GAME_STATE_ENTER_NAME)
                        else: self.set_game_state(GAME_STATE_GAME_OVER)
                    else: self.reset_player_after_death(); self._reset_level_timer()
                    return
                
                if self.player.alive: self.player.update(current_game_ticks,self.maze,self.enemies,self.UI_PANEL_WIDTH)
                
                for enemy_obj in list(self.enemies): 
                    if self.player: enemy_obj.update(self.player.get_position(),self.maze,current_game_ticks)
                    else: enemy_obj.update((0,0),self.maze,current_game_ticks) 
                    if not enemy_obj.alive and (not hasattr(enemy_obj, 'bullets') or not enemy_obj.bullets): enemy_obj.kill() 
                
                for p_up in list(self.power_ups): 
                    if p_up.update(): p_up.kill() 
                
                for fragment in list(self.core_fragments): 
                    if fragment.update(): pass 
                
                self.rings.update(); self.check_collisions() 
                
                if FPS > 0 and random.random() < (POWERUP_SPAWN_CHANCE / FPS): self.try_spawn_powerup()
                
                if self.player and not self.player.alive: 
                    self.play_sound('player_death'); self.lives -= 1
                    if self.lives <= 0:
                        self.drone_system.set_player_level(self.level); self.drone_system._save_unlocks()
                        if not get_game_setting("SETTINGS_MODIFIED") and leaderboard.is_high_score(self.score,self.level): self.set_game_state(GAME_STATE_ENTER_NAME)
                        else: self.set_game_state(GAME_STATE_GAME_OVER)
                    else: self.reset_player_after_death(); self._reset_level_timer()
                    return
            
            for ring_anim in list(self.animating_rings):
                dx = ring_anim['target_pos'][0]-ring_anim['pos'][0]; dy = ring_anim['target_pos'][1]-ring_anim['pos'][1]
                dist = math.hypot(dx,dy)
                if dist < ring_anim['speed']:
                    self.animating_rings.remove(ring_anim); self.displayed_collected_rings += 1
                    self.displayed_collected_rings = min(self.displayed_collected_rings,self.collected_rings)
                else: ring_anim['pos'][0]+=(dx/dist)*ring_anim['speed']; ring_anim['pos'][1]+=(dy/dist)*ring_anim['speed']

            if self.level_cleared_pending_animation and not self.animating_rings:
                self.level_up(); self.level_cleared_pending_animation = False

        elif self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused: 
            self.update_bonus_level()
        elif self.game_state.startswith("architect_vault") and not self.paused: 
            self.update_architect_vault()
        elif self.game_state in [GAME_STATE_SETTINGS,GAME_STATE_LEADERBOARD,GAME_STATE_DRONE_SELECT,GAME_STATE_MAIN_MENU]:
            for star in self.menu_stars:
                star[0] -= star[2]
                if star[0] < 0: star[0] = WIDTH; star[1] = random.randint(0, HEIGHT)

    def check_for_level_clear_condition(self): 
        if self.player and self.collected_rings >= self.total_rings_per_level and not self.level_cleared_pending_animation:
            self.player.moving_forward = False; self.level_cleared_pending_animation = True

    def check_collisions(self): 
        if not self.player or not self.player.alive: return
        
        if not self.level_cleared_pending_animation: 
            collided_rings_sprites = pygame.sprite.spritecollide(self.player,self.rings,True,pygame.sprite.collide_rect_ratio(0.7))
            for ring_sprite in collided_rings_sprites:
                self.score += 10; self.play_sound('collect_ring'); self.collected_rings += 1
                self.drone_system.add_player_cores(5) 
                
                anim_ring_surf = None
                if hasattr(ring_sprite,'image'):
                    try: anim_ring_surf = pygame.transform.smoothscale(ring_sprite.image.copy(), (15,15))
                    except: anim_ring_surf = self._create_fallback_icon((15,15),"",GOLD, font_to_use=self.fonts["ui_emoji_small"])
                if anim_ring_surf: self.animating_rings.append({'pos':list(ring_sprite.rect.center),'target_pos':self.ring_ui_target_pos,'speed':15,'surface':anim_ring_surf,'alpha':255})
                
                self.check_for_level_clear_condition()
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
                if hasattr(enemy_obj, 'bullets'): # Check if enemy has bullets attribute
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


    def draw_ui(self):
        if not self.player: return
        panel_y_start=GAME_PLAY_AREA_HEIGHT; panel_height=BOTTOM_PANEL_HEIGHT
        try:
            panel_surf=pygame.Surface((WIDTH,panel_height),pygame.SRCALPHA); panel_surf.fill((20,25,35,220))
            pygame.draw.line(panel_surf,(80,120,170,200),(0,0),(WIDTH,0),2); self.screen.blit(panel_surf,(0,panel_y_start))
            
            h_padding=20; v_padding=10; element_spacing=6; bar_height=16; icon_to_bar_gap=10; icon_spacing=5; text_icon_spacing=4
            current_time=pygame.time.get_ticks()
            
            label_font = self.fonts.get("ui_text")
            value_font = self.fonts.get("ui_values")
            emoji_general_font = self.fonts.get("ui_emoji_general")
            emoji_small_font = self.fonts.get("ui_emoji_small")
            timer_font = self.fonts.get("ui_values") # Use ui_values for timer as well, or specific timer_display_font
            
            # Fallback if fonts are not loaded (should not happen if _initialize_fonts is correct)
            if not label_font: label_font = pygame.font.Font(None, 28)
            if not value_font: value_font = pygame.font.Font(None, 30)
            if not emoji_general_font: emoji_general_font = pygame.font.Font(None, 32)
            if not emoji_small_font: emoji_small_font = pygame.font.Font(None, 20)
            if not timer_font: timer_font = pygame.font.Font(None, 30)


            def render_text_safe(text, font, color):
                return font.render(text, True, color) 

            # Vitals section (Health, Weapon Charge, Power-up, Lives)
            vitals_x_start=h_padding; current_vitals_y=panel_y_start+panel_height-v_padding
            vitals_section_width=int(WIDTH/3.2); min_bar_segment_width=20; bar_segment_reduction_factor=0.75
            
            _health_icon_char_temp="❤️"; _health_icon_surf_temp=render_text_safe(_health_icon_char_temp,emoji_small_font,RED)
            _health_icon_width_temp=_health_icon_surf_temp.get_width(); _bar_start_x_for_lives_alignment=vitals_x_start+_health_icon_width_temp+icon_to_bar_gap
            if self.current_drone_life_icon_surface:
                lives_y_pos=current_vitals_y-self.ui_icon_size_lives[1]; lives_draw_x=_bar_start_x_for_lives_alignment
                for i in range(self.lives): self.screen.blit(self.current_drone_life_icon_surface,(lives_draw_x+i*(self.ui_icon_size_lives[0]+icon_spacing),lives_y_pos))
                current_vitals_y=lives_y_pos-element_spacing
            
            health_bar_y_pos=current_vitals_y-bar_height; health_icon_char="❤️"; health_icon_surf=render_text_safe(health_icon_char,emoji_small_font,RED)
            self.screen.blit(health_icon_surf,(vitals_x_start,health_bar_y_pos+(bar_height-health_icon_surf.get_height())//2))
            bar_start_x_health=vitals_x_start+health_icon_surf.get_width()+icon_to_bar_gap
            available_width_for_health_bar=vitals_section_width-health_icon_surf.get_width()-icon_to_bar_gap
            bar_segment_width_health=max(min_bar_segment_width,int(available_width_for_health_bar*bar_segment_reduction_factor))
            health_percentage=self.player.health/self.player.max_health if self.player.max_health>0 else 0
            health_bar_width_fill=int(bar_segment_width_health*health_percentage)
            health_fill_color=GREEN if health_percentage>0.6 else YELLOW if health_percentage>0.3 else RED
            pygame.draw.rect(self.screen,(40,40,40,200),(bar_start_x_health,health_bar_y_pos,bar_segment_width_health,bar_height))
            if health_bar_width_fill>0: pygame.draw.rect(self.screen,health_fill_color,(bar_start_x_health,health_bar_y_pos,health_bar_width_fill,bar_height))
            pygame.draw.rect(self.screen,WHITE,(bar_start_x_health,health_bar_y_pos,bar_segment_width_health,bar_height),1)
            current_vitals_y=health_bar_y_pos-element_spacing
            
            # Weapon Charge Bar
            weapon_bar_y_pos=current_vitals_y-bar_height
            weapon_icon_char=WEAPON_MODE_ICONS.get(self.player.current_weapon_mode,"💥")
            weapon_icon_surf=render_text_safe(weapon_icon_char,emoji_small_font,ORANGE)
            self.screen.blit(weapon_icon_surf,(vitals_x_start,weapon_bar_y_pos+(bar_height-weapon_icon_surf.get_height())//2))
            bar_start_x_weapon=vitals_x_start+weapon_icon_surf.get_width()+icon_to_bar_gap
            bar_segment_width_weapon=max(min_bar_segment_width,int((vitals_section_width-weapon_icon_surf.get_width()-icon_to_bar_gap)*bar_segment_reduction_factor))
            charge_fill_pct,weapon_ready_color=0.0,PLAYER_BULLET_COLOR
            cooldown_duration=self.player.current_shoot_cooldown; time_since_last_shot=current_time-self.player.last_shot_time
            if self.player.current_weapon_mode==get_game_setting("WEAPON_MODE_HEATSEEKER"): 
                weapon_ready_color=MISSILE_COLOR
                time_since_last_shot=current_time-self.player.last_missile_shot_time
                cooldown_duration=self.player.current_missile_cooldown
            elif self.player.current_weapon_mode==get_game_setting("WEAPON_MODE_LIGHTNING"): 
                weapon_ready_color=get_game_setting("LIGHTNING_COLOR") # Ensure this color is defined
            if cooldown_duration > 0: charge_fill_pct=min(1.0,time_since_last_shot/cooldown_duration)
            else: charge_fill_pct=1.0
            charge_bar_fill_color=weapon_ready_color if charge_fill_pct>=1.0 else ORANGE
            weapon_bar_width_fill=int(bar_segment_width_weapon*charge_fill_pct)
            pygame.draw.rect(self.screen,(40,40,40,200),(bar_start_x_weapon,weapon_bar_y_pos,bar_segment_width_weapon,bar_height))
            if weapon_bar_width_fill>0: pygame.draw.rect(self.screen,charge_bar_fill_color,(bar_start_x_weapon,weapon_bar_y_pos,weapon_bar_width_fill,bar_height))
            pygame.draw.rect(self.screen,WHITE,(bar_start_x_weapon,weapon_bar_y_pos,bar_segment_width_weapon,bar_height),1)
            current_vitals_y=weapon_bar_y_pos-element_spacing

            # Power-up Bar
            active_powerup_for_ui=self.player.active_powerup_type
            if active_powerup_for_ui and (self.player.shield_active or self.player.speed_boost_active):
                powerup_bar_y_pos=current_vitals_y-bar_height; powerup_icon_char=""; powerup_bar_fill_color=WHITE; powerup_fill_percentage=0.0
                if active_powerup_for_ui=="shield" and self.player.shield_active:
                    powerup_icon_char="🛡️"; powerup_bar_fill_color=POWERUP_TYPES["shield"]["color"]; remaining_time=self.player.shield_end_time-current_time
                    if self.player.shield_duration>0 and remaining_time>0: powerup_fill_percentage=remaining_time/self.player.shield_duration
                    else: powerup_fill_percentage = 0
                elif active_powerup_for_ui=="speed_boost" and self.player.speed_boost_active:
                    powerup_icon_char="💨"; powerup_bar_fill_color=POWERUP_TYPES["speed_boost"]["color"]; remaining_time=self.player.speed_boost_end_time-current_time
                    if self.player.speed_boost_duration>0 and remaining_time>0: powerup_fill_percentage=remaining_time/self.player.speed_boost_duration
                    else: powerup_fill_percentage = 0
                powerup_fill_percentage = max(0, min(1, powerup_fill_percentage))
                if powerup_icon_char:
                    powerup_icon_surf=render_text_safe(powerup_icon_char,emoji_small_font,WHITE)
                    self.screen.blit(powerup_icon_surf,(vitals_x_start,powerup_bar_y_pos+(bar_height-powerup_icon_surf.get_height())//2))
                    bar_start_x=vitals_x_start+powerup_icon_surf.get_width()+icon_to_bar_gap
                    bar_segment_width=max(min_bar_segment_width,int((vitals_section_width-powerup_icon_surf.get_width()-icon_to_bar_gap)*bar_segment_reduction_factor))
                    bar_width_fill=int(bar_segment_width*powerup_fill_percentage)
                    pygame.draw.rect(self.screen,(40,40,40,200),(bar_start_x,powerup_bar_y_pos,bar_segment_width,bar_height))
                    if bar_width_fill>0: pygame.draw.rect(self.screen,powerup_bar_fill_color,(bar_start_x,powerup_bar_y_pos,bar_width_fill,bar_height))
                    pygame.draw.rect(self.screen,WHITE,(bar_start_x,powerup_bar_y_pos,bar_segment_width,bar_height),1)
            
            # Collectibles section (Rings, Cores, Fragments)
            collectibles_x_anchor=WIDTH-h_padding; current_collectibles_y=panel_y_start+panel_height-v_padding
            
            # Cores Display
            cores_emoji_char="💠"; cores_value_str=f" {self.drone_system.get_player_cores()}"; 
            cores_icon_surf=render_text_safe(cores_emoji_char,emoji_general_font,GOLD)
            cores_value_text_surf=render_text_safe(cores_value_str,value_font,GOLD)
            cores_display_height=max(cores_icon_surf.get_height(),cores_value_text_surf.get_height())
            cores_y_pos=current_collectibles_y-cores_display_height
            total_cores_width=cores_icon_surf.get_width()+text_icon_spacing+cores_value_text_surf.get_width()
            cores_start_x=collectibles_x_anchor-total_cores_width
            self.screen.blit(cores_icon_surf,(cores_start_x,cores_y_pos+(cores_display_height-cores_icon_surf.get_height())//2))
            self.screen.blit(cores_value_text_surf,(cores_start_x+cores_icon_surf.get_width()+text_icon_spacing,cores_y_pos+(cores_display_height-cores_value_text_surf.get_height())//2))
            current_collectibles_y=cores_y_pos-element_spacing
            
            # Rings Display
            rings_y_pos = current_collectibles_y # Initialize before conditional block
            if self.ring_ui_icon:
                ring_icon_h=self.ui_icon_size_rings[1]; rings_y_pos=current_collectibles_y-ring_icon_h
                total_ring_icons_width_only=max(0,self.total_rings_per_level*(self.ui_icon_size_rings[0]+icon_spacing)-icon_spacing if self.total_rings_per_level>0 else 0)
                rings_block_start_x=collectibles_x_anchor-total_ring_icons_width_only
                for i in range(self.total_rings_per_level):
                    icon_to_draw=self.ring_ui_icon if i < self.displayed_collected_rings else self.ring_ui_icon_empty
                    if icon_to_draw: self.screen.blit(icon_to_draw,(rings_block_start_x+i*(self.ui_icon_size_rings[0]+icon_spacing),rings_y_pos))
                current_collectibles_y=rings_y_pos-element_spacing
            
            # Fragments Display
            num_fragments_collected=len(self.drone_system.get_collected_fragments_ids())
            if TOTAL_CORE_FRAGMENTS_NEEDED>0:
                frag_text_str=f"Fragments: {num_fragments_collected}/{TOTAL_CORE_FRAGMENTS_NEEDED}"; 
                frag_color=PURPLE if num_fragments_collected<TOTAL_CORE_FRAGMENTS_NEEDED else GOLD
                frag_surf=render_text_safe(frag_text_str,label_font,frag_color)
                frag_y_pos=current_collectibles_y-frag_surf.get_height()
                frag_x_pos=collectibles_x_anchor-frag_surf.get_width()
                self.screen.blit(frag_surf,(frag_x_pos,frag_y_pos))

            # Center Info (Score, Level, Timer)
            vitals_approx_end_x=vitals_x_start+vitals_section_width+h_padding; collectibles_section_approx_width=WIDTH/3.5
            collectibles_approx_start_x=WIDTH-h_padding-collectibles_section_approx_width
            center_section_alloc_width=collectibles_approx_start_x-vitals_approx_end_x
            center_section_mid_x=vitals_approx_end_x+(center_section_alloc_width/2)
            info_y_pos=panel_y_start+(panel_height-label_font.get_height())//2
            
            score_emoji_char="🏆 "; score_text_str=f"Score: {self.score}"
            score_emoji_surf=render_text_safe(score_emoji_char,emoji_general_font,GOLD)
            score_text_surf=render_text_safe(score_text_str,label_font,GOLD)
            
            level_emoji_char="🎯 "; level_text_str = f"Level: {self.level}"
            if self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING: level_text_str = "Bonus!" # Old bonus
            elif self.game_state.startswith("architect_vault"): level_text_str = "Architect's Vault"
            level_emoji_surf=render_text_safe(level_emoji_char,emoji_general_font,CYAN)
            level_text_surf=render_text_safe(level_text_str,label_font,CYAN)
            
            time_icon_char="⏱ "; time_ms_to_display=self.level_time_remaining_ms
            # Architect's Vault extraction has its own timer display logic further down
            if self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING: # Old bonus timer
                elapsed_bonus_time = pygame.time.get_ticks()-self.bonus_level_timer_start
                bonus_duration = getattr(self, 'bonus_level_duration_ms', 60000)
                time_ms_to_display = max(0,bonus_duration-elapsed_bonus_time)
            
            time_value_str = f"{max(0,time_ms_to_display//1000)//60:02d}:{max(0,time_ms_to_display//1000)%60:02d}"
            time_color=WHITE
            if(time_ms_to_display//1000)<=10 and self.game_state != GAME_STATE_ARCHITECT_VAULT_EXTRACTION : # Don't apply blink if vault extraction has its own
                time_color=RED if(current_time//250)%2==0 else DARK_RED
            elif(time_ms_to_display//1000)<=30 and self.game_state != GAME_STATE_ARCHITECT_VAULT_EXTRACTION: 
                time_color=YELLOW
            
            time_icon_surf=render_text_safe(time_icon_char,emoji_general_font,time_color)
            time_value_surf=render_text_safe(time_value_str,timer_font,time_color) # Use timer_font
            
            spacing_between_center_elements=25
            center_elements_total_width = (score_emoji_surf.get_width()+text_icon_spacing+score_text_surf.get_width()+spacing_between_center_elements+
                                         level_emoji_surf.get_width()+text_icon_spacing+level_text_surf.get_width()+spacing_between_center_elements+
                                         time_icon_surf.get_width()+text_icon_spacing+time_value_surf.get_width())
            current_info_x = center_section_mid_x-(center_elements_total_width/2)
            
            self.screen.blit(score_emoji_surf,(current_info_x,info_y_pos+(score_text_surf.get_height()-score_emoji_surf.get_height())//2))
            current_info_x+=score_emoji_surf.get_width()+text_icon_spacing
            self.screen.blit(score_text_surf,(current_info_x,info_y_pos))
            current_info_x+=score_text_surf.get_width()+spacing_between_center_elements
            
            self.screen.blit(level_emoji_surf,(current_info_x,info_y_pos+(level_text_surf.get_height()-level_emoji_surf.get_height())//2))
            current_info_x+=level_emoji_surf.get_width()+text_icon_spacing
            self.screen.blit(level_text_surf,(current_info_x,info_y_pos))
            current_info_x+=level_text_surf.get_width()+spacing_between_center_elements
            
            # Only draw the general timer if not in Architect's Vault extraction phase (which has its own timer display)
            if not (self.game_state.startswith("architect_vault") and self.architect_vault_current_phase == "extraction"):
                self.screen.blit(time_icon_surf,(current_info_x,info_y_pos+(time_value_surf.get_height()-time_icon_surf.get_height())//2))
                current_info_x+=time_icon_surf.get_width()+text_icon_spacing
                self.screen.blit(time_value_surf,(current_info_x,info_y_pos))

            # Ring animation target position update
            if self.total_rings_per_level > 0 and self.ring_ui_icon:
                _total_ring_icons_display_width = max(0, self.total_rings_per_level*(self.ui_icon_size_rings[0]+icon_spacing)-icon_spacing if self.total_rings_per_level>0 else 0)
                _rings_block_start_x_no_text = collectibles_x_anchor - _total_ring_icons_display_width
                _target_ring_row_y_for_anim = rings_y_pos # Use the calculated y_pos for rings
                _next_ring_slot_index = max(0, min(self.displayed_collected_rings, self.total_rings_per_level-1))
                target_slot_x_offset = _next_ring_slot_index * (self.ui_icon_size_rings[0]+icon_spacing)
                target_slot_center_x = _rings_block_start_x_no_text + target_slot_x_offset + self.ui_icon_size_rings[0]//2
                target_slot_center_y = _target_ring_row_y_for_anim + self.ui_icon_size_rings[1]//2
                self.ring_ui_target_pos = (target_slot_center_x, target_slot_center_y)
            
            for ring_anim in self.animating_rings: # Draw animated rings
                if 'surface' in ring_anim and ring_anim['surface']: 
                    self.screen.blit(ring_anim['surface'], (int(ring_anim['pos'][0]),int(ring_anim['pos'][1])))

            # Architect Vault Timer / Message (if in vault) - specific handling for extraction timer already done
            if self.game_state.startswith("architect_vault"):
                vault_msg_font = self.fonts.get("vault_message")
                if self.architect_vault_message and current_time < self.architect_vault_message_timer and vault_msg_font:
                    msg_surf = render_text_safe(self.architect_vault_message, vault_msg_font, GOLD)
                    msg_bg_surf = pygame.Surface((msg_surf.get_width()+20, msg_surf.get_height()+10), pygame.SRCALPHA)
                    msg_bg_surf.fill((10,0,20, 200)) 
                    msg_bg_surf.blit(msg_surf, (10,5))
                    self.screen.blit(msg_bg_surf, msg_bg_surf.get_rect(centerx=WIDTH//2, bottom=GAME_PLAY_AREA_HEIGHT - 20))
                
                # Specific Extraction Timer (already handled above, but ensure it's drawn if needed here too)
                if self.architect_vault_current_phase == "extraction" and timer_font:
                    time_val_str = f"{max(0,self.level_time_remaining_ms//1000)//60:02d}:{max(0,self.level_time_remaining_ms//1000)%60:02d}"
                    time_color = RED if (self.level_time_remaining_ms // 1000) <= 10 and (current_time // 250) % 2 == 0 else DARK_RED
                    if (self.level_time_remaining_ms // 1000) > 10: time_color = YELLOW
                    # Use a different font for this prominent timer if desired, e.g., self.fonts["vault_timer"]
                    escape_timer_font = self.fonts.get("vault_timer", timer_font) # Fallback to general timer font
                    timer_surf = render_text_safe(f"ESCAPE: {time_val_str}", escape_timer_font, time_color)
                    self.screen.blit(timer_surf, timer_surf.get_rect(centerx=WIDTH//2, top=20))


        except Exception as e:
            print(f"Error during UI drawing: {e}")


    def draw_overlay(self): 
        current_time = pygame.time.get_ticks() 
        if self.game_state == GAME_STATE_GAME_OVER:
            try:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180)); self.screen.blit(overlay, (0,0))
                go_text = self.fonts["large_text"].render("GAME OVER", True, RED)
                sc_text = self.fonts["ui_text"].render(f"Final Score: {self.score}", True, WHITE)
                self.screen.blit(go_text, go_text.get_rect(center=(WIDTH//2, HEIGHT//2-100)))
                self.screen.blit(sc_text, sc_text.get_rect(center=(WIDTH//2, HEIGHT//2-20)))
                
                can_submit_score=not get_game_setting("SETTINGS_MODIFIED")
                is_new_high=can_submit_score and leaderboard.is_high_score(self.score,self.level)
                prompt_y_offset=HEIGHT//2+40
                
                if not can_submit_score:
                    no_lb_text=self.fonts["ui_text"].render("Leaderboard disabled (custom settings).",True,YELLOW)
                    self.screen.blit(no_lb_text,no_lb_text.get_rect(center=(WIDTH//2,prompt_y_offset)))
                    prompt_y_offset+=self.fonts["ui_text"].get_height()+10
                
                prompt_str="R: Restart  M: Menu  Q: Quit"; prompt_clr=WHITE
                if can_submit_score and is_new_high: prompt_str="New High Score! Press any key to enter name."; prompt_clr=GOLD
                elif can_submit_score: prompt_str="R: Restart  L: Leaderboard  M: Menu  Q: Quit"
                
                prompt_surf = self.fonts["ui_text"].render(prompt_str,True,prompt_clr)
                self.screen.blit(prompt_surf,prompt_surf.get_rect(center=(WIDTH//2,prompt_y_offset)))
            except Exception as e: print(f"Error drawing Game Over overlay: {e}")

        elif self.game_state == GAME_STATE_ENTER_NAME:
            try:
                overlay = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((0,0,0,200)); self.screen.blit(overlay,(0,0))
                self.screen.blit(self.fonts["large_text"].render("New High Score!",True,GOLD),self.fonts["large_text"].render("New High Score!",True,GOLD).get_rect(center=(WIDTH//2,HEIGHT//2-150)))
                self.screen.blit(self.fonts["ui_text"].render(f"Your Score: {self.score} (Level: {self.level})",True,WHITE),self.fonts["ui_text"].render(f"Your Score: {self.score} (Level: {self.level})",True,WHITE).get_rect(center=(WIDTH//2,HEIGHT//2-80)))
                self.screen.blit(self.fonts["ui_text"].render("Enter Name (6 chars, A-Z):",True,WHITE),self.fonts["ui_text"].render("Enter Name (6 chars, A-Z):",True,WHITE).get_rect(center=(WIDTH//2,HEIGHT//2-20)))
                input_box = pygame.Rect(WIDTH//2-125,HEIGHT//2+30,250,50); pygame.draw.rect(self.screen,WHITE,input_box,2)
                self.screen.blit(self.fonts["input_text"].render(self.player_name_input,True,WHITE),self.fonts["input_text"].render(self.player_name_input,True,WHITE).get_rect(center=input_box.center))
                self.screen.blit(self.fonts["ui_text"].render("Press ENTER to submit.",True,CYAN),self.fonts["ui_text"].render("Press ENTER to submit.",True,CYAN).get_rect(center=(WIDTH//2,HEIGHT//2+120)))
            except Exception as e: print(f"Error drawing Enter Name overlay: {e}")

        elif self.game_state == GAME_STATE_LEADERBOARD:
            self.screen.fill(BLACK) 
            if self.menu_stars:
                for star_params in self.menu_stars: pygame.draw.circle(self.screen,WHITE,(int(star_params[0]),int(star_params[1])),star_params[3])
            try:
                title_surf=self.fonts["large_text"].render("Leaderboard",True,GOLD)
                title_bg=pygame.Surface((title_surf.get_width()+30,title_surf.get_height()+15),pygame.SRCALPHA); title_bg.fill((20,20,20,180))
                title_bg.blit(title_surf,title_surf.get_rect(center=(title_bg.get_width()//2,title_bg.get_height()//2)))
                self.screen.blit(title_bg,title_bg.get_rect(center=(WIDTH//2,HEIGHT//2-300)))
                
                scores_to_display = leaderboard.get_top_scores()
                score_item_y_start = HEIGHT//2-200
                header_y = HEIGHT//2-250
                item_line_height = (self.fonts["leaderboard_entry"].get_height() if self.fonts.get("leaderboard_entry") else 30) + 10
                
                if not scores_to_display:
                    no_scores_surf=self.fonts["ui_text"].render("No scores yet!",True,WHITE)
                    no_scores_bg=pygame.Surface((no_scores_surf.get_width()+20,no_scores_surf.get_height()+10),pygame.SRCALPHA)
                    no_scores_bg.fill((30,30,30,160)); no_scores_bg.blit(no_scores_surf,(10,5))
                    self.screen.blit(no_scores_bg,no_scores_bg.get_rect(center=(WIDTH//2,HEIGHT//2)))
                else:
                    cols = {"Rank":WIDTH//2-350,"Name":WIDTH//2-250,"Level":WIDTH//2+50,"Score":WIDTH//2+200}
                    header_font = self.fonts.get("leaderboard_header", self.fonts["ui_text"]) 
                    entry_font = self.fonts.get("leaderboard_entry", self.fonts["ui_text"])   

                    for col_name,x_pos in cols.items():
                        header_surf=header_font.render(col_name,True,WHITE)
                        header_bg=pygame.Surface((header_surf.get_width()+10,header_surf.get_height()+5),pygame.SRCALPHA)
                        header_bg.fill((40,40,40,170)); header_bg.blit(header_surf,(5,2))
                        self.screen.blit(header_bg,(x_pos,header_y))
                    
                    for i,entry in enumerate(scores_to_display):
                        y_pos = score_item_y_start + i * item_line_height
                        texts_to_draw = [
                            (f"{i+1}.",WHITE,cols["Rank"]),
                            (entry.get('name','N/A'),CYAN,cols["Name"]),
                            (str(entry.get('level','-')),GREEN,cols["Level"]),
                            (str(entry.get('score',0)),GOLD,cols["Score"])
                        ]
                        for text_str,color,x_coord in texts_to_draw:
                            text_surf=entry_font.render(text_str,True,color)
                            item_bg=pygame.Surface((text_surf.get_width()+8,text_surf.get_height()+4),pygame.SRCALPHA)
                            item_bg.fill((30,30,30,150)); item_bg.blit(text_surf,(4,2))
                            self.screen.blit(item_bg,(x_coord,y_pos))
                
                menu_prompt_surf=self.fonts["ui_text"].render("ESC: Main Menu | Q: Quit",True,WHITE)
                prompt_bg=pygame.Surface((menu_prompt_surf.get_width()+20,menu_prompt_surf.get_height()+10),pygame.SRCALPHA); prompt_bg.fill((20,20,20,180))
                prompt_bg.blit(menu_prompt_surf,(10,5)); self.screen.blit(prompt_bg,prompt_bg.get_rect(center=(WIDTH//2,HEIGHT-100)))
            except Exception as e: print(f"Error drawing Leaderboard: {e}")

        elif (self.game_state == GAME_STATE_PLAYING or self.game_state.startswith("architect_vault") or self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING) and self.paused:
            try:
                overlay = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((0,0,0,128)); self.screen.blit(overlay,(0,0))
                pause_title_font = self.fonts["large_text"]
                pause_options_font = self.fonts["ui_text"]
                self.screen.blit(pause_title_font.render("PAUSED",True,WHITE), pause_title_font.render("PAUSED",True,WHITE).get_rect(center=(WIDTH//2,HEIGHT//2-40)))
                
                pause_text = "P: Continue | M: Menu | Q: Quit"
                if self.game_state == GAME_STATE_PLAYING:
                     pause_text = "P: Continue | L: Leaderboard | M: Menu | Q: Quit"
                elif self.game_state.startswith("architect_vault"): 
                     pause_text = "P: Continue | ESC: Main Menu (Exit Vault) | Q: Quit"
                # Old bonus level uses the default pause_text

                self.screen.blit(pause_options_font.render(pause_text,True,WHITE), pause_options_font.render(pause_text,True,WHITE).get_rect(center=(WIDTH//2,HEIGHT//2+40)))
            except Exception as e: print(f"Error drawing Pause overlay: {e}")


    def draw_architect_vault(self):
        self.screen.fill(ARCHITECT_VAULT_BG_COLOR) 
        if self.maze: self.maze.draw_architect_vault(self.screen) 
        
        if self.game_state == GAME_STATE_ARCHITECT_VAULT_ENTRY_PUZZLE:
            self.architect_vault_terminals.draw(self.screen)
            # Draw fragment hints for puzzle
            collected_frag_ids = self.drone_system.get_collected_fragments_ids()
            frag_y_start = 50; frag_font = self.fonts.get("small_text")
            if frag_font and CORE_FRAGMENT_DETAILS:
                for i, frag_key_enum in enumerate(CORE_FRAGMENT_DETAILS.keys()): # Use enumerate for index
                    details = CORE_FRAGMENT_DETAILS[frag_key_enum]
                    if not details: continue
                    frag_id = details["id"]
                    is_collected = frag_id in collected_frag_ids
                    is_used_for_terminal = i < len(self.architect_vault_puzzle_terminals_activated) and self.architect_vault_puzzle_terminals_activated[i]
                    
                    text_color = GREEN if is_used_for_terminal else (WHITE if is_collected else GREY)
                    try:
                        frag_name_surf = frag_font.render(f"F{i+1}: {details['name']}", True, text_color)
                        self.screen.blit(frag_name_surf, (WIDTH - frag_name_surf.get_width() - 20, frag_y_start + i * 30))
                    except Exception as e: print(f"Error drawing fragment hint {details['name']}: {e}")


        if self.player: self.player.draw(self.screen)
        self.enemies.draw(self.screen) 

        self.draw_ui() 
        if self.paused: self.draw_overlay()


    def draw(self):
        self.screen.fill(BLACK) 
        
        if self.game_state == GAME_STATE_MAIN_MENU: self.draw_main_menu()
        elif self.game_state == GAME_STATE_DRONE_SELECT: self.draw_drone_select_menu()
        elif self.game_state == GAME_STATE_SETTINGS: self.draw_settings_menu()
        elif self.game_state == GAME_STATE_LEADERBOARD: self.draw_overlay() 
        elif self.game_state.startswith("architect_vault"): 
            self.draw_architect_vault()
        elif self.game_state in [GAME_STATE_PLAYING, GAME_STATE_GAME_OVER, GAME_STATE_ENTER_NAME, GAME_STATE_BONUS_LEVEL_PLAYING]: 
            if self.maze: self.maze.draw(self.screen) 
            self.rings.draw(self.screen); self.power_ups.draw(self.screen); self.core_fragments.draw(self.screen)
            if self.player: self.player.draw(self.screen)
            for enemy_obj in self.enemies: enemy_obj.draw(self.screen) 
            self.draw_ui()
            if self.game_state != GAME_STATE_PLAYING or self.paused:
                 if not (self.game_state == GAME_STATE_BONUS_LEVEL_PLAYING and not self.paused): # Avoid double overlay if old bonus not paused
                    self.draw_overlay()
        
        pygame.display.flip()

    def level_up(self, from_bonus_level_completion=False):
        if self.drone_system.are_all_core_fragments_collected() and not self.drone_system.has_completed_architect_vault():
            print("All core fragments collected! Transitioning to The Architect's Vault.")
            self.set_game_state(GAME_STATE_ARCHITECT_VAULT_INTRO)
            return

        if not from_bonus_level_completion: 
            self.level += 1
        
        self.collected_rings = 0; self.displayed_collected_rings = 0
        self.total_rings_per_level = min(self.total_rings_per_level + 1, 15)
        self.drone_system.set_player_level(self.level) 
        
        if self.player:
            if self.all_enemies_killed_this_level: self.player.cycle_weapon_state(force_cycle=False)
            self.player.health = min(self.player.health + 25, self.player.max_health)
            self.player.reset_active_powerups()
        
        self.all_enemies_killed_this_level = False
        self.maze = Maze(game_area_x_offset=self.UI_PANEL_WIDTH, maze_type="standard")
        new_player_pos = self.get_safe_spawn_point(self.player_spawn_check_dimension, self.player_spawn_check_dimension)
        
        if self.player:
            current_drone_id = self.player.drone_id
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) 
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite)
        
        self.spawn_enemies(); self.core_fragments.empty(); self.place_collectibles(initial_setup=True)
        self._reset_level_timer(); self.play_sound('level_up')
        self.animating_rings.clear()
        if self.player: self.player.moving_forward = False
        
        if not self.game_state.startswith("architect_vault"):
            self.set_game_state(GAME_STATE_PLAYING)


    def reset_player_after_death(self): 
        new_player_pos = self.get_safe_spawn_point(self.player_spawn_check_dimension, self.player_spawn_check_dimension)
        if self.player:
            current_drone_id = self.player.drone_id
            effective_drone_stats = self.drone_system.get_drone_stats(current_drone_id, is_in_architect_vault=False) 
            drone_config = self.drone_system.get_drone_config(current_drone_id)
            player_ingame_sprite = drone_config.get("ingame_sprite_path")
            self.player.reset(new_player_pos[0], new_player_pos[1], drone_id=current_drone_id,
                              drone_stats=effective_drone_stats, drone_sprite_path=player_ingame_sprite,
                              health_override=None) 
        self.animating_rings.clear(); self.level_cleared_pending_animation = False

    def restart_game(self):
        self.initialize_game_session()

    def quit_game(self):
        print("Quitting game.")
        self.drone_system._save_unlocks() 
        pygame.quit()
        sys.exit()

    def run(self):
        # Initial check for FULLSCREEN_MODE setting
        is_fullscreen = get_game_setting("FULLSCREEN_MODE")
        if isinstance(is_fullscreen, bool) and is_fullscreen : # Check if it's explicitly True
             self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else: # Default to windowed or if setting is False/None
             self.screen = pygame.display.set_mode((WIDTH, HEIGHT), 0)


        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    # Ensure game_settings are loaded and accessible before Game instantiation
    # This is important if game_settings.py itself does some dynamic calculations at import time.
    try:
        import game_settings
        if game_settings.get_game_setting("WIDTH") is None: # A key that should exist
            print("CRITICAL: Default game settings failed to load via get_game_setting. Exiting.")
            sys.exit()
    except ImportError:
        print("CRITICAL: game_settings.py could not be imported. Exiting.")
        sys.exit()
    except Exception as e:
        print(f"CRITICAL: Error during game_settings import or access: {e}. Exiting.")
        sys.exit()

    # Set fullscreen based on settings *before* Game init if possible, or handle in Game.run()
    # For now, Game.run() handles it.
    # set_game_setting("FULLSCREEN_MODE", False) # Example: force windowed for testing

    game_instance = Game()
    game_instance.run()
