import pygame
import random

# Import necessary constants from game_settings.py
try:
    from game_settings import (
        TILE_SIZE, WIDTH, MAZE_ROWS, GAME_PLAY_AREA_HEIGHT, # Core dimensions
        BLUE, # Default wall color for standard maze
        ARCHITECT_VAULT_WALL_COLOR # Wall color for architect vault
    )
except ImportError:
    print("Warning (maze.py): Could not import constants from game_settings. Using fallback values.")
    TILE_SIZE = 80
    WIDTH = 1920
    GAME_PLAY_AREA_HEIGHT = 1080 - 120
    MAZE_ROWS = GAME_PLAY_AREA_HEIGHT // TILE_SIZE
    BLUE = (0, 100, 255)
    ARCHITECT_VAULT_WALL_COLOR = (150, 120, 200)


class Maze:
    def __init__(self, game_area_x_offset=0, maze_type="standard"):
        """
        Initializes the Maze using the logic from the user's uploaded file.
        Args:
            game_area_x_offset (int): The horizontal offset from the left of the screen
                                      where the maze drawing area begins.
            maze_type (str): "standard" or "architect_vault" to determine styling.
        """
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type # Used to select wall color in drawing

        # Use MAZE_COLS calculated from WIDTH and TILE_SIZE, and MAZE_ROWS from game_settings
        self.actual_maze_cols = (WIDTH - self.game_area_x_offset) // TILE_SIZE
        self.actual_maze_rows = MAZE_ROWS 

        self.walls = [] # Will store tuples of ((x1,y1), (x2,y2))

        if self.actual_maze_cols <= 0 or self.actual_maze_rows <= 0:
            print(f"ERROR (Maze.__init__): Maze dimensions are invalid. Cols: {self.actual_maze_cols}, Rows: {self.actual_maze_rows}.")
            self.actual_maze_cols = max(1, self.actual_maze_cols) # Ensure at least 1x1
            self.actual_maze_rows = max(1, self.actual_maze_rows)
            self.grid = [[0]] # A single path cell for fallback
            self.walls = self._create_wall_lines_from_uploaded_logic()
            print(f"Debug (Maze.__init__): Minimal 1x1 grid created. Walls: {len(self.walls)}")
            return

        # Initialize grid: 1 represents a wall, 0 represents a path.
        self.grid = [[1 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]

        print(f"[DEBUG] Maze __init__: Grid size: {self.actual_maze_rows}x{self.actual_maze_cols}. Calling generation (User's Recursive Backtracker)...")
        self._generate_maze_from_uploaded_logic(0, 0) # Start generation, typically from (0,0) or random

        self.walls = self._create_wall_lines_from_uploaded_logic()
        print(f"[DEBUG] Maze __init__: Maze fully initialized. Number of walls: {len(self.walls)}")

    def _generate_maze_from_uploaded_logic(self, row, col):
        """
        Generates the maze using the Recursive Backtracker algorithm from the user's uploaded file.
        Modifies self.grid by carving paths (setting cells to 0).
        """
        self.grid[row][col] = 0 # Mark current cell as path
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)] # E, W, S, N
        random.shuffle(directions)  

        for dr, dc in directions:
            # Move two steps to find the next cell
            new_row, new_col = row + 2 * dr, col + 2 * dc
            
            # Check if the new cell is within bounds
            if 0 <= new_row < self.actual_maze_rows and 0 <= new_col < self.actual_maze_cols:
                # Check if the new cell is an unvisited wall
                if self.grid[new_row][new_col] == 1:
                    # Carve path through the intermediate wall cell
                    self.grid[row + dr][col + dc] = 0
                    # Recursively call for the new cell
                    self._generate_maze_from_uploaded_logic(new_row, new_col)

    def _create_wall_lines_from_uploaded_logic(self):
        """
        Creates wall line segments based on the logic from the user's uploaded file.
        This method can produce horizontal, vertical, and diagonal lines across wall cells.
        """
        print("[DEBUG] _create_wall_lines_from_uploaded_logic: Starting wall creation.")
        lines = []
        ts = TILE_SIZE
        for r in range(self.actual_maze_rows):
            for c in range(self.actual_maze_cols):
                if self.grid[r][c] == 1: # If the current cell is a wall
                    x1 = c * ts
                    y1 = r * ts
                    
                    # Determine x2: if cell to the right is also a wall, extend line horizontally
                    x2 = x1 + ts if (c + 1 < self.actual_maze_cols and self.grid[r][c + 1] == 1) else x1
                    # Determine y2: if cell below is also a wall, extend line vertically
                    y2 = y1 + ts if (r + 1 < self.actual_maze_rows and self.grid[r + 1][c] == 1) else y1
                    
                    # This logic from the uploaded file:
                    # If x2 was extended (wall to right) AND y2 was extended (wall below),
                    # it forms a diagonal from (x1,y1) to (x1+TS, y1+TS) for this wall cell.
                    # Otherwise, it forms a horizontal or vertical line segment for this wall cell's edge.
                    if x1 != x2 or y1 != y2: # Only add if it forms a line (not just a point)
                        lines.append(((x1, y1), (x2, y2)))
        print(f"[DEBUG] _create_wall_lines_from_uploaded_logic: Finished. Number of wall segments: {len(lines)}")
        return lines

    def draw(self, surface):
        """Draws the maze walls."""
        wall_color = BLUE if self.maze_type == "standard" else ARCHITECT_VAULT_WALL_COLOR
        wall_thickness = 2 if self.maze_type == "standard" else 3
        
        if not self.walls: 
            # print("[DEBUG] draw: No walls to draw.")
            return

        for line_segment in self.walls:
            p1_relative, p2_relative = line_segment
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])
            pygame.draw.line(surface, wall_color, abs_p1, abs_p2, wall_thickness)

    def draw_architect_vault(self, surface): # This can be merged into draw() or kept separate
        self.draw(surface) # The maze_type in __init__ handles color selection

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height):
        """
        Checks for collision between an object and the maze walls using logic from uploaded file.
        Args:
            obj_center_x_abs (float): Absolute center X-coordinate of the object on screen.
            obj_center_y_abs (float): Absolute center Y-coordinate of the object on screen.
            obj_width (float): Width of the object's collision hitbox.
            obj_height (float): Height of the object's collision hitbox.
        Returns:
            bool: True if collision with any wall line, False otherwise.
        """
        # Create the object's collision rectangle in absolute screen coordinates
        drone_rect = pygame.Rect(
            int(obj_center_x_abs - obj_width / 2), 
            int(obj_center_y_abs - obj_height / 2), 
            int(obj_width), 
            int(obj_height)
        )

        for line_segment in self.walls:
            p1_relative, p2_relative = line_segment
            # Convert wall line to absolute coordinates
            abs_p1 = (p1_relative[0] + self.game_area_x_offset, p1_relative[1])
            abs_p2 = (p2_relative[0] + self.game_area_x_offset, p2_relative[1])

            # Create a small rectangle around the wall line for collision detection
            # This is a common way to check collision with lines if not using line-rect intersection
            # The thickness of this rect (e.g., 4 pixels) accounts for line thickness and some tolerance.
            line_thickness_for_collision = 4 
            wall_rect = pygame.Rect(
                min(abs_p1[0], abs_p2[0]) - line_thickness_for_collision // 2,
                min(abs_p1[1], abs_p2[1]) - line_thickness_for_collision // 2,
                abs(abs_p1[0] - abs_p2[0]) + line_thickness_for_collision,
                abs(abs_p1[1] - abs_p2[1]) + line_thickness_for_collision
            )
            # Ensure minimum width/height for very short or perfectly horizontal/vertical lines
            if wall_rect.width < line_thickness_for_collision: wall_rect.width = line_thickness_for_collision
            if wall_rect.height < line_thickness_for_collision: wall_rect.height = line_thickness_for_collision
            
            if drone_rect.colliderect(wall_rect):
                # More precise check: clipline
                if drone_rect.clipline(abs_p1, abs_p2):
                    return True # Collision detected
        return False # No collision

    def get_path_cells(self):
        """
        Returns a list of (center_x_relative, center_y_relative) tuples for all path cells.
        Coordinates are relative to the maze's top-left (0,0), before game_area_x_offset.
        """
        path_cells_relative_centers = []
        if self.actual_maze_rows == 0 or self.actual_maze_cols == 0: 
            return path_cells_relative_centers

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

