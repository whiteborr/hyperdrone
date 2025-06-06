# entities/maze.py
import pygame
import random
import logging

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, MAZE_ROWS, GAME_PLAY_AREA_HEIGHT, 
    BLUE, WHITE, ARCHITECT_VAULT_WALL_COLOR
)

logger = logging.getLogger(__name__)

class Maze: 
    def __init__(self, game_area_x_offset=0, maze_type="standard"): 
        self.game_area_x_offset = game_area_x_offset 
        self.maze_type = maze_type 

        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE 
        self.actual_maze_rows = MAZE_ROWS 
        
        # Grid: 1 for wall, 0 for path
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)] 
        
        # This populates self.grid with a maze layout
        if self.actual_maze_rows > 0 and self.actual_maze_cols > 0:
            self._generate_maze_grid(0, 0)

        # The 'walls' attribute is a list of line segments.
        # This is the single source of truth for both drawing and collision detection.
        self.walls = self._create_wall_lines() 

    def _generate_maze_grid(self, row, col): 
        """
        Generates the maze grid using Recursive Backtracker. Modifies self.grid.
        """
        self.grid[row][col] = 0 # Mark current cell as part of the path
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)] 
        random.shuffle(directions) 

        for dr, dc in directions: 
            new_row, new_col = row + 2 * dr, col + 2 * dc 
            
            if 0 <= new_row < self.actual_maze_rows and 0 <= new_col < self.actual_maze_cols: 
                if self.grid[new_row][new_col] == 1: 
                    self.grid[row + dr][col + dc] = 0 
                    self._generate_maze_grid(new_row, new_col) 

    def _create_wall_lines(self):
        """
        Creates wall line segments based on the exact logic from your original working file.
        This creates the intended visual style with gaps for the player to navigate.
        """
        lines = [] 
        ts = TILE_SIZE 
        for r in range(self.actual_maze_rows): 
            for c in range(self.actual_maze_cols): 
                if self.grid[r][c] == 1: 
                    x1, y1 = c * ts, r * ts 
                    
                    # Connect to adjacent wall tiles, creating the unique line-based look
                    x2 = x1 + ts if (c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1) else x1 
                    y2 = y1 + ts if (r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1) else y1 
                    
                    if x1 != x2 or y1 != y2: 
                        lines.append(((x1, y1), (x2, y2))) 
        return lines 

    def draw(self, surface): 
        """
        Draws the maze walls using the pre-computed list of line segments.
        """
        wall_color = ARCHITECT_VAULT_WALL_COLOR if self.maze_type == "architect_vault" else BLUE
        wall_thickness = 3 if self.maze_type == "architect_vault" else 2
        
        if not self.walls:
            return

        for line_segment in self.walls: 
            p1_relative, p2_relative = line_segment 
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) 
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) 
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, wall_thickness) 

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height): 
        """
        Collision check based on the actual line segments using clipline.
        This ensures collision detection matches exactly what is drawn on screen.
        """
        obj_rect = pygame.Rect(
            int(obj_center_x_abs - obj_width / 2), 
            int(obj_center_y_abs - obj_height / 2), 
            int(obj_width), 
            int(obj_height) 
        ) 

        for line_segment in self.walls: 
            p1_relative, p2_relative = line_segment 
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) 
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) 

            if obj_rect.clipline(abs_p1, abs_p2):
                return True # Collision detected
        return False # No collision with any wall line segment

    def get_walkable_tiles_abs(self):
        """
        Returns a list of all walkable floor tiles as absolute pixel center coordinates.
        This is the reliable way to get spawn points.
        """
        walkable_tiles = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0: # 0 represents a path
                    abs_x = c * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    abs_y = r * TILE_SIZE + TILE_SIZE // 2
                    walkable_tiles.append((abs_x, abs_y))
        return walkable_tiles
