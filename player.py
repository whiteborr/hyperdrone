import math
import random
import os
import pygame

from game_settings import (
    BLUE, ORANGE, CYAN, WHITE, YELLOW, LIGHT_BLUE, GREEN
)

from drone_configs import PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS, PHANTOM_CLOAK_ALPHA
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
    else:
        print("ERROR (player.py): game_settings module imported, but get_game_setting function NOT FOUND or not callable.")
except ImportError as e:
    print(f"CRITICAL ERROR (player.py): Could not import 'game_settings' module: {e}. Using internal defaults.")
except Exception as e:
    print(f"CRITICAL ERROR (player.py): Exception during import of 'game_settings': {e}. Using internal defaults.")

def get_game_setting(key):
    global _using_internal_player_defaults
    if _game_settings_get_function:
        try:
            value = _game_settings_get_function(key)
            return value
        except Exception as e:
            print(f"ERROR (player.py): Error calling get_game_setting from game_settings module for key '{key}': {e}. Reverting to internal fallback.")
            _using_internal_player_defaults = True

    defaults = {
        "PLAYER_MAX_HEALTH":100, "PLAYER_SPEED":3, "ROTATION_SPEED":5,
        "PLAYER_BASE_SHOOT_COOLDOWN":500, "PLAYER_RAPID_FIRE_COOLDOWN":150,
        "MISSILE_COOLDOWN":5000, "INITIAL_WEAPON_MODE":0,
        "PLAYER_BULLET_SPEED":5, "PLAYER_BULLET_LIFETIME":100,
        "PLAYER_DEFAULT_BULLET_SIZE": 4, "PLAYER_BIG_BULLET_SIZE": 16,
        "BOUNCING_BULLET_MAX_BOUNCES":2, "PIERCING_BULLET_MAX_PIERCES":1,
        "MISSILE_SPEED":4, "MISSILE_LIFETIME":800, "MISSILE_TURN_RATE":4, "MISSILE_DAMAGE":50,
        "SPEED_BOOST_POWERUP_DURATION":10000, "PLAYER_BULLET_COLOR": YELLOW,
        "WEAPON_MODE_DEFAULT": 0, "WEAPON_MODE_TRI_SHOT": 1, "WEAPON_MODE_RAPID_SINGLE":2,
        "WEAPON_MODE_RAPID_TRI":3, "WEAPON_MODE_BIG_SHOT":4, "WEAPON_MODE_BOUNCE":5,
        "WEAPON_MODE_PIERCE":6, "WEAPON_MODE_HEATSEEKER":7, "WEAPON_MODE_HEATSEEKER_PLUS_BULLETS":8,
        "WEAPON_MODE_LIGHTNING": 9,
        "WEAPON_MODES_SEQUENCE": [0,1,2,3,4,5,6,7,8,9],
        "WIDTH": 1920, "HEIGHT": 1080, "TILE_SIZE": 80,
        "LIGHTNING_COLOR": (0, 220, 220), "LIGHTNING_DAMAGE": 15,
        "LIGHTNING_LIFETIME": 60,
        "LIGHTNING_COOLDOWN": 750,
        "LIGHTNING_ZAP_RANGE": 80 * 7,
        "PHANTOM_CLOAK_COOLDOWN_MS": 15000, "PHANTOM_CLOAK_DURATION_MS": 5000,
        "PHANTOM_CLOAK_ALPHA": 70,
        "POWERUP_TYPES": {
            "shield": { "color": LIGHT_BLUE, "image_filename": "shield_icon.png", "duration": 35000 },
            "speed_boost": { "color": GREEN, "image_filename": "speed_icon.png", "duration": 10000, "multiplier": 2.0 },
            "weapon_upgrade": { "color": BLUE, "image_filename": "weapon_icon.png" }
        },
        "SHIELD_POWERUP_DURATION": 35000,
        "WEAPON_MODE_NAMES": {
            0: "Single Shot", 1: "Tri-Shot", 2: "Rapid Single", 3: "Rapid Tri-Shot",
            4: "Big Shot", 5: "Bounce Shot", 6: "Pierce Shot", 7: "Heatseeker",
            8: "Seeker + Rapid", 9: "Lightning"
        }
    }
    val = defaults.get(key)
    if val is None:
        print(f"CRITICAL ERROR (player.py get_game_setting fallback): Key '{key}' NOT FOUND in internal defaults!")
    return val

K_LEFT = pygame.K_LEFT
K_RIGHT = pygame.K_RIGHT
K_c = pygame.K_c

MAX_SPEED_BOOST_STACK_DURATION = (get_game_setting("SPEED_BOOST_POWERUP_DURATION") or 10000) * 2

class Drone(BaseDrone):
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound=None, drone_system=None):
        super().__init__(x, y, speed=drone_stats.get("speed", get_game_setting("PLAYER_SPEED")))
        self.moving_forward = False
        self.drone_id = drone_id
        self.raw_drone_stats = drone_stats
        self.drone_system = drone_system
        self.base_speed = self.raw_drone_stats.get("speed", self.speed)
        self.rotation_speed = self.raw_drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.max_health = self.raw_drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.health = self.max_health
        self.fire_rate_multiplier = self.raw_drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = self.raw_drone_stats.get("special_ability")
        self.sprite_path = drone_sprite_path
        self.original_image = None
        sprite_render_dimensions = (int(self.size * 1.5), int(self.size * 1.5))
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
            if self.sprite_path is not None and not isinstance(self.sprite_path, str):
                print(f"Warning: Invalid sprite_path type for {self.drone_id}: '{type(self.sprite_path)}'. Using fallback drawing.")

        try:
            initial_weapon_mode_val = get_game_setting("INITIAL_WEAPON_MODE")
            weapon_modes_sequence_val = get_game_setting("WEAPON_MODES_SEQUENCE")
            if weapon_modes_sequence_val is None or not isinstance(weapon_modes_sequence_val, list) or not weapon_modes_sequence_val:
                weapon_modes_sequence_val = [0]
                initial_weapon_mode_val = 0
            if initial_weapon_mode_val is None or initial_weapon_mode_val not in weapon_modes_sequence_val:
                initial_weapon_mode_val = weapon_modes_sequence_val[0]
            self.weapon_mode_index = weapon_modes_sequence_val.index(initial_weapon_mode_val)
            self.current_weapon_mode = weapon_modes_sequence_val[self.weapon_mode_index]
        except Exception as e:
            print(f"CRITICAL ERROR (Drone.__init__): Exception during weapon initialization: {e}. Defaulting weapon.")
            self.weapon_mode_index = 0
            self.current_weapon_mode = 0

        self.current_bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        self.base_shoot_cooldown_config = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        self.rapid_shoot_cooldown_config = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        self.missile_cooldown_config = get_game_setting("MISSILE_COOLDOWN")
        self.lightning_cooldown_config = get_game_setting("LIGHTNING_COOLDOWN")
        self._update_weapon_attributes()

        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.alive = True
        self.crash_sound = crash_sound
        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.shield_active = False; self.shield_start_time = 0; self.shield_duration = 0
        self.shield_end_time = 0; self.shield_visual_radius_factor = 1.0
        self.shield_is_co_effect_of_speed_boost = False
        self.speed_boost_armed = False; self.armed_boost_duration = 0; self.armed_boost_multiplier = 0.0
        self.speed_boost_active = False; self.speed_boost_start_time = 0
        self.speed_boost_duration = 0; self.speed_boost_end_time = 0
        self.active_powerup_type = None
        self.is_cloaked = False
        self.last_cloak_time = - (get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS") or 15000)
        self.cloak_end_time = 0
        self.can_cloak = (self.special_ability == "phantom_cloak")

    def get_position(self):
        return self.x, self.y

    def handle_input(self, keys, current_time):
        if keys[K_LEFT]: self.rotate("left", self.rotation_speed)
        if keys[K_RIGHT]: self.rotate("right", self.rotation_speed)
        if self.can_cloak and keys[K_c]:
            self.try_activate_cloak(current_time)

    def try_activate_cloak(self, current_time):
        if not self.can_cloak or self.is_cloaked: return False
        cooldown = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")
        if current_time - self.last_cloak_time >= cooldown:
            self.is_cloaked = True
            duration = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
            self.cloak_end_time = current_time + duration
            self.last_cloak_time = current_time
            return True
        return False

    def activate_shield(self, duration_ms, is_from_speed_boost=False):
        current_time = pygame.time.get_ticks()
        self.shield_active = True
        self.shield_start_time = current_time
        self.shield_duration = duration_ms
        self.shield_end_time = current_time + duration_ms
        self.shield_is_co_effect_of_speed_boost = is_from_speed_boost
        if not is_from_speed_boost:
            self.active_powerup_type = "shield"
        elif self.speed_boost_active:
             self.active_powerup_type = "speed_boost"

    def arm_speed_boost(self, duration_ms, multiplier):
        current_time = pygame.time.get_ticks()
        if self.speed_boost_active:
            remaining_time = max(0, self.speed_boost_end_time - current_time)
            new_total_duration = min(remaining_time + duration_ms, MAX_SPEED_BOOST_STACK_DURATION)
            self.speed_boost_end_time = current_time + new_total_duration
            self.speed_boost_duration = new_total_duration
            if self.shield_is_co_effect_of_speed_boost:
                self.activate_shield(new_total_duration, is_from_speed_boost=True)
        elif not self.speed_boost_armed:
            self.speed_boost_armed = True
            self.armed_boost_duration = duration_ms
            self.armed_boost_multiplier = multiplier
        elif self.speed_boost_armed and not self.speed_boost_active:
            self.armed_boost_duration = duration_ms
            self.armed_boost_multiplier = multiplier

    def attempt_speed_boost_activation(self):
        if self.speed_boost_armed and not self.speed_boost_active and self.moving_forward:
            current_time = pygame.time.get_ticks()
            self.speed = self.base_speed * self.armed_boost_multiplier
            self.speed_boost_active = True
            self.speed_boost_start_time = current_time
            self.speed_boost_duration = self.armed_boost_duration
            self.speed_boost_end_time = current_time + self.speed_boost_duration
            self.activate_shield(self.speed_boost_duration, is_from_speed_boost=True)
            self.active_powerup_type = "speed_boost"
            self.speed_boost_armed = False
            self.armed_boost_duration = 0
            self.armed_boost_multiplier = 0.0

    def _update_weapon_attributes(self):
        mode = self.current_weapon_mode
        self.current_bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE") \
            if mode == get_game_setting("WEAPON_MODE_BIG_SHOT") \
            else get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        rapid_modes = [
            get_game_setting("WEAPON_MODE_RAPID_SINGLE"),
            get_game_setting("WEAPON_MODE_RAPID_TRI"),
            get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS")
        ]
        if mode in rapid_modes:
            self.current_shoot_cooldown = self.rapid_shoot_cooldown_config * self.fire_rate_multiplier
        elif mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
             self.current_shoot_cooldown = self.lightning_cooldown_config * self.fire_rate_multiplier
        else:
            self.current_shoot_cooldown = self.base_shoot_cooldown_config * self.fire_rate_multiplier
        self.current_missile_cooldown = self.missile_cooldown_config * self.fire_rate_multiplier

    def cycle_weapon_state(self, force_cycle=False):
        weapon_sequence = get_game_setting("WEAPON_MODES_SEQUENCE")
        
        # Check for invalid or empty weapon sequence
        if weapon_sequence is None or not isinstance(weapon_sequence, list) or not weapon_sequence:
            print("ERROR (cycle_weapon_state): WEAPON_MODES_SEQUENCE is invalid or empty. Cannot cycle weapon.")
            return
        
        num_weapon_modes = len(weapon_sequence)
        max_weapon_index = num_weapon_modes - 1

        # If there are no weapons or only one weapon in the sequence
        if num_weapon_modes <= 0:
            print("ERROR (cycle_weapon_state): No weapons defined in WEAPON_MODES_SEQUENCE.")
            return
        
        if num_weapon_modes == 1:
            # If only one weapon, ensure it's set (especially if called with force_cycle=False initially)
            # but don't change if it's already set.
            if self.current_weapon_mode != weapon_sequence[0] or self.weapon_mode_index != 0:
                self.weapon_mode_index = 0
                self.current_weapon_mode = weapon_sequence[0]
                self._update_weapon_attributes()
            # print("DEBUG: Only one weapon mode available. No cycle.")
            return

        # If already at the last weapon mode in the sequence, do not cycle further.
        if self.weapon_mode_index >= max_weapon_index:
            # print(f"DEBUG: Max weapon (Index: {self.weapon_mode_index}) reached. No further upgrade from cycle_weapon_state.")
            return
     
        self.weapon_mode_index += 1
        
        # Ensure the index is within bounds (should be, due to the check above)
        # self.weapon_mode_index = min(self.weapon_mode_index, max_weapon_index) 
        # This line is technically redundant if the logic is correct, but can be a safeguard.

        self.current_weapon_mode = weapon_sequence[self.weapon_mode_index]
        self._update_weapon_attributes()
        
        weapon_names = get_game_setting("WEAPON_MODE_NAMES")
        current_weapon_name = "Unknown"
        if isinstance(weapon_names, dict): 
            current_weapon_name = weapon_names.get(self.current_weapon_mode, f"Unknown Mode ID: {self.current_weapon_mode}")
        # You can uncomment the line below for debugging weapon changes:
        # print(f"Weapon cycled to: {current_weapon_name} (Index: {self.weapon_mode_index})")

    def update_movement(self, maze=None):
        if self.moving_forward:
            if self.speed <= 0: return
            angle_rad = math.radians(self.angle)
            old_x, old_y = self.x, self.y
            delta_x = math.cos(angle_rad) * self.speed
            delta_y = math.sin(angle_rad) * self.speed
            self.x += delta_x
            self.y += delta_y
            self.rect.center = (int(self.x), int(self.y))
            if maze and hasattr(maze, 'is_wall'):
                collided_wall_type = maze.is_wall(self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height)
                if collided_wall_type:
                    self.x, self.y = old_x, old_y
                    self.rect.center = (int(self.x), int(self.y))
                    if collided_wall_type == "internal" and not self.shield_active:
                        self.take_damage(10, self.crash_sound)
        self.rect.center = (int(self.x), int(self.y))

    def update(self, current_time, maze=None, enemies_group=None, ui_panel_width=0):
        if not self.alive:
            self.bullets_group.update()
            self.missiles_group.update()
            return
        cloak_duration = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        if self.is_cloaked and current_time >= self.cloak_end_time:
            self.is_cloaked = False
        if self.speed_boost_active and current_time >= self.speed_boost_end_time:
            self.speed_boost_active = False
            self.speed = self.base_speed
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None
        elif not self.speed_boost_active:
            self.speed = self.base_speed
        if self.shield_active and current_time >= self.shield_end_time:
            self.shield_active = False
            self.shield_duration = 0
            self.shield_is_co_effect_of_speed_boost = False
            if self.active_powerup_type == "shield": self.active_powerup_type = None
        if self.speed_boost_active:
            self.active_powerup_type = "speed_boost"
        elif self.shield_active and not self.shield_is_co_effect_of_speed_boost:
            self.active_powerup_type = "shield"
        elif not self.speed_boost_active and not self.shield_active :
            self.active_powerup_type = None
        self.update_movement(maze)
        half_w = self.rect.width / 2
        half_h = self.rect.height / 2
        game_area_left = ui_panel_width + half_w
        game_area_right = get_game_setting("WIDTH") - half_w
        game_area_top = half_h
        game_area_bottom = get_game_setting("HEIGHT") - half_h
        clamped = False
        if self.x < game_area_left: self.x = game_area_left; clamped = True
        elif self.x > game_area_right: self.x = game_area_right; clamped = True
        if self.y < game_area_top: self.y = game_area_top; clamped = True
        elif self.y > game_area_bottom: self.y = game_area_bottom; clamped = True
        if clamped:
            self.rect.center = (int(self.x), int(self.y))
        self.bullets_group.update()
        self.missiles_group.update()
        if self.shield_active:
            self.shield_visual_radius_factor = 1.0 + 0.1 * math.sin(current_time * 0.005)

    def get_raycast_endpoint(self, start_pos_tuple, direction_angle_degrees, max_range, maze_obj, step_size=3):
        """
        Raycasts from start_pos in a direction, stopping at the first wall or at max_range.
        Returns the pygame.math.Vector2 endpoint of where the ray visually stops.
        """
        start_pos = pygame.math.Vector2(start_pos_tuple)
        direction_rad = math.radians(direction_angle_degrees)
        
        final_end_point = pygame.math.Vector2(
            start_pos.x + math.cos(direction_rad) * max_range,
            start_pos.y + math.sin(direction_rad) * max_range
        )

        if not maze_obj:
            return final_end_point 

        current_pos = pygame.math.Vector2(start_pos) # Make a copy
        num_steps = int(max_range / step_size)
        if num_steps <= 0: num_steps = 1 # Ensure at least one check if max_range is small

        for i in range(num_steps + 1): # Iterate up to and including max_range distance
            # Calculate current point to check
            # For i=0, current_range is 0, current_check_pos is start_pos
            # For i=num_steps, current_range is max_range, current_check_pos is final_end_point
            current_range = i * step_size 
            if current_range > max_range: # Don't check beyond max_range
                current_range = max_range
            
            current_check_pos = pygame.math.Vector2(
                start_pos.x + math.cos(direction_rad) * current_range,
                start_pos.y + math.sin(direction_rad) * current_range
            )
            
            # Check if this point is inside a wall
            if maze_obj.is_wall(current_check_pos.x, current_check_pos.y, 2, 2): # Use a small 2x2 check area
                # Wall hit. If it's the very first check (i=0) and start_pos is in wall, return start_pos.
                if i == 0:
                    return start_pos 
                
                # Otherwise, the collision happened between the previous point and current_check_pos.
                # Return the previous clear point.
                prev_range = (i - 1) * step_size
                previous_clear_pos = pygame.math.Vector2(
                    start_pos.x + math.cos(direction_rad) * prev_range,
                    start_pos.y + math.sin(direction_rad) * prev_range
                )
                return previous_clear_pos
            
            if current_range >= max_range: # Reached max_range without hitting a wall (for this iteration)
                break 
                
        return final_end_point # No wall hit within max_range

    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time = pygame.time.get_ticks()
        can_fire_primary_component = (
            self.alive and
            current_time - self.last_shot_time >= self.current_shoot_cooldown and
            self.current_weapon_mode != get_game_setting("WEAPON_MODE_HEATSEEKER")
        )
        if can_fire_primary_component:
            tip_x, tip_y = self.get_tip_position()
            active_mode = self.current_weapon_mode
            fired_this_call = False
            raycast_step_size = 3 # Define step_size for raycasting checks, tune as needed

            if active_mode == get_game_setting("WEAPON_MODE_LIGHTNING"):
                closest_visible_enemy = None
                min_dist_to_visible_enemy_sq = float('inf') # Using squared distance for comparison efficiency
                
                zap_range = get_game_setting("LIGHTNING_ZAP_RANGE")
                if zap_range is None: zap_range = get_game_setting("TILE_SIZE") * 7

                if enemies_group and maze:
                    for enemy_sprite in enemies_group:
                        if enemy_sprite.alive:
                            enemy_center_vec = pygame.math.Vector2(enemy_sprite.rect.center)
                            tip_vec = pygame.math.Vector2(tip_x, tip_y)
                            
                            vector_to_enemy = enemy_center_vec - tip_vec
                            dist_to_enemy = vector_to_enemy.length()

                            if dist_to_enemy == 0 or dist_to_enemy > zap_range:
                                continue

                            angle_to_enemy_rad = math.atan2(vector_to_enemy.y, vector_to_enemy.x)
                            angle_to_enemy_deg = math.degrees(angle_to_enemy_rad)
                            
                            # Raycast towards the enemy up to the enemy's actual distance
                            ray_hit_point = self.get_raycast_endpoint(
                                (tip_x, tip_y),
                                angle_to_enemy_deg,
                                dist_to_enemy, 
                                maze,
                                step_size=raycast_step_size 
                            )
                            
                            # If the ray reached (or got very close to) the enemy, it's a clear shot
                            if ray_hit_point.distance_to(enemy_center_vec) < raycast_step_size * 1.5: # Tolerance
                                current_dist_sq = dist_to_enemy**2
                                if current_dist_sq < min_dist_to_visible_enemy_sq:
                                    min_dist_to_visible_enemy_sq = current_dist_sq
                                    closest_visible_enemy = enemy_sprite
                
                lightning_params = {
                    "origin_pos": (tip_x, tip_y),
                    "damage": get_game_setting("LIGHTNING_DAMAGE"),
                    "lifetime": get_game_setting("LIGHTNING_LIFETIME"),
                    "color": get_game_setting("LIGHTNING_COLOR"),
                    "owner": self,
                    "maze": maze
                }

                if closest_visible_enemy:
                    lightning_params["target_enemy"] = closest_visible_enemy
                else:
                    # No visible enemy, fire straight, stopping at walls
                    actual_end_point = self.get_raycast_endpoint(
                        (tip_x, tip_y), 
                        self.angle, # Player's current facing angle
                        zap_range, 
                        maze,
                        step_size=raycast_step_size
                    )
                    lightning_params["end_point"] = actual_end_point
                
                new_lightning_bullet = LightningBullet(**lightning_params)
                self.bullets_group.add(new_lightning_bullet)
                fired_this_call = True
            
            else: # Other bullet types
                bullet_fire_angles = [self.angle]
                current_bullet_base_speed = get_game_setting("PLAYER_BULLET_SPEED")
                current_bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                current_bullet_speed_val = current_bullet_base_speed
                bullet_bounces = 0
                bullet_pierces = 0
                rapid_modes_for_bullets = [
                    get_game_setting("WEAPON_MODE_RAPID_SINGLE"),
                    get_game_setting("WEAPON_MODE_RAPID_TRI"),
                    get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS")
                ]
                if active_mode in rapid_modes_for_bullets:
                    current_bullet_speed_val = current_bullet_base_speed * 1.5
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
                        size=self.current_bullet_size,
                        bounces=bullet_bounces,
                        pierce_count=bullet_pierces,
                        maze=maze,
                        owner=self
                    )
                    self.bullets_group.add(new_bullet)
                fired_this_call = True

            if fired_this_call:
                self.last_shot_time = current_time
                if sound:
                    sound.play()

        can_fire_missile_component = (
            self.alive and
            current_time - self.last_missile_shot_time >= self.current_missile_cooldown and
            self.current_weapon_mode in [
                get_game_setting("WEAPON_MODE_HEATSEEKER"),
                get_game_setting("WEAPON_MODE_HEATSEEKER_PLUS_BULLETS")
            ]
        )
        if can_fire_missile_component:
            fire_missile_anyway = (self.current_weapon_mode == get_game_setting("WEAPON_MODE_HEATSEEKER"))
            has_live_enemies = enemies_group and any(enemy.alive for enemy in enemies_group)
            if fire_missile_anyway or has_live_enemies:
                tip_x, tip_y = self.get_tip_position()
                current_missile_damage = get_game_setting("MISSILE_DAMAGE")
                effective_enemies_group = enemies_group if has_live_enemies else None
                new_missile = Missile(tip_x, tip_y, self.angle, effective_enemies_group, maze, damage=current_missile_damage)
                self.missiles_group.add(new_missile)
                self.last_missile_shot_time = current_time
                if missile_sound:
                    missile_sound.play()
                elif sound:
                    sound.play()

    def reset_active_powerups(self):
        self.shield_active = False; self.shield_duration = 0; self.shield_end_time = 0
        self.shield_is_co_effect_of_speed_boost = False
        self.speed_boost_active = False; self.speed_boost_duration = 0; self.speed_boost_end_time = 0
        self.speed = self.base_speed
        self.speed_boost_armed = False; self.armed_boost_duration = 0; self.armed_boost_multiplier = 0.0
        self.active_powerup_type = None
        self.is_cloaked = False

    def take_damage(self, amount, sound=None):
        if self.shield_active: return
        if self.is_cloaked: amount *= 1.5
        if self.alive:
            self.health -= amount
            if sound: sound.play()
            if self.health <= 0:
                self.health = 0
                self.alive = False

    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None):
        self.__init__(x, y, drone_id, drone_stats, drone_sprite_path, self.crash_sound, self.drone_system)
        self.x = x
        self.y = y
        self.angle = 0
        self.alive = True
        self.moving_forward = False
        if health_override is not None:
            self.health = min(health_override, self.max_health)
        self.rect.center = (int(self.x), int(self.y))

    def _draw_original_drone_shape(self, surface):
        s = self.size * 0.8
        p_nose = (s * 0.7, 0)
        p_wing_rt_front = (s * 0.1, -s * 0.4); p_wing_rt_rear = (-s * 0.5, -s * 0.25)
        p_wing_lt_front = (s * 0.1, s * 0.4); p_wing_lt_rear = (-s * 0.5, s * 0.25)
        p_tail_rt = (-s * 0.3, -s * 0.1); p_tail_lt = (-s * 0.3, s * 0.1)
        body_points_rel = [p_nose, p_wing_rt_front, p_wing_rt_rear, p_tail_rt, p_tail_lt, p_wing_lt_rear, p_wing_lt_front]
        cockpit_points_rel = [(s*0.35,0),(s*0.15,-s*0.1),(s*0.05,-s*0.08),(s*0.05,s*0.08),(s*0.15,s*0.1)]
        engine_glow_l_rel = (-s*0.35,s*0.15); engine_glow_r_rel = (-s*0.35,-s*0.15); engine_glow_radius = s*0.08
        angle_rad = math.radians(self.angle); cos_a = math.cos(angle_rad); sin_a = math.sin(angle_rad)
        def rt(p):
            x_r = p[0] * cos_a - p[1] * sin_a
            y_r = p[0] * sin_a + p[1] * cos_a
            return (x_r + self.x, y_r + self.y)
        body_abs = [rt(p) for p in body_points_rel]; cockpit_abs = [rt(p) for p in cockpit_points_rel]
        eng_l_abs = rt(engine_glow_l_rel); eng_r_abs = rt(engine_glow_r_rel)
        pygame.draw.polygon(surface, BLUE, body_abs); pygame.draw.polygon(surface, WHITE, body_abs, 2)
        pygame.draw.polygon(surface, CYAN, cockpit_abs); pygame.draw.polygon(surface, WHITE, cockpit_abs, 1)
        pygame.draw.circle(surface, CYAN, (int(eng_l_abs[0]), int(eng_l_abs[1])), int(engine_glow_radius))
        pygame.draw.circle(surface, CYAN, (int(eng_r_abs[0]), int(eng_r_abs[1])), int(engine_glow_radius))

    def draw(self, surface):
        if not self.alive and not self.bullets_group and not self.missiles_group:
            return
        if self.alive:
            cloak_alpha_setting = get_game_setting("PHANTOM_CLOAK_ALPHA")
            current_alpha = cloak_alpha_setting if self.is_cloaked else 255
            if not self.original_image:
                if self.is_cloaked:
                    temp_draw_size = int(self.size * 2.2)
                    temp_surf = pygame.Surface((temp_draw_size, temp_draw_size), pygame.SRCALPHA)
                    ox, oy = self.x, self.y
                    self.x, self.y = temp_surf.get_width() / 2, temp_surf.get_height() / 2
                    self._draw_original_drone_shape(temp_surf)
                    self.x, self.y = ox, oy
                    temp_surf.set_alpha(current_alpha)
                    surface.blit(temp_surf, temp_surf.get_rect(center=(int(self.x), int(self.y))))
                else:
                    self._draw_original_drone_shape(surface)
            else:
                rot_img = pygame.transform.rotate(self.original_image, -self.angle)
                if self.is_cloaked:
                    img_to_blit = rot_img.copy()
                    img_to_blit.set_alpha(current_alpha)
                else:
                    img_to_blit = rot_img
                surface.blit(img_to_blit, img_to_blit.get_rect(center=self.rect.center))
            if self.speed_boost_active and self.moving_forward:
                s = self.size * 0.8
                angle_rad = math.radians(self.angle); cos_a = math.cos(angle_rad); sin_a = math.sin(angle_rad)
                def rt(p): x_r=p[0]*cos_a-p[1]*sin_a; y_r=p[0]*sin_a+p[1]*cos_a; return(x_r+self.x,y_r+self.y)
                flame_len = self.size * 0.8 * random.uniform(0.8, 1.2); flame_w = self.size * 0.4
                fl_tip = (-s * 0.5 - flame_len, 0); fl_b1 = (-s * 0.45, flame_w / 2); fl_b2 = (-s * 0.45, -flame_w / 2)
                pygame.draw.polygon(surface, ORANGE, [rt(p) for p in [fl_tip, fl_b1, fl_b2]])
                pygame.draw.polygon(surface, YELLOW, [rt((-s*0.5-flame_len*0.6,0)),rt((-s*0.45,flame_w/3)),rt((-s*0.45,-flame_w/3))])
            if self.shield_active:
                powerup_types_info = get_game_setting("POWERUP_TYPES")
                shield_info = {}
                if isinstance(powerup_types_info, dict):
                    shield_info = powerup_types_info.get("shield", {})
                shield_base_color = shield_info.get("color", LIGHT_BLUE)
                shield_alpha_color = (*shield_base_color[:3], 100)
                shield_radius_base = max(self.rect.width, self.rect.height) * 0.65
                shield_radius_animated = int(shield_radius_base * self.shield_visual_radius_factor)
                shield_surface_diameter = shield_radius_animated * 2
                if shield_surface_diameter > 0:
                    shield_surf = pygame.Surface((shield_surface_diameter, shield_surface_diameter), pygame.SRCALPHA)
                    pygame.draw.circle(shield_surf, shield_alpha_color,
                                       (shield_radius_animated, shield_radius_animated), shield_radius_animated)
                    surface.blit(shield_surf, shield_surf.get_rect(center=self.rect.center))

        for bullet in self.bullets_group:
            bullet.draw(surface)

        self.missiles_group.draw(surface)