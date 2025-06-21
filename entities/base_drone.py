# entities/base_drone.py
from math import radians, cos, sin
from pygame.sprite import Sprite
from pygame import Rect
from pygame.transform import rotate

from settings_manager import get_setting

class BaseDrone(Sprite):
    def __init__(self, x, y, size, speed):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.speed = speed
        self.angle = 0.0
        self.moving_forward = False
        self.alive = True
        
        self.rect = Rect(x - size / 2, y - size / 2, size, size)
        self.collision_rect = self.rect.inflate(-size * 0.2, -size * 0.2)

    def get_position(self):
        """Returns the current (x, y) position of the drone."""
        return (self.x, self.y)

    def rotate(self, direction, rotation_speed):
        """Rotates the drone based on the original game logic."""
        if direction == "left":
            self.angle -= rotation_speed
        elif direction == "right":
            self.angle += rotation_speed
        self.angle %= 360

    def update_movement(self, maze=None, game_area_x_offset=0):
        if self.moving_forward:
            # Note: math functions use radians, not degrees
            rad_angle = radians(self.angle)
            dx = cos(rad_angle) * self.speed
            dy = sin(rad_angle) * self.speed
            
            # Check for wall collision before moving
            if maze:
                # Test the new position before actually moving
                new_x = self.x + dx
                new_y = self.y + dy
                
                # Check if the new position would cause a collision
                wall_collision = maze.is_wall(new_x, new_y, self.size, self.size)
                if wall_collision:
                    # If collision detected, don't move in that direction
                    dx = 0
                    dy = 0
                    # Apply wall collision damage if this is a player drone
                    if hasattr(self, 'take_damage') and hasattr(self, 'drone_id'):
                        self.take_damage(5, 'crash')
            
            self.x += dx
            self.y += dy

        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

    def update(self, maze=None, game_area_x_offset=0):
        if self.alive:
            self.update_movement(maze, game_area_x_offset)

    def draw(self, surface):
        if self.alive and hasattr(self, 'image') and self.image:
            # The angle is inverted here to match the reversed rotation logic,
            # ensuring the visual rotation on screen feels correct.
            rotated_image = rotate(self.image, -self.angle)
            draw_rect = rotated_image.get_rect(center=self.rect.center)
            surface.blit(rotated_image, draw_rect)

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0 
        self.alive = True
        self.moving_forward = False
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center