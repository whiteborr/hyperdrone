# entities/maze.py
import pygame
import random
import logging

import game_settings as gs

logger = logging.getLogger(__name__)

class Maze: 
    def __init__(self, game_area_x_offset=0, maze_type="standard"): 
        self.game_area_x_offset = game_area_x_offset 
        self.maze_type = maze_type 

        # Dynamically calculate dimensions based on current game settings
        width = gs.get_game_setting("WIDTH")
        height = gs.get_game_setting("HEIGHT")
        self.tile_size = gs.get_game_setting("TILE_SIZE")
        self.bottom_panel_height = gs.get_game_setting("BOTTOM_PANEL_HEIGHT")

        self.actual_maze_cols = (width - self.game_area_x_offset) // self.tile_size
        self.actual_maze_rows = (height - self.bottom_panel_height) // self.tile_size
        
        # Grid: 1 for wall, 0 for path
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)] 
        
        if self.actual_maze_rows > 0 and self.actual_maze_cols > 0:
            self._generate_maze_grid(1, 1)
            self._create_perimeter()

        # This list of lines is for both drawing and collision detection
        self.walls = self._create_wall_lines()
        
        # Add border lines around the perimeter
        self.border_lines = self._create_border_lines() 

    def _generate_maze_grid(self, row, col): 
        self.grid[row][col] = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)] 
        random.shuffle(directions) 

        for dr, dc in directions: 
            new_row, new_col = row + 2 * dr, col + 2 * dc 
            if 0 <= new_row < self.actual_maze_rows and 0 <= new_col < self.actual_maze_cols: 
                if self.grid[new_row][new_col] == 1: 
                    self.grid[row + dr][col + dc] = 0 
                    self._generate_maze_grid(new_row, new_col) 

    def _create_perimeter(self):
        """Ensures the maze is fully enclosed by walls."""
        if self.actual_maze_rows == 0 or self.actual_maze_cols == 0: return
        for c in range(self.actual_maze_cols):
            self.grid[0][c] = 1
            self.grid[self.actual_maze_rows - 1][c] = 1
        for r in range(self.actual_maze_rows):
            self.grid[r][0] = 1
            self.grid[r][self.actual_maze_cols - 1] = 1

    def _create_wall_lines(self):
        """
        Creates wall line segments based on the original implementation.
        """
        lines = [] 
        ts = self.tile_size 
        for r in range(self.actual_maze_rows): 
            for c in range(self.actual_maze_cols): 
                if self.grid[r][c] == 1: 
                    x1, y1 = c * ts, r * ts 
                    
                    # Connect to adjacent wall tiles
                    x2 = x1 + ts if (c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1) else x1 
                    y2 = y1 + ts if (r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1) else y1 
                    
                    if x1 != x2 or y1 != y2: 
                        lines.append(((x1, y1), (x2, y2)))
        return lines
        
    def _create_border_lines(self):
        """
        Creates border lines around the perimeter of the maze.
        """
        width = self.actual_maze_cols * self.tile_size
        full_height = gs.get_game_setting("HEIGHT") - self.bottom_panel_height
        
        # Create the four border lines
        border_lines = [
            # Top border
            ((0, 0), (width, 0)),
            # Right border
            ((width, 0), (width, full_height)),
            # Bottom border - aligned exactly with the top of the HUD
            ((0, full_height), (width, full_height)),
            # Left border
            ((0, 0), (0, full_height))
        ]
        
        return border_lines

    def draw(self, surface, camera=None): 
        """
        Draws the maze walls using the pre-computed list of line segments.
        """
        wall_color = gs.ARCHITECT_VAULT_WALL_COLOR if self.maze_type == "architect_vault" else gs.BLUE
        wall_thickness = 2
        border_thickness = 3
        border_color = gs.RED if self.maze_type == "architect_vault" else gs.GOLD
        
        if not self.walls: return

        # Draw internal walls
        for line_segment in self.walls: 
            p1_relative, p2_relative = line_segment 
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) 
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) 
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, wall_thickness)
            
        # Draw border lines
        for line_segment in self.border_lines:
            p1_relative, p2_relative = line_segment
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])
            pygame.draw.line(surface, border_color, abs_p1, abs_p2, border_thickness) 

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height): 
        """
        Collision check based on the actual line segments using clipline.
        """
        obj_rect = pygame.Rect(
            int(obj_center_x_abs - obj_width / 2), 
            int(obj_center_y_abs - obj_height / 2), 
            int(obj_width), 
            int(obj_height) 
        ) 

        # Check collision with internal walls
        for line_segment in self.walls: 
            p1_relative, p2_relative = line_segment 
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) 
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) 

            if obj_rect.clipline(abs_p1, abs_p2):
                return True # Collision detected
                
        # Check collision with border lines
        for line_segment in self.border_lines:
            p1_relative, p2_relative = line_segment
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])
            
            if obj_rect.clipline(abs_p1, abs_p2):
                return True # Collision detected
                
        return False # No collision with any wall line segment

    def get_walkable_tiles_abs(self):
        """
        Returns a list of all walkable floor tiles as absolute pixel center coordinates.
        """
        walkable_tiles = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0:
                    abs_x = c * self.tile_size + self.tile_size // 2 + self.game_area_x_offset
                    abs_y = r * self.tile_size + self.tile_size // 2
                    walkable_tiles.append((abs_x, abs_y))
        return walkable_tiles