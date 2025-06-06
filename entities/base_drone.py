import math
import pygame

import game_settings as gs
from game_settings import (
    # Import specific constants if they are used very frequently in this base class
    # For BaseDrone, these were the ones directly used in the original file
    TILE_SIZE,
    WIDTH,
    GAME_PLAY_AREA_HEIGHT,
    CYAN
    # PLAYER_SPEED is used as a default, access via gs.get_game_setting("PLAYER_SPEED")
)

class BaseDrone(pygame.sprite.Sprite):
    def __init__(self, x, y, size, speed):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.speed = speed
        self.angle = 0.0
        self.moving_forward = False
        self.alive = True
        
        # Initialize rect and collision_rect here to ensure they always exist
        self.rect = pygame.Rect(x - size / 2, y - size / 2, size, size)
        self.collision_rect = self.rect.inflate(-size * 0.2, -size * 0.2) # Example inflation

    def rotate(self, direction, rotation_speed):
        if direction == "left":
            self.angle += rotation_speed
        elif direction == "right":
            self.angle -= rotation_speed
        self.angle %= 360

    def update_movement(self, maze=None, game_area_x_offset=0):
        """
        Handles the drone's movement and wall collision detection.
        This has been updated to call a specific collision handler.
        """
        if self.moving_forward:
            rad_angle = math.radians(self.angle)
            dx = math.cos(rad_angle) * self.speed
            dy = math.sin(rad_angle) * self.speed
            
            next_x = self.x + dx
            next_y = self.y + dy

            wall_hit = False
            if maze:
                # Use the drone's specific collision rect for the check
                collision_width = self.collision_rect.width if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8
                collision_height = self.collision_rect.height if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8
                
                if maze.is_wall(next_x, next_y, collision_width, collision_height):
                    wall_hit = True

            # Call the collision handler regardless of the outcome
            # The child class (PlayerDrone) will decide what to do.
            self._handle_wall_collision(wall_hit, dx, dy)
            
            # Only update position if no wall was hit
            if not wall_hit:
                self.x = next_x
                self.y = next_y

        # Update rect positions after movement
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

    def draw(self, surface):
        if self.alive:
            # If a subclass (like PlayerDrone) properly sets and rotates self.image,
            # this will draw the correct rotated sprite.
            # If self.image is the default Surface([self.size, self.size]), this won't show much.
            # The original draw method had a fallback to draw a triangle, which might be useful
            # for debugging if a subclass fails to set its image.
            if self.image and (self.image.get_width() > 1 or self.image.get_height() > 1):
                # Assumes subclasses handle rotation of their specific original_image into self.image
                surface.blit(self.image, self.rect)
            else:  # Fallback for basic drawing if self.image is minimal or not set by subclass
                # Draw a simple triangle if no proper image is set
                points = [
                    (self.size / 2, 0),  # Tip
                    (0, self.size),      # Bottom-left
                    (self.size, self.size)  # Bottom-right
                ]
                shape_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                pygame.draw.polygon(shape_surf, CYAN, points)
                
                rotated_image = pygame.transform.rotate(shape_surf, -self.angle)
                draw_rect = rotated_image.get_rect(center=self.rect.center)
                surface.blit(rotated_image, draw_rect)

    def update(self, maze=None, game_area_x_offset=0):
        if self.alive:
            self.update_movement(maze, game_area_x_offset)
            # Subclasses (like PlayerDrone) will handle rotation of self.image in their own update.
            # BaseDrone's rect is updated in update_movement.
        else:
            self.kill()  # Remove from sprite groups if not alive

    def _handle_wall_collision(self, wall_hit, dx, dy):
        """
        Placeholder for wall collision logic. Child classes like PlayerDrone
        will override this to implement specific behaviors like taking damage.
        """
        # If a wall is hit, the default behavior is just to stop moving.
        if wall_hit:
            self.moving_forward = False

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.alive = True
        self.moving_forward = False
        self.rect.center = (int(self.x), int(self.y))
        self.collision_rect.center = self.rect.center
