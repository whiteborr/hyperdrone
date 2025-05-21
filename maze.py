import pygame
import random

# Import necessary constants from game_settings.py
try:
    from game_settings import (
        TILE_SIZE, WIDTH, MAZE_ROWS, GAME_PLAY_AREA_HEIGHT, # Core dimensions
        BLUE, # Default wall color
        ARCHITECT_VAULT_WALL_COLOR, # Specific color for Architect's Vault walls
        # ARCHITECT_VAULT_ACCENT_COLOR is not used directly in maze.py for walls
    )
except ImportError:
    print("Warning (maze.py): Could not import constants from game_settings. Using fallback values.")
    # Fallback values if game_settings.py is not found or constants are missing
    TILE_SIZE = 80
    WIDTH = 1920
    GAME_PLAY_AREA_HEIGHT = 1080 - 120
    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE
    BLUE = (0, 100, 255)
    ARCHITECT_VAULT_WALL_COLOR = (150, 120, 200)


class Maze:
    def __init__(self, game_area_x_offset=0, maze_type="standard"):
        """
        Initializes the Maze.
        Args:
            game_area_x_offset (int): The horizontal offset from the left of the screen
                                      where the maze drawing area begins.
            maze_type (str): "standard" or "architect_vault" to determine styling.
        """
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type

        # Calculate actual number of columns based on available width and tile size
        # MAZE_ROWS is imported and represents the fixed number of rows.
        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE
        self.actual_maze_rows = MAZE_ROWS # MAZE_ROWS is calculated in game_settings

        self.walls = [] # List to store wall line segments for drawing and collision

        # Ensure maze dimensions are valid
        if self.actual_maze_cols <= 0 or self.actual_maze_rows <= 0:
            print(f"ERROR (Maze.__init__): Maze dimensions are invalid. Cols: {self.actual_maze_cols}, Rows: {self.actual_maze_rows}.")
            # Create a minimal fallback grid if dimensions are problematic
            self.actual_maze_cols = max(1, self.actual_maze_cols)
            self.actual_maze_rows = max(1, self.actual_maze_rows)
            self.grid = [[0]] # A single path cell
            self.create_wall_lines_from_grid()
            print(f"Debug (Maze.__init__): Minimal 1x1 grid created due to invalid dimensions. Walls: {len(self.walls)}")
            return

        # Initialize grid: 1 represents a wall, 0 represents a path.
        # The grid is initially all walls.
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]

        # Generate the maze paths using Recursive Backtracker algorithm
        # print(f"Debug (Maze.__init__): Initializing maze generation for a {self.actual_maze_rows}x{self.actual_maze_cols} grid.")
        self._generate_maze_recursive_backtracker(0, 0) # Start generation from top-left cell

        # Convert the grid representation into drawable wall line segments
        self.create_wall_lines_from_grid()
        # print(f"Debug (Maze.__init__): Maze initialized. Number of wall segments: {len(self.walls)}")
        # if self.walls:
        #     print(f"Debug (Maze.__init__): First wall segment: {self.walls[0]}")


    def _generate_maze_recursive_backtracker(self, r, c):
        """
        Generates the maze using a Recursive Backtracker algorithm.
        Modifies self.grid by carving paths (setting cells to 0).
        Args:
            r (int): Current row index.
            c (int): Current column index.
        """
        if not (0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols):
            return # Out of bounds

        self.grid[r][c] = 0 # Mark current cell as a path

        # Define directions: (dr, dc, wall_dr, wall_dc)
        # (dr, dc) is for the next cell, (wall_dr, wall_dc) is for the wall between current and next cell
        directions = [
            (0, 2, 0, 1),  # East: move 2 cols right, wall is 1 col right
            (0, -2, 0, -1), # West: move 2 cols left, wall is 1 col left
            (2, 0, 1, 0),  # South: move 2 rows down, wall is 1 row down
            (-2, 0, -1, 0)  # North: move 2 rows up, wall is 1 row up
        ]
        random.shuffle(directions)

        for dr_next, dc_next, dr_wall, dc_wall in directions:
            next_r, next_c = r + dr_next, c + dc_next
            wall_r, wall_c = r + dr_wall, c + dc_wall

            # Check if the next cell is within bounds and is an unvisited wall (value 1)
            if (0 <= next_r < self.actual_maze_rows and
                0 <= next_c < self.actual_maze_cols and
                self.grid[next_r][next_c] == 1):

                # Also ensure the wall to be broken is within bounds
                if (0 <= wall_r < self.actual_maze_rows and
                    0 <= wall_c < self.actual_maze_cols):
                    
                    self.grid[wall_r][wall_c] = 0 # Carve path through the wall
                    self._generate_maze_recursive_backtracker(next_r, next_c) # Recursively visit the next cell

    def create_wall_lines_from_grid(self):
        """
        Creates line segments for drawing the maze walls based on the self.grid.
        A wall line is drawn on the edge of a path cell (0) if the adjacent cell
        in that direction is a wall cell (1) or if it's a boundary of the maze.
        Wall segments are stored as ((p1_relative, p2_relative), "type_info").
        Coordinates are relative to the maze's top-left corner (0,0).
        """
        self.walls = []
        ts = TILE_SIZE # Shorthand for tile size

        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                # Only consider drawing walls around path cells
                if self.grid[r][c] == 0: # If current cell (r,c) is a path
                    cell_x, cell_y = c * ts, r * ts # Top-left corner of the current cell

                    # Check South Wall (bottom edge of current cell)
                    if r + 1 < self.actual_maze_rows: # If there's a row below
                        if self.grid[r + 1][c] == 1: # If cell below is a wall
                            p1 = (cell_x, cell_y + ts)
                            p2 = (cell_x + ts, cell_y + ts)
                            self.walls.append(((p1, p2), "internal_south"))
                    else: # Last row, so this is a bottom perimeter wall for this path cell
                        p1 = (cell_x, cell_y + ts)
                        p2 = (cell_x + ts, cell_y + ts)
                        self.walls.append(((p1, p2), "perimeter_bottom"))

                    # Check East Wall (right edge of current cell)
                    if c + 1 < self.actual_maze_cols: # If there's a column to the right
                        if self.grid[r][c + 1] == 1: # If cell to the right is a wall
                            p1 = (cell_x + ts, cell_y)
                            p2 = (cell_x + ts, cell_y + ts)
                            self.walls.append(((p1, p2), "internal_east"))
                    else: # Last column, so this is a right perimeter wall
                        p1 = (cell_x + ts, cell_y)
                        p2 = (cell_x + ts, cell_y + ts)
                        self.walls.append(((p1, p2), "perimeter_right"))

                    # Check North Wall (top edge of current cell) - only if it's the first row
                    if r == 0:
                        p1 = (cell_x, cell_y)
                        p2 = (cell_x + ts, cell_y)
                        self.walls.append(((p1, p2), "perimeter_top"))
                    # Or if the cell above is a wall (for internal north walls)
                    elif self.grid[r-1][c] == 1:
                        p1 = (cell_x, cell_y)
                        p2 = (cell_x + ts, cell_y)
                        self.walls.append(((p1, p2), "internal_north"))


                    # Check West Wall (left edge of current cell) - only if it's the first column
                    if c == 0:
                        p1 = (cell_x, cell_y)
                        p2 = (cell_x, cell_y + ts)
                        self.walls.append(((p1, p2), "perimeter_left"))
                    # Or if the cell to the left is a wall (for internal west walls)
                    elif self.grid[r][c-1] == 1:
                        p1 = (cell_x, cell_y)
                        p2 = (cell_x, cell_y + ts)
                        self.walls.append(((p1, p2), "internal_west"))
        # Remove duplicate walls that might arise from this logic (e.g. internal_south of one cell is internal_north of another)
        # A set of frozensets of points can find unique lines regardless of p1,p2 order
        unique_wall_lines = set()
        filtered_walls = []
        for line_segment_tuple, wall_type in self.walls:
            p1, p2 = line_segment_tuple
            # Normalize point order for uniqueness check (e.g., sort by x then y)
            line_key = tuple(sorted((p1,p2)))
            if line_key not in unique_wall_lines:
                unique_wall_lines.add(line_key)
                filtered_walls.append((line_segment_tuple, wall_type)) # Keep original type for now
        self.walls = filtered_walls


    def draw(self, surface):
        """Draws the standard maze walls."""
        wall_color = BLUE # Default wall color from game_settings
        wall_thickness = 2
        self._draw_walls_internal(surface, wall_color, wall_thickness)

    def draw_architect_vault(self, surface):
        """Draws the maze walls with Architect's Vault styling."""
        wall_color = ARCHITECT_VAULT_WALL_COLOR # Vault-specific color
        wall_thickness = 3 # Slightly thicker for thematic effect
        self._draw_walls_internal(surface, wall_color, wall_thickness)

    def _draw_walls_internal(self, surface, color, thickness):
        """Internal helper to draw wall segments."""
        if not self.walls: return

        for line_segment_tuple, wall_type in self.walls:
            p1_relative, p2_relative = line_segment_tuple
            # Apply the game_area_x_offset to shift drawing horizontally
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])
            pygame.draw.line(surface, color, abs_p1, abs_p2, thickness)

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height):
        """
        Checks for collision between an object and the maze walls.
        Args:
            obj_center_x_abs (float): Absolute center X-coordinate of the object on screen.
            obj_center_y_abs (float): Absolute center Y-coordinate of the object on screen.
            obj_width (float): Width of the object's collision hitbox.
            obj_height (float): Height of the object's collision hitbox.
        Returns:
            str: The type of wall hit (e.g., "internal_south", "perimeter_left") or None if no collision.
        """
        # Create the object's collision rectangle in absolute screen coordinates
        obj_rect = pygame.Rect(
            obj_center_x_abs - obj_width / 2,
            obj_center_y_abs - obj_height / 2,
            obj_width,
            obj_height
        )

        for line_segment_tuple, wall_type in self.walls:
            p1_relative, p2_relative = line_segment_tuple # Relative coordinates of the wall segment

            # Convert wall segment to absolute screen coordinates for collision check
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])

            # Use obj_rect.clipline to check if the line segment (abs_p1, abs_p2)
            # intersects with obj_rect.
            # clipline returns () if no intersection, or the clipped line segment if it intersects.
            if obj_rect.clipline(abs_p1, abs_p2): # Check for any intersection
                return wall_type # Return the type of wall hit
        return None # No collision

    def get_path_cells(self):
        """
        Returns a list of (center_x_relative, center_y_relative) tuples for all path cells.
        Coordinates are relative to the maze's top-left (0,0), before game_area_x_offset.
        """
        path_cells_relative_centers = []
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 0: # 0 represents a path
                    center_x_rel = c * TILE_SIZE + TILE_SIZE // 2
                    center_y_rel = r * TILE_SIZE + TILE_SIZE // 2
                    path_cells_relative_centers.append((center_x_rel, center_y_rel))
        return path_cells_relative_centers

    def get_random_path_cell_center_abs(self):
        """
        Returns the absolute screen coordinates (center_x, center_y) of a random path cell.
        Returns None if no path cells exist.
        """
        path_cells_rel = self.get_path_cells()
        if not path_cells_rel:
            return None
        
        rel_center_x, rel_center_y = random.choice(path_cells_rel)
        abs_center_x = rel_center_x + self.game_area_x_offset
        abs_center_y = rel_center_y
        return abs_center_x, abs_center_y