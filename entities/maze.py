# entities/maze.py
import pygame
import random
import logging
import math
from settings_manager import get_setting
from constants import BLUE, RED, GOLD, ARCHITECT_VAULT_WALL_COLOR, DARK_PURPLE, WHITE

logger = logging.getLogger(__name__)

class Maze: 
    def __init__(self, game_area_x_offset=0, maze_type="standard"): 
        self.game_area_x_offset = game_area_x_offset 
        self.maze_type = maze_type 

        # Dynamically calculate dimensions based on current game settings
        width = get_setting("display", "WIDTH", 1920)
        height = get_setting("display", "HEIGHT", 1080)
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.bottom_panel_height = get_setting("display", "BOTTOM_PANEL_HEIGHT", 120)

        # Calculate maze dimensions to use all available space within the border
        self.available_width = width - self.game_area_x_offset
        self.available_height = height - self.bottom_panel_height
        
        # Calculate dimensions to ensure the maze extends to the borders
        self.actual_maze_cols = self.available_width // self.tile_size
        self.actual_maze_rows = self.available_height // self.tile_size
        
        # Grid: 1 for wall, 0 for path
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)] 
        
        if self.actual_maze_rows > 0 and self.actual_maze_cols > 0:
            self._generate_maze_grid(1, 1)

        # This list of lines is for both drawing and collision detection
        self.walls = self._create_wall_lines()
        
        # Add border lines around the perimeter
        self.border_lines = self._create_border_lines()
        
        # For corrupted effect
        self.corruption_pulse = 0

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

    def _create_wall_lines(self):
        lines = [] 
        ts = self.tile_size 
        
        for r in range(self.actual_maze_rows): 
            for c in range(self.actual_maze_cols): 
                if self.grid[r][c] == 1: 
                    x1, y1 = c * ts, r * ts 
                    
                    # Connect to adjacent wall tiles
                    x2 = x1 + ts if (c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1) else x1 
                    y2 = y1 + ts if (r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1) else y1 
                    
                    # Handle edge cases for right and bottom borders
                    if c == self.actual_maze_cols - 1:
                        x2 = self.available_width
                    if r == self.actual_maze_rows - 1:
                        y2 = self.available_height
                    
                    if x1 != x2 or y1 != y2: 
                        lines.append(((x1, y1), (x2, y2)))
        
        return lines
        
    def _create_border_lines(self):
        # Create the four border lines exactly at the edges
        border_lines = [
            # Top border
            ((0, 0), (self.available_width, 0)),
            # Right border
            ((self.available_width, 0), (self.available_width, self.available_height)),
            # Bottom border
            ((0, self.available_height), (self.available_width, self.available_height)),
            # Left border
            ((0, 0), (0, self.available_height))
        ]
        
        return border_lines

    def draw(self, surface, camera=None): 
        # Determine wall color based on maze type
        if self.maze_type == "architect_vault":
            wall_color = ARCHITECT_VAULT_WALL_COLOR
        elif self.maze_type == "corrupted":
            # Create a pulsing, corrupted color effect
            self.corruption_pulse += 0.05
            pulse = (math.sin(self.corruption_pulse) + 1) / 2 # Oscillates between 0 and 1
            r = int(70 + pulse * 60)
            g = int(20 + pulse * 40)
            b = int(90 + pulse * 60)
            wall_color = (r, g, b)
        else:
            wall_color = BLUE

        wall_thickness = 2
        border_thickness = 3
        border_color = RED if self.maze_type == "architect_vault" else GOLD
        
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
        walkable_tiles = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0:
                    abs_x = c * self.tile_size + self.tile_size // 2 + self.game_area_x_offset
                    abs_y = r * self.tile_size + self.tile_size // 2
                    walkable_tiles.append((abs_x, abs_y))
        return walkable_tiles
