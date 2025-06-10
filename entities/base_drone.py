# entities/base_drone.py
import math
import pygame

import game_settings as gs

class BaseDrone(pygame.sprite.Sprite):
    def __init__(self, x, y, size, speed):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.speed = speed
        self.angle = 0.0
        self.move_direction = 0  # 0 = stop, 1 = forward, -1 = backward
        self.alive = True
        
        self.rect = pygame.Rect(x - size / 2, y - size / 2, size, size)
        self.collision_rect = self.rect.inflate(-size * 0.2, -size * 0.2)

    def rotate(self, direction, rotation_speed):
        if direction == "left":
            self.angle -= rotation_speed
        elif direction == "right":
            self.angle += rotation_speed
        self.angle %= 360

    def update_movement(self, maze=None, game_area_x_offset=0):
        if self.move_direction != 0:
            rad_angle = math.radians(self.angle)
            # Apply direction to speed
            dx = math.cos(rad_angle) * self.speed * self.move_direction
            dy = math.sin(rad_angle) * self.speed * self.move_direction
            
            final_dx, final_dy = self._handle_wall_collision(maze, dx, dy)
            
            final_x = self.x + final_dx
            final_y = self.y + final_dy
            
            collision_width = self.collision_rect.width if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8
            collision_height = self.collision_rect.height if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8

            if not maze or not maze.is_wall(final_x, final_y, collision_width, collision_height):
                self.x = final_x
                self.y = final_y

        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

    def draw(self, surface):
        if self.alive:
            if hasattr(self, 'image') and self.image and (self.image.get_width() > 1 or self.image.get_height() > 1):
                surface.blit(self.image, self.rect)
            else:
                points = [ (self.size / 2, 0), (0, self.size), (self.size, self.size) ]
                shape_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                pygame.draw.polygon(shape_surf, gs.CYAN, points)
                
                rotated_image = pygame.transform.rotate(shape_surf, -self.angle)
                draw_rect = rotated_image.get_rect(center=self.rect.center)
                surface.blit(rotated_image, draw_rect)

    def update(self, maze=None, game_area_x_offset=0):
        if self.alive:
            self.update_movement(maze, game_area_x_offset)
        else:
            self.kill()

    def _handle_wall_collision(self, maze, dx, dy):
        if not maze:
            return dx, dy

        next_x = self.x + dx
        next_y = self.y + dy

        collision_width = self.collision_rect.width if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8
        collision_height = self.collision_rect.height if hasattr(self, 'collision_rect') and self.collision_rect else self.size * 0.8

        if not maze.is_wall(next_x, next_y, collision_width, collision_height):
            return dx, dy

        wall_normal_x, wall_normal_y = 0, 0
        if maze.is_wall(self.x + dx, self.y, collision_width, collision_height):
            wall_normal_x = -1 if dx > 0 else 1
        if maze.is_wall(self.x, self.y + dy, collision_width, collision_height):
            wall_normal_y = -1 if dy > 0 else 1

        norm_len = math.hypot(wall_normal_x, wall_normal_y)
        if norm_len > 0:
            wall_normal_x /= norm_len
            wall_normal_y /= norm_len

        dot_product = dx * wall_normal_x + dy * wall_normal_y
        
        slide_dx = dx - dot_product * wall_normal_x
        slide_dy = dy - dot_product * wall_normal_y
        
        return slide_dx, slide_dy

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.alive = True
        self.move_direction = 0
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center