import pygame
import math
import os
import random 

import game_settings as gs 
from game_settings import (
    TILE_SIZE, WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT,
    WEAPON_MODES_SEQUENCE, INITIAL_WEAPON_MODE,
    PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BIG_BULLET_SIZE,
    PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN,
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES,
    MISSILE_COOLDOWN, MISSILE_DAMAGE,
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING, POWERUP_TYPES, 
    PHANTOM_CLOAK_ALPHA_SETTING, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS,
    GREEN, YELLOW, RED, WHITE, LIGHT_BLUE, ORANGE, CYAN, ELECTRIC_BLUE, 
    PLAYER_SPEED, PLAYER_MAX_HEALTH, ROTATION_SPEED, 
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, 
    MISSILE_COLOR, 
    LIGHTNING_COLOR, CORE_FRAGMENT_DETAILS,
    SPEED_BOOST_POWERUP_DURATION, SHIELD_POWERUP_DURATION, 
    FLAME_COLORS, 
    THRUST_PARTICLE_SPREAD_ANGLE, 
    THRUST_PARTICLE_LIFETIME_BLAST,
    THRUST_PARTICLE_START_SIZE_BLAST_MIN,
    THRUST_PARTICLE_START_SIZE_BLAST_MAX,
    THRUST_PARTICLE_SPEED_MIN_BLAST,
    THRUST_PARTICLE_SPEED_MAX_BLAST,
    THRUST_PARTICLE_SHRINK_RATE_BLAST,
    get_game_setting 
)
try:
    from .bullet import Bullet, Missile, LightningZap 
    from .particle import Particle 
except ImportError:
    print("Warning (player.py): Could not import Bullet, Missile, LightningZap or Particle. Effects will be affected.")
    # Minimal placeholder if these classes are not found (should not happen in full project)
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass
    class Particle(pygame.sprite.Sprite): pass


try:
    from .base_drone import BaseDrone 
except ImportError:
    print("Warning (player.py): Could not import BaseDrone from .base_drone. Player class might not function correctly.")
    # Minimal placeholder for BaseDrone if not found
    class BaseDrone(pygame.sprite.Sprite): 
        def __init__(self, x,y,speed, size=None): 
            super().__init__()
            self.x = x
            self.y = y
            self.speed = speed 
            self.angle = 0.0 
            self.moving_forward = False
            self.alive = True
            self.size = size if size is not None else TILE_SIZE * 0.8
            self.rect = pygame.Rect(x - self.size / 2, y - self.size / 2, self.size, self.size) 
            self.collision_rect = self.rect.copy()
        
        def update_movement(self, maze=None, game_area_x_offset=0):
            # This is a simplified placeholder movement logic.
            # The actual BaseDrone has more detailed boundary checks.
            if self.moving_forward and self.alive:
                angle_rad = math.radians(self.angle)
                dx = math.cos(angle_rad) * self.speed 
                dy = math.sin(angle_rad) * self.speed
                next_x = self.x + dx
                next_y = self.y + dy

                collided = False
                if maze and self.collision_rect: # Check if maze and collision_rect exist
                    temp_collision_rect = self.collision_rect.copy()
                    temp_collision_rect.center = (next_x, next_y)
                    # Use the maze's is_wall method for collision
                    if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery, 
                                    self.collision_rect.width, self.collision_rect.height):
                        collided = True
                
                if not collided:
                    self.x = next_x
                    self.y = next_y
                else:
                    # Stop movement on collision for this placeholder
                    self.moving_forward = False 

            # Boundary checks (simplified for placeholder)
            if self.collision_rect and self.rect: # Ensure rects exist
                half_col_width = self.collision_rect.width / 2
                half_col_height = self.collision_rect.height / 2
                min_x_bound = game_area_x_offset + half_col_width
                max_x_bound = WIDTH - half_col_width
                min_y_bound = half_col_height
                max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height
                self.x = max(min_x_bound, min(self.x, max_x_bound))
                self.y = max(min_y_bound, min(self.y, max_y_bound))
                self.rect.center = (int(self.x), int(self.y))
                self.collision_rect.center = self.rect.center


class PlayerDrone(BaseDrone): # Renamed from Drone to PlayerDrone for clarity
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound, drone_system): 
        base_speed_from_stats = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.drone_visual_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) # Default visual size
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats) 
        
        self.drone_id = drone_id 
        self.drone_system = drone_system  # Store reference to DroneSystem
        
        self.x = float(x) # Ensure position is float for smooth movement
        self.y = float(y) 
        
        # Apply base stats from the provided drone_stats dictionary
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH")) 
        self.base_speed = base_speed_from_stats
        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED")) 
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0) 
        self.special_ability = drone_stats.get("special_ability")  # e.g., "phantom_cloak", "omega_boost"
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0) # Multiplier for bullet damage

        self.max_health = self.base_hp 
        self.health = self.max_health 
        self.current_speed = self.speed  # Current speed can be modified by power-ups
        self.rotation_speed = self.base_turn_speed 
        
        self.original_image = None # Will hold the loaded, unrotated sprite
        self.image = None # Will hold the currently rotated sprite for drawing
        self._load_sprite(drone_sprite_path)  # Load and scale the drone's visual sprite


        # Weapon system initialization
        initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            print(f"Warning (player.py): Initial weapon mode {initial_weapon_mode_gs} not in sequence. Defaulting.")
            self.weapon_mode_index = 0 # Default to the first weapon in the sequence
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index] 

        self.bullets_group = pygame.sprite.Group() # For standard bullets
        self.missiles_group = pygame.sprite.Group() # For heatseeker missiles
        self.lightning_zaps_group = pygame.sprite.Group() # For chain lightning
        self.last_shot_time = 0 # Timestamp of the last primary weapon shot
        self.last_missile_shot_time = 0 # Timestamp for missile cooldown
        self.last_lightning_time = 0 # Timestamp for lightning cooldown
        self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") 
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") 
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") 
        self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE") 
        self._update_weapon_attributes() # Set initial weapon stats

        # Power-up states
        self.active_powerup_type = None # Tracks the type of the currently active timed power-up (e.g., "shield", "speed_boost")
        self.shield_active = False 
        self.shield_end_time = 0 
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION")  # Duration from settings
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) # For shield visual effect

        self.speed_boost_active = False 
        self.speed_boost_end_time = 0 
        self.speed_boost_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION") 
        self.speed_boost_multiplier = POWERUP_TYPES.get("speed_boost", {}).get("multiplier", 1.8)
        self.original_speed_before_boost = self.speed # Store original speed to revert after boost
        self.shield_tied_to_speed_boost = False # If shield is activated as part of speed boost

        # Thrust particle effects
        self.thrust_particles = pygame.sprite.Group() 
        self.thrust_particle_spawn_timer = 0
        self.THRUST_PARTICLE_SPAWN_INTERVAL = 25 # Milliseconds between particle emissions
        self.PARTICLES_PER_EMISSION = random.randint(2, 4) # Number of particles per emission
        self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4 # Distance from center to flame ports

        # Cloak ability states (for Phantom drone)
        self.cloak_active = False # Is the cloak ability currently in effect?
        self.cloak_start_time = 0  # When the current cloak started
        self.cloak_end_time = 0 # When the current cloak effect will end
        self.last_cloak_activation_time = -float('inf')  # Ensure cloak can be used at game start
        self.cloak_cooldown_end_time = 0  # When the cloak ability can be used again
        self.is_cloaked_visual = False  # Controls the visual transparency
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING") 
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS") 
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS") 

        self.crash_sound = crash_sound # Sound effect for collisions
        
        # Initialize collision rectangle based on the visual rect
        if self.rect: 
            self.collision_rect_width = self.rect.width * 0.7 # Collision box is smaller than visual
            self.collision_rect_height = self.rect.height * 0.7 
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height) 
            self.collision_rect.center = self.rect.center 
        else: # Fallback if self.rect wasn't initialized (should not happen with _load_sprite)
            col_size = self.size * 0.7 
            self.collision_rect_width = col_size
            self.collision_rect_height = col_size
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2, 
                                               col_size, col_size)

    def _load_sprite(self, sprite_path): 
        """Loads and scales the drone's visual sprite."""
        default_size = self.drone_visual_size 
        loaded_successfully = False
        if sprite_path and os.path.exists(sprite_path): 
            try: 
                loaded_image = pygame.image.load(sprite_path).convert_alpha() 
                self.original_image = pygame.transform.smoothscale(loaded_image, default_size) 
                loaded_successfully = True
            except pygame.error as e: 
                print(f"Error loading player sprite '{sprite_path}': {e}. Using fallback.") 
        
        if not loaded_successfully:
            if sprite_path and not os.path.exists(sprite_path) : print(f"Warning: Player sprite path not found: {sprite_path}. Using fallback.") 
            # Create a simple fallback visual if loading fails
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA) 
            self.original_image.fill((0, 200, 0, 150)) # Semi-transparent green
            pygame.draw.circle(self.original_image, (255,255,255), (default_size[0]//2, default_size[1]//2), default_size[0]//3, 2) # White circle

        self.image = self.original_image.copy() # Current image for drawing is a copy
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        
        # Update dependent visual attributes if rect was successfully created
        if self.rect: 
            self.drone_visual_size = self.rect.size # Update visual size based on loaded sprite
            self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4 
            self.collision_rect_width = self.rect.width * 0.7 
            self.collision_rect_height = self.rect.height * 0.7 
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height) 
            self.collision_rect.center = self.rect.center
        else: # Fallback for collision rect if self.rect is None
            col_size = self.size * 0.7 
            self.collision_rect_width = col_size
            self.collision_rect_height = col_size
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2, 
                                               col_size, col_size)


    def _update_weapon_attributes(self): 
        """Updates bullet size and shoot cooldown based on the current weapon mode and drone stats."""
        # Determine base bullet size and cooldown for the current mode
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT: 
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE") 
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 # Slower for big shots
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]: 
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE") 
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN") 
        else: # Default, Tri-shot, Bounce, Pierce
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE") 
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") 
        
        # Apply drone's base fire rate multiplier and any fragment buffs
        if self.base_fire_rate_multiplier != 0: 
            effective_fr_mult = self.base_fire_rate_multiplier
            # Check for core fragment buffs if DroneSystem is available
            if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
                for frag_id in self.drone_system.get_collected_fragments_ids():
                    # Find fragment configuration
                    frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                    if frag_conf and frag_conf.get("buff", {}).get("type") == "fire_rate":
                        effective_fr_mult *= frag_conf["buff"]["value"] # Apply multiplicative buff
            
            self.current_shoot_cooldown /= effective_fr_mult # Faster shooting means lower cooldown
            self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / effective_fr_mult
            self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / effective_fr_mult
        else: # Safety for zero multiplier (infinite cooldown)
            self.current_shoot_cooldown = float('inf')
            self.current_missile_cooldown = float('inf')
            self.current_lightning_cooldown = float('inf')

    def _emit_thrust_particles(self, current_time_ms):
        """Emits thrust particles if speed boost is active and player is moving."""
        if self.speed_boost_active and self.moving_forward:
            if current_time_ms > self.thrust_particle_spawn_timer:
                self.thrust_particle_spawn_timer = current_time_ms + self.THRUST_PARTICLE_SPAWN_INTERVAL
                num_particles_to_spawn = self.PARTICLES_PER_EMISSION
                
                # Particles emit from behind the drone
                emission_base_angle_deg = (self.angle + 180) % 360 # Opposite to drone's facing angle
                # Offset emission point slightly behind the drone's center
                emission_angle_rad_for_offset = math.radians(self.angle + 180) 
                
                offset_x = math.cos(emission_angle_rad_for_offset) * self.flame_port_offset_distance
                offset_y = math.sin(emission_angle_rad_for_offset) * self.flame_port_offset_distance
                
                for _ in range(num_particles_to_spawn):
                    particle = Particle(
                        x=self.x,  # Start from drone center, offset applied by Particle class
                        y=self.y,  
                        color_list=gs.FLAME_COLORS, # Use predefined flame colors
                        min_speed=gs.get_game_setting("THRUST_PARTICLE_SPEED_MIN_BLAST"),
                        max_speed=gs.get_game_setting("THRUST_PARTICLE_SPEED_MAX_BLAST"),
                        min_size=gs.get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MIN"),
                        max_size=gs.get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MAX"),
                        lifetime_frames=gs.get_game_setting("THRUST_PARTICLE_LIFETIME_BLAST"),
                        base_angle_deg=emission_base_angle_deg, 
                        spread_angle_deg=gs.get_game_setting("THRUST_PARTICLE_SPREAD_ANGLE"), 
                        x_offset=offset_x, # Pass calculated offset
                        y_offset=offset_y,
                        blast_mode=True # Use blast_mode for flame-like appearance
                    )
                    self.thrust_particles.add(particle)

    def _update_thrust_particles(self):
        """Updates all active thrust particles."""
        self.thrust_particles.update()

    def update_movement(self, maze=None, game_area_x_offset=0): 
        """Updates player movement, handling wall collisions and screen boundaries."""
        if self.moving_forward and self.alive:
            angle_rad = math.radians(self.angle)
            dx = math.cos(angle_rad) * self.current_speed # Use current_speed (can be boosted)
            dy = math.sin(angle_rad) * self.current_speed
            next_x = self.x + dx
            next_y = self.y + dy

            collided_with_wall = False 
            if maze and self.collision_rect: # Ensure maze and collision_rect are valid
                temp_collision_rect = self.collision_rect.copy()
                temp_collision_rect.center = (next_x, next_y)
                # Use the maze's is_wall method, which works for both Maze and MazeChapter2
                if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                self.collision_rect.width, self.collision_rect.height):
                    collided_with_wall = True 
            
            if collided_with_wall:
                self._handle_wall_collision(True, dx, dy) # Pass wall_hit_boolean and movement delta
            else:
                self.x = next_x
                self.y = next_y
        
        # Boundary checks for the game area
        if self.collision_rect and self.rect: # Ensure rects are valid
            half_col_width = self.collision_rect.width / 2
            half_col_height = self.collision_rect.height / 2
            min_x_bound = game_area_x_offset + half_col_width
            max_x_bound = WIDTH - half_col_width # Assuming WIDTH is screen width
            min_y_bound = half_col_height
            max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height # Assuming GAME_PLAY_AREA_HEIGHT

            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))
            
            self.rect.center = (int(self.x), int(self.y))
            self.collision_rect.center = self.rect.center


    def update(self, current_time_ms, maze, enemies_group, game_area_x_offset=0): 
        """Main update loop for the player drone."""
        if not self.alive: 
            # If dead, might still want to update bullets for a short while or handle explosion
            self.bullets_group.update(maze, game_area_x_offset)
            self.missiles_group.update(enemies_group, maze, game_area_x_offset)
            self.lightning_zaps_group.update(current_time_ms)
            self._update_thrust_particles() # Let existing particles fade
            return 
            
        self.update_powerups(current_time_ms) # Update shield, speed boost, cloak timers
        self.update_movement(maze, game_area_x_offset) # Handle movement and wall collisions
        
        # Emit and update thrust particles if speed boost is active
        if self.speed_boost_active and self.moving_forward:
            self._emit_thrust_particles(current_time_ms)
        self._update_thrust_particles() 
        
        # Update projectiles
        self.bullets_group.update(maze, game_area_x_offset) 
        self.missiles_group.update(enemies_group, maze, game_area_x_offset) # Missiles need enemy group for targeting
        self.lightning_zaps_group.update(current_time_ms) 
        
        # Update visual sprite (rotation and cloaking transparency)
        current_alpha_to_set = 255
        if self.is_cloaked_visual: # If cloak effect is active
            current_alpha_to_set = self.phantom_cloak_alpha 
        
        if self.original_image: # Ensure original_image is loaded
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle) # Pygame rotates counter-clockwise
            self.image = rotated_image.convert_alpha() # Ensure per-pixel alpha
            self.image.set_alpha(current_alpha_to_set) # Apply transparency for cloak
            
            if self.rect: # Ensure rect exists
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
                if self.collision_rect: # Ensure collision_rect exists
                    self.collision_rect.center = self.rect.center
            else: # Fallback if rect somehow not initialized
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect: 
                    self.collision_rect.center = self.rect.center
                 
        elif self.rect: # If no original_image but rect exists (e.g. BaseDrone fallback)
             self.rect.center = (int(self.x), int(self.y))
             if self.collision_rect: self.collision_rect.center = self.rect.center


    def _handle_wall_collision(self, wall_hit_boolean, dx, dy): 
        """Handles the consequences of colliding with a wall."""
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        
        if wall_hit_boolean and not self.shield_active and not is_invincible_setting:
            self.take_damage(10, self.crash_sound) # Take damage if not shielded or invincible
        
        # Stop forward movement regardless of damage, as a wall was hit
        self.moving_forward = False  

    def rotate(self, direction, rotation_speed_override=None): 
        """Rotates the drone left or right."""
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed 
        if direction == "left": 
            self.angle -= effective_rotation_speed 
        elif direction == "right": 
            self.angle += effective_rotation_speed 
        self.angle %= 360  # Keep angle within 0-359 degrees

    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None): 
        """Handles firing the drone's current weapon."""
        current_time_ms = pygame.time.get_ticks() 
        
        # Check cooldowns for different weapon types
        can_shoot_primary = (current_time_ms - self.last_shot_time) > self.current_shoot_cooldown 
        can_shoot_missile = (current_time_ms - self.last_missile_shot_time) > self.current_missile_cooldown 
        can_shoot_lightning = (current_time_ms - self.last_lightning_time) > self.current_lightning_cooldown 
        
        # Calculate bullet spawn position (nose of the drone)
        nose_offset_factor = (self.rect.height / 2 if self.rect else TILE_SIZE * 0.4) * 0.7 
        rad_angle_shoot = math.radians(self.angle) 
        
        raw_bullet_start_x = self.x + math.cos(rad_angle_shoot) * nose_offset_factor 
        raw_bullet_start_y = self.y + math.sin(rad_angle_shoot) * nose_offset_factor 

        bullet_start_x = raw_bullet_start_x
        bullet_start_y = raw_bullet_start_y
        
        # Check if bullet spawn point is inside a wall and adjust if necessary
        projectile_check_diameter = self.bullet_size * 2 # Approximate size for wall check
        if maze:
            if maze.is_wall(raw_bullet_start_x, raw_bullet_start_y, projectile_check_diameter, projectile_check_diameter):
                max_steps_back = 10 # How many steps to try moving spawn point back
                step_dist = nose_offset_factor / max_steps_back if max_steps_back > 0 else 0
                found_clear_spawn = False
                for i in range(1, max_steps_back + 1):
                    current_offset = nose_offset_factor - (i * step_dist)
                    if current_offset < 0: current_offset = 0 # Don't go behind drone center
                    
                    test_x = self.x + math.cos(rad_angle_shoot) * current_offset
                    test_y = self.y + math.sin(rad_angle_shoot) * current_offset
                    
                    if not maze.is_wall(test_x, test_y, projectile_check_diameter, projectile_check_diameter):
                        bullet_start_x = test_x
                        bullet_start_y = test_y
                        found_clear_spawn = True
                        break 
                    if current_offset == 0: # If even at drone center it's in a wall, spawn there
                        bullet_start_x = test_x 
                        bullet_start_y = test_y
                        break 
                
                if not found_clear_spawn: # If no clear point found after stepping back, spawn at drone center
                    bullet_start_x = self.x
                    bullet_start_y = self.y
        
        # Fire standard bullets (if not exclusively missile or lightning mode)
        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]: 
            if can_shoot_primary: 
                if sound: sound.play() 
                self.last_shot_time = current_time_ms 
                angles_to_fire = [0] # Default single shot
                # Adjust for multi-shot modes
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI: 
                    angles_to_fire = [-15, 0, 15] # Spread angles for tri-shot
                
                for angle_offset in angles_to_fire: 
                    effective_bullet_angle = self.angle + angle_offset 
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED") 
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME") 
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR") 
                    current_bullet_damage = 15 * self.bullet_damage_multiplier # Base damage * multiplier
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT: current_bullet_damage *= 2.5 # Big shot bonus
                    
                    bounces = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES") if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0 
                    pierces = get_game_setting("PIERCING_BULLET_MAX_PIERCES") if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0 
                    can_pierce_walls_flag = (self.current_weapon_mode == WEAPON_MODE_PIERCE) # Pierce mode can go through walls

                    new_bullet = Bullet(bullet_start_x, bullet_start_y, effective_bullet_angle, 
                                        bullet_speed, bullet_lifetime, self.bullet_size, bullet_color, 
                                        current_bullet_damage, bounces, pierces,
                                        can_pierce_walls=can_pierce_walls_flag) 
                    self.bullets_group.add(new_bullet)
        
        # Fire missiles (for heatseeker modes)
        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: 
            if can_shoot_missile: 
                if missile_sound: missile_sound.play() 
                self.last_missile_shot_time = current_time_ms 
                missile_dmg = get_game_setting("MISSILE_DAMAGE") * self.bullet_damage_multiplier
                new_missile = Missile(bullet_start_x, bullet_start_y, self.angle, missile_dmg, enemies_group) 
                self.missiles_group.add(new_missile) 
        
        # Fire lightning (for lightning mode)
        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING: 
            if can_shoot_lightning: 
                if sound: sound.play()  # Use primary shoot sound for lightning
                self.last_lightning_time = current_time_ms 
                
                # Find closest enemy for initial zap target
                closest_enemy_for_zap = None 
                if enemies_group: 
                    min_dist = float('inf') 
                    for enemy_sprite in enemies_group: 
                        if not enemy_sprite.alive: continue 
                        dist = math.hypot(enemy_sprite.rect.centerx - self.x, enemy_sprite.rect.centery - self.y) 
                        if dist < get_game_setting("LIGHTNING_ZAP_RANGE") and dist < min_dist: 
                            min_dist = dist 
                            closest_enemy_for_zap = enemy_sprite 
                
                lightning_dmg = get_game_setting("LIGHTNING_DAMAGE") * self.bullet_damage_multiplier
                if maze is None: 
                    print("CRITICAL WARNING (Player.shoot): Maze object not provided for LightningZap!")
                
                # Create the lightning zap entity
                new_zap = LightningZap(self, closest_enemy_for_zap, lightning_dmg, 
                                       get_game_setting("LIGHTNING_LIFETIME"), 
                                       maze) # Pass maze for wall collision checks
                self.lightning_zaps_group.add(new_zap)

    def take_damage(self, amount, sound=None): 
        """Reduces player health, handling invincibility and shield."""
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        
        if is_invincible_setting: # Global invincibility setting (debug/cheat)
            return 

        effective_amount = amount
        # Apply damage reduction from core fragments if DroneSystem is available
        if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
            for frag_id in self.drone_system.get_collected_fragments_ids():
                frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                if frag_conf and frag_conf.get("buff_alt", {}).get("type") == "damage_reduction":
                    effective_amount *= (1.0 - frag_conf["buff_alt"]["value"]) # Apply reduction
        
        if not self.alive: return # Already dead
        if self.shield_active: # Shield absorbs damage
            if sound: sound.play()  # Play a shield hit sound if available
            return 
            
        self.health -= effective_amount 
        if sound: sound.play() # Play damage sound
        if self.health <= 0: 
            self.health = 0 
            self.alive = False # Player is destroyed

    def activate_shield(self, duration, is_from_speed_boost=False):
        """Activates the player's shield power-up."""
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration
        self.shield_duration = duration 
        self.shield_glow_pulse_time_offset = pygame.time.get_ticks() * 0.005 # Randomize pulse start

        if is_from_speed_boost:
            self.shield_tied_to_speed_boost = True # Shield is part of speed boost
        else: 
            self.active_powerup_type = "shield" # Shield is its own power-up
            self.shield_tied_to_speed_boost = False

    def arm_speed_boost(self, duration, multiplier): 
        """Prepares the speed boost; activates on next forward movement."""
        self.speed_boost_duration = duration 
        self.speed_boost_multiplier = multiplier 
        self.active_powerup_type = "speed_boost"  # Mark speed boost as the current power-up

    def attempt_speed_boost_activation(self): 
        """Activates speed boost if armed and player starts moving forward."""
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward: 
            self.speed_boost_active = True 
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration 
            self.original_speed_before_boost = self.current_speed # Store current speed
            self.current_speed = self.current_speed * self.speed_boost_multiplier # Apply boost
            self.activate_shield(self.speed_boost_duration, is_from_speed_boost=True) # Speed boost also grants a shield

    def try_activate_cloak(self, current_time_ms): 
        """Attempts to activate the Phantom Cloak ability."""
        if self.special_ability == "phantom_cloak" and not self.cloak_active and \
           current_time_ms > self.cloak_cooldown_end_time: # Check cooldown
            self.cloak_active = True 
            self.is_cloaked_visual = True # For visual transparency
            self.cloak_end_time = current_time_ms + self.phantom_cloak_duration_ms 
            self.last_cloak_activation_time = current_time_ms  # Track last activation for cooldown
            return True # Cloak activated
        return False # Cloak not available or on cooldown

    def cycle_weapon_state(self, force_cycle=True):  
        """Cycles to the next available weapon mode."""
        if not force_cycle and self.current_weapon_mode == WEAPON_MODES_SEQUENCE[-1]:  
            return False  # Already at the last weapon, no forced cycle
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE) 
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index] 
        self._update_weapon_attributes() # Update stats for the new weapon mode
        return True 
    
    def update_powerups(self, current_time_ms):
        """Updates the state of active power-ups (shield, speed boost, cloak)."""
        # Shield timer
        if self.shield_active and current_time_ms > self.shield_end_time: 
            # Only deactivate shield if it's not tied to an active speed boost
            if not (self.shield_tied_to_speed_boost and self.speed_boost_active and current_time_ms <= self.speed_boost_end_time):
                self.shield_active = False 
                if self.active_powerup_type == "shield": self.active_powerup_type = None # Clear if it was the primary powerup
                self.shield_tied_to_speed_boost = False # Reset flag

        # Speed boost timer
        if self.speed_boost_active and current_time_ms > self.speed_boost_end_time: 
            self.speed_boost_active = False 
            self.current_speed = self.original_speed_before_boost # Revert to original speed
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None # Clear if it was primary
            if self.shield_tied_to_speed_boost: # If shield was tied to this boost, deactivate it too
                self.shield_active = False
                self.shield_tied_to_speed_boost = False 
        
        # Cloak timer and cooldown
        if self.cloak_active and current_time_ms > self.cloak_end_time: 
            self.cloak_active = False 
            self.is_cloaked_visual = False # Become visible
            self.cloak_cooldown_end_time = current_time_ms + self.phantom_cloak_cooldown_ms # Start cooldown

    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None, preserve_weapon=False):
        """Resets the player drone's state, typically on new level or after death."""
        previous_drone_id = self.drone_id # Store previous ID to check if sprite needs reloading

        # Reset position and orientation
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0 
        self.alive = True 
        self.moving_forward = False 
        
        # Update drone ID and apply new base stats
        self.drone_id = drone_id 
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)

        self.max_health = self.base_hp
        self.health = health_override if health_override is not None else self.max_health # Set health (full or override)
        
        self.speed = self.base_speed # Reset current speed to base speed
        self.current_speed = self.speed 
        self.rotation_speed = self.base_turn_speed
        self.original_speed_before_boost = self.speed # Reset for speed boost logic

        # Reload sprite if drone type changed or sprite wasn't loaded
        if previous_drone_id != self.drone_id or \
           not self.original_image or \
           (self.original_image and self.original_image.get_width() == 0): 
            self._load_sprite(drone_sprite_path)
        else: # If same drone, just re-rotate and update rect
            if self.original_image: 
                self.image = pygame.transform.rotate(self.original_image, -self.angle) 
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect: 
                    self.collision_rect.center = self.rect.center

        # Ensure image and rect are valid after potential reload or reset
        if self.original_image and not self.image: 
             self.image = pygame.transform.rotate(self.original_image, -self.angle)
        if self.image and not self.rect: 
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        elif self.rect: # Update existing rect
            self.rect.center = (int(self.x), int(self.y))

        if self.rect: # Update collision rect based on visual rect
            self.drone_visual_size = self.rect.size 
            self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        
        # Reset weapon system
        if not preserve_weapon: # Optionally preserve weapon state (e.g., for defense mode respawn)
            initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
            try:
                self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
            except ValueError:
                self.weapon_mode_index = 0 
            self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        
        self._update_weapon_attributes() # Apply stats for current (or reset) weapon
        
        # Clear projectiles and reset timers
        self.bullets_group.empty()
        self.missiles_group.empty()
        self.lightning_zaps_group.empty()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0
        
        self.reset_active_powerups() # Deactivate all power-ups

    def reset_active_powerups(self): 
        """Deactivates all active power-ups and resets their timers."""
        self.shield_active = False 
        self.shield_end_time = 0 
        self.speed_boost_active = False 
        self.speed_boost_end_time = 0 
        self.current_speed = self.base_speed  # Revert to base speed
        self.original_speed_before_boost = self.base_speed 
        self.cloak_active = False 
        self.is_cloaked_visual = False 
        self.cloak_end_time = 0 
        self.active_powerup_type = None 
        self.thrust_particles.empty() 
        self.shield_tied_to_speed_boost = False


    def get_position(self): 
        """Returns the player's current center position as (x, y)."""
        return (self.x, self.y) 

    def draw(self, surface): 
        """Draws the player drone, its projectiles, and effects."""
        # Only draw if alive or if there are lingering effects like projectiles/particles
        if not self.alive and not self.bullets_group and not self.missiles_group and not self.lightning_zaps_group and not self.thrust_particles:  
            return 
        
        self.thrust_particles.draw(surface) # Draw thrust particles

        if self.alive and self.image and self.original_image:  # Ensure image is valid
            surface.blit(self.image, self.rect) # Draw the drone sprite

            # Draw shield effect if active
            if self.shield_active:
                current_time = pygame.time.get_ticks()
                # Create a pulsing effect for the shield
                pulse_factor = (math.sin(current_time * 0.012 + self.shield_glow_pulse_time_offset) + 1) / 2 
                
                shield_alpha = int(180 + pulse_factor * 75) # Pulsing alpha
                shield_color_tuple = POWERUP_TYPES.get("shield", {}).get("color", LIGHT_BLUE)
                final_shield_color = (*shield_color_tuple[:3], shield_alpha) # Color with alpha
                
                try:
                    # Create a mask from the drone's image to draw an outline shield
                    if self.image.get_width() > 0 and self.image.get_height() > 0:
                        drone_mask = pygame.mask.from_surface(self.image)
                        outline_points = drone_mask.outline(1) # Get outline points

                        if outline_points:
                            # Offset outline points to screen coordinates
                            screen_outline_points = [(p[0] + self.rect.left, p[1] + self.rect.top) for p in outline_points]
                            
                            line_thickness = int(2 + pulse_factor * 2) # Pulsing thickness
                            pygame.draw.polygon(surface, final_shield_color, screen_outline_points, line_thickness)
                    else:
                        # Fallback if image has zero dimensions (should not happen if loaded correctly)
                        print("Warning (Player.draw): self.image has zero dimension, cannot create mask for shield.")
                except pygame.error as e: # Catch errors during mask creation or drawing
                    print(f"Error creating mask or drawing shield outline: {e}")
        
        # Draw projectiles
        self.bullets_group.draw(surface) 
        self.missiles_group.draw(surface) 
        for zap in self.lightning_zaps_group: # Lightning zaps need custom drawing
            zap.draw(surface)                 

        # Draw health bar if alive
        if self.alive: 
            self.draw_health_bar(surface) 

    def draw_health_bar(self, surface): 
        """Draws the player's health bar above the drone."""
        if not self.alive or not self.rect: return # Don't draw if dead or no rect
        bar_width = self.rect.width * 0.8 
        bar_height = 5 
        bar_x = self.rect.centerx - bar_width / 2 
        bar_y = self.rect.top - bar_height - 3 # Position above the drone
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage 
        
        # Draw background of health bar
        pygame.draw.rect(surface, (80,0,0) if health_percentage < 0.3 else (50,50,50), (bar_x, bar_y, bar_width, bar_height)) 
        # Determine fill color based on health
        fill_color = RED 
        if health_percentage >= 0.6: fill_color = GREEN 
        elif health_percentage >= 0.3: fill_color = YELLOW 
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height)) 
        # Draw border
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

