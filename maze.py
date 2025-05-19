import random

import pygame

from game_settings import BLUE, TILE_SIZE, WIDTH, MAZE_ROWS

class Maze:
    def __init__(self, game_area_x_offset=0):
        self.game_area_x_offset = game_area_x_offset
        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE
        self.actual_maze_rows = MAZE_ROWS

        self.walls = [] # Will store tuples: (line_segment, wall_type)

        if self.actual_maze_cols <= 0 or self.actual_maze_rows <= 0:
            print(f"ERROR: Maze dimensions are invalid. Cols: {self.actual_maze_cols}, Rows: {self.actual_maze_rows}.")
            self.actual_maze_cols = max(1, self.actual_maze_cols)
            self.actual_maze_rows = max(1, self.actual_maze_rows)
            self.grid = [[1]] # Minimal grid
            # Add perimeter even for minimal/error grid, they will be relative to 0,0 of this small grid
            self.add_perimeter_walls()
            return

        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]
        if self.actual_maze_cols > 0 and self.actual_maze_rows > 0:
            self.generate_maze(0, 0)
        
        self.create_internal_wall_lines() # Generates internal walls
        self.add_perimeter_walls()      # Adds perimeter walls

    def generate_maze(self, row, col):
        if not (0 <= row < self.actual_maze_rows and 0 <= col < self.actual_maze_cols):
            return
        self.grid[row][col] = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(directions)

        for dr, dc in directions:
            wall_row, wall_col = row + dr, col + dc
            new_row, new_col = row + 2 * dr, col + 2 * dc

            if (0 <= new_row < self.actual_maze_rows and \
                0 <= new_col < self.actual_maze_cols and \
                self.grid[new_row][new_col] == 1):
                if (0 <= wall_row < self.actual_maze_rows and \
                    0 <= wall_col < self.actual_maze_cols):
                    self.grid[wall_row][wall_col] = 0
                    self.generate_maze(new_row, new_col)

    def create_internal_wall_lines(self):
        """
        Generates internal maze wall lines and adds them to self.walls
        with type "internal". Coordinates are relative.
        """
        internal_lines = []
        for r_idx in range(self.actual_maze_rows):
            for c_idx in range(self.actual_maze_cols):
                if self.grid[r_idx][c_idx] == 1:
                    x1_rel = c_idx * TILE_SIZE
                    y1 = r_idx * TILE_SIZE
                    x2_rel = x1_rel
                    if c_idx + 1 < self.actual_maze_cols and self.grid[r_idx][c_idx + 1] == 1:
                        x2_rel = x1_rel + TILE_SIZE
                    y2 = y1
                    if r_idx + 1 < self.actual_maze_rows and self.grid[r_idx + 1][c_idx] == 1:
                        y2 = y1 + TILE_SIZE
                    if x1_rel != x2_rel or y1 != y2:
                        internal_lines.append(((x1_rel, y1), (x2_rel, y2)))
        
        for line_segment in internal_lines:
            self.walls.append((line_segment, "internal"))

    def add_perimeter_walls(self):
        """Adds the four outer border walls to self.walls with type "perimeter".
           Coordinates are relative to the maze's game area origin.
        """
        top_left_rel_x = 0
        top_right_rel_x = self.actual_maze_cols * TILE_SIZE
        top_y = 0
        bottom_y = self.actual_maze_rows * TILE_SIZE
        left_x_rel = 0
        right_x_rel = self.actual_maze_cols * TILE_SIZE

        perimeter_segments = [
            (((top_left_rel_x, top_y), (top_right_rel_x, top_y)), "perimeter"),        # Top
            (((top_left_rel_x, bottom_y), (top_right_rel_x, bottom_y)), "perimeter"),  # Bottom
            (((left_x_rel, top_y), (left_x_rel, bottom_y)), "perimeter"),              # Left
            (((right_x_rel, top_y), (right_x_rel, bottom_y)), "perimeter")             # Right
        ]
        self.walls.extend(perimeter_segments)

    def draw(self, surface):
        for line_segment, wall_type in self.walls: # Unpack the tuple
            p1_rel, p2_rel = line_segment
            
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])
            pygame.draw.line(surface, BLUE, abs_p1, abs_p2, 2)

    def is_wall(self, abs_x, abs_y, width, height):
        """
        Checks for collision with walls.
        Returns the type of wall hit ("internal", "perimeter") or None.
        """
        object_rect_abs = pygame.Rect(
            abs_x - width / 2,
            abs_y - height / 2,
            width,
            height
        )

        for line_segment, wall_type in self.walls: # Unpack type here
            p1_rel, p2_rel = line_segment
            
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])

            line_thickness_for_collision = 4 # Make collision rect a bit thicker than visual line
            wall_rect = pygame.Rect(min(abs_p1[0], abs_p2[0]) - line_thickness_for_collision // 2,
                                    min(abs_p1[1], abs_p2[1]) - line_thickness_for_collision // 2,
                                    abs(abs_p1[0] - abs_p2[0]) + line_thickness_for_collision,
                                    abs(abs_p1[1] - abs_p2[1]) + line_thickness_for_collision)
            
            # Ensure rect has some dimension for purely horizontal/vertical lines
            if wall_rect.width < line_thickness_for_collision : wall_rect.width = line_thickness_for_collision
            if wall_rect.height < line_thickness_for_collision : wall_rect.height = line_thickness_for_collision


            if object_rect_abs.colliderect(wall_rect):
                return wall_type # Return the type of wall hit
        return None # No collision

    def get_path_cells(self):
        path_cells_relative = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0:
                    center_x_rel = c * TILE_SIZE + TILE_SIZE // 2
                    center_y_rel = r * TILE_SIZE + TILE_SIZE // 2
                    path_cells_relative.append((center_x_rel, center_y_rel))
        return path_cells_relative