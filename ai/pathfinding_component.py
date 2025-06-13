# ai/pathfinding_component.py
import math
import random
import logging
import pygame

from hyperdrone_core.pathfinding import a_star_search, find_wall_follow_target, find_alternative_target
from settings_manager import get_setting

logger = logging.getLogger(__name__)

class PathfinderComponent:
    def __init__(self, enemy):
        self.enemy = enemy
        
        # Pathfinding attributes
        self.path = []
        self.current_path_index = 0
        self.last_path_recalc_time = 0
        
        # Get tile size for calculations
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.PATH_RECALC_INTERVAL = 1000
        self.WAYPOINT_THRESHOLD = tile_size * 0.3
        
        # Stuck detection
        self.stuck_timer = 0
        self.last_pos_check = (enemy.x, enemy.y)
        self.STUCK_TIME_THRESHOLD_MS = 2500
        self.STUCK_MOVE_THRESHOLD = 0.5
        self.alternative_target = None
        self.alternative_target_timer = 0
        self.ALTERNATIVE_TARGET_TIMEOUT = 5000  # 5 seconds before trying primary target again

    def set_target(self, target_pos, maze, current_time_ms, game_area_x_offset=0):
        """Set a new destination and recalculate path if needed"""
        if not target_pos or not maze:
            self.path = []
            return
            
        self._recalculate_path(target_pos, maze, current_time_ms, game_area_x_offset)

    def _recalculate_path(self, target_pos, maze, current_time_ms, game_area_x_offset=0):
        """Calculate a path to the target position using A* pathfinding"""
        if not target_pos or not maze:
            self.path = []
            return
            
        # Check if we should use alternative target
        if self.alternative_target and current_time_ms - self.alternative_target_timer < self.ALTERNATIVE_TARGET_TIMEOUT:
            # Continue using alternative target
            target_pos = self._grid_to_pixel_center(self.alternative_target[0], self.alternative_target[1], game_area_x_offset)
        else:
            # Reset alternative target
            self.alternative_target = None
            
        # Calculate or recalculate path
        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms
            enemy_grid = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
            target_grid = self._pixel_to_grid(target_pos[0], target_pos[1], game_area_x_offset)
            
            # Validate grid positions
            if not (0 <= enemy_grid[0] < maze.actual_maze_rows and 0 <= enemy_grid[1] < maze.actual_maze_cols and 
                   0 <= target_grid[0] < maze.actual_maze_rows and 0 <= target_grid[1] < maze.actual_maze_cols):
                self.path = []
                return
                
            # Check if target is in a wall
            if hasattr(maze, 'grid') and maze.grid[target_grid[0]][target_grid[1]] == 1:
                self.path = []
                return
                
            # Try to find path to target
            grid_path = a_star_search(maze.grid, enemy_grid, target_grid, maze.actual_maze_rows, maze.actual_maze_cols)
            
            if grid_path and len(grid_path) > 1:
                # Path found
                self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path]
                self.current_path_index = 1
                
                # Reset alternative target if we found a path to primary target
                if not self.alternative_target:
                    self.alternative_target = None
            else:
                # No path found, try to find alternative target
                if not self.alternative_target:
                    alt_target = find_alternative_target(
                        maze, 
                        enemy_grid, 
                        target_grid, 
                        maze.actual_maze_rows, 
                        maze.actual_maze_cols
                    )
                    
                    if alt_target:
                        self.alternative_target = alt_target
                        self.alternative_target_timer = current_time_ms
                        
                        # Try to find path to alternative target
                        alt_path = a_star_search(
                            maze.grid, 
                            enemy_grid, 
                            alt_target, 
                            maze.actual_maze_rows, 
                            maze.actual_maze_cols
                        )
                        
                        if alt_path and len(alt_path) > 1:
                            self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in alt_path]
                            self.current_path_index = 1
                            return
                
                self.path = []
                
        # If no path and we have a target, at least face towards it
        if not self.path and target_pos:
            dx, dy = target_pos[0] - self.enemy.x, target_pos[1] - self.enemy.y
            if math.hypot(dx, dy) > 0:
                self.enemy.angle = math.degrees(math.atan2(dy, dx))

    def update_movement(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, speed_override=None):
        """Update movement along the calculated path and handle stuck detection"""
        # Check for stuck condition
        is_stuck = self._handle_stuck_logic(current_time_ms, delta_time_ms, maze, game_area_x_offset)
        if is_stuck:
            return True
            
        # Move along path if not stuck
        effective_speed = speed_override if speed_override is not None else self.enemy.speed
        if not self.path or self.current_path_index >= len(self.path):
            return False
            
        target = self.path[self.current_path_index]
        dx, dy = target[0] - self.enemy.x, target[1] - self.enemy.y
        dist = math.hypot(dx, dy)
        
        if dist < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                self.path = []
                return False
                
        target = self.path[self.current_path_index]
        dx, dy = target[0] - self.enemy.x, target[1] - self.enemy.y
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            self.enemy.angle = math.degrees(math.atan2(dy, dx))
            move_x, move_y = (dx/dist)*effective_speed, (dy/dist)*effective_speed
            next_x, next_y = self.enemy.x + move_x, self.enemy.y + move_y
            
            if not (maze and self.enemy.collision_rect and maze.is_wall(next_x, next_y, 
                                                                  self.enemy.collision_rect.width, 
                                                                  self.enemy.collision_rect.height)):
                self.enemy.x, self.enemy.y = next_x, next_y
        
        self.enemy.rect.center = (self.enemy.x, self.enemy.y)
        game_play_area_height = get_setting("display", "HEIGHT", 1080)
        self.enemy.rect.clamp_ip(pygame.Rect(game_area_x_offset, 0, 
                                       get_setting("display", "WIDTH", 1920) - game_area_x_offset, 
                                       game_play_area_height))
        self.enemy.x, self.enemy.y = self.enemy.rect.centerx, self.enemy.rect.centery
        if self.enemy.collision_rect:
            self.enemy.collision_rect.center = self.enemy.rect.center
            
        return False

    def _handle_stuck_logic(self, current_time_ms, delta_time_ms, maze, game_area_x_offset):
        """Handle stuck detection and resolution"""
        dist_moved = math.hypot(self.enemy.x - self.last_pos_check[0], self.enemy.y - self.last_pos_check[1])
        if dist_moved < self.STUCK_MOVE_THRESHOLD:
            self.stuck_timer += delta_time_ms
        else:
            self.stuck_timer = 0
            self.last_pos_check = (self.enemy.x, self.enemy.y)

        if self.stuck_timer > self.STUCK_TIME_THRESHOLD_MS:
            logger.warning(f"Enemy {id(self.enemy)} detected as stuck. Attempting to unstick.")
            
            # Try to find a path along the wall using A* pathfinding
            if maze and hasattr(maze, 'grid'):
                # Get current position in grid coordinates
                current_grid_pos = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
                
                # Find a target position along the wall
                wall_follow_target = find_wall_follow_target(
                    maze, 
                    current_grid_pos, 
                    maze.actual_maze_rows, 
                    maze.actual_maze_cols
                )
                
                if wall_follow_target:
                    # Convert target back to pixel coordinates
                    target_pixel = self._grid_to_pixel_center(wall_follow_target[0], wall_follow_target[1], game_area_x_offset)
                    
                    # Force a new path calculation to the wall-following target
                    self.path = []
                    self.last_path_recalc_time = 0
                    self._recalculate_path(target_pixel, maze, current_time_ms, game_area_x_offset)
                    self.stuck_timer = 0
                    return True
            
            # Fallback: try to get walkable tiles from maze
            walkable_tiles = []
            if hasattr(maze, 'get_walkable_tiles_abs'):
                walkable_tiles = maze.get_walkable_tiles_abs()
            elif hasattr(maze, 'get_path_cells_abs'):
                walkable_tiles = maze.get_path_cells_abs()
                
            if walkable_tiles:
                # Find tiles that are not too close to current position
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                viable_tiles = [p for p in walkable_tiles if tile_size * 3 < math.hypot(p[0] - self.enemy.x, p[1] - self.enemy.y) < tile_size * 12]
                if viable_tiles:
                    unstick_target = random.choice(viable_tiles)
                    # Force a new path calculation
                    self.path = []
                    self.last_path_recalc_time = 0
                    self._recalculate_path(unstick_target, maze, current_time_ms, game_area_x_offset)
                    self.stuck_timer = 0
                    return True
            
            # Last resort: move in a random direction
            angle = random.uniform(0, 2 * math.pi)
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            self.enemy.x += math.cos(angle) * tile_size * 2
            self.enemy.y += math.sin(angle) * tile_size * 2
            self.enemy.rect.center = (self.enemy.x, self.enemy.y)
            self.enemy.collision_rect.center = self.enemy.rect.center
            self.stuck_timer = 0
            return True
        return False

    def _pixel_to_grid(self, px, py, offset=0):
        """Convert pixel coordinates to grid coordinates"""
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return int(py / tile_size), int((px - offset) / tile_size)
        
    def _grid_to_pixel_center(self, r, c, offset=0):
        """Convert grid coordinates to pixel coordinates (center of cell)"""
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return (c*tile_size)+(tile_size/2)+offset, (r*tile_size)+(tile_size/2)