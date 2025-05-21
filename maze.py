import random
import pygame

from game_settings import (
    BLUE, TILE_SIZE, WIDTH, MAZE_ROWS,
    ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR # Import vault colors
)

class Maze:
    def __init__(self, game_area_x_offset=0, maze_type="standard"): # Added maze_type
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type # Store the maze type

        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE
        self.actual_maze_rows = MAZE_ROWS

        self.walls = [] # Will store tuples: (line_segment, wall_type)

        if self.actual_maze_cols <= 0 or self.actual_maze_rows <= 0:
            print(f"ERROR: Maze dimensions are invalid. Cols: {self.actual_maze_cols}, Rows: {self.actual_maze_rows}.")
            self.actual_maze_cols = max(1, self.actual_maze_cols) # Ensure at least 1x1
            self.actual_maze_rows = max(1, self.actual_maze_rows)
            self.grid = [[0]] # Minimal grid (a single path cell)
            self.create_wall_lines_from_grid() # Create walls for this minimal grid
            return

        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]
        
        self.generate_maze(0, 0) # Start generation from top-left
        
        if self.maze_type == "architect_vault":
            # self.open_up_vault_maze(ratio_to_remove=0.1) # Optional: make vault more open
            pass

        self.create_wall_lines_from_grid()

    def generate_maze(self, row, col):
        """
        Generates the maze using a Recursive Backtracker algorithm.
        Marks cells as paths (0) in self.grid.
        """
        if not (0 <= row < self.actual_maze_rows and 0 <= col < self.actual_maze_cols):
            return # Out of bounds
        
        self.grid[row][col] = 0 # Mark current cell as path
        
        directions = [(0, 1, "E"), (0, -1, "W"), (1, 0, "S"), (-1, 0, "N")] # dx, dy, direction_char
        random.shuffle(directions)

        for dr, dc, direction_char in directions:
            # Neighboring cell in the direction of the wall to be broken
            wall_row, wall_col = row + dr, col + dc
            # Cell beyond the wall
            new_row, new_col = row + 2 * dr, col + 2 * dc

            # Check if the cell beyond the wall is within bounds and is a wall (not yet visited)
            if (0 <= new_row < self.actual_maze_rows and \
                0 <= new_col < self.actual_maze_cols and \
                self.grid[new_row][new_col] == 1):
                
                # Also ensure the wall cell itself is within bounds (it should be if new_row/col is)
                if (0 <= wall_row < self.actual_maze_rows and \
                    0 <= wall_col < self.actual_maze_cols):
                    
                    self.grid[wall_row][wall_col] = 0 # Break down the wall
                    self.generate_maze(new_row, new_col) # Recursively visit the new cell

    def create_wall_lines_from_grid(self):
        """
        Creates line segments for drawing the maze walls based on the self.grid.
        A wall line is drawn on the edge of a path cell (0) if the adjacent cell in that direction
        is a wall cell (1) or if it's a boundary of the maze.
        Stores lines in self.walls as ((p1, p2), "type").
        Coordinates are relative to the maze's game area origin (top-left of the maze grid).
        """
        self.walls = []
        ts = TILE_SIZE

        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                # Check North wall for cell (r,c)
                # A North wall exists if we are at the top row (r=0) OR the cell above (r-1,c) is a wall (1)
                # AND the current cell (r,c) itself is a path (0) - we only draw walls for paths.
                # This logic was slightly off. We should draw walls *of* path cells.
                # If grid[r][c] is a path (0):
                if self.grid[r][c] == 0:
                    # Check cell to the NORTH
                    if r == 0 or self.grid[r-1][c] == 1:
                        p1 = (c * ts, r * ts)
                        p2 = ((c + 1) * ts, r * ts)
                        self.walls.append(((p1, p2), "N"))
                    
                    # Check cell to the WEST
                    if c == 0 or self.grid[r][c-1] == 1:
                        p1 = (c * ts, r * ts)
                        p2 = (c * ts, (r + 1) * ts)
                        self.walls.append(((p1, p2), "W"))
                
                # Always draw the bottom boundary wall for the last row of path cells
                if r == self.actual_maze_rows - 1 and self.grid[r][c] == 0:
                    p1 = (c * ts, (r + 1) * ts)
                    p2 = ((c + 1) * ts, (r + 1) * ts)
                    self.walls.append(((p1, p2), "S_boundary"))

                # Always draw the right boundary wall for the last column of path cells
                if c == self.actual_maze_cols - 1 and self.grid[r][c] == 0:
                    p1 = ((c + 1) * ts, r * ts)
                    p2 = ((c + 1) * ts, (r + 1) * ts)
                    self.walls.append(((p1, p2), "E_boundary"))
        
        # The above logic might miss some walls or create duplicates.
        # A more common approach for drawing from a grid where 0=path, 1=wall:
        # Iterate all cells. If a cell is a path, check its N,S,E,W neighbors.
        # If a neighbor is a wall (or boundary), draw the shared edge.
        # This can lead to drawing lines twice (e.g. S wall of cell A is N wall of cell B).
        #
        # Simpler: Iterate all cells. If grid[r][c] is a path (0):
        #   Draw its TOP wall if cell (r-1,c) is a wall (1) OR r=0.
        #   Draw its LEFT wall if cell (r,c-1) is a wall (1) OR c=0.
        # Then, separately, draw the overall RIGHT and BOTTOM perimeter of the maze.

        self.walls = [] # Reset for the corrected logic
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0: # If current cell is a path
                    # Check North: if it's the top border OR the cell above is a wall
                    if r == 0 or (r > 0 and self.grid[r-1][c] == 1):
                        self.walls.append((((c * ts, r * ts), ((c + 1) * ts, r * ts)), "N_wall"))
                    
                    # Check West: if it's the left border OR the cell to the left is a wall
                    if c == 0 or (c > 0 and self.grid[r][c-1] == 1):
                        self.walls.append((((c * ts, r * ts), (c * ts, (r + 1) * ts)), "W_wall"))
        
        # Add the overall rightmost vertical boundary line for the maze
        self.walls.append((((self.actual_maze_cols * ts, 0), (self.actual_maze_cols * ts, self.actual_maze_rows * ts)), "Perimeter_E"))
        # Add the overall bottommost horizontal boundary line for the maze
        self.walls.append((( (0, self.actual_maze_rows * ts), (self.actual_maze_cols * ts, self.actual_maze_rows * ts)), "Perimeter_S"))


    def draw(self, surface): # Standard maze draw
        wall_color = BLUE
        for line_segment, wall_type in self.walls:
            p1_rel, p2_rel = line_segment
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, 2)

    def draw_architect_vault(self, surface): # Themed draw for the vault
        wall_color = ARCHITECT_VAULT_WALL_COLOR 
        for line_segment, wall_type in self.walls:
            p1_rel, p2_rel = line_segment
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, 3) 


    def is_wall(self, abs_x, abs_y, width, height):
        object_rect_abs = pygame.Rect(
            abs_x - width / 2,
            abs_y - height / 2,
            width,
            height
        )

        for line_segment, wall_type in self.walls:
            p1_rel, p2_rel = line_segment
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])
            
            line_thickness_for_collision = 4 
            min_x = min(abs_p1[0], abs_p2[0]) - line_thickness_for_collision // 2
            min_y = min(abs_p1[1], abs_p2[1]) - line_thickness_for_collision // 2
            line_rect_width = abs(abs_p1[0] - abs_p2[0]) + line_thickness_for_collision
            line_rect_height = abs(abs_p1[1] - abs_p2[1]) + line_thickness_for_collision

            if line_rect_width < line_thickness_for_collision : line_rect_width = line_thickness_for_collision
            if line_rect_height < line_thickness_for_collision : line_rect_height = line_thickness_for_collision
            
            wall_rect = pygame.Rect(min_x, min_y, line_rect_width, line_rect_height)

            if object_rect_abs.colliderect(wall_rect):
                return wall_type 
        return None

    def get_path_cells(self): # Returns list of (center_x_rel, center_y_rel) for path cells
        path_cells_relative = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0: # 0 represents a path
                    center_x_rel = c * TILE_SIZE + TILE_SIZE // 2
                    center_y_rel = r * TILE_SIZE + TILE_SIZE // 2
                    path_cells_relative.append((center_x_rel, center_y_rel))
        return path_cells_relative

