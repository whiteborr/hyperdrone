import math
import os
import random
import pygame

from base_drone import BaseDrone
from bullet import Bullet
from game_settings import (
    BLACK, RED, GREEN, YELLOW,
    ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR, # ENEMY_COLOR can be a fallback
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_COLOR, ENEMY_BULLET_LIFETIME,
    TILE_SIZE
)

class Enemy(BaseDrone):
    """
    Represents an enemy drone that moves towards the player and shoots.
    Inherits from BaseDrone for common drone functionalities.
    Now uses a sprite for its appearance.
    """
    def __init__(self, x, y, shoot_sound=None, sprite_path="assets/drones/TR-3B_enemy.png"): # Added sprite_path
        """
        Initializes an Enemy instance.
        Args:
            x (int/float): The initial x-coordinate of the enemy.
            y (int/float): The initial y-coordinate of the enemy.
            shoot_sound (pygame.mixer.Sound, optional): Sound effect for when the enemy shoots.
            sprite_path (str, optional): Path to the enemy's sprite image.
        """
        # Initialize BaseDrone with enemy-specific speed and default size.
        # The self.size will be used for collision rect and fallback drawing.
        # The visual size will come from the sprite.
        super().__init__(x, y, size=30, speed=ENEMY_SPEED)

        self.health = ENEMY_HEALTH
        self.max_health = ENEMY_HEALTH
        self.is_stunned = False
        self.stun_end_time = 0

        self.original_image = None # Will hold the loaded, unrotated sprite
        # self.image is inherited from pygame.sprite.Sprite, will hold the rotated sprite

        if sprite_path:
            try:
                if os.path.exists(sprite_path):
                    loaded_image = pygame.image.load(sprite_path).convert_alpha()
                    # Determine render dimensions. You can use a fixed size or scale based on self.size
                    # Example: Scale to be slightly larger than self.size (e.g., 45x45 if self.size is 30)
                    render_width = int(self.size * 1.5)
                    render_height = int(self.size * 1.5)
                    # Or use a fixed size if your TR-3B_enemy.png is designed for it e.g. (40,40)
                    # render_width = 40
                    # render_height = 40
                    self.original_image = pygame.transform.smoothscale(loaded_image, (render_width, render_height))
                    self.image = self.original_image.copy() # Start with a copy
                    self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                else:
                    print(f"WARNING: Enemy sprite not found at '{sprite_path}'. Using fallback drawing.")
                    self._setup_fallback_image()
            except pygame.error as e:
                print(f"ERROR loading enemy sprite '{sprite_path}': {e}. Using fallback drawing.")
                self._setup_fallback_image()
        else:
            self._setup_fallback_image()
        # Corner lights that blink periodically
        self.blink_timer = 0
        self.blink_interval = random.randint(500, 2000) # milliseconds
        self.light_on = True

        self.bullets = []
        self.last_shot_time = 0
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN
        self.shoot_sound = shoot_sound

        self.maze_ref = None

    def _setup_fallback_image(self):
        """Sets up a placeholder image and rect if sprite loading fails."""
        # This ensures self.image and self.rect exist for Pygame sprite group operations
        # The actual drawing will use dynamic shapes if self.original_image is None.
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        self.image.fill((0,0,0,0)) # Transparent
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))


    def stun(self, duration_ms):
        """
        Stuns the enemy for a given duration in milliseconds.
        """
        self.is_stunned = True
        self.stun_end_time = pygame.time.get_ticks() + duration_ms

    def update(self, player_position, maze=None, current_time=0):
        """
        Updates the enemy's state, including AI, movement, and shooting.
        """
        self.maze_ref = maze

        if not self.alive:
            self._update_bullets()
            if not self.bullets:
                self.kill()
            return

        if self.is_stunned:
            if current_time > self.stun_end_time:
                self.is_stunned = False
            else:
                self._update_bullets()
                # Ensure rect is updated even if stunned and using sprite
                if self.original_image:
                    # Potentially apply a stun visual effect to self.image here if desired
                    pass
                self.rect.center = (int(self.x), int(self.y))
                return

        dx = player_position[0] - self.x
        dy = player_position[1] - self.y
        self.angle = math.degrees(math.atan2(dy, dx))
        distance_to_player = math.hypot(dx, dy)

        if distance_to_player > TILE_SIZE * 1.5:
            self.moving_forward = True
            self.update_movement(self.maze_ref)
        else:
            self.moving_forward = False

        # Update image rotation and rect if using a sprite
        if self.original_image:
            self.image = pygame.transform.rotate(self.original_image, -self.angle) # Pygame rotates counter-clockwise
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        else: # Fallback if no sprite, ensure rect is still updated for collision
            self.rect.center = (int(self.x), int(self.y))


        if distance_to_player < 400 and current_time - self.last_shot_time > self.shoot_cooldown:
            self.shoot()
        current_ticks = pygame.time.get_ticks() # If you pass current_time, use that
        if current_ticks - self.blink_timer > self.blink_interval:
            self.light_on = not self.light_on
            self.blink_timer = current_ticks
            self.blink_interval = random.randint(500, 2000) # Vary the blink

        self._update_bullets()

    def _update_bullets(self):
        """Helper method to update the enemy's bullets and remove dead ones."""
        for bullet in list(self.bullets):
            bullet.update()
            if not bullet.alive:
                self.bullets.remove(bullet)
                bullet.kill()

    def shoot(self):
        """Creates a bullet and adds it to the enemy's bullet list."""
        if self.alive:
            tip_x, tip_y = self.get_tip_position()
            new_bullet = Bullet(
                x=tip_x, y=tip_y, angle=self.angle,
                speed=ENEMY_BULLET_SPEED,
                color=ENEMY_BULLET_COLOR,
                lifetime=ENEMY_BULLET_LIFETIME,
                damage=10,
                maze=self.maze_ref,
                owner=self
            )
            self.bullets.append(new_bullet)
            self.last_shot_time = pygame.time.get_ticks()
            if self.shoot_sound:
                self.shoot_sound.play()

    def draw(self, surface):
        """Draws the enemy (sprite or fallback) and its health bar."""
        if not self.alive and not self.bullets:
            return

        if self.alive:
            if self.original_image and self.image: # If sprite is loaded
                image_to_draw = self.image
                if self.is_stunned:
                    # Simple stun visual: tint the sprite
                    # Create a temporary surface for tinting to preserve original_image and image
                    temp_stun_image = self.image.copy()
                    temp_stun_image.fill((100, 100, 255, 100), special_flags=pygame.BLEND_RGBA_ADD) # Additive blueish tint
                    image_to_draw = temp_stun_image
                surface.blit(image_to_draw, self.rect.topleft)
            else: # Fallback dynamic drawing
                angle_rad = math.radians(self.angle)
                s = self.size
                p1 = (s * 1.2 * math.cos(angle_rad) + self.x, s * 1.2 * math.sin(angle_rad) + self.y)
                p2 = (s * 0.8 * math.cos(angle_rad + 2.2) + self.x, s * 0.8 * math.sin(angle_rad + 2.2) + self.y)
                p3 = (s * 0.8 * math.cos(angle_rad - 2.2) + self.x, s * 0.8 * math.sin(angle_rad - 2.2) + self.y)
                center_circle_radius = s // 3
                detail_circle_radius = s // 5
                current_enemy_color = (100, 100, 200) if self.is_stunned else ENEMY_COLOR

                pygame.draw.polygon(surface, (30, 30, 30), [p1, p2, p3])
                pygame.draw.circle(surface, (150,150,150) if not self.is_stunned else (100,100,100),
                                   (int(self.x), int(self.y)), center_circle_radius)
                pygame.draw.circle(surface, current_enemy_color, (int(p1[0]), int(p1[1])), detail_circle_radius)
                pygame.draw.polygon(surface, BLACK, [p1, p2, p3], 1)

            self.draw_health_bar(surface)

        for bullet in self.bullets:
            bullet.draw(surface)

    def take_damage(self, amount):
        """Applies damage to the enemy's health."""
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False

    def draw_health_bar(self, surface):
        """Draws the enemy's health bar above it."""
        if self.alive:
            # Use self.rect from the sprite if available, otherwise base on self.size
            ref_width = self.rect.width if self.original_image else self.size * 1.5
            ref_top = self.rect.top if self.original_image else (self.y - self.size * 0.75)

            bar_width = ref_width
            bar_height = 5
            bar_x = self.rect.left if self.original_image else int(self.x - bar_width // 2)
            bar_y = ref_top - bar_height * 2 # Position above the sprite/dynamic drawing

            health_percentage = self.health / self.max_health if self.max_health > 0 else 0
            filled_width = int(bar_width * health_percentage)

            if health_percentage > 0.6: health_color = GREEN
            elif health_percentage > 0.3: health_color = YELLOW
            else: health_color = RED

            pygame.draw.rect(surface, (128, 128, 128), (bar_x, bar_y, int(bar_width), bar_height))
            if filled_width > 0:
                pygame.draw.rect(surface, health_color, (bar_x, bar_y, filled_width, bar_height))
            pygame.draw.rect(surface, BLACK, (bar_x, bar_y, int(bar_width), bar_height), 1)

    def reset(self, x, y):
        """
        Resets the enemy's state.
        """
        # Re-initialize with the sprite path
        sprite_path_to_use = "assets/drones/TR-3B_enemy.png" # Or pass dynamically if enemies can change sprites
        self.__init__(x, y, shoot_sound=self.shoot_sound, sprite_path=sprite_path_to_use)
        # Explicitly ensure alive state and health are reset if __init__ doesn't cover all cases post-initial call
        self.alive = True
        self.health = self.max_health
        self.is_stunned = False
        self.rect.center = (int(self.x), int(self.y)) # Ensure rect is updated on reset