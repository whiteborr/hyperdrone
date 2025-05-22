import pygame
import random

import game_settings as gs
from game_settings import (
    # Constants directly used by the Maze class
    TILE_SIZE, WIDTH, MAZE_ROWS, GAME_PLAY_AREA_HEIGHT, #
    BLUE, #
    ARCHITECT_VAULT_WALL_COLOR #
    # Other settings like colors could be gs.COLOR_NAME if preferred
)

class Maze: #
    def __init__(self, game_area_x_offset=0, maze_type="standard"): #
        """
        Initializes the Maze using the logic from the user's uploaded file.
        Args:
            game_area_x_offset (int): The horizontal offset from the left of the screen
                                      where the maze drawing area begins.
            maze_type (str): "standard" or "architect_vault" to determine styling.
        """
        self.game_area_x_offset = game_area_x_offset #
        self.maze_type = maze_type #

        # Use directly imported constants or gs.get_game_setting for dynamic values
        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE #
        self.actual_maze_rows = MAZE_ROWS #
        self.walls = [] #
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)] #
        self._generate_maze_from_uploaded_logic(0, 0) #
        self.walls = self._create_wall_lines_from_uploaded_logic() #


    def _generate_maze_from_uploaded_logic(self, row, col): #
        """
        Generates the maze using the Recursive Backtracker algorithm from the user's uploaded file.
        Modifies self.grid by carving paths (setting cells to 0).
        """
        self.grid[row][col] = 0 #
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)] #
        random.shuffle(directions) #

        for dr, dc in directions: #
            new_row, new_col = row + 2 * dr, col + 2 * dc #
            
            if 0 <= new_row < self.actual_maze_rows and 0 <= new_col < self.actual_maze_cols: #
                if self.grid[new_row][new_col] == 1: #
                    self.grid[row + dr][col + dc] = 0 #
                    self._generate_maze_from_uploaded_logic(new_row, new_col) #

    def _create_wall_lines_from_uploaded_logic(self): #
        """
        Creates wall line segments based on the logic from the user's uploaded file.
        This method can produce horizontal, vertical, and diagonal lines across wall cells.
        """
        lines = [] #
        ts = TILE_SIZE #
        for r in range(self.actual_maze_rows): #
            for c in range(self.actual_maze_cols): #
                if self.grid[r][c] == 1: #
                    x1 = c * ts #
                    y1 = r * ts #
                    
                    x2 = x1 + ts if (c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1) else x1 #
                    y2 = y1 + ts if (r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1) else y1 #
                    
                    if x1 != x2 or y1 != y2: #
                        lines.append(((x1, y1), (x2, y2))) #
        return lines #

    def draw(self, surface): #
        """Draws the maze walls."""
        wall_color = BLUE if self.maze_type == "standard" else ARCHITECT_VAULT_WALL_COLOR #
        wall_thickness = 2 if self.maze_type == "standard" else 3 #
        
        if not self.walls: #
            return #

        for line_segment in self.walls: #
            p1_relative, p2_relative = line_segment #
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) #
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) #
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, wall_thickness) #

    def draw_architect_vault(self, surface): #
        self.draw(surface) #

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height): #
        """
        Checks for collision between an object and the maze walls using logic from uploaded file.
        This method is used for entity-wall pixel-based collision, not directly by A* grid checks.
        """
        drone_rect = pygame.Rect(
            int(obj_center_x_abs - obj_width / 2), #
            int(obj_center_y_abs - obj_height / 2), #
            int(obj_width), #
            int(obj_height) #
        ) #

        for line_segment in self.walls: #
            p1_relative, p2_relative = line_segment #
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1]) #
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1]) #

            line_thickness_for_collision = 4 #
            wall_rect = pygame.Rect(
                min(abs_p1[0], abs_p2[0]) - line_thickness_for_collision // 2, #
                min(abs_p1[1], abs_p2[1]) - line_thickness_for_collision // 2, #
                abs(abs_p1[0] - abs_p2[0]) + line_thickness_for_collision, #
                abs(abs_p1[1] - abs_p2[1]) + line_thickness_for_collision #
            ) #
            if wall_rect.width < line_thickness_for_collision: wall_rect.width = line_thickness_for_collision #
            if wall_rect.height < line_thickness_for_collision: wall_rect.height = line_thickness_for_collision #
            
            if drone_rect.colliderect(wall_rect): #
                if drone_rect.clipline(abs_p1, abs_p2): #
                    return True #
        return False #

    def get_path_cells(self): #
        """
        Returns a list of (center_x_relative, center_y_relative) tuples for all path cells.
        Coordinates are relative to the maze's top-left (0,0), before game_area_x_offset.
        """
        path_cells_relative_centers = [] #
        if self.actual_maze_rows == 0 or self.actual_maze_cols == 0: #
            return path_cells_relative_centers #

        for r in range(self.actual_maze_rows): #
            for c in range(self.actual_maze_cols): #
                if self.grid[r][c] == 0: #
                    center_x_rel = c * TILE_SIZE + TILE_SIZE // 2 #
                    center_y_rel = r * TILE_SIZE + TILE_SIZE // 2 #
                    path_cells_relative_centers.append((center_x_rel, center_y_rel)) #
        return path_cells_relative_centers #

    def get_random_path_cell_center_abs(self): #
        """
        Returns the absolute screen coordinates (center_x, center_y) of a random path cell.
        Returns None if no path cells exist.
        """
        path_cells_rel = self.get_path_cells() #
        if not path_cells_rel: #
            return None #
        
        rel_center_x, rel_center_y = random.choice(path_cells_rel) #
        abs_center_x = rel_center_x + self.game_area_x_offset #
        abs_center_y = rel_center_y #
        return abs_center_x, abs_center_y #