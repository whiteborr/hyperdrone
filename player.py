import math
import random
import os
import pygame

# Attempt to import game_settings specific colors, will use fallbacks if not found by get_game_setting
try:
    from game_settings import (
        BLUE, ORANGE, CYAN, WHITE, YELLOW, LIGHT_BLUE, GREEN
    )
except ImportError:
    # Define fallback colors if game_settings.py is not available during player.py direct execution
    # (though get_game_setting below has its own more robust color fallbacks if needed at runtime)
    BLUE, ORANGE, CYAN, WHITE, YELLOW, LIGHT_BLUE, GREEN = (0,0,255), (255,165,0), (0,255,255), (255,255,255), (255,255,0), (173,216,230), (0,255,0)


# Constants for special abilities, fetched via get_game_setting but defined here for fallback if drone_configs not available
# These specific constants from drone_configs are usually accessed via get_game_setting
# PHANTOM_CLOAK_DURATION_MS = 5000 (example, will be fetched)
# PHANTOM_CLOAK_COOLDOWN_MS = 15000 (example, will be fetched)
# PHANTOM_CLOAK_ALPHA = 70 (example, will be fetched)

from base_drone import BaseDrone
from bullet import Bullet, Missile, LightningBullet

_game_settings_module = None
_game_settings_get_function = None
_using_internal_player_defaults = True

try:
    import game_settings as gs_module
    _game_settings_module = gs_module
    if hasattr(gs_module, 'get_game_setting') and callable(gs_module.get_game_setting):
        _game_settings_get_function = gs_module.get_game_setting
        _using_internal_player_defaults = False
        # print("DEBUG (player.py): Successfully using get_game_setting from game_settings module.")
    else:
        print("ERROR (player.py): game_settings module imported, but get_game_setting function NOT FOUND or not callable. Using internal defaults.")
except ImportError as e:
    print(f"CRITICAL ERROR (player.py): Could not import 'game_settings' module: {e}. Using internal defaults.")
except Exception as e:
    print(f"CRITICAL ERROR (player.py): Exception during import of 'game_settings': {e}. Using internal defaults.")

def get_game_setting(key):
    global _using_internal_player_defaults
    if _game_settings_get_function:
        try:
            value = _game_settings_get_function(key)
            # print(f"DEBUG (player.py - gs): Fetched '{key}': {value}")
            return value
        except Exception as e:
            print(f"ERROR (player.py): Error calling get_game_setting from game_settings module for key '{key}': {e}. Reverting to internal fallback.")
            _using_internal_player_defaults = True # Force fallback if external function fails

    # Internal defaults if game_settings.get_game_setting is not available or fails
    # These should ideally mirror game_settings.py's DEFAULT_SETTINGS for consistency
    fb_height = 1080
    fb_bottom_panel_height = 120 # Default if not found via game_settings
    fb_game_play_area_height = fb_height - fb_bottom_panel_height

    defaults = {
        "WIDTH": 1920, "HEIGHT": fb_height,
        "BOTTOM_PANEL_HEIGHT": fb_bottom_panel_height,          # NEW Fallback
        "GAME_PLAY_AREA_HEIGHT": fb_game_play_area_height,    # NEW Fallback
        "PLAYER_MAX_HEALTH":100, "PLAYER_SPEED":3, "ROTATION_SPEED":5,
        "PLAYER_BASE_SHOOT_COOLDOWN":500, "PLAYER_RAPID_FIRE_COOLDOWN":150,
        "MISSILE_COOLDOWN":5000, "INITIAL_WEAPON_MODE":0,
        "PLAYER_BULLET_SPEED":5, "PLAYER_BULLET_LIFETIME":100,
        "PLAYER_DEFAULT_BULLET_SIZE": 4, "PLAYER_BIG_BULLET_SIZE": 16,
        "BOUNCING_BULLET_MAX_BOUNCES":2, "PIERCING_BULLET_MAX_PIERCES":1,
        "MISSILE_SPEED":4, "MISSILE_LIFETIME":800, "MISSILE_TURN_RATE":4, "MISSILE_DAMAGE":50,
        "SPEED_BOOST_POWERUP_DURATION":10000, 
        "PLAYER_BULLET_COLOR": YELLOW if 'YELLOW' in globals() else (255,255,0), # Use imported or literal
        "WEAPON_MODE_DEFAULT": 0, "WEAPON_MODE_TRI_SHOT": 1, "WEAPON_MODE_RAPID_SINGLE":2,
        "WEAPON_MODE_RAPID_TRI":3, "WEAPON_MODE_BIG_SHOT":4, "WEAPON_MODE_BOUNCE":5,
        "WEAPON_MODE_PIERCE":6, "WEAPON_MODE_HEATSEEKER":7, "WEAPON_MODE_HEATSEEKER_PLUS_BULLETS":8,
        "WEAPON_MODE_LIGHTNING": 9,
        "WEAPON_MODES_SEQUENCE": [0,1,2,3,4,5,6,7,8,9], # Ensure this matches game_settings
        "TILE_SIZE": 80,
        "LIGHTNING_COLOR": (0, 220, 220), "LIGHTNING_DAMAGE": 15,
        "LIGHTNING_LIFETIME": 60, "LIGHTNING_COOLDOWN": 750,
        "LIGHTNING_ZAP_RANGE": 250, # Fallback value, consistent with game_settings
        "PHANTOM_CLOAK_COOLDOWN_MS": 15000, "PHANTOM_CLOAK_DURATION_MS": 5000,
        "PHANTOM_CLOAK_ALPHA": 70,
        "POWERUP_TYPES": { # Ensure this matches game_settings for color access
            "shield": { "color": LIGHT_BLUE if 'LIGHT_BLUE' in globals() else (173,216,230), "image_filename": "shield_icon.png", "duration": 35000 },
            "speed_boost": { "color": GREEN if 'GREEN' in globals() else (0,255,0), "image_filename": "speed_icon.png", "duration": 10000, "multiplier": 2.0 },
            "weapon_upgrade": { "color": BLUE if 'BLUE' in globals() else (0,0,255), "image_filename": "weapon_icon.png" }
        },
        "SHIELD_POWERUP_DURATION": 35000,
        "WEAPON_MODE_NAMES": { # Ensure this matches game_settings
            0: "Single Shot", 1: "Tri-Shot", 2: "Rapid Single", 3: "Rapid Tri-Shot",
            4: "Big Shot", 5: "Bounce Shot", 6: "Pierce Shot", 7: "Heatseeker",
            8: "Seeker + Rapid", 9: "Lightning"
        }
    }
    val = defaults.get(key)
    if val is None:
        # Fallback for colors if not in defaults and not imported
        if key == "ORANGE": return (255,165,0) 
        if key == "CYAN": return (0,255,255)
        print(f"CRITICAL ERROR (player.py get_game_setting fallback): Key '{key}' NOT FOUND in internal defaults!")
    # if _using_internal_player_defaults:
        # print(f"DEBUG (player.py - internal): Fetched '{key}': {val}")
    return val

# Pygame key constants, defined globally in player.py for direct use in handle_input
K_LEFT = pygame.K_LEFT
K_RIGHT = pygame.K_RIGHT
K_c = pygame.K_c # Key for cloak

MAX_SPEED_BOOST_STACK_DURATION = (get_game_setting("SPEED_BOOST_POWERUP_DURATION") or 10000) * 2

class Drone(BaseDrone):
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound=None, drone_system=None):
        super().__init__(x, y, speed=drone_stats.get("speed", get_game_setting("PLAYER_SPEED")))
        self.moving_forward = False
        self.drone_id = drone_id
        self.raw_drone_stats = drone_stats # Store raw stats from drone_system
        self.drone_system = drone_system # Reference to drone system for potential future use

        # Apply stats from drone_stats (which could be modified by Omega-9, etc.)
        self.base_speed = self.raw_drone_stats.get("speed", self.speed) # Base speed for this drone type
        self.rotation_speed = self.raw_drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.max_health = self.raw_drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.health = self.max_health
        self.fire_rate_multiplier = self.raw_drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = self.raw_drone_stats.get("special_ability") # e.g., "phantom_cloak"

        self.sprite_path = drone_sprite_path
        self.original_image = None # Will hold the loaded and scaled sprite image
        sprite_render_dimensions = (int(self.size * 1.5), int(self.size * 1.5)) # Example scaling

        if self.sprite_path and isinstance(self.sprite_path, str):
            try:
                if os.path.exists(self.sprite_path):
                    loaded_image = pygame.image.load(self.sprite_path).convert_alpha()
                    self.original_image = pygame.transform.smoothscale(loaded_image, sprite_render_dimensions)
                    self.rect = self.original_image.get_rect(center=(int(self.x), int(self.y)))
                else:
                    print(f"Sprite file not found: '{self.sprite_path}'. Using fallback drawing for {self.drone_id}.")
            except pygame.error as e:
                print(f"Error loading drone sprite '{self.sprite_path}': {e}. Using fallback drawing for {self.drone_id}.")
        else:
            if self.sprite_path is not None and not isinstance(self.sprite_path, str): # Path provided but invalid type
                print(f"Warning: Invalid sprite_path type for {self.drone_id}: '{type(self.sprite_path)}'. Using fallback drawing.")
            # If self.sprite_path is None, it will use the fallback drawing by default.

        # Weapon Initialization
        try:
            initial_weapon_mode_val = get_game_setting("INITIAL_WEAPON_MODE")
            weapon_modes_sequence_val = get_game_setting("WEAPON_MODES_SEQUENCE")

            if weapon_modes_sequence_val is None or not isinstance(weapon_modes_sequence_val, list) or not weapon_modes_sequence_val:
                # Fallback if sequence is invalid
                weapon_modes_sequence_val = [get_game_setting("WEAPON_MODE_DEFAULT")] # Must be a list
                initial_weapon_mode_val = weapon_modes_sequence_val[0]
            
            if initial_weapon_mode_val is None or initial_weapon_mode_val not in weapon_modes_sequence_val:
                initial_weapon_mode_val = weapon_modes_sequence_val[0] # Default to first in sequence

            self.weapon_mode_index = weapon_modes_sequence_val.index(initial_weapon_mode_val)
            self.current_weapon_mode = weapon_modes_sequence_val[self.weapon_mode_index]
        except Exception as e: # Broad exception for critical weapon setup
            print(f"CRITICAL ERROR (Drone.__init__): Exception during weapon initialization: {e}. Defaulting weapon.")
            # Safe defaults
            self.weapon_mode_index = 0
            default_weapon_mode_val = get_game_setting("WEAPON_MODE_DEFAULT") # Should be 0
            self.current_weapon_mode = default_weapon_mode_val if default_weapon_mode_val is not None else 0


        self.current_bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        self.base_shoot_cooldown_config = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        self.rapid_shoot_cooldown_config = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        self.missile_cooldown_config = get_game_setting("MISSILE_COOLDOWN")
        self.lightning_cooldown_config = get_game_setting("LIGHTNING_COOLDOWN")
        self._update_weapon_attributes() # Set initial cooldowns based on weapon mode

        self.last_shot_time = 0
        self.last_missile_shot_time = 0 # Separate cooldown for missiles
        self.alive = True
        self.crash_sound = crash_sound # Passed from Game class
        self.bullets_group = pygame.sprite.Group() # For player's bullets
        self.missiles_group = pygame.sprite.Group() # For player's missiles

        # Power-up states
        self.shield_active = False; self.shield_start_time = 0; self.shield_duration = 0
        self.shield_end_time = 0; self.shield_visual_radius_factor = 1.0
        self.shield_is_co_effect_of_speed_boost = False # True if shield is due to speed boost

        self.speed_boost_armed = False; self.armed_boost_duration = 0; self.armed_boost_multiplier = 0.0
        self.speed_boost_active = False; self.speed_boost_start_time = 0
        self.speed_boost_duration = 0; self.speed_boost_end_time = 0
        self.active_powerup_type = None # For UI display: "shield", "speed_boost"

        # Cloak ability states
        self.is_cloaked = False
        # Initialize last_cloak_time to allow immediate first use if available
        self.last_cloak_time = - (get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS") or 15000) 
        self.cloak_end_time = 0
        self.can_cloak = (self.special_ability == "phantom_cloak")


    def get_position(self): # Helper if needed
        return self.x, self.y

    def handle_input(self, keys, current_time):
        # Movement handled by Game class setting self.moving_forward
        if keys[K_LEFT]: self.rotate("left", self.rotation_speed)
        if keys[K_RIGHT]: self.rotate("right", self.rotation_speed)
        
        if self.can_cloak and keys[K_c]: # Check for cloak activation key
            self.try_activate_cloak(current_time)

    def try_activate_cloak(self, current_time):
        if not self.can_cloak or self.is_cloaked: return False # Cannot cloak if already cloaked or not capable
        
        cooldown = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")
        if current_time - self.last_cloak_time >= cooldown:
            self.is_cloaked = True
            duration = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
            self.cloak_end_time = current_time + duration
            self.last_cloak_time = current_time # Record when cloak was activated for cooldown
            # print(f"Player cloaked at {current_time} for {duration}ms. Cooldown started.")
            return True
        # else:
            # print(f"Cloak on cooldown. Last used: {self.last_cloak_time}, Current: {current_time}, Needed: {cooldown}")
        return False

    def activate_shield(self, duration_ms, is_from_speed_boost=False):
        current_time = pygame.time.get_ticks()
        self.shield_active = True
        self.shield_start_time = current_time # For potential UI or effects
        self.shield_duration = duration_ms
        self.shield_end_time = current_time + duration_ms
        self.shield_is_co_effect_of_speed_boost = is_from_speed_boost

        if not is_from_speed_boost:
            self.active_powerup_type = "shield"
        elif self.speed_boost_active: # If shield is from speed boost, ensure speed boost is the primary displayed powerup
             self.active_powerup_type = "speed_boost"
        # print(f"Shield activated. Duration: {duration_ms}ms. From Speed Boost: {is_from_speed_boost}")


    def arm_speed_boost(self, duration_ms, multiplier):
        current_time = pygame.time.get_ticks()
        if self.speed_boost_active: # If already active, extend duration (stacking)
            remaining_time = max(0, self.speed_boost_end_time - current_time)
            new_total_duration = min(remaining_time + duration_ms, MAX_SPEED_BOOST_STACK_DURATION)
            self.speed_boost_end_time = current_time + new_total_duration
            self.speed_boost_duration = new_total_duration # Update total duration
            if self.shield_is_co_effect_of_speed_boost: # Also extend associated shield
                self.activate_shield(new_total_duration, is_from_speed_boost=True)
            # print(f"Speed boost extended. New end time: {self.speed_boost_end_time}")
        elif not self.speed_boost_armed: # If not armed and not active, arm it
            self.speed_boost_armed = True
            self.armed_boost_duration = duration_ms
            self.armed_boost_multiplier = multiplier
            # print(f"Speed boost armed. Duration: {duration_ms}, Multiplier: {multiplier}")
        elif self.speed_boost_armed and not self.speed_boost_active: # If armed but not yet active, re-arm with new values
            self.armed_boost_duration = duration_ms
            self.armed_boost_multiplier = multiplier
            # print(f"Speed boost re-armed. Duration: {duration_ms}, Multiplier: {multiplier}")


    def attempt_speed_boost_activation(self):
        # Called when player starts moving forward (e.g., UP arrow press in Game class)
        if self.speed_boost_armed and not self.speed_boost_active and self.moving_forward:
            current_time = pygame.time.get_ticks()
            self.speed = self.base_speed * self.armed_boost_multiplier # Apply speed multiplier
            self.speed_boost_active = True
            self.speed_boost_start_time = current_time
            self.speed_boost_duration = self.armed_boost_duration
            self.speed_boost_end_time = current_time + self.speed_boost_duration
            
            # Speed boost also grants a shield for its duration
            self.activate_shield(self.speed_boost_duration, is_from_speed_boost=True)
            self.active_powerup_type = "speed_boost" # For UI

            # Consume the armed boost
            self.speed_boost_armed = False
            self.armed_boost_duration = 0
            self.armed_boost_multiplier = 0.0
            # print(f"Speed boost ACTIVATED. Speed: {self.speed}. Duration: {self.speed_boost_duration}")

    def _update_weapon_attributes(self):
        mode = self.current_weapon_mode
        self.current_bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE") \
            if mode == get_game_setting("WEAPON_MODE_BIG_SHOT") \
            else get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

        rapid_modes = [
            get_game_setting("WEAPON_MODE_RAPID_SINGLE"),
            get_game_setting("WEAPON_MODE_RAPID_TRI"),
            get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS") # This mode also has rapid bullets
        ]
        if mode in rapid_modes:
            self.current_shoot_cooldown = self.rapid_shoot_cooldown_config * self.fire_rate_multiplier
        elif mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
             self.current_shoot_cooldown = self.lightning_cooldown_config * self.fire_rate_multiplier
        else: # Default, Tri-shot, Big-shot, Bounce, Pierce, Heatseeker (missile part)
            self.current_shoot_cooldown = self.base_shoot_cooldown_config * self.fire_rate_multiplier
        
        # Missile cooldown is independent but affected by fire_rate_multiplier as well
        self.current_missile_cooldown = self.missile_cooldown_config * self.fire_rate_multiplier


    def cycle_weapon_state(self, force_cycle=False): # force_cycle used by weapon pickup
        weapon_sequence = get_game_setting("WEAPON_MODES_SEQUENCE")
        
        if weapon_sequence is None or not isinstance(weapon_sequence, list) or not weapon_sequence:
            print("ERROR (cycle_weapon_state): WEAPON_MODES_SEQUENCE is invalid or empty. Cannot cycle weapon.")
            return
        
        num_weapon_modes = len(weapon_sequence)
        max_weapon_index = num_weapon_modes - 1

        if num_weapon_modes <= 0:
            print("ERROR (cycle_weapon_state): No weapons defined in WEAPON_MODES_SEQUENCE.")
            return
        
        if num_weapon_modes == 1: # Only one weapon, no cycling
            if self.current_weapon_mode != weapon_sequence[0] or self.weapon_mode_index != 0: # Ensure it's set
                self.weapon_mode_index = 0
                self.current_weapon_mode = weapon_sequence[0]
                self._update_weapon_attributes()
            return

        # If already at the last weapon mode, do not cycle further unless force_cycle (e.g. from a hypothetical "max weapon" item)
        # Standard weapon upgrade pickup should not cycle past max.
        if self.weapon_mode_index >= max_weapon_index and not force_cycle: # Allow force_cycle to potentially wrap or special behavior
            # print(f"DEBUG: Max weapon (Index: {self.weapon_mode_index}) reached. No further upgrade from cycle_weapon_state.")
            return
        
        # Logic for forced cycle (e.g., if you wanted it to wrap or a special effect on max weapon pickup)
        if force_cycle and self.weapon_mode_index >= max_weapon_index:
            # Example: could wrap to the first weapon, or give a score bonus, etc.
            # For now, let's assume force_cycle from a pickup simply tries to ensure an upgrade happens if possible,
            # but still respects the max if no further distinct modes exist.
            # If the intention is that a pickup *always* grants the next in sequence even if current is max,
            # this logic would need to change (e.g. self.weapon_mode_index = (self.weapon_mode_index + 1) % num_weapon_modes for wrapping)
            # Current behavior: if at max, even force_cycle won't go beyond unless sequence itself changes.
            pass # No change if at max, even if forced, under current "don't go beyond sequence" logic.

        if self.weapon_mode_index < max_weapon_index:
            self.weapon_mode_index += 1
        # If self.weapon_mode_index was already max_weapon_index, it remains max_weapon_index.
        
        self.current_weapon_mode = weapon_sequence[self.weapon_mode_index]
        self._update_weapon_attributes()
        
        weapon_names = get_game_setting("WEAPON_MODE_NAMES")
        current_weapon_name = "Unknown"
        if isinstance(weapon_names, dict): 
            current_weapon_name = weapon_names.get(self.current_weapon_mode, f"Unknown Mode ID: {self.current_weapon_mode}")
        # print(f"Weapon cycled to: {current_weapon_name} (Index: {self.weapon_mode_index})")

    def update_movement(self, maze=None):
        if self.moving_forward:
            if self.speed <= 0: return # No movement if speed is zero or negative
            
            angle_rad = math.radians(self.angle)
            old_x, old_y = self.x, self.y # Store position before movement for collision resolution
            
            delta_x = math.cos(angle_rad) * self.speed
            delta_y = math.sin(angle_rad) * self.speed
            
            self.x += delta_x
            self.y += delta_y
            self.rect.center = (int(self.x), int(self.y)) # Update rect to new potential position

            if maze and hasattr(maze, 'is_wall'): # Check for maze collision
                # Use a small representative rect for collision, or drone's full rect
                collided_wall_type = maze.is_wall(self.rect.centerx, self.rect.centery, 
                                                  self.rect.width * 0.8, self.rect.height * 0.8) # Use a slightly smaller rect
                
                if collided_wall_type: # If collision detected
                    self.x, self.y = old_x, old_y # Revert to old position
                    self.rect.center = (int(self.x), int(self.y)) # Reset rect position
                    
                    # Optional: specific effect based on wall type
                    if collided_wall_type == "internal" and not self.shield_active:
                        # Example: take minor damage for hitting internal walls without shield
                        self.take_damage(10, self.crash_sound) 
                        # Could also add a small bounce-back or stop movement
                        self.moving_forward = False 
        
        # Ensure rect is always centered on x, y, even if not moving due to collision logic above or no input
        self.rect.center = (int(self.x), int(self.y))


    # UPDATED: Note parameter name change from ui_panel_width to left_panel_width for clarity
    def update(self, current_time, maze=None, enemies_group=None, left_panel_width=0):
        if not self.alive:
            self.bullets_group.update() # Still update projectiles if player is dead but they exist
            self.missiles_group.update()
            return

        # Cloak update
        # cloak_duration = get_game_setting("PHANTOM_CLOAK_DURATION_MS") # Not needed here, only in try_activate
        if self.is_cloaked and current_time >= self.cloak_end_time:
            self.is_cloaked = False
            # print("Player uncloaked.")

        # Speed boost update
        if self.speed_boost_active and current_time >= self.speed_boost_end_time:
            self.speed_boost_active = False
            self.speed = self.base_speed # Revert to drone's base speed
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None
            # print("Speed boost expired.")
        elif not self.speed_boost_active: 
            self.speed = self.base_speed # Ensure speed is correct if no boost

        # Shield update
        if self.shield_active and current_time >= self.shield_end_time:
            self.shield_active = False
            self.shield_duration = 0
            self.shield_is_co_effect_of_speed_boost = False
            if self.active_powerup_type == "shield": self.active_powerup_type = None
            # print("Shield expired.")
        
        # Determine active powerup type for UI display
        if self.speed_boost_active:
            self.active_powerup_type = "speed_boost"
        elif self.shield_active and not self.shield_is_co_effect_of_speed_boost:
            self.active_powerup_type = "shield"
        elif not self.speed_boost_active and not self.shield_active :
            self.active_powerup_type = None

        # Movement update (calls self.update_movement which handles maze collision)
        self.update_movement(maze)

        # Screen boundary clamping
        half_w = self.rect.width / 2
        half_h = self.rect.height / 2
        
        game_area_left = left_panel_width + half_w # left_panel_width will be 0 for new HUD
        game_area_right = get_game_setting("WIDTH") - half_w
        game_area_top = half_h
        # UPDATED: Use GAME_PLAY_AREA_HEIGHT for bottom boundary
        game_area_bottom = get_game_setting("GAME_PLAY_AREA_HEIGHT") - half_h 
        
        clamped = False
        if self.x < game_area_left: self.x = game_area_left; clamped = True
        elif self.x > game_area_right: self.x = game_area_right; clamped = True
        
        if self.y < game_area_top: self.y = game_area_top; clamped = True
        elif self.y > game_area_bottom: self.y = game_area_bottom; clamped = True # Check against new bottom
        
        if clamped:
            self.rect.center = (int(self.x), int(self.y)) # Update rect if clamped

        # Update bullets and missiles
        self.bullets_group.update()
        self.missiles_group.update()

        # Shield visual effect update (pulsing)
        if self.shield_active:
            self.shield_visual_radius_factor = 1.0 + 0.1 * math.sin(current_time * 0.005)


    def get_raycast_endpoint(self, start_pos_tuple, direction_angle_degrees, max_range, maze_obj, step_size=3):
        start_pos = pygame.math.Vector2(start_pos_tuple)
        direction_rad = math.radians(direction_angle_degrees)
        
        final_end_point = pygame.math.Vector2(
            start_pos.x + math.cos(direction_rad) * max_range,
            start_pos.y + math.sin(direction_rad) * max_range
        )

        if not maze_obj: return final_end_point 

        num_steps = int(max_range / step_size)
        if num_steps <= 0: num_steps = 1

        for i in range(num_steps + 1): 
            current_range = i * step_size 
            if current_range > max_range: current_range = max_range
            
            current_check_pos = pygame.math.Vector2(
                start_pos.x + math.cos(direction_rad) * current_range,
                start_pos.y + math.sin(direction_rad) * current_range
            )
            
            if maze_obj.is_wall(current_check_pos.x, current_check_pos.y, 2, 2): # Small check area
                if i == 0: return start_pos # Started inside a wall
                
                prev_range = (i - 1) * step_size # Point before collision
                previous_clear_pos = pygame.math.Vector2(
                    start_pos.x + math.cos(direction_rad) * prev_range,
                    start_pos.y + math.sin(direction_rad) * prev_range
                )
                return previous_clear_pos
            
            if current_range >= max_range: break # Reached max_range without wall hit
                
        return final_end_point


    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time = pygame.time.get_ticks()
        
        # Check for primary weapon fire (bullets, lightning)
        can_fire_primary_component = (
            self.alive and
            current_time - self.last_shot_time >= self.current_shoot_cooldown and
            # Heatseeker only mode doesn't fire standard bullets from this check
            self.current_weapon_mode != get_game_setting("WEAPON_MODE_HEATSEEKER") 
        )

        if can_fire_primary_component:
            tip_x, tip_y = self.get_tip_position()
            active_mode = self.current_weapon_mode
            fired_this_call = False # To ensure sound plays only once if multiple bullets fired
            raycast_step_size = 3 

            if active_mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
                closest_visible_enemy = None
                min_dist_to_visible_enemy_sq = float('inf')
                zap_range = get_game_setting("LIGHTNING_ZAP_RANGE") # Default: TILE_SIZE * 7 from player.py fallback
                
                if enemies_group and maze:
                    for enemy_sprite in enemies_group:
                        if enemy_sprite.alive:
                            enemy_center_vec = pygame.math.Vector2(enemy_sprite.rect.center)
                            tip_vec = pygame.math.Vector2(tip_x, tip_y)
                            vector_to_enemy = enemy_center_vec - tip_vec
                            dist_to_enemy = vector_to_enemy.length()

                            if dist_to_enemy == 0 or dist_to_enemy > zap_range: continue

                            angle_to_enemy_deg = math.degrees(math.atan2(vector_to_enemy.y, vector_to_enemy.x))
                            
                            ray_hit_point = self.get_raycast_endpoint(
                                (tip_x, tip_y), angle_to_enemy_deg, dist_to_enemy, 
                                maze, step_size=raycast_step_size 
                            )
                            
                            if ray_hit_point.distance_to(enemy_center_vec) < raycast_step_size * 1.5: # Tolerance
                                current_dist_sq = dist_to_enemy**2
                                if current_dist_sq < min_dist_to_visible_enemy_sq:
                                    min_dist_to_visible_enemy_sq = current_dist_sq
                                    closest_visible_enemy = enemy_sprite
                
                lightning_params = {
                    "origin_pos": (tip_x, tip_y),
                    "damage": get_game_setting("LIGHTNING_DAMAGE"),
                    "lifetime": get_game_setting("LIGHTNING_LIFETIME"),
                    "color": get_game_setting("LIGHTNING_COLOR"), "owner": self, "maze": maze
                }

                if closest_visible_enemy:
                    lightning_params["target_enemy"] = closest_visible_enemy
                else: # No visible enemy, fire straight, stopping at walls or max range
                    actual_end_point = self.get_raycast_endpoint(
                        (tip_x, tip_y), self.angle, zap_range, maze, step_size=raycast_step_size
                    )
                    lightning_params["end_point"] = actual_end_point
                
                new_lightning_bullet = LightningBullet(**lightning_params)
                self.bullets_group.add(new_lightning_bullet) # Lightning is a type of "bullet"
                fired_this_call = True
            
            else: # Other bullet types (single, tri, big, bounce, pierce)
                bullet_fire_angles = [self.angle]
                current_bullet_base_speed = get_game_setting("PLAYER_BULLET_SPEED")
                current_bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                current_bullet_speed_val = current_bullet_base_speed
                bullet_bounces = 0
                bullet_pierces = 0

                # Rapid modes also affect regular bullets if part of WEAPON_MODE_HEATSEEKER_PLUS_BULLETS
                rapid_modes_for_bullets = [
                    get_game_setting("WEAPON_MODE_RAPID_SINGLE"),
                    get_game_setting("WEAPON_MODE_RAPID_TRI"),
                    get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS") 
                ]
                if active_mode in rapid_modes_for_bullets:
                    current_bullet_speed_val = current_bullet_base_speed * 1.5 # Faster bullets for rapid modes

                if active_mode == get_game_setting("WEAPON_MODE_BOUNCE"):
                    bullet_bounces = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES")
                elif active_mode == get_game_setting("WEAPON_MODE_PIERCE"):
                    bullet_pierces = get_game_setting("PIERCING_BULLET_MAX_PIERCES")

                tri_shot_modes_for_bullets = [
                    get_game_setting("WEAPON_MODE_TRI_SHOT"),
                    get_game_setting("WEAPON_MODE_RAPID_TRI")
                ]
                if active_mode in tri_shot_modes_for_bullets:
                    bullet_fire_angles = [self.angle - 15, self.angle, self.angle + 15]
                
                for ang in bullet_fire_angles:
                    new_bullet = Bullet(
                        tip_x, tip_y, ang,
                        speed=current_bullet_speed_val,
                        color=get_game_setting("PLAYER_BULLET_COLOR"),
                        lifetime=current_bullet_lifetime,
                        size=self.current_bullet_size, # This is set by _update_weapon_attributes
                        bounces=bullet_bounces,
                        pierce_count=bullet_pierces,
                        maze=maze, owner=self
                    )
                    self.bullets_group.add(new_bullet)
                fired_this_call = True

            if fired_this_call:
                self.last_shot_time = current_time
                if sound: sound.play()

        # Check for missile component fire (Heatseeker modes)
        can_fire_missile_component = (
            self.alive and
            current_time - self.last_missile_shot_time >= self.current_missile_cooldown and
            self.current_weapon_mode in [
                get_game_setting("WEAPON_MODE_HEATSEEKER"),
                get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS")
            ]
        )
        if can_fire_missile_component:
            # Fire missile if mode is heatseeker-only OR if there are live enemies for combo mode
            fire_missile_anyway = (self.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER"))
            has_live_enemies = enemies_group and any(enemy.alive for enemy in enemies_group)

            if fire_missile_anyway or has_live_enemies:
                tip_x, tip_y = self.get_tip_position()
                current_missile_damage = get_game_setting("MISSILE_DAMAGE")
                # Pass enemies_group only if there are live enemies for targeting, else missile fires straight
                effective_enemies_group = enemies_group if has_live_enemies else None 
                
                new_missile = Missile(tip_x, tip_y, self.angle, 
                                      effective_enemies_group, 
                                      maze, damage=current_missile_damage)
                self.missiles_group.add(new_missile)
                self.last_missile_shot_time = current_time # Use separate cooldown timer for missiles
                if missile_sound: missile_sound.play()
                elif sound: sound.play() # Fallback to default shoot sound if no missile sound

    def reset_active_powerups(self):
        # Reset shield
        self.shield_active = False; self.shield_duration = 0; self.shield_end_time = 0
        self.shield_is_co_effect_of_speed_boost = False
        # Reset speed boost
        self.speed_boost_active = False; self.speed_boost_duration = 0; self.speed_boost_end_time = 0
        self.speed = self.base_speed # Reset to drone's base speed
        self.speed_boost_armed = False; self.armed_boost_duration = 0; self.armed_boost_multiplier = 0.0
        # Reset UI indicator
        self.active_powerup_type = None
        # Reset cloak
        self.is_cloaked = False
        # No need to reset last_cloak_time here, cooldown persists across deaths/resets if desired,
        # or could be reset if cloak should be available immediately on new life/level.
        # Current: cooldown persists.

    def take_damage(self, amount, sound=None):
        if self.shield_active: return # No damage if shield is active
        if self.is_cloaked: # Take more damage if hit while cloaked (risk/reward for some cloak types)
            amount *= 1.5 
        
        if self.alive:
            self.health -= amount
            if sound: sound.play() # Play damage/crash sound
            if self.health <= 0:
                self.health = 0
                self.alive = False
                # Death handling (e.g. explosion, game over check) typically done in Game class

    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None):
        # Re-initialize the drone to a clean state, used for respawn or new game
        # Call __init__ with new parameters. Pass existing crash_sound and drone_system.
        self.__init__(x, y, drone_id, drone_stats, drone_sprite_path, self.crash_sound, self.drone_system)
        
        # Explicitly set position and angle for reset
        self.x = x
        self.y = y
        self.angle = 0 # Reset angle to default facing (e.g., right)
        self.alive = True
        self.moving_forward = False # Ensure not moving on reset

        if health_override is not None: # Allow overriding health on reset
            self.health = min(health_override, self.max_health)
        else: # Default to max health for this drone type
            self.health = self.max_health 
            
        self.rect.center = (int(self.x), int(self.y))
        # Clear any active power-ups
        self.reset_active_powerups()
        # Clear projectiles
        self.bullets_group.empty()
        self.missiles_group.empty()


    def _draw_original_drone_shape(self, surface): # Fallback drawing if no sprite
        s = self.size * 0.8 # Scale factor for points
        # Points relative to drone center (0,0) before rotation and translation
        p_nose = (s * 0.7, 0)
        p_wing_rt_front = (s * 0.1, -s * 0.4); p_wing_rt_rear = (-s * 0.5, -s * 0.25)
        p_wing_lt_front = (s * 0.1, s * 0.4); p_wing_lt_rear = (-s * 0.5, s * 0.25)
        p_tail_rt = (-s * 0.3, -s * 0.1); p_tail_lt = (-s * 0.3, s * 0.1)
        
        body_points_rel = [p_nose, p_wing_rt_front, p_wing_rt_rear, p_tail_rt, 
                           p_tail_lt, p_wing_lt_rear, p_wing_lt_front]
        cockpit_points_rel = [(s*0.35,0),(s*0.15,-s*0.1),(s*0.05,-s*0.08),
                              (s*0.05,s*0.08),(s*0.15,s*0.1)]
        engine_glow_l_rel = (-s*0.35,s*0.15); engine_glow_r_rel = (-s*0.35,-s*0.15)
        engine_glow_radius = s*0.08

        angle_rad = math.radians(self.angle); cos_a = math.cos(angle_rad); sin_a = math.sin(angle_rad)
        
        # Helper to rotate and translate points
        def rt(p): 
            x_r = p[0] * cos_a - p[1] * sin_a
            y_r = p[0] * sin_a + p[1] * cos_a
            return (x_r + self.x, y_r + self.y) # Translate to drone's current position
            
        body_abs = [rt(p) for p in body_points_rel]
        cockpit_abs = [rt(p) for p in cockpit_points_rel]
        eng_l_abs = rt(engine_glow_l_rel); eng_r_abs = rt(engine_glow_r_rel)

        # Get colors from settings or use fallbacks
        drone_body_color = get_game_setting("BLUE") or (0,0,255)
        drone_outline_color = get_game_setting("WHITE") or (255,255,255)
        cockpit_color = get_game_setting("CYAN") or (0,255,255)
        engine_color = get_game_setting("CYAN") or (0,255,255)

        pygame.draw.polygon(surface, drone_body_color, body_abs)
        pygame.draw.polygon(surface, drone_outline_color, body_abs, 2) # Outline
        pygame.draw.polygon(surface, cockpit_color, cockpit_abs)
        pygame.draw.polygon(surface, drone_outline_color, cockpit_abs, 1) # Cockpit outline
        pygame.draw.circle(surface, engine_color, (int(eng_l_abs[0]), int(eng_l_abs[1])), int(engine_glow_radius))
        pygame.draw.circle(surface, engine_color, (int(eng_r_abs[0]), int(eng_r_abs[1])), int(engine_glow_radius))


    def draw(self, surface):
        # Only draw if alive or has active projectiles (for their draw calls)
        if not self.alive and not self.bullets_group and not self.missiles_group:
            return

        if self.alive:
            cloak_alpha_setting = get_game_setting("PHANTOM_CLOAK_ALPHA") 
            current_alpha = cloak_alpha_setting if self.is_cloaked else 255

            if not self.original_image: # Fallback drawing if no sprite image
                if self.is_cloaked:
                    # Draw to a temporary surface for alpha blending
                    temp_draw_size = int(self.size * 2.2) # Ensure surface is large enough for rotation
                    temp_surf = pygame.Surface((temp_draw_size, temp_draw_size), pygame.SRCALPHA)
                    
                    # Temporarily adjust self.x, self.y to draw centered on temp_surf
                    original_screen_x, original_screen_y = self.x, self.y
                    self.x, self.y = temp_surf.get_width() / 2, temp_surf.get_height() / 2
                    self._draw_original_drone_shape(temp_surf) # Draw centered on temp surface
                    self.x, self.y = original_screen_x, original_screen_y # Restore actual position
                    
                    temp_surf.set_alpha(current_alpha)
                    # Blit the temp surface centered at the drone's actual screen position
                    surface.blit(temp_surf, temp_surf.get_rect(center=(int(self.x), int(self.y))))
                else: # Not cloaked, draw directly
                    self._draw_original_drone_shape(surface)
            else: # Sprite image exists
                # Rotate the original sprite (negative angle for Pygame rotation)
                rot_img = pygame.transform.rotate(self.original_image, -self.angle)
                
                img_to_blit = rot_img
                if self.is_cloaked: # Apply alpha if cloaked
                    img_to_blit = rot_img.copy() # Work on a copy to not affect original rotated image
                    img_to_blit.set_alpha(current_alpha)
                
                # Blit the (potentially cloaked) rotated image
                # Ensure self.rect is up-to-date from update() method
                surface.blit(img_to_blit, img_to_blit.get_rect(center=self.rect.center))

            # Draw speed boost flame effect if active and moving
            if self.speed_boost_active and self.moving_forward:
                s = self.size * 0.8
                angle_rad = math.radians(self.angle); cos_a = math.cos(angle_rad); sin_a = math.sin(angle_rad)
                def rt(p): x_r=p[0]*cos_a-p[1]*sin_a; y_r=p[0]*sin_a+p[1]*cos_a; return(x_r+self.x,y_r+self.y)
                
                flame_len = self.size * 0.8 * random.uniform(0.8, 1.2)
                flame_w = self.size * 0.4
                # Points for the flame polygon, relative to drone's rear
                fl_tip = (-s * 0.5 - flame_len, 0) 
                fl_b1 = (-s * 0.45, flame_w / 2)
                fl_b2 = (-s * 0.45, -flame_w / 2)
                
                outer_flame_color = get_game_setting("ORANGE") or (255,165,0)
                inner_flame_color = get_game_setting("YELLOW") or (255,255,0)

                pygame.draw.polygon(surface, outer_flame_color, [rt(p) for p in [fl_tip, fl_b1, fl_b2]])
                # Inner, brighter part of the flame
                pygame.draw.polygon(surface, inner_flame_color, [rt((-s*0.5-flame_len*0.6,0)),rt((-s*0.45,flame_w/3)),rt((-s*0.45,-flame_w/3))])

            # Draw shield visual effect
            if self.shield_active:
                powerup_types_info = get_game_setting("POWERUP_TYPES")
                shield_info = {}
                if isinstance(powerup_types_info, dict): # Ensure it's a dict before .get()
                    shield_info = powerup_types_info.get("shield", {}) # Default to empty if "shield" key missing
                
                shield_base_color = shield_info.get("color", LIGHT_BLUE if 'LIGHT_BLUE' in globals() else (173,216,230)) # Fallback color
                shield_alpha_color = (*shield_base_color[:3], 100) # Apply alpha for transparency
                
                shield_radius_base = max(self.rect.width, self.rect.height) * 0.65 # Base radius on drone size
                shield_radius_animated = int(shield_radius_base * self.shield_visual_radius_factor) # Pulsing radius
                
                shield_surface_diameter = shield_radius_animated * 2
                if shield_surface_diameter > 0: # Ensure valid surface size
                    shield_surf = pygame.Surface((shield_surface_diameter, shield_surface_diameter), pygame.SRCALPHA)
                    pygame.draw.circle(shield_surf, shield_alpha_color,
                                       (shield_radius_animated, shield_radius_animated), shield_radius_animated)
                    surface.blit(shield_surf, shield_surf.get_rect(center=self.rect.center))

        # Draw active bullets and missiles (they handle their own appearance)
        for bullet in self.bullets_group: # Bullets and LightningBullets
            bullet.draw(surface)

        self.missiles_group.draw(surface) # Missiles group handles drawing its sprites