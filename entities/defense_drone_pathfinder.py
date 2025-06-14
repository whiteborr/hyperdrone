import pygame
import logging
from typing import List, Tuple, Optional
from entities.path_manager import PathManager
from entities.enemy_pathfinder import PathfindingEnemy
from constants import RED, YELLOW, GREEN, WHITE, DARK_GREY

logger = logging.getLogger(__name__)

class DefenseDronePathfinder(PathfindingEnemy):
    """
    Defense drone that uses A* pathfinding and displays the proper sprite
    """
    def __init__(self, grid_pos: Tuple[int, int], path_manager: PathManager, 
                 asset_manager, sprite_key: str,
                 speed: float = 1.0, health: int = 100, damage: int = 10):
        super().__init__(grid_pos, path_manager, speed, health, damage)
        
        # Load the proper sprite
        self.sprite_key = sprite_key
        self.asset_manager = asset_manager
        self.load_sprite()
        
    def load_sprite(self):
        """Load the proper sprite for this defense drone"""
        if not self.asset_manager:
            logger.warning(f"No asset manager provided for DefenseDronePathfinder")
            return
            
        loaded_image = self.asset_manager.get_image(self.sprite_key)
        if loaded_image:
            try:
                # Scale the image to the proper size
                self.size = self.path_manager.tile_size * 0.8
                self.original_image = pygame.transform.smoothscale(loaded_image, (self.size, self.size))
                self.image = self.original_image.copy()
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                self.collision_rect = self.rect.inflate(-4, -4)
            except Exception as e:
                logger.error(f"Error loading sprite for DefenseDronePathfinder: {e}")
        else:
            logger.warning(f"Could not load sprite with key '{self.sprite_key}' for DefenseDronePathfinder")
            
    def draw(self, surface: pygame.Surface, camera=None):
        """Draw the enemy with camera transformation if provided"""
        if not self.image or not self.rect:
            return
            
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            surface.blit(self.image, screen_rect)
        else:
            surface.blit(self.image, self.rect)
            
        # Draw health bar
        if self.alive:
            self._draw_health_bar(surface, camera)
            
    def _draw_health_bar(self, surface: pygame.Surface, camera=None):
        """Draw a health bar above the enemy"""
        if not self.alive or not self.rect:
            return
            
        # Health bar dimensions
        bar_width = self.rect.width * 0.8
        bar_height = 4
        
        # Position above the enemy
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 2
        
        # Apply camera transformation if provided
        if camera:
            bar_x, bar_y = camera.apply_to_pos((bar_x, bar_y))
            bar_width *= camera.zoom_level
            bar_height *= camera.zoom_level
            
        # Calculate health percentage
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        
        # Draw background
        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, bar_height))
        
        # Draw filled portion
        if filled_width > 0:
            # Color based on health percentage
            if health_percentage < 0.3:
                fill_color = RED
            elif health_percentage < 0.6:
                fill_color = YELLOW
            else:
                fill_color = GREEN
                
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
            
        # Draw border
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)