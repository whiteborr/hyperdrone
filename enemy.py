import math
import pygame

from base_drone import BaseDrone # Enemy inherits from BaseDrone
from bullet import Bullet       # For enemy projectiles
from game_settings import (     # Import necessary settings and colors
    BLACK, RED, GREEN, YELLOW,  # Colors for health bar and enemy
    ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR, # Basic enemy stats
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_COLOR, ENEMY_BULLET_LIFETIME,
    TILE_SIZE # For AI behavior, like maintaining distance
)

class Enemy(BaseDrone):
    """
    Represents an enemy drone that moves towards the player and shoots.
    Inherits from BaseDrone for common drone functionalities.
    """
    def __init__(self, x, y, shoot_sound=None):
        """
        Initializes an Enemy instance.
        Args:
            x (int/float): The initial x-coordinate of the enemy.
            y (int/float): The initial y-coordinate of the enemy.
            shoot_sound (pygame.mixer.Sound, optional): Sound effect for when the enemy shoots.
        """
        # Initialize BaseDrone with enemy-specific speed and default size.
        super().__init__(x, y, size=30, speed=ENEMY_SPEED) # size can be adjusted

        self.health = ENEMY_HEALTH # Set health from game settings.
        self.max_health = ENEMY_HEALTH # Store max health for health bar calculation.
        self.is_stunned = False      # Flag to indicate if the enemy is currently stunned.
        self.stun_end_time = 0       # Time (in ticks) when the stun effect wears off.

        # Adjust rect size to match visual size if different from BaseDrone's default.
        # If using dynamic drawing, self.size is key. If using a sprite sheet for enemies,
        # self.image and self.rect would be set up differently.
        self.rect.size = (self.size, self.size) # Ensure rect matches the enemy's logical size.
        self.rect.center = (int(self.x), int(self.y)) # Position the rect.

        # For dynamic drawing, self.image might not be used directly for the main sprite,
        # but it's good practice for sprite groups.
        # If you have specific enemy sprites, load them here.
        # self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        # self._draw_enemy_appearance() # Call a method to draw initial appearance if not using sprite sheets.

        self.bullets = [] # List to manage bullets fired by this enemy.
        self.last_shot_time = 0 # Time of the last shot, for cooldown.
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN # Cooldown duration from game settings.
        self.shoot_sound = shoot_sound # Sound effect for shooting.
        
        self.maze_ref = None # Reference to the maze for collision detection by enemy/bullets.

    def _draw_enemy_appearance(self):
        """
        (Optional) Draws the enemy's visual representation onto self.image if not using a pre-loaded sprite.
        This is a placeholder if you have a more complex drawing routine or sprite sheets.
        The current draw() method handles dynamic drawing directly to the screen.
        """
        # Example: if you wanted to pre-render to self.image:
        # self.image.fill((0,0,0,0)) # Clear for transparency
        # pygame.draw.circle(self.image, ENEMY_COLOR, (self.size//2, self.size//2), self.size//2)
        pass


    def stun(self, duration_ms):
        """
        Stuns the enemy for a given duration in milliseconds.
        A stunned enemy typically cannot move or shoot.
        """
        self.is_stunned = True
        self.stun_end_time = pygame.time.get_ticks() + duration_ms
        # Optionally, change appearance when stunned (e.g., color tint).
        # self._draw_enemy_appearance() # If appearance changes and is pre-rendered.

    def update(self, player_position, maze=None, current_time=0):
        """
        Updates the enemy's state, including AI, movement, and shooting.
        Args:
            player_position (tuple): The (x, y) coordinates of the player.
            maze (Maze, optional): The game maze for collision detection.
            current_time (int, optional): The current game time in ticks (from pygame.time.get_ticks()).
        """
        self.maze_ref = maze # Store maze reference for use by bullets.

        if not self.alive:
            # If enemy is "dead" (e.g., playing death animation), still update its bullets.
            self._update_bullets()
            if not self.bullets: # If no more bullets are active.
                self.kill() # Remove this enemy sprite from all groups.
            return

        # Handle stun effect.
        if self.is_stunned:
            if current_time > self.stun_end_time:
                self.is_stunned = False
                # self._draw_enemy_appearance() # Revert appearance if it changed.
            else:
                self._update_bullets() # Stunned enemies might still have active bullets.
                self.rect.center = (int(self.x), int(self.y)) # Ensure rect is updated.
                return # Don't move or shoot if stunned.

        # --- Basic AI: Face and move towards the player ---
        dx = player_position[0] - self.x
        dy = player_position[1] - self.y
        self.angle = math.degrees(math.atan2(dy, dx)) # Face the player.
        distance_to_player = math.hypot(dx, dy)

        # Movement logic: move if not too close to the player.
        # TILE_SIZE * 1.5 is an example minimum distance.
        if distance_to_player > TILE_SIZE * 1.5:
            self.moving_forward = True
            self.update_movement(self.maze_ref) # BaseDrone's movement logic with maze collision.
        else:
            self.moving_forward = False

        self.rect.center = (int(self.x), int(self.y)) # Update rect after potential movement.

        # --- Shooting logic ---
        # Check distance and cooldown before shooting.
        # Example: shoot if player is within 400 pixels.
        if distance_to_player < 400 and current_time - self.last_shot_time > self.shoot_cooldown:
            self.shoot() # shoot() will use self.maze_ref for its bullets.

        self._update_bullets() # Update all active bullets fired by this enemy.

    def _update_bullets(self):
        """Helper method to update the enemy's bullets and remove dead ones."""
        for bullet in list(self.bullets): # Iterate over a copy for safe removal.
            bullet.update() # Bullet.update() handles its own logic including wall collision.
            if not bullet.alive:
                self.bullets.remove(bullet)
                bullet.kill() # Also remove from any global sprite groups it might be in.

    def shoot(self):
        """Creates a bullet and adds it to the enemy's bullet list and potentially a global group."""
        if self.alive: # Only shoot if alive.
            tip_x, tip_y = self.get_tip_position() # Get position of drone's "nose".
            new_bullet = Bullet(
                x=tip_x, y=tip_y, angle=self.angle,
                speed=ENEMY_BULLET_SPEED,
                color=ENEMY_BULLET_COLOR,
                lifetime=ENEMY_BULLET_LIFETIME,
                damage=10, # Example damage for enemy bullets, could be from game_settings
                maze=self.maze_ref,  # Pass the maze reference to the bullet for its own collisions.
                owner=self # Mark this enemy as the owner.
            )
            self.bullets.append(new_bullet)
            # If you have a sprite group for ALL game bullets (player + enemy) in your Game class:
            # self.game.all_projectiles_group.add(new_bullet) # Example
            
            self.last_shot_time = pygame.time.get_ticks() # Reset shot cooldown timer.
            if self.shoot_sound:
                self.shoot_sound.play()

    def draw(self, surface):
        """Draws the enemy and its health bar onto the given surface."""
        if not self.alive and not self.bullets: # Don't draw if dead and no bullets left.
            return

        if self.alive: # Draw the enemy itself if it's alive.
            # --- Dynamic Enemy Drawing Example ---
            # This is a more detailed example than BaseDrone's simple triangle.
            # Replace this with your sprite blitting if you use sprite sheets for enemies.
            angle_rad = math.radians(self.angle)
            s = self.size # Use self.size for scaling points.

            # Define points for a more distinct enemy shape (e.g., a different kind of triangle or polygon).
            # Example: A slightly more aggressive looking triangle.
            p1 = (s * 1.2 * math.cos(angle_rad) + self.x, s * 1.2 * math.sin(angle_rad) + self.y) # Nose point
            p2 = (s * 0.8 * math.cos(angle_rad + 2.2) + self.x, s * 0.8 * math.sin(angle_rad + 2.2) + self.y) # Rear-left
            p3 = (s * 0.8 * math.cos(angle_rad - 2.2) + self.x, s * 0.8 * math.sin(angle_rad - 2.2) + self.y) # Rear-right
            
            # Central body/cockpit circle
            center_circle_radius = s // 3
            
            # "Eye" or detail circles on the points
            detail_circle_radius = s // 5

            current_enemy_color = (100, 100, 200) if self.is_stunned else ENEMY_COLOR # Change color if stunned.

            # Draw components
            pygame.draw.polygon(surface, (30, 30, 30), [p1, p2, p3]) # Darker base for depth
            pygame.draw.circle(surface, (150,150,150) if not self.is_stunned else (100,100,100),
                               (int(self.x), int(self.y)), center_circle_radius) # Central circle
            pygame.draw.circle(surface, current_enemy_color, (int(p1[0]), int(p1[1])), detail_circle_radius) # "Eye" at nose
            # pygame.draw.circle(surface, current_enemy_color, (int(p2[0]), int(p2[1])), detail_circle_radius) # Detail on wing
            # pygame.draw.circle(surface, current_enemy_color, (int(p3[0]), int(p3[1])), detail_circle_radius) # Detail on wing
            pygame.draw.polygon(surface, BLACK, [p1, p2, p3], 1) # Outline for definition.
            # --- End Dynamic Enemy Drawing Example ---

            self.draw_health_bar(surface) # Draw the health bar.

        # Draw enemy's active bullets.
        for bullet in self.bullets:
            bullet.draw(surface) # Bullet.draw() handles its own appearance.

    def take_damage(self, amount):
        """Applies damage to the enemy's health."""
        if self.alive: # Can only take damage if alive.
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False # Mark as no longer alive.
                # print(f"DEBUG: Enemy (ID: {id(self)}) DIED.")
            # else:
                # print(f"DEBUG: Enemy (ID: {id(self)}) health now {self.health}. Alive: {self.alive}")

    def draw_health_bar(self, surface):
        """Draws the enemy's health bar above it."""
        if self.alive: # Only draw health bar if alive.
            bar_width = self.size * 1.5 # Width of the health bar.
            bar_height = 5             # Height of the health bar.
            
            # Position the health bar above the enemy.
            bar_x = int(self.x - bar_width // 2)
            bar_y = int(self.y - self.size * 0.75 - bar_height * 2) # Adjust y-offset as needed.

            health_percentage = self.health / self.max_health if self.max_health > 0 else 0
            filled_width = int(bar_width * health_percentage)

            # Determine health bar color based on percentage.
            if health_percentage > 0.6: health_color = GREEN
            elif health_percentage > 0.3: health_color = YELLOW
            else: health_color = RED

            # Draw the background of the health bar (grey).
            pygame.draw.rect(surface, (128, 128, 128), (bar_x, bar_y, int(bar_width), bar_height))
            if filled_width > 0: # Draw the filled part representing current health.
                pygame.draw.rect(surface, health_color, (bar_x, bar_y, filled_width, bar_height))
            # Draw a border around the health bar.
            pygame.draw.rect(surface, BLACK, (bar_x, bar_y, int(bar_width), bar_height), 1)

    def reset(self, x, y):
        """
        Resets the enemy's state to be reused (e.g., for object pooling or respawning).
        Args:
            x (int/float): The new x-coordinate.
            y (int/float): The new y-coordinate.
        """
        # Re-initialize most attributes as in __init__.
        super().__init__(x, y, size=self.size, speed=ENEMY_SPEED) # Reset BaseDrone attributes.
        self.health = self.max_health # Reset to full health.
        self.angle = 0 # Reset orientation.
        self.alive = True
        self.is_stunned = False
        self.stun_end_time = 0
        self.bullets.clear() # Clear any existing bullets.
        self.last_shot_time = 0 # Reset shot timer.
        self.rect.center = (int(self.x), int(self.y)) # Update rect position.
        # self._draw_enemy_appearance() # If using pre-rendered appearance.
        self.maze_ref = None # Reset maze reference, will be set on next update.
