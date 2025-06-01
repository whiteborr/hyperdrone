# entities/maze_chapter2.py
import pygame
import random

# Attempt to import from game_settings, with fallbacks for standalone use
try:
    import game_settings as gs
    TILE_SIZE = gs.TILE_SIZE
    BLUE = gs.BLUE # Default wall color
    BLACK = gs.BLACK # Default path color
    RED = gs.RED # Default core reactor color (can be changed)
    WHITE = gs.WHITE # For drawing accents or debug
    # WIDTH = gs.WIDTH # Not directly used in this class for drawing, but good for context
    # GAME_PLAY_AREA_HEIGHT = gs.GAME_PLAY_AREA_HEIGHT # Not directly used
except (ImportError, AttributeError):
    print("Warning (maze_chapter2.py): game_settings not fully available. Using fallback values.")
    TILE_SIZE = 32
    BLUE = (0, 0, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    WHITE = (255, 255, 255)
    # WIDTH = 1920 # Fallback
    # GAME_PLAY_AREA_HEIGHT = 1080 - 120 # Fallback


class MazeChapter2:
    """
    Represents the tile-based maze for Chapter 2.
    This maze is defined by a fixed tilemap.
    """
    MAZE_TILEMAP = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [1,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,1,0,1],
        [1,0,1,1,1,1,0,1,1,1,1,1,0,1,0,1,0,1,0,1],
        [1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,1,0,1,0,1],
        [1,0,1,1,1,1,1,1,1,0,1,1,0,1,0,1,0,1,1,1],
        [1,0,0,0,0,0,0,0,1,0,1,0,0,1,0,1,0,0,0,1],
        [1,1,1,1,1,1,1,0,1,0,1,0,1,1,0,1,1,1,0,1],
        [1,0,0,0,0,0,1,0,1,0,1,0,0,0,0,1,0,0,0,1],
        [1,1,1,0,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1],
        [1,0,0,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,1],
        [1,0,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1],
        [1,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,1],
        [1,0,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,0,1,1],
        [1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        [1,1,1,1,1,1,'C',1,1,1,1,1,1,1,1,1,1,1,1,1],
    ]

    # Define fixed enemy spawn points as grid coordinates (row, col)
    ENEMY_SPAWN_GRID_POSITIONS = [
        (1, 1),  # Top-left area
        (1, 18), # Top-right area
        (7, 1),  # Mid-left
        (7, 18), # Mid-right
        (13, 1), # Bottom-left path entrance
        (13, 18) # Bottom-right path entrance
    ]

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        """
        Initializes the Chapter 2 Maze.

        Args:
            game_area_x_offset (int): The x-offset of the game area from the screen's left edge.
            maze_type (str): A string identifier for this maze type.
        """
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type # Store the type, might be useful for specific logic
        self.grid = MazeChapter2.MAZE_TILEMAP # Use the class attribute tilemap

        self.actual_maze_rows = len(self.grid)
        self.actual_maze_cols = len(self.grid[0]) if self.actual_maze_rows > 0 else 0

        # Define colors for drawing (can be overridden by game_settings)
        self.wall_color = BLUE
        self.path_color = BLACK # Or any other color for path visualization if needed
        self.core_reactor_placeholder_color = RED # Color for the 'C' tile if drawn directly by maze

        self.core_reactor_grid_pos = None # Stores (row, col) of 'C'
        self.core_reactor_abs_spawn_pos = None # Stores absolute pixel center (x, y) for 'C'
        self._find_core_reactor_spawn()

        self.enemy_spawn_points_abs = [] # List of (abs_x, abs_y) for enemy spawns
        self._calculate_enemy_spawn_points_abs()

        print(f"MazeChapter2 initialized: {self.actual_maze_rows}x{self.actual_maze_cols} grid. X-Offset: {self.game_area_x_offset}")

    def _find_core_reactor_spawn(self):
        """Locates the 'C' tile in the MAZE_TILEMAP and calculates its absolute spawn position."""
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    # Calculate center of the tile for spawning
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    print(f"MazeChapter2: Core Reactor ('C') found at grid {self.core_reactor_grid_pos}, abs pixel {self.core_reactor_abs_spawn_pos}")
                    return
        print("Warning (maze_chapter2.py): Core Reactor ('C') tile not found in MAZE_TILEMAP.")

    def _calculate_enemy_spawn_points_abs(self):
        """Calculates absolute pixel coordinates for predefined enemy spawn grid positions."""
        self.enemy_spawn_points_abs = []
        for r_idx, c_idx in self.ENEMY_SPAWN_GRID_POSITIONS:
            if 0 <= r_idx < self.actual_maze_rows and 0 <= c_idx < self.actual_maze_cols:
                if self.grid[r_idx][c_idx] == 0: # Ensure spawn is on a walkable path (0)
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))
                else:
                    print(f"Warning (maze_chapter2.py): Defined enemy spawn ({r_idx},{c_idx}) is on a wall or special tile. Skipping.")
            else:
                print(f"Warning (maze_chapter2.py): Defined enemy spawn ({r_idx},{c_idx}) is out of grid bounds. Skipping.")
        print(f"MazeChapter2: Calculated {len(self.enemy_spawn_points_abs)} absolute enemy spawn points.")

    def draw(self, surface):
        """
        Draws the tilemap onto the given Pygame surface.
        Args:
            surface (pygame.Surface): The surface to draw the maze on.
        """
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                rect = pygame.Rect(
                    c_idx * TILE_SIZE + self.game_area_x_offset,
                    r_idx * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE
                )
                if tile_type == 1: # Wall
                    pygame.draw.rect(surface, self.wall_color, rect)
                elif tile_type == 0: # Path
                    # Optionally draw path tiles, or leave background color if transparent
                    # pygame.draw.rect(surface, self.path_color, rect) # Example: draw black paths
                    pass # Assuming background is already black or desired color
                elif tile_type == 'C': # Core Reactor location
                    # The actual CoreReactor entity will be drawn by the GameController.
                    # This can draw a placeholder or just treat it as a path for visual consistency.
                    # For now, let's draw a distinct placeholder.
                    pygame.draw.rect(surface, self.core_reactor_placeholder_color, rect)
                    pygame.draw.circle(surface, WHITE, rect.center, TILE_SIZE // 4) # Small white circle in center

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width=None, obj_height=None):
        """
        Checks if the given absolute pixel coordinates (center of object) are inside a wall tile.
        For tile-based collision, we convert pixel coordinates to grid coordinates.
        Args:
            obj_center_x_abs (float): Absolute x-coordinate of the object's center.
            obj_center_y_abs (float): Absolute y-coordinate of the object's center.
            obj_width (float, optional): Width of the object, for more advanced collision.
            obj_height (float, optional): Height of the object, for more advanced collision.

        Returns:
            bool: True if the center point is within a wall tile (1), False otherwise.
                  Also returns True if out of bounds.
        """
        # Convert absolute pixel center to grid coordinates
        grid_c = int((obj_center_x_abs - self.game_area_x_offset) / TILE_SIZE)
        grid_r = int(obj_center_y_abs / TILE_SIZE)

        # Check if the grid coordinates are within the maze boundaries
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            # Return True if the tile type is 1 (a wall)
            return self.grid[grid_r][grid_c] == 1
        
        # If out of bounds, consider it a wall for collision purposes
        return True

    def get_core_reactor_spawn_position_abs(self):
        """
        Returns the absolute pixel coordinates (center x, center y) for the Core Reactor spawn.
        Returns None if 'C' tile was not found.
        """
        return self.core_reactor_abs_spawn_pos

    def get_enemy_spawn_points_abs(self):
        """
        Returns a list of absolute pixel coordinates (center x, center y) for enemy spawns.
        """
        return self.enemy_spawn_points_abs

    def get_path_cells_abs(self):
        """
        Returns a list of (center_x_abs, center_y_abs) tuples for all path cells (tile type '0' or 'C').
        Useful for AI pathfinding or random item placement on paths.
        """
        path_cells_abs_centers = []
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                if tile_type == 0 or tile_type == 'C': # Treat 'C' as walkable for pathfinding
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    path_cells_abs_centers.append((center_x_abs, center_y_abs))
        return path_cells_abs_centers

    def get_random_path_cell_center_abs(self):
        """
        Returns the absolute screen coordinates (center_x, center_y) of a random path cell.
        Returns None if no path cells exist.
        """
        path_cells_abs = self.get_path_cells_abs()
        if not path_cells_abs:
            return None
        return random.choice(path_cells_abs)

if __name__ == '__main__':
    # This block allows testing the MazeChapter2 class independently.
    # It requires Pygame to be initialized and a screen to be set up.
    pygame.init()
    
    # Use constants from game_settings if available, otherwise fallbacks
    try:
        screen_width, screen_height = gs.WIDTH, gs.HEIGHT
        ts = gs.TILE_SIZE
    except (NameError, AttributeError): # Fallback if gs or its attributes are not defined
        screen_width, screen_height = 800, 600
        ts = 32

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("MazeChapter2 Test")
    clock = pygame.time.Clock()

    # Instantiate the maze with an example offset
    test_maze = MazeChapter2(game_area_x_offset=50)

    print(f"Core Reactor Spawn (abs pixels): {test_maze.get_core_reactor_spawn_position_abs()}")
    print(f"Enemy Spawns (abs pixels): {test_maze.get_enemy_spawn_points_abs()}")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill(BLACK)  # Clear screen with black (or your path color)
        test_maze.draw(screen)  # Draw the maze

        # Example: Test is_wall with mouse position
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if test_maze.is_wall(mouse_x, mouse_y):
            # Draw a small red circle if mouse is over a wall
            pygame.draw.circle(screen, (255,0,0), (mouse_x, mouse_y), 5)
        else:
            # Draw a small green circle if mouse is over a path
            pygame.draw.circle(screen, (0,255,0), (mouse_x, mouse_y), 5)

        pygame.display.flip()
        clock.tick(30) # Limit FPS for the test

    pygame.quit()
