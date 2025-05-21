import pygame
import math
import os # For os.path.exists

# Corrected import to use 'game_settings.py'
from game_settings import (
    PLAYER_SPEED, PLAYER_MAX_HEALTH, WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT, TILE_SIZE,
    GREEN, YELLOW, RED, BLACK, BLUE, CYAN, WHITE, LIGHT_BLUE, ORANGE, # Added ORANGE for consistency
    ROTATION_SPEED, # Added missing import for ROTATION_SPEED
    PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN, # For weapon cooldowns
    POWERUP_TYPES, PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
    PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BIG_BULLET_SIZE,
    WEAPON_MODES_SEQUENCE, INITIAL_WEAPON_MODE, WEAPON_MODE_ICONS, # For weapon system
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES,
    MISSILE_COOLDOWN, MISSILE_DAMAGE, MISSILE_COLOR, # For missile weapon
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, LIGHTNING_COLOR, # For lightning
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, # Specific weapon mode constants
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING,
    PHANTOM_CLOAK_ALPHA_SETTING, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS,
    SHIELD_POWERUP_DURATION, SPEED_BOOST_POWERUP_DURATION, # For powerup durations
    get_game_setting # To fetch current settings if needed elsewhere
)
# Assuming bullet.py contains Bullet, Missile and LightningZap classes
try:
    from bullet import Bullet, Missile, LightningZap
except ImportError:
    print("Warning (player.py): Could not import Bullet, Missile, or LightningZap from bullet.py. Shooting will be affected.")
    # Define dummy classes if bullet.py or specific classes are not found
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass

from base_drone import BaseDrone # Assuming base_drone.py is accessible

class Drone(BaseDrone):
    # Updated __init__ to accept all parameters from game_loop.py
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound=None, drone_system=None):
        # Get base speed from drone_stats for BaseDrone's __init__
        # Provide a fallback to PLAYER_SPEED if "speed" is not in drone_stats
        base_speed_from_stats = drone_stats.get("speed", PLAYER_SPEED)
        super().__init__(x, y, speed=base_speed_from_stats) # Pass speed to BaseDrone

        self.drone_id = drone_id
        self.drone_system = drone_system # Store reference to DroneSystem

        # Initialize attributes based on drone_stats
        self.base_hp = drone_stats.get("hp", PLAYER_MAX_HEALTH)
        # self.base_speed is already handled by super().__init__ via base_speed_from_stats
        self.base_turn_speed = drone_stats.get("turn_speed", ROTATION_SPEED) # Use ROTATION_SPEED as fallback
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)


        self.max_health = self.base_hp
        self.health = self.max_health
        # self.speed is set by BaseDrone's __init__
        self.current_speed = self.speed # current_speed can be modified by power-ups
        self.rotation_speed = self.base_turn_speed # Player's specific rotation speed

        # Sprite loading
        self.original_image = None # Will hold the unrotated base image
        self.image = None          # The current image to be drawn (potentially rotated/alpha-modified)
        # self.rect is initialized by BaseDrone, but _load_sprite will update it based on actual image size
        self._load_sprite(drone_sprite_path) # Load the drone's visual sprite

        # Weapon system initialization
        # Use get_game_setting to ensure INITIAL_WEAPON_MODE is current if settings can change
        initial_weapon_mode_setting = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_setting)
        except ValueError: # Fallback if initial mode not in sequence
            print(f"Warning: Initial weapon mode '{initial_weapon_mode_setting}' not in sequence. Defaulting to first.")
            self.weapon_mode_index = 0
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]

        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.lightning_zaps_group = pygame.sprite.Group()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0

        # Cooldowns and bullet properties are set by _update_weapon_attributes
        self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN # Will be updated
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") # Get from settings
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") # Get from settings
        self.bullet_size = PLAYER_DEFAULT_BULLET_SIZE # Will be updated
        self._update_weapon_attributes() # Set initial weapon stats correctly

        # Power-ups / Abilities
        self.active_powerup_type = None
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION")
        # Ensure self.rect exists before accessing its width for shield_visual_radius
        self.shield_visual_radius = (self.rect.width // 2 + 5) if self.rect else (TILE_SIZE // 2 + 5)
        self.shield_pulse_angle = 0 # For shield pulsing animation

        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.speed_boost_multiplier = 1.0 # Set by power-up details
        self.original_speed_before_boost = self.speed # Store base speed

        self.cloak_active = False
        self.cloak_start_time = 0
        self.cloak_end_time = 0
        self.last_cloak_activation_time = -float('inf') # Initialize to allow immediate first cloak
        self.cloak_cooldown_end_time = 0
        self.is_cloaked_visual = False # For drawing with alpha
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING")
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")

        self.crash_sound = crash_sound

        # Collision rectangle, based on loaded sprite's rect
        # BaseDrone initializes a collision_rect, we might refine it here after sprite load
        if self.rect: # Ensure self.rect is set by _load_sprite
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: # Fallback if rect somehow not set (should not happen)
            self.collision_rect = pygame.Rect(self.x - TILE_SIZE*0.35, self.y - TILE_SIZE*0.35, TILE_SIZE*0.7, TILE_SIZE*0.7)


    def _load_sprite(self, sprite_path):
        """Loads the drone's visual sprite and updates self.image and self.rect."""
        # Default size for the sprite, e.g., 80% of a tile
        # This size should be appropriate for your game's visual scale.
        default_sprite_size = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))

        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, default_sprite_size)
            except pygame.error as e:
                print(f"Player Log: Error loading sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None # Flag to use default drawing
        else:
            if sprite_path: print(f"Player Log: Sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None: # Create a default colored shape if no sprite
            self.original_image = pygame.Surface(default_sprite_size, pygame.SRCALPHA)
            # Example: A simple green triangle pointing right (consistent with 0 angle)
            # points = [(default_sprite_size[0], default_sprite_size[1] // 2), (0, 0), (0, default_sprite_size[1])]
            # pygame.draw.polygon(self.original_image, GREEN, points)
            # For consistency with detailed draw, use a placeholder color for now.
            # The detailed draw method will take over if original_image is complex.
            # If using the simple draw from BaseDrone, this fill will be used.
            self.original_image.fill((*GREEN, 180)) # Semi-transparent green
            pygame.draw.circle(self.original_image, WHITE, (default_sprite_size[0]//2, default_sprite_size[1]//2), default_sprite_size[0]//3, 2)


        self.image = self.original_image.copy() # Start with a copy for manipulations
        # Update self.rect based on the loaded image and current position (self.x, self.y from BaseDrone)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        # Update collision_rect based on the new self.rect from the loaded sprite
        self.collision_rect_width = self.rect.width * 0.7
        self.collision_rect_height = self.rect.height * 0.7
        self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center


    def _update_weapon_attributes(self):
        """Sets weapon parameters (cooldown, bullet size) based on the current weapon mode."""
        # Use get_game_setting for all constants to ensure current values are used
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 # Slower for big shot
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        else: # Default, Tri-shot, Bounce, Pierce
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")

        # Apply the drone's inherent fire rate multiplier
        if self.base_fire_rate_multiplier != 0: # Avoid division by zero
            self.current_shoot_cooldown /= self.base_fire_rate_multiplier
            self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / self.base_fire_rate_multiplier
            self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / self.base_fire_rate_multiplier
        else: # Fallback if fire rate multiplier is zero (should not happen with valid configs)
            self.current_shoot_cooldown = 99999 # Effectively disable shooting
            self.current_missile_cooldown = 99999
            self.current_lightning_cooldown = 99999

    def get_position(self):
        return self.x, self.y

    # This method overrides the one in BaseDrone.py if BaseDrone has one.
    # Ensures player rotation is CCW for "left" key.
    def rotate(self, direction, rotation_speed_override=None):
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed
        if direction == "left":  # Turn Counter-Clockwise
            self.angle -= effective_rotation_speed
        elif direction == "right":  # Turn Clockwise
            self.angle += effective_rotation_speed
        self.angle %= 360

    def handle_input(self, keys): # Usually called by EventManager or GameController
        if keys[pygame.K_LEFT]:
            self.rotate("left")
        if keys[pygame.K_RIGHT]:
            self.rotate("right")

    def update(self, current_time, maze, enemies_group, game_area_x_offset=0):
        if not self.alive:
            return

        # Movement is handled by BaseDrone's update_movement or an override here
        # BaseDrone.update_movement uses self.moving_forward, self.angle, self.current_speed
        # Ensure self.current_speed is updated by powerups before this call
        self.update_powerups(current_time) # Update powerup states and current_speed first

        # Call the movement logic from BaseDrone (or this class if overridden)
        # BaseDrone.update_movement needs access to self.current_speed for movement calculation
        # We can pass it or ensure BaseDrone uses self.current_speed if it exists, else self.speed
        # For now, let's assume BaseDrone.update_movement uses self.speed, and we update self.speed for boosts.
        # A better way is for BaseDrone.update_movement to use a speed argument or self.current_speed.
        # Let's assume BaseDrone.update_movement uses self.speed.
        # So, if speed_boost_active, self.speed (from BaseDrone) should be the boosted speed.
        # This is handled by self.activate_powerup and self.update_powerups.

        super().update_movement(maze, game_area_x_offset) # Call BaseDrone's movement

        # Projectile updates
        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset)
        self.lightning_zaps_group.update(current_time) # Pass current_time for effects

        # Visual updates (image rotation and alpha for cloak)
        current_alpha = self.phantom_cloak_alpha if self.is_cloaked_visual else 255
        if self.original_image:
            # Pygame's rotate is CCW for positive angles. Our self.angle is CCW positive.
            # To make the sprite point in the direction of self.angle (where 0 is right),
            # we need to rotate by -self.angle.
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle)
            self.image = rotated_image.convert_alpha() # Ensure it handles transparency
            self.image.set_alpha(current_alpha)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect: # Update collision rect if it exists
                self.collision_rect.center = self.rect.center
        else: # Fallback if original_image didn't load (should be handled by _load_sprite)
            if self.rect: self.rect.center = (int(self.x), int(self.y))


    def _update_movement(self, maze, game_area_x_offset):
        """
        Player-specific movement logic, if different from BaseDrone.
        For now, this can be identical to BaseDrone's or call super().
        This is overridden here to ensure it uses self.current_speed.
        """
        if self.moving_forward and self.alive:
            angle_rad = math.radians(self.angle)
            # Use self.current_speed which accounts for speed boosts
            dx = math.cos(angle_rad) * self.current_speed # 0 angle is right
            dy = math.sin(angle_rad) * self.current_speed # Positive angle is CCW

            next_x = self.x + dx
            next_y = self.y + dy
            
            temp_collision_rect = self.collision_rect.copy()
            temp_collision_rect.center = (next_x, next_y)

            collided_wall_type = None
            if maze:
                collided_wall_type = maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                                self.collision_rect_width, self.collision_rect_height)

            if collided_wall_type:
                self._handle_wall_collision(collided_wall_type, dx, dy)
            else:
                self.x = next_x
                self.y = next_y

        # Boundary checks
        half_col_width = self.collision_rect_width / 2
        half_col_height = self.collision_rect_height / 2
        min_x_bound = game_area_x_offset + half_col_width
        max_x_bound = get_game_setting("WIDTH") - half_col_width
        min_y_bound = half_col_height
        max_y_bound = get_game_setting("GAME_PLAY_AREA_HEIGHT") - half_col_height

        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))

        if self.rect: self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect: self.collision_rect.center = (int(self.x), int(self.y))


    def _handle_wall_collision(self, wall_type, dx, dy):
        """Player's response to hitting a wall."""
        # Take damage only if not shielded and it's an "internal" wall (or any wall if desired)
        if not self.shield_active: # (wall_type == "internal" or wall_type) # Example condition
            self.take_damage(10, self.crash_sound) # Damage amount can be a constant

        # Simple stop: prevent further movement into the wall this frame
        # More complex: bounce or slide
        self.moving_forward = False # Stop thrust
        # Optionally, revert position slightly if stuck
        # self.x -= dx * 0.1
        # self.y -= dy * 0.1


    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time = pygame.time.get_ticks()
        can_shoot_primary = (current_time - self.last_shot_time) > self.current_shoot_cooldown
        can_shoot_missile = (current_time - self.last_missile_shot_time) > self.current_missile_cooldown
        can_shoot_lightning = (current_time - self.last_lightning_time) > self.current_lightning_cooldown

        # Calculate bullet origin (tip of the drone)
        # Use self.rect.height or a fixed offset. Assume self.rect is valid.
        nose_offset_factor = (self.rect.height / 2 if self.rect else TILE_SIZE * 0.4) * 0.7 # Offset from center
        rad_angle_shoot = math.radians(self.angle) # Current facing angle
        # For 0 angle = right: cos for x, sin for y
        bullet_start_x = self.x + math.cos(rad_angle_shoot) * nose_offset_factor
        bullet_start_y = self.y + math.sin(rad_angle_shoot) * nose_offset_factor

        # Primary bullet firing
        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]:
            if can_shoot_primary:
                if sound: sound.play()
                self.last_shot_time = current_time
                angles_to_fire = [0] # Default single shot
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI:
                    angles_to_fire = [-15, 0, 15]

                for angle_offset in angles_to_fire:
                    effective_bullet_angle = self.angle + angle_offset
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                    current_bullet_damage = 10 * self.bullet_damage_multiplier # Base damage 10
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
                        current_bullet_damage *= 2.5

                    max_b = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES") if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0
                    max_p = get_game_setting("PIERCING_BULLET_MAX_PIERCES") if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0

                    new_bullet = Bullet(bullet_start_x, bullet_start_y, effective_bullet_angle,
                                        bullet_speed, bullet_lifetime, self.bullet_size, bullet_color,
                                        current_bullet_damage, max_b, max_p)
                    self.bullets_group.add(new_bullet)

        # Heatseeker Missiles
        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or \
           self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if can_shoot_missile:
                if missile_sound: missile_sound.play()
                self.last_missile_shot_time = current_time
                missile_dmg = get_game_setting("MISSILE_DAMAGE") * self.bullet_damage_multiplier
                new_missile = Missile(bullet_start_x, bullet_start_y, self.angle, missile_dmg, enemies_group)
                self.missiles_group.add(new_missile)

        # Lightning
        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if can_shoot_lightning:
                if sound: sound.play() # Or specific lightning sound
                self.last_lightning_time = current_time
                target_enemy_pos = None
                if enemies_group:
                    # Find closest enemy within LIGHTNING_ZAP_RANGE
                    closest_enemy = None; min_dist_sq = float('inf')
                    zap_range_sq = get_game_setting("LIGHTNING_ZAP_RANGE") ** 2
                    for enemy in enemies_group:
                        if not enemy.alive: continue
                        dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
                        if dist_sq < zap_range_sq and dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq; closest_enemy = enemy
                    if closest_enemy: target_enemy_pos = closest_enemy.rect.center
                
                lightning_dmg = get_game_setting("LIGHTNING_DAMAGE") * self.bullet_damage_multiplier
                # LightningZap start_pos should be player's center or weapon tip
                new_zap = LightningZap(self.rect.center, target_enemy_pos, lightning_dmg, get_game_setting("LIGHTNING_LIFETIME"))
                self.lightning_zaps_group.add(new_zap)


    def take_damage(self, amount, sound=None):
        if not self.alive: return
        if self.shield_active:
            if amount > 0 and sound: sound.play() # Play sound even if shielded
            return

        self.health -= amount
        if sound: sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw_health_bar(self, surface):
        if not self.alive or not self.rect: return

        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3

        health_percentage = max(0, self.health / self.max_health)
        filled_width = bar_width * health_percentage

        pygame.draw.rect(surface, (80,0,0) if health_percentage < 0.3 else (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED
        if health_percentage >= 0.6: fill_color = GREEN
        elif health_percentage >= 0.3: fill_color = YELLOW
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def activate_shield(self, duration_ms, is_from_speed_boost=False):
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration_ms
        self.shield_duration = duration_ms # Store for UI or reference
        if not is_from_speed_boost: # Only set as primary if not a co-effect
            self.active_powerup_type = "shield"

    def arm_speed_boost(self, duration_ms, multiplier_val):
        self.speed_boost_duration = duration_ms
        self.speed_boost_multiplier = multiplier_val
        self.active_powerup_type = "speed_boost" # Mark as armed

    def attempt_speed_boost_activation(self): # Called when player starts moving
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.original_speed_before_boost = self.speed # Store current base speed (from BaseDrone)
            self.current_speed = self.speed * self.speed_boost_multiplier # Apply boost to current_speed
            # Activate a co-shield with speed boost
            co_shield_duration = self.speed_boost_duration // 2 # Example: half the boost duration
            self.activate_shield(co_shield_duration, is_from_speed_boost=True)

    def try_activate_cloak(self, current_time_ms):
        if self.special_ability == "phantom_cloak" and \
           not self.cloak_active and \
           current_time_ms > self.cloak_cooldown_end_time: # Check cooldown
            self.cloak_active = True
            self.is_cloaked_visual = True # For drawing with alpha
            self.cloak_start_time = current_time_ms
            self.cloak_end_time = current_time_ms + self.phantom_cloak_duration_ms
            # Cooldown starts after cloak *ends*
            # self.last_cloak_activation_time = current_time_ms # Not strictly needed if cooldown starts on end
            print(f"Player: Cloak ON at {current_time_ms}, ends {self.cloak_end_time}")
            return True
        # print(f"Player: Cloak FAILED. Active: {self.cloak_active}, Cooldown ends: {self.cloak_cooldown_end_time}, Current: {current_time_ms}")
        return False

    def cycle_weapon_state(self, force_cycle=True):
        if not WEAPON_MODES_SEQUENCE: return False
        if not force_cycle and self.weapon_mode_index == len(WEAPON_MODES_SEQUENCE) - 1:
            return False # At last weapon, don't cycle unless forced

        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes()
        print(f"Player: Weapon cycled to {WEAPON_MODE_NAMES.get(self.current_weapon_mode, 'Unknown')}")
        return True

    def update_powerups(self, current_time_ms):
        # Shield
        if self.shield_active and current_time_ms > self.shield_end_time:
            self.shield_active = False
            if self.active_powerup_type == "shield": self.active_powerup_type = None

        # Speed Boost
        if self.speed_boost_active and current_time_ms > self.speed_boost_end_time:
            self.speed_boost_active = False
            self.current_speed = self.speed # Revert to base speed (from BaseDrone, which is original_speed_before_boost)
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None

        # Cloak
        if self.cloak_active and current_time_ms > self.cloak_end_time:
            self.cloak_active = False
            self.is_cloaked_visual = False
            self.cloak_cooldown_end_time = current_time_ms + self.phantom_cloak_cooldown_ms
            print(f"Player: Cloak OFF at {current_time_ms}, cooldown until {self.cloak_cooldown_end_time}")


    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None):
        # Re-initialize with new drone data, calling BaseDrone's __init__ via super()
        base_speed_from_stats = drone_stats.get("speed", PLAYER_SPEED)
        super().__init__(x, y, speed=base_speed_from_stats) # Re-call BaseDrone's init

        self.drone_id = drone_id
        # self.drone_system is set in __init__ and should persist unless new one is passed

        self.base_hp = drone_stats.get("hp", PLAYER_MAX_HEALTH)
        self.base_turn_speed = drone_stats.get("turn_speed", ROTATION_SPEED)
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)

        self.max_health = self.base_hp
        self.health = health_override if health_override is not None else self.max_health

        # self.speed is set by BaseDrone's __init__ to base_speed_from_stats
        self.current_speed = self.speed # Reset current_speed to the (potentially new) base speed
        self.rotation_speed = self.base_turn_speed

        self._load_sprite(drone_sprite_path) # Reload sprite and update rect based on new drone

        # Reset weapon state to initial for the drone
        initial_weapon_mode_setting = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_setting)
        except ValueError: self.weapon_mode_index = 0
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes() # Apply attributes for this weapon mode

        self.bullets_group.empty()
        self.missiles_group.empty()
        self.lightning_zaps_group.empty()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0

        self.reset_active_powerups() # Clear all active powerups and ability states

    def reset_active_powerups(self):
        self.shield_active = False; self.shield_end_time = 0
        self.speed_boost_active = False; self.speed_boost_end_time = 0
        self.current_speed = self.speed # Reset current_speed to the base speed of the current drone
        self.original_speed_before_boost = self.speed # Update this as well

        self.cloak_active = False; self.is_cloaked_visual = False; self.cloak_end_time = 0
        # Cooldown for cloak should persist unless explicitly reset by game design
        # self.cloak_cooldown_end_time = 0 # Uncomment to reset cloak cooldown on player death/reset

        self.active_powerup_type = None


    def draw(self, surface):
        if not self.alive and not (self.bullets_group or self.missiles_group or self.lightning_zaps_group):
            return # Don't draw if dead and no projectiles active

        if self.alive and self.image: # Player itself
            surface.blit(self.image, self.rect) # self.image is rotated and alpha-set in update()
            if self.shield_active: # Draw shield visual
                current_time_ticks = pygame.time.get_ticks()
                pulse = abs(math.sin(current_time_ticks * 0.005 + self.shield_pulse_angle))
                alpha = int(50 + pulse * 70)
                shield_base_color = POWERUP_TYPES.get("shield", {}).get("color", LIGHT_BLUE)
                shield_draw_color = (*shield_base_color[:3], alpha)
                for i in range(1, 4):
                    pygame.draw.circle(surface, shield_draw_color, self.rect.center,
                                     int(self.shield_visual_radius + i * 2 - pulse * 3), 2)
        
        # Draw projectiles
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        self.lightning_zaps_group.draw(surface)

        if self.alive: # Health bar only if alive
            self.draw_health_bar(surface)


# Minimal main for testing player.py standalone
if __name__ == '__main__':
    pygame.init()
    # Ensure WIDTH and HEIGHT are available, e.g. from game_settings or defined here for test
    try:
        from game_settings import WIDTH as SCREEN_WIDTH, HEIGHT as SCREEN_HEIGHT, FPS as GAME_FPS
        from game_settings import PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED, PLAYER_DEFAULT_BULLET_SIZE
        from game_settings import INITIAL_WEAPON_MODE, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS, PHANTOM_CLOAK_ALPHA_SETTING
    except ImportError: # Fallbacks for standalone test
        SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600; GAME_FPS = 60
        PLAYER_MAX_HEALTH, PLAYER_SPEED, ROTATION_SPEED, PLAYER_DEFAULT_BULLET_SIZE = 100,3,5,4
        INITIAL_WEAPON_MODE = 0; PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS, PHANTOM_CLOAK_ALPHA_SETTING = 5000,15000,70


    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Player Drone Test")

    class MockSound:
        def play(self): pass
    mock_crash_sound = MockSound()
    mock_shoot_sound = MockSound()
    mock_missile_sound = MockSound()

    # For testing, we need a dummy drone_stats and drone_system
    mock_drone_stats = {
        "hp": PLAYER_MAX_HEALTH, "speed": PLAYER_SPEED, "turn_speed": ROTATION_SPEED,
        "fire_rate_multiplier": 1.0, "special_ability": "phantom_cloak", # Test with cloak
        "bullet_damage_multiplier": 1.0
    }
    mock_drone_id = "TEST_PHANTOM"
    # Provide a placeholder path or ensure an image exists for testing
    mock_sprite_path = os.path.join("assets", "drones", "phantom_2d.png") # Example
    if not os.path.exists(mock_sprite_path):
        print(f"Test Warning: Sprite {mock_sprite_path} not found, will use fallback.")
        mock_sprite_path = None


    player_drone = Drone(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                         mock_drone_id, mock_drone_stats, mock_sprite_path,
                         mock_crash_sound, None) # drone_system can be None for this test

    clock = pygame.time.Clock()
    running = True

    class MockMaze:
        def is_wall(self, x, y, width, height): return False
    mock_maze = MockMaze()
    mock_enemies_group = pygame.sprite.Group()

    while running:
        current_tick_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP: player_drone.moving_forward = True
                if event.key == pygame.K_DOWN: player_drone.moving_forward = False
                if event.key == pygame.K_SPACE: player_drone.shoot(mock_shoot_sound, mock_missile_sound, mock_maze, mock_enemies_group)
                if event.key == pygame.K_c: player_drone.try_activate_cloak(current_tick_time)
                if event.key == pygame.K_s: player_drone.cycle_weapon_state()
                if event.key == pygame.K_h: player_drone.take_damage(20) # Test damage
                if event.key == pygame.K_p: # Test shield powerup
                    player_drone.activate_shield(5000) # 5 sec shield
                if event.key == pygame.K_o: # Test speed boost (arm it)
                    player_drone.arm_speed_boost(3000, 2.0) # 3 sec, 2x speed


            if event.type == pygame.KEYUP:
                 if event.key == pygame.K_UP: player_drone.moving_forward = False

        keys = pygame.key.get_pressed()
        player_drone.handle_input(keys)

        player_drone.update(current_tick_time, mock_maze, mock_enemies_group)

        screen.fill(BLACK)
        player_drone.draw(screen)
        pygame.display.flip()
        clock.tick(GAME_FPS)

    pygame.quit()