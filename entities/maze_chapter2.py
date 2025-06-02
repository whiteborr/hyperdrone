# entities/maze_chapter2.py
import pygame
import random

try:
    import game_settings as gs
    TILE_SIZE = gs.TILE_SIZE
    BLUE = gs.BLUE 
    BLACK = gs.BLACK 
    RED = gs.RED 
    WHITE = gs.WHITE 
except (ImportError, AttributeError):
    # print("Warning (maze_chapter2.py): game_settings not fully available. Using fallback values.")
    TILE_SIZE = 32
    BLUE = (0, 0, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    WHITE = (255, 255, 255)


class MazeChapter2:
    # MAZE_TILEMAP with improved connectivity for A* pathfinding
    # '0' is path, '1' is wall, 'C' is Core Reactor (also a path for AI)
    MAZE_TILEMAP = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], # Row 0
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # Row 1 (Spawn (1,1), (1,18)) - Opened up
        [1,0,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1], # Row 2
        [1,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1], # Row 3 - Opened path to right
        [1,0,1,1,0,1,1,1,1,0,1,1,0,1,1,1,0,1,0,1], # Row 4 - Path from (4,4)
        [1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,1,0,1], # Row 5 - Path from (5,10)
        [1,0,1,1,1,1,1,0,1,0,1,1,1,1,0,1,0,1,0,1], # Row 6 - Path from (6,14), (6,16)
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # Row 7 (Spawn (7,1), (7,18)) - Opened up significantly
        [1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,0,1,1,1], # Row 8 - Path at (8,16)
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # Row 9 - Opened up
        [1,0,1,1,1,1,0,1,1,1,1,1,0,1,0,1,1,1,0,1], # Row 10
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # Row 11 - Opened up
        [1,0,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1], # Row 12
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # Row 13 (Spawn (13,1), (13,18)) - Already open
        [1,1,1,1,1,1,'C',1,1,1,1,1,1,1,1,1,1,1,1,1], # Row 14 (Reactor 'C' at (14,6))
    ]


    ENEMY_SPAWN_GRID_POSITIONS = [
        (1, 1), (1, 18), (7, 1), (7, 18), (13, 1), (13, 18)
    ]

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        self.grid = MazeChapter2.MAZE_TILEMAP
        self.actual_maze_rows = len(self.grid)
        self.actual_maze_cols = len(self.grid[0]) if self.actual_maze_rows > 0 else 0

        self.wall_color = BLUE
        self.path_color = BLACK 
        self.core_reactor_grid_pos = None
        self.core_reactor_abs_spawn_pos = None
        self._find_core_reactor_spawn()

        self.enemy_spawn_points_abs = []
        self._calculate_enemy_spawn_points_abs()
        
        self.wall_line_thickness = 2 

        # print(f"MazeChapter2 initialized: {self.actual_maze_rows}x{self.actual_maze_cols} grid. X-Offset: {self.game_area_x_offset}")

    def _find_core_reactor_spawn(self):
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    # print(f"MazeChapter2: Core Reactor ('C') found at grid {self.core_reactor_grid_pos}, abs pixel {self.core_reactor_abs_spawn_pos}")
                    return
        print("Warning (maze_chapter2.py): Core Reactor ('C') tile not found in MAZE_TILEMAP.")

    def _calculate_enemy_spawn_points_abs(self):
        self.enemy_spawn_points_abs = []
        for r_idx, c_idx in self.ENEMY_SPAWN_GRID_POSITIONS:
            if 0 <= r_idx < self.actual_maze_rows and 0 <= c_idx < self.actual_maze_cols:
                # Enemies should spawn on a walkable tile (0 or 'C')
                if self.grid[r_idx][c_idx] == 0 or self.grid[r_idx][c_idx] == 'C':
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))
                else:
                    print(f"Warning (maze_chapter2.py): Defined enemy spawn ({r_idx},{c_idx}) is on a wall. Value: {self.grid[r_idx][c_idx]}. Skipping.")
            else:
                print(f"Warning (maze_chapter2.py): Defined enemy spawn ({r_idx},{c_idx}) is out of grid bounds. Skipping.")
        if not self.enemy_spawn_points_abs:
            print("CRITICAL WARNING (maze_chapter2.py): No valid enemy spawn points calculated from ENEMY_SPAWN_GRID_POSITIONS!")
        # else:
            # print(f"MazeChapter2: Calculated {len(self.enemy_spawn_points_abs)} absolute enemy spawn points.")

    def draw(self, surface):
        for r_idx, row_data in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row_data):
                x = c_idx * TILE_SIZE + self.game_area_x_offset
                y = r_idx * TILE_SIZE

                if tile_type == 1: 
                    # Top line
                    if r_idx == 0 or (r_idx > 0 and self.grid[r_idx - 1][c_idx] != 1):
                        pygame.draw.line(surface, self.wall_color, (x, y), (x + TILE_SIZE, y), self.wall_line_thickness)
                    # Bottom line
                    if r_idx == self.actual_maze_rows - 1 or \
                       (r_idx + 1 < self.actual_maze_rows and self.grid[r_idx + 1][c_idx] != 1):
                        pygame.draw.line(surface, self.wall_color, (x, y + TILE_SIZE), (x + TILE_SIZE, y + TILE_SIZE), self.wall_line_thickness)
                    # Left line
                    if c_idx == 0 or (c_idx > 0 and self.grid[r_idx][c_idx - 1] != 1):
                        pygame.draw.line(surface, self.wall_color, (x, y), (x, y + TILE_SIZE), self.wall_line_thickness)
                    # Right line
                    if c_idx == self.actual_maze_cols - 1 or \
                       (c_idx + 1 < self.actual_maze_cols and self.grid[r_idx][c_idx + 1] != 1):
                        pygame.draw.line(surface, self.wall_color, (x + TILE_SIZE, y), (x + TILE_SIZE, y + TILE_SIZE), self.wall_line_thickness)
                
                elif tile_type == 0 or tile_type == 'C': 
                    pass # Path or Reactor tile, draw nothing (background shows through)

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width=None, obj_height=None):
        grid_c = int((obj_center_x_abs - self.game_area_x_offset) / TILE_SIZE)
        grid_r = int(obj_center_y_abs / TILE_SIZE)

        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            return self.grid[grid_r][grid_c] == 1 
        return True 

    def get_core_reactor_spawn_position_abs(self):
        return self.core_reactor_abs_spawn_pos

    def get_enemy_spawn_points_abs(self):
        return self.enemy_spawn_points_abs

    def get_path_cells_abs(self):
        path_cells_abs_centers = []
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                if tile_type == 0 or tile_type == 'C': 
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    path_cells_abs_centers.append((center_x_abs, center_y_abs))
        return path_cells_abs_centers

    def get_random_path_cell_center_abs(self):
        path_cells_abs = self.get_path_cells_abs()
        if not path_cells_abs:
            return None
        return random.choice(path_cells_abs)

if __name__ == '__main__':
    pygame.init()
    try:
        screen_width, screen_height = gs.WIDTH, gs.HEIGHT
        ts_test = gs.TILE_SIZE 
    except (NameError, AttributeError): 
        screen_width, screen_height = 800, 600
        ts_test = 32

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("MazeChapter2 Test - Line Walls & Improved Paths")
    clock = pygame.time.Clock()
    test_maze = MazeChapter2(game_area_x_offset=50)
    
    if 'TILE_SIZE' not in globals() or TILE_SIZE != ts_test:
        TILE_SIZE = ts_test 

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False
        
        try: screen_fill_color = gs.BLACK
        except NameError: screen_fill_color = (0,0,0)
        screen.fill(screen_fill_color)
        test_maze.draw(screen)
        
        reactor_pos = test_maze.get_core_reactor_spawn_position_abs()
        if reactor_pos:
            try: core_color = gs.RED; outer_color = gs.WHITE
            except NameError: core_color = (255,0,0); outer_color = (255,255,255)
            pygame.draw.circle(screen, core_color, (int(reactor_pos[0]), int(reactor_pos[1])), TILE_SIZE // 3)
            pygame.draw.circle(screen, outer_color, (int(reactor_pos[0]), int(reactor_pos[1])), TILE_SIZE // 3, 2)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        if test_maze.is_wall(mouse_x, mouse_y):
            pygame.draw.circle(screen, (255,0,0), (mouse_x, mouse_y), 5)
        else:
            pygame.draw.circle(screen, (0,255,0), (mouse_x, mouse_y), 5)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()