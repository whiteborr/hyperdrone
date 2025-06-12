import heapq
import pygame
import logging
from typing import List, Tuple, Dict, Set, Optional

logger = logging.getLogger(__name__)

class PathManager:
    """
    Handles grid-based pathfinding and path validation for tower placement
    """
    def __init__(self, grid_width: int, grid_height: int, tile_size: int):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = tile_size
        self.grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
        self.spawn_points = []
        self.goal_point = None
        
    def set_grid(self, grid: List[List[int]]):
        """Set the grid directly from a 2D array"""
        if not grid or not grid[0]:
            logger.error("Invalid grid provided to PathManager")
            return
        self.grid_height = len(grid)
        self.grid_width = len(grid[0])
        self.grid = grid
        
    def set_spawn_points(self, points: List[Tuple[int, int]]):
        """Set spawn points for enemies"""
        self.spawn_points = points
        
    def set_goal_point(self, point: Tuple[int, int]):
        """Set the goal point that enemies try to reach"""
        self.goal_point = point
        
    def is_valid_position(self, row: int, col: int) -> bool:
        """Check if a position is within grid bounds"""
        return 0 <= row < self.grid_height and 0 <= col < self.grid_width
        
    def is_walkable(self, row: int, col: int) -> bool:
        """Check if a tile is walkable (not a wall or tower)"""
        if not self.is_valid_position(row, col):
            return False
        # Assuming: 0 = walkable path, 1 = wall/obstacle, 'T' = designated turret spot, 'U' = used turret spot
        return self.grid[row][col] != 1 and self.grid[row][col] != 'U'
        
    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get walkable neighboring tiles"""
        neighbors = []
        # Check 4 adjacent tiles (no diagonals)
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            new_row, new_col = row + dr, col + dc
            if self.is_walkable(new_row, new_col):
                neighbors.append((new_row, new_col))
        return neighbors
        
    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance heuristic for A* algorithm"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        A* pathfinding algorithm to find shortest path from start to goal
        Returns a list of (row, col) tuples representing the path
        """
        if not self.is_walkable(*start) or not self.is_walkable(*goal):
            logger.warning(f"Start {start} or goal {goal} is not walkable")
            return []
            
        # Priority queue for A*
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        # For path reconstruction
        came_from = {}
        
        # Cost from start to current node
        g_score = {start: 0}
        
        # Estimated cost from start to goal through current node
        f_score = {start: self.heuristic(start, goal)}
        
        # Set of nodes already evaluated
        closed_set = set()
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]  # Reverse to get start-to-goal order
                
            closed_set.add(current)
            
            for neighbor in self.get_neighbors(*current):
                if neighbor in closed_set:
                    continue
                    
                tentative_g_score = g_score.get(current, float('inf')) + 1
                
                if neighbor not in [item[1] for item in open_set] or tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
        logger.warning(f"No path found from {start} to {goal}")
        return []  # No path found
        
    def can_place_tower(self, row: int, col: int) -> bool:
        """
        Check if placing a tower at (row, col) would block all paths to the goal
        Returns True if tower can be placed, False otherwise
        """
        if not self.is_valid_position(row, col):
            return False
            
        # Special case: If the tile is marked as 'T' in the original grid,
        # it's a designated turret spot and should always allow placement
        if self.grid[row][col] == 'T':
            return True
            
        # For non-turret spots, check if it's walkable
        if not self.is_walkable(row, col):
            return False
            
        if not self.goal_point or not self.spawn_points:
            logger.error("Goal point or spawn points not set")
            return False
            
        # Temporarily mark the tile as a tower
        original_value = self.grid[row][col]
        self.grid[row][col] = 'T'
        
        # Check if at least one spawn point has a valid path to the goal
        has_valid_path = False
        for spawn in self.spawn_points:
            path = self.find_path(spawn, self.goal_point)
            if path:
                has_valid_path = True
                break
                
        # Restore the original grid value
        self.grid[row][col] = original_value
        
        return has_valid_path
        
    def grid_to_pixel(self, row: int, col: int) -> Tuple[int, int]:
        """Convert grid coordinates to pixel coordinates (center of tile)"""
        x = col * self.tile_size + self.tile_size // 2
        y = row * self.tile_size + self.tile_size // 2
        return (x, y)
        
    def pixel_to_grid(self, x: int, y: int) -> Tuple[int, int]:
        """Convert pixel coordinates to grid coordinates"""
        col = x // self.tile_size
        row = y // self.tile_size
        return (row, col)