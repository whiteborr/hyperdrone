import pygame
import math
import random
import os

# Import Bullet class
try:
    from bullet import Bullet
except ImportError:
    print("Warning (enemy.py): Could not import Bullet from bullet.py. Enemy shooting will be affected.")
    # Define a dummy Bullet class if bullet.py or Bullet class is not found
    class Bullet(pygame.sprite.Sprite):
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0):
            super().__init__()
            self.image = pygame.Surface([size*2, size*2])
            self.rect = self.image.get_rect(center=(x,y))
            self.alive = True
        def update(self, maze=None, game_area_x_offset=0): # Added game_area_x_offset for consistency
            if not self.alive: self.kill()
        def draw(self, surface):
            if self.alive: surface.blit(self.image, self.rect)


# Import necessary constants from game_settings
try:
    from game_settings import (
        TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR,
        ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME,
        ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE, PLAYER_DEFAULT_BULLET_SIZE, # Used as a base for enemy bullet size
        WIDTH, GAME_PLAY_AREA_HEIGHT, # For boundary checks
        # PROTOTYPE_DRONE_SPRITE_PATH is used by game_loop when creating specific enemies
    )
except ImportError:
    print("Warning (enemy.py): Could not import all constants from game_settings. Using fallbacks.")
    TILE_SIZE = 80
    ENEMY_SPEED = 1.5
    ENEMY_HEALTH = 100
    ENEMY_COLOR = (255, 0, 0) # RED
    ENEMY_BULLET_SPEED = 5
    ENEMY_BULLET_COOLDOWN = 1500
    ENEMY_BULLET_LIFETIME = 75
    ENEMY_BULLET_COLOR = (255, 100, 0)
    ENEMY_BULLET_DAMAGE = 10
    PLAYER_DEFAULT_BULLET_SIZE = 4
    WIDTH = 1920
    GAME_PLAY_AREA_HEIGHT = 1080 - 120


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0  # Angle in degrees, 0 is right, positive is CCW
        self.speed = ENEMY_SPEED
        self.health = ENEMY_HEALTH
        self.max_health = ENEMY_HEALTH
        self.alive = True
        self.shoot_sound = shoot_sound
        self.player_ref = target_player_ref # Reference to player object for advanced AI (optional)

        self.original_image = None # Will hold the base image, unrotated
        self.image = None          # The current rotated image for drawing
        self.rect = None           # Pygame rect for position and collision
        self.collision_rect = None # Potentially smaller rect for more precise collision

        self._load_sprite(sprite_path) # Load visual sprite

        self.bullets = pygame.sprite.Group() # Group to manage enemy's bullets
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, int(ENEMY_BULLET_COOLDOWN)) # Stagger initial shots
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN
        
        # Base size for its own bullets, can be derived from player's default or a specific enemy setting
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3

        # Simple AI state
        self.state = "patrolling" # Possible states: "patrolling", "chasing", "attacking"
        self.patrol_target_pos = None # For patrolling state
        self.state_timer = 0 # Timer for state-based actions

    def _load_sprite(self, sprite_path):
        """Loads the enemy's sprite or creates a default one."""
        # Default size relative to TILE_SIZE, e.g., 70% of a tile
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7))
        
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, default_size)
            except pygame.error as e:
                print(f"Error loading enemy sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None # Flag to use default drawing
        else:
            if sprite_path: print(f"Warning: Enemy sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None: # Create a default colored shape if no sprite
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill(ENEMY_COLOR) # Use default ENEMY_COLOR
            # Example: draw a simple triangle pointing right
            # points = [(default_size[0], default_size[1]//2), (0,0), (0, default_size[1])]
            # pygame.draw.polygon(self.original_image, (0,0,0), points, 2) # Black outline

        self.image = self.original_image.copy() # Start with a copy
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        # Define a collision rectangle, potentially smaller than the visual sprite
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def update(self, player_pos, maze, current_time, game_area_x_offset=0): # Added game_area_x_offset
        """Updates the enemy's state, movement, and actions."""
        if not self.alive:
            if not self.bullets: # Only kill if no active bullets
                self.kill()
            self.bullets.update(maze, game_area_x_offset) # Still update bullets if enemy is dead but bullets are live
            return

        self._update_ai(player_pos, maze, current_time)
        self._update_movement(maze, game_area_x_offset) # Pass game_area_x_offset

        # Rotate image for drawing
        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Negative for Pygame's CCW rotation
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect.center = self.rect.center # Keep collision rect centered

        # Update and manage bullets
        self.bullets.update(maze, game_area_x_offset) # Pass game_area_x_offset

        # Shooting logic
        if player_pos and (current_time - self.last_shot_time > self.shoot_cooldown):
            # Check if player is within a certain range to shoot
            dx_player = player_pos[0] - self.x
            dy_player = player_pos[1] - self.y
            distance_to_player = math.hypot(dx_player, dy_player)
            
            # Define a shooting range, e.g., 10 tiles
            shooting_range = TILE_SIZE * 10 
            if distance_to_player < shooting_range:
                self.shoot(target_pos=player_pos) # Pass player_pos as target_pos
                self.last_shot_time = current_time

    def _update_ai(self, player_pos, maze, current_time):
        """Basic AI logic for state transitions and targeting."""
        if not player_pos: # No player, just patrol
            self.state = "patrolling"
        else:
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            distance_to_player = math.hypot(dx, dy)

            # Define AI behavior ranges
            chase_range = TILE_SIZE * 8
            # attack_range = TILE_SIZE * 6 # Could be used for different shooting behavior

            if distance_to_player < chase_range:
                self.state = "chasing"
                # Aim towards player: angle from self to player_pos
                # math.atan2(y, x) gives angle from positive x-axis
                target_angle_rad = math.atan2(dy, dx) 
                self.angle = math.degrees(target_angle_rad) # Convert to degrees
            else:
                self.state = "patrolling"
        
        if self.state == "patrolling":
            # Simple patrol: if no target or timer up, pick a new random direction (angle)
            if not self.patrol_target_pos or current_time > self.state_timer:
                self.angle += random.uniform(-45, 45) # Change direction slightly
                self.angle %= 360
                # Could also set a self.patrol_target_pos within the maze
                self.state_timer = current_time + random.randint(2000, 5000) # Patrol for 2-5 seconds

    def _update_movement(self, maze, game_area_x_offset=0): # Added game_area_x_offset
        """Updates position based on current angle and speed, with collision."""
        rad_angle = math.radians(self.angle)
        # Corrected movement: 0 degrees angle is right
        move_dx = math.cos(rad_angle) * self.speed
        move_dy = math.sin(rad_angle) * self.speed

        next_x = self.x + move_dx
        next_y = self.y + move_dy

        # Use collision_rect for checking
        temp_collision_rect = self.collision_rect.copy()
        temp_collision_rect.center = (next_x, next_y)

        collided = False
        if maze:
            if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery, 
                            self.collision_rect_width, self.collision_rect_height):
                collided = True

        if not collided:
            self.x = next_x
            self.y = next_y
        else:
            # Simple collision response: turn randomly and stop moving this frame
            self.angle += random.choice([-90, 90, 180]) # Turn away
            self.angle %= 360
            # Optionally, move back slightly: self.x -= move_dx * 0.5; self.y -= move_dy * 0.5

        # Boundary checks (ensure enemy stays within game area)
        half_col_width = self.collision_rect_width / 2
        half_col_height = self.collision_rect_height / 2

        min_x_bound = game_area_x_offset + half_col_width
        max_x_bound = WIDTH - half_col_width
        min_y_bound = half_col_height
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height
        
        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))
        
        self.rect.center = (int(self.x), int(self.y))
        self.collision_rect.center = self.rect.center

    def shoot(self, target_pos=None):
        """Creates and fires a bullet."""
        if not self.alive:
            return

        # Calculate bullet origin (e.g., tip of the enemy sprite)
        # This offset depends on how the sprite is drawn and its size.
        # Assuming self.angle = 0 means facing right.
        rad_fire_angle = math.radians(self.angle)
        tip_offset_distance = self.rect.width / 2 # Approx distance from center to "nose"
        
        fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance
        fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance
        
        bullet_angle_to_fire = self.angle # Default to current facing angle
        if target_pos: # If a specific target position is given (e.g., player's current location)
            dx_target = target_pos[0] - fire_origin_x
            dy_target = target_pos[1] - fire_origin_y
            bullet_angle_to_fire = math.degrees(math.atan2(dy_target, dx_target))
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=bullet_angle_to_fire,
            speed=ENEMY_BULLET_SPEED,
            lifetime=ENEMY_BULLET_LIFETIME,
            size=self.enemy_bullet_size, # Use defined enemy bullet size
            color=ENEMY_BULLET_COLOR,
            damage=ENEMY_BULLET_DAMAGE
            # No bounces or pierces for basic enemy bullets by default
        )
        self.bullets.add(new_bullet)
        if self.shoot_sound:
            self.shoot_sound.play()

    def take_damage(self, amount):
        """Reduces enemy health by a given amount."""
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            # Death effects/sounds would be handled by the game loop observing 'alive'

    def draw(self, surface):
        """Draws the enemy and its bullets."""
        if self.alive: # Only draw enemy if alive
            surface.blit(self.image, self.rect)
            # Optional: draw health bar
            # self._draw_health_bar(surface) 
        
        self.bullets.draw(surface) # Draw bullets even if enemy just died

    def _draw_health_bar(self, surface): # Example helper for health bar
        if self.alive and self.health < self.max_health:
            bar_width = self.rect.width * 0.8
            bar_height = 5
            bar_x = self.rect.centerx - bar_width / 2
            bar_y = self.rect.top - bar_height - 2 # Position above sprite

            health_percent = self.health / self.max_health
            fill_width = int(bar_width * health_percent)
            
            pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height)) # BG
            health_color = (0,255,0) if health_percent > 0.5 else (255,255,0) if health_percent > 0.2 else (255,0,0)
            if fill_width > 0:
                pygame.draw.rect(surface, health_color, (bar_x, bar_y, fill_width, bar_height))
            pygame.draw.rect(surface, (200,200,200), (bar_x, bar_y, bar_width, bar_height), 1) # Border