# entities/defense_drone.py
import pygame
import math
import logging

from settings_manager import get_setting
from constants import GREEN, YELLOW, RED, WHITE

logger = logging.getLogger(__name__)

class DefenseDrone(pygame.sprite.Sprite):
    def __init__(self, x, y, asset_manager, sprite_asset_key, path_to_core, **kwargs):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.path = path_to_core if path_to_core else []
        self.current_path_index = 1 if self.path and len(self.path) > 1 else -1
        self.angle = 0
        self.speed = kwargs.get('speed', 1.5)
        self.health = kwargs.get('health', 100)
        self.max_health = self.health
        self.contact_damage = kwargs.get('contact_damage', 25)
        self.alive = True
        self._load_sprite()

    def _load_sprite(self):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        default_size = (int(tile_size * 0.7), int(tile_size * 0.7))
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None:
            logger.warning(f"DefenseDrone: Could not load sprite with key '{self.sprite_asset_key}'")
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill((255, 0, 0, 180))
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)

    def update(self, _, maze, __, ___, game_area_x_offset=0, is_defense_mode=True):
        if not self.alive:
            return
        
        self._update_movement_along_path(maze, game_area_x_offset)
        
        if self.image and self.original_image:
            self.image = pygame.transform.rotate(self.original_image, -self.angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect:
                self.collision_rect.center = self.rect.center

    def _update_movement_along_path(self, maze, game_area_x_offset=0):
        if not self.path or self.current_path_index >= len(self.path):
            return
            
        target = self.path[self.current_path_index]
        dx, dy = target[0] - self.x, target[1] - self.y
        dist = math.hypot(dx, dy)
        
        # Check if we've reached the waypoint
        if dist < 5:  # Close enough to waypoint
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                # Reached end of path
                return
            return
            
        # Move toward the waypoint
        if dist > 0:
            self.angle = math.degrees(math.atan2(dy, dx))
            move_x = (dx / dist) * self.speed
            move_y = (dy / dist) * self.speed
            
            next_x, next_y = self.x + move_x, self.y + move_y
            
            # Check for wall collision
            if not (maze and hasattr(maze, 'is_wall') and 
                    maze.is_wall(next_x, next_y, self.collision_rect.width, self.collision_rect.height)):
                self.x, self.y = next_x, next_y
                
        # Update rect position
        self.rect.center = (int(self.x), int(self.y))
        
        # Keep within game area
        game_play_area_height = get_setting("display", "HEIGHT", 1080)
        self.rect.clamp_ip(pygame.Rect(
            game_area_x_offset, 0, 
            get_setting("display", "WIDTH", 1920) - game_area_x_offset, 
            game_play_area_height
        ))
        
        # Update position from rect
        self.x, self.y = float(self.rect.centerx), float(self.rect.centery)
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

    def take_damage(self, amount):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                # Create explosion effect when enemy dies
                if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                    x, y = self.rect.center
                    self.asset_manager.game_controller._create_enemy_explosion(x, y)

    def draw(self, surface, camera=None):
        if not self.alive or not self.image:
            return
            
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            surface.blit(self.image, screen_rect)
        else:
            surface.blit(self.image, self.rect)
            
        # Draw health bar
        if self.alive:
            self._draw_health_bar(surface, camera)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect:
            return
            
        bar_w, bar_h = self.rect.width * 0.8, 5
        
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
        else:
            screen_rect = self.rect
            
        bar_x = screen_rect.centerx - bar_w / 2
        bar_y = screen_rect.top - bar_h - 3
        
        fill_w = bar_w * (self.health / self.max_health if self.max_health > 0 else 0)
        
        if self.health / self.max_health > 0.6:
            fill_color = GREEN
        elif self.health / self.max_health > 0.3:
            fill_color = YELLOW
        else:
            fill_color = RED
            
        pygame.draw.rect(surface, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
        
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h))
            
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)