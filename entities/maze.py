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
        tile_size = gs.get_game_setting("TILE_SIZE")

        self.actual_maze_cols = (width - self.game_area_x_offset) // tile_size
        self.actual_maze_rows = height // tile_size
        
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)] 
        
        if self.actual_maze_rows > 0 and self.actual_maze_cols > 0:
            self._generate_maze_grid(1, 1)
            self._create_perimeter()
            self._punch_holes_in_walls(hole_probability=0.15)

        self.walls = self._create_wall_lines() 

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

    def _punch_holes_in_walls(self, hole_probability):
        """
        Intelligently finds straight wall segments and punches a hole in the middle
        to create playable gaps that bullets can pass through.
        """
        for r in range(1, self.actual_maze_rows - 1):
            for c in range(1, self.actual_maze_cols - 2):
                if self.grid[r][c - 1] == 1 and self.grid[r][c] == 1 and self.grid[r][c + 1] == 1:
                    if random.random() < hole_probability:
                        self.grid[r][c] = 0

        for r in range(1, self.actual_maze_rows - 2):
            for c in range(1, self.actual_maze_cols - 1):
                if self.grid[r - 1][c] == 1 and self.grid[r][c] == 1 and self.grid[r + 1][c] == 1:
                    if random.random() < hole_probability:
                        self.grid[r][c] = 0

    def _create_perimeter(self):
        if self.actual_maze_rows == 0 or self.actual_maze_cols == 0: return
        for c in range(self.actual_maze_cols):
            self.grid[0][c] = 1
            self.grid[self.actual_maze_rows - 1][c] = 1
        for r in range(self.actual_maze_rows):
            self.grid[r][0] = 1
            self.grid[r][self.actual_maze_cols - 1] = 1

    def _create_wall_lines(self):
        lines = set()
        ts = gs.TILE_SIZE
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 1:
                    x1, y1 = c * ts, r * ts
                    
                    if c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1:
                        lines.add( ((x1, y1), (x1 + ts, y1)) )
                    
                    if r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1:
                        lines.add( ((x1, y1), (x1, y1 + ts)) )
                        
                    if r + 1 < self.actual_maze_rows and c + 1 < self.actual_maze_cols and self.grid[r+1][c+1] == 1:
                         lines.add( ((x1, y1), (x1 + ts, y1 + ts)) )

                    if r + 1 < self.actual_maze_rows and c - 1 >= 0 and self.grid[r+1][c-1] == 1:
                         lines.add( ((x1, y1), (x1 - ts, y1 + ts)) )
        return list(lines)

    def draw(self, surface, camera=None): 
        wall_color = gs.ARCHITECT_VAULT_WALL_COLOR if self.maze_type == "architect_vault" else gs.BLUE
        wall_thickness = 3 if self.maze_type == "architect_vault" else 2
        
        if not self.walls:
            return

        for line_segment in self.walls: 
            p1_relative, p2_relative = line_segment 
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) 
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) 
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, wall_thickness) 

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height): 
        points_to_check = [
            (obj_center_x_abs - obj_width / 2, obj_center_y_abs - obj_height / 2),
            (obj_center_x_abs + obj_width / 2, obj_center_y_abs - obj_height / 2),
            (obj_center_x_abs - obj_width / 2, obj_center_y_abs + obj_height / 2),
            (obj_center_x_abs + obj_width / 2, obj_center_y_abs + obj_height / 2)
        ]

        for px, py in points_to_check:
            grid_c = int((px - self.game_area_x_offset) / gs.TILE_SIZE)
            grid_r = int(py / gs.TILE_SIZE)

            if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
                if self.grid[grid_r][grid_c] == 1:
                    return True
            else:
                return True
        return False

    def get_walkable_tiles_abs(self):
        walkable_tiles = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0:
                    abs_x = c * gs.TILE_SIZE + gs.TILE_SIZE // 2 + self.game_area_x_offset
                    abs_y = r * gs.TILE_SIZE + gs.TILE_SIZE // 2
                    walkable_tiles.append((abs_x, abs_y))
        return walkable_tiles