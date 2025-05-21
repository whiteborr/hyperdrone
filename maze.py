import random
import pygame

from game_settings import (
    BLUE, TILE_SIZE, WIDTH, MAZE_ROWS,
    ARCHITECT_VAULT_WALL_COLOR, ARCHITECT_VAULT_ACCENT_COLOR # Import vault colors
)

class Maze:
    def __init__(self, game_area_x_offset=0, maze_type="standard"): 
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type 

        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE
        self.actual_maze_rows = MAZE_ROWS

        self.walls = [] 

        if self.actual_maze_cols <= 0 or self.actual_maze_rows <= 0:
            print(f"ERROR (Maze.__init__): Maze dimensions are invalid. Cols: {self.actual_maze_cols}, Rows: {self.actual_maze_rows}.")
            self.actual_maze_cols = max(1, self.actual_maze_cols) 
            self.actual_maze_rows = max(1, self.actual_maze_rows)
            self.grid = [[0]] 
            self.create_wall_lines_from_grid() 
            print(f"Debug (Maze.__init__): Minimal 1x1 grid created. Walls: {len(self.walls)}")
            return

        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]
        
        print(f"Debug (Maze.__init__): Initializing maze generation for a {self.actual_maze_rows}x{self.actual_maze_cols} grid.")
        self.generate_maze(0, 0) 
        
        # Optional: Print a small part of the generated grid for debugging
        # print("Debug (Maze.__init__): Sample of generated grid (first 5x5 or less):")
        # for r in range(min(5, self.actual_maze_rows)):
        #     print(self.grid[r][:min(5, self.actual_maze_cols)])
        
        if self.maze_type == "architect_vault":
            # Placeholder for any vault-specific maze modifications
            pass

        self.create_wall_lines_from_grid()
        print(f"Debug (Maze.__init__): Maze initialized. Number of wall segments: {len(self.walls)}")
        if self.walls:
            print(f"Debug (Maze.__init__): First wall segment: {self.walls[0]}")


    def generate_maze(self, row, col):
        """
        Generates the maze using a Recursive Backtracker algorithm.
        Marks cells as paths (0) in self.grid.
        """
        if not (0 <= row < self.actual_maze_rows and 0 <= col < self.actual_maze_cols):
            return 
        
        self.grid[row][col] = 0 
        
        directions = [(0, 1, "E"), (0, -1, "W"), (1, 0, "S"), (-1, 0, "N")] 
        random.shuffle(directions)

        for dr, dc, direction_char in directions:
            wall_row, wall_col = row + dr, col + dc 
            new_row, new_col = row + 2 * dr, col + 2 * dc 

            if (0 <= new_row < self.actual_maze_rows and \
                0 <= new_col < self.actual_maze_cols and \
                self.grid[new_row][new_col] == 1):
                
                if (0 <= wall_row < self.actual_maze_rows and \
                    0 <= wall_col < self.actual_maze_cols):
                    
                    self.grid[wall_row][wall_col] = 0 
                    self.generate_maze(new_row, new_col) 

    def create_wall_lines_from_grid(self):
        """
        Creates line segments for drawing the maze walls based on the self.grid.
        A wall line is drawn on the edge of a path cell (0) if the adjacent cell in that direction
        is a wall cell (1) or if it's a boundary of the maze.
        Internal walls are typed "internal", perimeter walls are "perimeter_X_cell".
        """
        self.walls = []
        ts = TILE_SIZE

        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0: # If current cell is a path
                    # Check South wall for cell (r,c)
                    if r + 1 < self.actual_maze_rows:
                        if self.grid[r+1][c] == 1: # Path above, wall below
                            p1 = (c * ts, (r + 1) * ts)
                            p2 = ((c + 1) * ts, (r + 1) * ts)
                            self.walls.append(((p1, p2), "internal"))
                    else: # Last row, this is a bottom perimeter wall for this path cell
                        p1 = (c * ts, (r + 1) * ts)
                        p2 = ((c + 1) * ts, (r + 1) * ts)
                        self.walls.append(((p1, p2), "perimeter_S_cell")) 

                    # Check East wall for cell (r,c)
                    if c + 1 < self.actual_maze_cols:
                        if self.grid[r][c+1] == 1: # Path to left, wall to right
                            p1 = ((c + 1) * ts, r * ts)
                            p2 = ((c + 1) * ts, (r + 1) * ts)
                            self.walls.append(((p1, p2), "internal"))
                    else: # Last col, this is a right perimeter wall for this path cell
                        p1 = ((c + 1) * ts, r * ts)
                        p2 = ((c + 1) * ts, (r + 1) * ts)
                        self.walls.append(((p1, p2), "perimeter_E_cell"))  

        # Add the absolute top and left perimeter walls for path cells on those edges
        for c_col in range(self.actual_maze_cols): 
            if self.grid[0][c_col] == 0: 
                 self.walls.append((((c_col * ts, 0 * ts), ((c_col + 1) * ts, 0 * ts)), "perimeter_N_cell"))
        for r_row in range(self.actual_maze_rows): 
            if self.grid[r_row][0] == 0: 
                 self.walls.append((((0 * ts, r_row * ts), (0 * ts, (r_row + 1) * ts)), "perimeter_W_cell"))
        
        # print(f"Debug (Maze.create_wall_lines_from_grid): Generated {len(self.walls)} wall segments.")


    def draw(self, surface): # Standard maze draw
        # print(f"Debug (Maze.draw): Drawing {len(self.walls)} wall segments.") # Optional: can be very verbose
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
        """
        Checks for collision with walls using Rect.clipline for better accuracy.
        Returns the type of wall hit ("internal", "perimeter_X_cell") or None.
        """
        # Create the object's rectangle in absolute screen coordinates
        obj_rect = pygame.Rect(
            abs_x - width / 2,
            abs_y - height / 2,
            width,
            height
        )

        for line_segment, wall_type in self.walls:
            p1_rel, p2_rel = line_segment # Relative coordinates of the wall segment
            
            # Convert wall segment to absolute screen coordinates
            abs_p1 = (p1_rel[0] + self.game_area_x_offset, p1_rel[1])
            abs_p2 = (p2_rel[0] + self.game_area_x_offset, p2_rel[1])
            
            # Use obj_rect.clipline to check if the line segment (abs_p1, abs_p2)
            # intersects with obj_rect.
            # clipline returns () if no intersection, or the clipped line segment if it intersects.
            if obj_rect.clipline(abs_p1, abs_p2): # Check for any intersection
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

