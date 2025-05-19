import math
import pygame

from game_settings import PLAYER_SPEED, CYAN

class BaseDrone(pygame.sprite.Sprite):  # Inherit from pygame.sprite.Sprite
    def __init__(self, x, y, size=30, speed=PLAYER_SPEED):
        super().__init__()  # Call the parent (Sprite) constructor
        self.x = x
        self.y = y
        self.size = size
        self.angle = 0
        self.health = 100  # Default health, can be overridden by subclasses
        self.alive = True
        self.bullets = []  # Each drone can manage its own bullets
        self.moving_forward = False
        self.speed = speed

        # It's good practice for Sprites to have an image and rect attribute
        # Though we draw dynamically, a rect is crucial for group collisions
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))  # Transparent placeholder
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def draw(self, surface, color=CYAN):
        """
        Draws the drone as a basic triangle.
        Subclasses should override this for more specific drawing.
        Note: This method is kept for potential direct use or as a fallback.
        """
        if not self.alive:
            return

        # Dynamic drawing (not using self.image here)
        drone_shape_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        points = [
            (self.size // 2, 0),
            (0, self.size),
            (self.size, self.size)
        ]
        pygame.draw.polygon(drone_shape_surface, color, points)
        rotated_surface = pygame.transform.rotate(drone_shape_surface, -self.angle)

        # Get new rect for the rotated image
        draw_rect = rotated_surface.get_rect(center=(self.x, self.y))
        surface.blit(rotated_surface, draw_rect.topleft)

        # Update self.rect for collision detection
        self.rect.center = (int(self.x), int(self.y))

    def rotate(self, direction, rotation_speed):
        """Rotates the drone."""
        if direction == "left":
            self.angle -= rotation_speed
        elif direction == "right":
            self.angle += rotation_speed
        self.angle %= 360  # Keep angle within 0-359 degrees

    def toggle_movement(self, move):
        """Toggles forward movement on or off."""
        if move == "start":
            self.moving_forward = True
        elif move == "stop":
            self.moving_forward = False

    def get_tip_position(self):
        """Calculates the position of the drone's 'tip' or 'nose'."""
        tip_offset = self.size * 0.5
        tip_x = self.x + math.cos(math.radians(self.angle)) * tip_offset
        tip_y = self.y + math.sin(math.radians(self.angle)) * tip_offset
        return tip_x, tip_y

    def update_movement(self, maze=None):
        """
        Updates the drone's position based on its speed and angle,
        with optional maze collision handling.
        """
        if self.moving_forward:
            angle_rad = math.radians(self.angle)
            new_x = self.x + math.cos(angle_rad) * self.speed
            new_y = self.y + math.sin(angle_rad) * self.speed

            # Store old position in case of collision
            old_x, old_y = self.x, self.y

            # Update position
            self.x = new_x
            self.y = new_y
            self.rect.center = (int(self.x), int(self.y))

            # Collision detection with maze
            if maze is not None and maze.is_wall(
                self.rect.centerx,
                self.rect.centery,
                self.rect.width,
                self.rect.height
            ):
                self.x, self.y = old_x, old_y
                self.rect.center = (int(self.x), int(self.y))

    def update(self):
        """
        Basic update method for a BaseDrone.
        Subclasses should extend this with their specific update logic.
        Required by Pygame sprite groups if you call group.update().
        """
        self.rect.center = (int(self.x), int(self.y))