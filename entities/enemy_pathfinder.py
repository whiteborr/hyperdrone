import pygame
import logging
from typing import List, Tuple, Optional
from entities.path_manager import PathManager
from constants import RED, GREEN, BLUE

logger = logging.getLogger(__name__)

class PathfindingEnemy(pygame.sprite.Sprite):
    """
    Enemy that uses A* pathfinding to navigate to a goal
    """
    def __init__(self, grid_pos: Tuple[int, int], path_manager: PathManager, 
                 speed: float = 1.0, health: int = 100, damage: int = 10):
        super().__init__()
        self.grid_pos = grid_pos
        self.path_manager = path_manager
        self.speed = speed
        self.health = health
        self.max_health = health
        self.damage = damage
        self.alive = True
        
        # Position in pixels (add game area offset)
        pixel_pos = path_manager.grid_to_pixel(*grid_pos)
        self.x, self.y = float(pixel_pos[0] + 300), float(pixel_pos[1])
        
        # Debug: log the actual grid position being used
        logger.info(f"Enemy created at grid {grid_pos}, pixel ({self.x}, {self.y})")
        
        # Create a simple sprite
        self.size = path_manager.tile_size // 2
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(RED)  # Red enemy
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect = self.rect.inflate(-4, -4)
        
        # Pathfinding variables
        self.path = []
        self.current_target_index = 0
        self.needs_path_recalculation = True
        
    def calculate_path(self):
        """Calculate path from current position to goal"""
        if not self.path_manager.goal_point:
            logger.error("Goal point not set in path manager")
            return
            
        # Convert pixel position to grid position (subtract game area offset first)
        adjusted_x = int(self.x - 300)  # Remove the game area offset
        current_grid_pos = self.path_manager.pixel_to_grid(adjusted_x, int(self.y))
        
        # Find path to goal
        self.path = self.path_manager.find_path(current_grid_pos, self.path_manager.goal_point)
        self.current_target_index = 0
        self.needs_path_recalculation = False
        
    def update(self):
        """Update enemy position and state"""
        if not self.alive:
            return
            
        # Check if we need to recalculate the path
        if self.needs_path_recalculation or not self.path:
            self.calculate_path()
            # If still no path after calculation, stop trying to recalculate
            if not self.path:
                self.needs_path_recalculation = False
                return
            
        # If we have a path, follow it
        if self.path and self.current_target_index < len(self.path):
            # Get current target tile center in pixels
            target_grid_pos = self.path[self.current_target_index]
            target_pixel_pos = self.path_manager.grid_to_pixel(*target_grid_pos)
            # Add game area offset
            target_pixel_pos = (target_pixel_pos[0] + 300, target_pixel_pos[1])
            

            
            # Calculate direction to target
            dx = target_pixel_pos[0] - self.x
            dy = target_pixel_pos[1] - self.y
            distance = (dx**2 + dy**2)**0.5
            
            # If we're close enough to the target, move to the next one
            if distance < self.speed * 2:  # Increased threshold
                self.current_target_index += 1
                # If we've reached the goal
                if self.current_target_index >= len(self.path):
                    self.reach_goal()
                    return
            else:
                # Move towards target
                if distance > 0:
                    dx, dy = dx / distance, dy / distance
                self.x += dx * self.speed * 2  # Increased speed multiplier
                self.y += dy * self.speed * 2
                
            # Update rect position
            self.rect.center = (int(self.x), int(self.y))
            self.collision_rect.center = self.rect.center
            
    def take_damage(self, amount: int):
        """Take damage and check if dead"""
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            
    def reach_goal(self):
        """Called when enemy reaches the goal"""
        logger.info("Enemy reached the goal!")
        # Damage the core reactor directly when reaching goal
        if hasattr(self, 'path_manager') and hasattr(self.path_manager, 'game_controller'):
            game_controller = self.path_manager.game_controller
            if hasattr(game_controller, 'combat_controller') and game_controller.combat_controller.core_reactor:
                damage = getattr(self, 'damage', 25)
                logger.info(f"Enemy damaging core for {damage} damage")
                game_controller.combat_controller.core_reactor.take_damage(damage, game_controller)
        self.alive = False
        
    def trigger_path_recalculation(self):
        """Mark that this enemy needs to recalculate its path"""
        self.needs_path_recalculation = True
        
    def draw_path(self, surface: pygame.Surface, camera=None):
        """Debug method to draw the enemy's path"""
        if not self.path:
            return
            
        # Convert path to pixel coordinates
        pixel_path = [self.path_manager.grid_to_pixel(*pos) for pos in self.path]
        
        # No camera transformation
            
        # Draw path as lines
        if len(pixel_path) > 1:
            pygame.draw.lines(surface, GREEN, False, pixel_path, 2)
            
        # Draw current target
        if self.current_target_index < len(pixel_path):
            target = pixel_path[self.current_target_index]
            pygame.draw.circle(surface, BLUE, target, 5)