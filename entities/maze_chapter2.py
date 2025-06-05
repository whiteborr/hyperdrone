import pygame
import os
import random
from heapq import heappush, heappop
import math
import logging 
import copy

# Assuming Enemy class is in the same directory or accessible via entities.enemy
try:
    from .enemy import Enemy
except ImportError:
    # Minimal placeholder if Enemy class is not found
    class Enemy(pygame.sprite.Sprite):
        def __init__(self, pos, path): # Simplified placeholder
            super().__init__()
            # Ensure gs is available or provide default if not
            tile_size_val = getattr(gs, 'TILE_SIZE', 32) # Default to 32 if gs.TILE_SIZE not found
            self.image = pygame.Surface((tile_size_val * 0.7, tile_size_val * 0.7)) 
            self.image.fill((200,0,0))
            self.rect = self.image.get_rect(center=pos)
            self.alive = True
            self.health = 100
            self.max_health = 100
        def take_damage(self, amount): self.health -= amount; return self.health <= 0
        def update(self, maze, current_time_ms, game_area_x_offset, dt): pass
        def draw_health_bar(self, surface): pass


import game_settings as gs
TILE_SIZE = gs.TILE_SIZE 
BLUE = gs.BLUE
BLACK = gs.BLACK
RED = gs.RED
WHITE = gs.WHITE
GREEN = gs.GREEN
WIDTH = gs.WIDTH 
HEIGHT = gs.HEIGHT 

logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Ensure logger is configured
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class MazeChapter2:
    # Class attributes for defining the map structure
    ROWS = 12
    COLS = 20 

    CORE_POS = (5, 9) 

    TURRET_POSITIONS_CLASS_LEVEL = [
        (3, 8),  (3, 10), 
        (7, 8),  (7, 10), 
        (5, 7)            
    ]

    ENEMY_SPAWN_GRID_POSITIONS_CLASS_LEVEL = [
        (0, 9),           
        (ROWS - 1, 9),    
        (5, 0),           
        (5, COLS - 1)     
    ]
    
    # Path segments are less critical if we make most of the map '0' for debugging
    # PATH_SEGMENTS_CLASS_LEVEL = [
    #     ((0, 9), (5, 9)),    
    #     ((ROWS - 1, 9), (5, 9)), 
    #     ((5, 0), (5, 9)),    
    #     ((5, COLS - 1), (5, 9))  
    # ]
    
    # TURRET_ACCESS_PATHS_CLASS_LEVEL = [
    #     ((3, 8), (3, 9)), 
    #     ((3, 10), (3, 9)),
    #     ((7, 8), (7, 9)), 
    #     ((7, 10), (7, 9)),
    # ]


    def _carve_path(self, grid, start_pos, end_pos):
        """Carves a straight path of 0s in the grid between start_pos and end_pos."""
        r1, c1 = start_pos
        r2, c2 = end_pos

        if not (0 <= r1 < self.ROWS and 0 <= c1 < self.COLS and \
                0 <= r2 < self.ROWS and 0 <= c2 < self.COLS):
            return

        if r1 == r2:  # Horizontal path
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if 0 <= r1 < self.ROWS and 0 <= c < self.COLS: 
                    grid[r1][c] = 0
        elif c1 == c2:  # Vertical path
            for r in range(min(r1, r2), max(r1, r2) + 1):
                if 0 <= r < self.ROWS and 0 <= c1 < self.COLS: 
                    grid[r][c1] = 0
        else:
            logger.warning(f"Path carving for non-straight line requested: {start_pos} to {end_pos}. Path not carved.")


    def _build_tilemap(self):
        """
        Constructs the initial grid layout for an instance.
        For debugging bullets, this version makes most of the map pathable ('0').
        """
        # Start with a grid of all paths ('0')
        grid = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]

        # Define border walls (optional, but helps define play area)
        for r in range(self.ROWS):
            grid[r][0] = 1  # Left border
            grid[r][self.COLS - 1] = 1 # Right border
        for c in range(self.COLS):
            grid[0][c] = 1  # Top border
            grid[self.ROWS - 1][c] = 1 # Bottom border
        
        # Place Core Reactor ('C')
        core_r, core_c = self.CORE_POS
        if 0 <= core_r < self.ROWS and 0 <= core_c < self.COLS:
            grid[core_r][core_c] = 'C'
        else: 
            logger.error(f"MazeChapter2 _build_tilemap: CORE_POS {self.CORE_POS} is out of bounds when placing 'C'.")

        # Place Turret Spots ('T') - Ensure these are not on the border walls
        for r_turret, c_turret in self.TURRET_POSITIONS_CLASS_LEVEL:
            if 0 < r_turret < self.ROWS -1 and 0 < c_turret < self.COLS -1 : # Check if not on border
                if grid[r_turret][c_turret] == 1: # Should ideally be 0 from initial fill
                     logger.warning(f"MazeChapter2 _build_tilemap: Turret position ({r_turret},{c_turret}) was unexpectedly a wall before becoming 'T'. This might indicate border placement conflict.")
                grid[r_turret][c_turret] = 'T' 
            else:
                logger.warning(f"MazeChapter2 _build_tilemap: Turret position ({r_turret},{c_turret}) is on a border wall. Skipping placement.")
        
        return grid

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        
        self.grid = self._build_tilemap() 
        
        self.ENEMY_SPAWN_GRID_POSITIONS = [] # Will be recalculated based on open map
        
        self.actual_maze_rows = len(self.grid)
        self.actual_maze_cols = len(self.grid[0]) if self.actual_maze_rows > 0 else 0
        
        self.wall_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", BLUE) 
        self.path_color = BLACK 
        self.turret_spot_color = (0, 100, 0, 150) 
        self.used_turret_spot_color = (50, 50, 50, 100)

        self.core_reactor_grid_pos = None 
        self.core_reactor_abs_spawn_pos = None 
        self._find_core_reactor_spawn() 

        # Recalculate enemy spawns for the open map to ensure they are on actual '0' tiles
        self._update_enemy_spawn_points_for_open_map()

        self.enemy_spawn_points_abs = [] 
        self.enemy_paths_to_core = {} 
        self._calculate_enemy_paths_and_spawn_points() 

        self.debug_mode = False 
        
        core_status_message = f"Core found at {self.core_reactor_grid_pos}" if self.core_reactor_grid_pos else "Core NOT found"
        logger.info(f"MazeChapter2 post-init (id: {id(self)}). Type: {maze_type}, Offset: {game_area_x_offset}, Grid: {self.actual_maze_rows}x{self.actual_maze_cols}. {core_status_message}. Enemy spawns: {len(self.enemy_spawn_points_abs)}")
        
        if not self.core_reactor_grid_pos :
             logger.error(f"MazeChapter2 CRITICAL INIT CHECK: 'C' was NOT found in the generated grid. Check _build_tilemap and CORE_POS.")

    def _update_enemy_spawn_points_for_open_map(self):
        """Adjusts spawn points to ensure they are on '0' after map is mostly open."""
        new_spawns = []
        potential_spawns = [
            (1, self.COLS // 2),            # Top edge, center column (moved from row 0)
            (self.ROWS - 2, self.COLS // 2), # Bottom edge, center column (moved from row ROWS-1)
            (self.ROWS // 2, 1),            # Left edge, center row (moved from col 0)
            (self.ROWS // 2, self.COLS - 2)  # Right edge, center row (moved from col COLS-1)
        ]
        for r,c in potential_spawns:
            if 0 <= r < self.ROWS and 0 <= c < self.COLS and self.grid[r][c] == 0:
                new_spawns.append((r,c))
            else: # Fallback if preferred spawn is now a wall (border) or other
                if r == 1 and self.grid[r+1][c] == 0: new_spawns.append((r+1, c)) # Try one row down
                elif r == self.ROWS - 2 and self.grid[r-1][c] == 0: new_spawns.append((r-1, c)) # Try one row up
                elif c == 1 and self.grid[r][c+1] == 0: new_spawns.append((r, c+1)) # Try one col right
                elif c == self.COLS - 2 and self.grid[r][c-1] == 0: new_spawns.append((r, c-1)) # Try one col left
                else: logger.warning(f"Could not find suitable open map spawn near ({r},{c})")
        
        self.ENEMY_SPAWN_GRID_POSITIONS = list(set(new_spawns)) # Use unique spawns
        if not self.ENEMY_SPAWN_GRID_POSITIONS and self.grid[self.ROWS // 2][self.COLS // 2] == 0:
            logger.warning("No edge spawns found for open map, defaulting to center spawn.")
            self.ENEMY_SPAWN_GRID_POSITIONS = [(self.ROWS // 2, self.COLS // 2)]


    def _find_core_reactor_spawn(self):
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    logger.debug(f"Core reactor 'C' found at grid ({r_idx},{c_idx}), abs_pos ({center_x_abs},{center_y_abs})")
                    return 
        logger.warning(f"MazeChapter2 WARNING (id:{id(self)}): Core reactor 'C' not found in self.grid during _find_core_reactor_spawn.")

    def _calculate_enemy_paths_and_spawn_points(self):
        self.enemy_spawn_points_abs = []
        self.enemy_paths_to_core = {}
        if not self.core_reactor_grid_pos:
            logger.error(f"MazeChapter2 ERROR (id:{id(self)}): Cannot calculate enemy paths, core reactor position ({self.core_reactor_grid_pos}) unknown.")
            return

        for r, c in self.ENEMY_SPAWN_GRID_POSITIONS:
            if not (0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols):
                logger.warning(f"MazeChapter2 WARNING (id:{id(self)}): Enemy spawn ({r},{c}) is out of bounds.")
                continue
            # For open map debug, most tiles should be 0, C, or T. '1' should only be borders.
            if self.grid[r][c] == 1: 
                logger.error(f"MazeChapter2 CRITICAL PATHING ERROR (Open Map Debug): Enemy spawn point ({r},{c}) is a WALL ('1') in self.grid. Grid value: {self.grid[r][c]}. This should not happen for chosen spawns.")
                continue 
            
            center_x_abs = c * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
            center_y_abs = r * TILE_SIZE + TILE_SIZE // 2
            self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))

            path_grid_coords = self.find_path_astar((r, c), self.core_reactor_grid_pos)
            if path_grid_coords:
                pixel_path = [self._grid_to_pixel_center(gr, gc) for gr, gc in path_grid_coords]
                self.enemy_paths_to_core[(r, c)] = pixel_path
            else:
                logger.warning(f"MazeChapter2 WARNING (id:{id(self)}): No path found from enemy spawn ({r},{c}) to core at {self.core_reactor_grid_pos} using self.grid.")

    def _grid_to_pixel_center(self, grid_row, grid_col):
        pixel_x = (grid_col * TILE_SIZE) + (TILE_SIZE // 2) + self.game_area_x_offset
        pixel_y = (grid_row * TILE_SIZE) + (TILE_SIZE // 2)
        return pixel_x, pixel_y

    def get_neighbors(self, grid_pos):
        r, c = grid_pos
        potential_neighbors = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]: 
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.actual_maze_rows and 0 <= nc < self.actual_maze_cols and self.grid[nr][nc] != 1:
                potential_neighbors.append((nr, nc))
        return potential_neighbors

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def find_path_astar(self, start_grid_pos, end_grid_pos):
        open_set = [] 
        heappush(open_set, (0, start_grid_pos)) 
        came_from = {} 
        g_score = { (r,col): float('inf') for r in range(self.actual_maze_rows) for col in range(self.actual_maze_cols) }
        g_score[start_grid_pos] = 0
        f_score = { (r,col): float('inf') for r in range(self.actual_maze_rows) for col in range(self.actual_maze_cols) }
        f_score[start_grid_pos] = self.manhattan_distance(start_grid_pos, end_grid_pos)
        open_set_hash = {start_grid_pos} 

        while open_set:
            _, current_pos = heappop(open_set)
            if current_pos not in open_set_hash: 
                continue
            open_set_hash.remove(current_pos)

            if current_pos == end_grid_pos:
                path = []
                temp = current_pos
                while temp in came_from:
                    path.append(temp)
                    temp = came_from[temp]
                path.append(start_grid_pos) 
                return path[::-1] 

            for neighbor_pos in self.get_neighbors(current_pos):
                tentative_g_score = g_score[current_pos] + 1 
                if tentative_g_score < g_score[neighbor_pos]:
                    came_from[neighbor_pos] = current_pos
                    g_score[neighbor_pos] = tentative_g_score
                    f_score[neighbor_pos] = tentative_g_score + self.manhattan_distance(neighbor_pos, end_grid_pos)
                    if neighbor_pos not in open_set_hash:
                        heappush(open_set, (f_score[neighbor_pos], neighbor_pos))
                        open_set_hash.add(neighbor_pos)
        return None 

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height):
        effective_obj_width = max(1, obj_width)
        effective_obj_height = max(1, obj_height)
        half_w = effective_obj_width / 2
        half_h = effective_obj_height / 2
        
        points_to_check = [
            (obj_center_x_abs - half_w, obj_center_y_abs - half_h), 
            (obj_center_x_abs + half_w, obj_center_y_abs - half_h), 
            (obj_center_x_abs - half_w, obj_center_y_abs + half_h), 
            (obj_center_x_abs + half_w, obj_center_y_abs + half_h), 
            (obj_center_x_abs, obj_center_y_abs)                    
        ]

        for px, py in points_to_check:
            grid_c = int((px - self.game_area_x_offset) / TILE_SIZE)
            grid_r = int(py / TILE_SIZE)

            if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
                tile_value = self.grid[grid_r][grid_c]
                is_tile_a_wall = (tile_value == 1) 
                if is_tile_a_wall:
                    logger.debug(f"Maze.is_wall (id:{id(self)}): COLLISION at point ({px:.1f},{py:.1f}) -> Grid ({grid_r},{grid_c}), self.grid value '{tile_value}'. Is wall? True")
                    return True 
            else: 
                logger.debug(f"Maze.is_wall (id:{id(self)}): Point ({px:.1f},{py:.1f}) -> Grid ({grid_r},{grid_c}) is OUT OF BOUNDS. Returning True.")
                return True 
        return False

    def can_place_turret(self, grid_r, grid_c):
        if not (0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols):
            logger.debug(f"can_place_turret (id:{id(self)}): ({grid_r},{grid_c}) is out of bounds.")
            return False 
        if self.grid[grid_r][grid_c] != 'T':
            logger.debug(f"can_place_turret (id:{id(self)}): Attempt to place turret at ({grid_r},{grid_c}). Tile is '{self.grid[grid_r][grid_c]}', not 'T'.")
            return False 

        # For an open map, path blocking check is less critical, but good to keep the structure
        original_tile_in_current_grid = self.grid[grid_r][grid_c] # Should be 'T'
        self.grid[grid_r][grid_c] = 'U' # Temporarily mark as Used, which is still pathable for A*
        
        all_paths_still_exist = True # Assume paths are fine initially
        if self.core_reactor_grid_pos: 
            for spawn_r_loop, spawn_c_loop in self.ENEMY_SPAWN_GRID_POSITIONS:
                if not (0 <= spawn_r_loop < self.actual_maze_rows and 0 <= spawn_c_loop < self.actual_maze_cols):
                    continue
                if not self.find_path_astar((spawn_r_loop, spawn_c_loop), self.core_reactor_grid_pos):
                    all_paths_still_exist = False 
                    break 
        
        self.grid[grid_r][grid_c] = original_tile_in_current_grid # Revert change (back to 'T')

        if not all_paths_still_exist:
            logger.info(f"MazeChapter2 (id:{id(self)}): Turret at ({grid_r},{grid_c}) would block an enemy path (should not happen with 'U' as pathable).")
            # This warning should be rare if 'U' is treated as pathable by A*.
            # If it occurs, it means A* logic in get_neighbors needs to explicitly allow 'U' if it doesn't already.
            # For now, the main check is simply if it's a 'T' spot.
            # The path blocking becomes relevant if placing a turret makes its tile a '1'.
            # Since we changed to 'U' and 'U' is not '1', path blocking by the turret tile itself is not an issue.
            # The A* check above is more of a sanity check now.
            # return False # Uncomment if strict path checking is needed even for 'U' spots
            
        return True

    def mark_turret_spot_as_occupied(self, grid_r, grid_c):
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            original_value_in_current_grid = self.grid[grid_r][grid_c]
            if original_value_in_current_grid == 'T':
                self.grid[grid_r][grid_c] = 'U' 
                logger.info(f"MazeChapter2 (id:{id(self)}): Turret spot ({grid_r},{grid_c}) marked as occupied (value changed from 'T' to 'U').")
                # No need to recalculate paths if 'U' is still considered pathable by A* and not a wall for bullets
                return True
            else:
                logger.warning(f"MazeChapter2 WARNING (id:{id(self)}): Attempted to mark non-'T' spot ({grid_r},{grid_c}) as occupied. Current value: {original_value_in_current_grid}")
        return False

    def draw(self, surface):
        for r_idx, row_data in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row_data):
                x = c_idx * TILE_SIZE + self.game_area_x_offset
                y = r_idx * TILE_SIZE
                rect = (x, y, TILE_SIZE, TILE_SIZE)

                if tile_type == 1: # Wall
                    pygame.draw.rect(surface, self.wall_color, rect)
                elif tile_type == 0: # Path
                    pygame.draw.rect(surface, self.path_color, rect)
                elif tile_type == 'C': # Core
                    pygame.draw.rect(surface, self.path_color, rect) # Draw path under core
                    pygame.draw.circle(surface, gs.CYAN, (x + TILE_SIZE // 2, y + TILE_SIZE // 2), TILE_SIZE // 3)
                elif tile_type == 'T': # Available Turret Spot
                    pygame.draw.rect(surface, self.path_color, rect) # Draw path under T
                    temp_surface_for_turret_spot = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    temp_surface_for_turret_spot.fill(self.turret_spot_color) # Green overlay
                    surface.blit(temp_surface_for_turret_spot, (x,y))
                    pygame.draw.rect(surface, GREEN, rect, 1) # Green border
                elif tile_type == 'U': # Used/Occupied Turret Spot
                    pygame.draw.rect(surface, self.path_color, rect) # Draw as path
                    # Optionally add a different visual cue for 'U'
                    # temp_surface_for_used_spot = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    # temp_surface_for_used_spot.fill(self.used_turret_spot_color) 
                    # surface.blit(temp_surface_for_used_spot, (x,y))
                    # pygame.draw.rect(surface, DARK_GREY, rect, 1) 


        if self.debug_mode:
            # Draw enemy spawn points (magenta circles)
            for r_spawn, c_spawn in self.ENEMY_SPAWN_GRID_POSITIONS: # Use the instance variable
                 abs_spawn_x, abs_spawn_y = self._grid_to_pixel_center(r_spawn, c_spawn)
                 pygame.draw.circle(surface, (255, 0, 255), (int(abs_spawn_x), int(abs_spawn_y)), TILE_SIZE // 4)
            
            # Draw calculated paths (orange lines)
            for (spawn_r, spawn_c), path_pixel_coords in self.enemy_paths_to_core.items():
                if path_pixel_coords and len(path_pixel_coords) > 1:
                    pygame.draw.lines(surface, (255, 165, 0), False, path_pixel_coords, 2) 

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode
        logger.info(f"MazeChapter2: Debug mode {'enabled' if self.debug_mode else 'disabled'}.")

    def get_core_reactor_spawn_position_abs(self):
        return self.core_reactor_abs_spawn_pos

    def get_enemy_spawn_points_abs(self):
        return self.enemy_spawn_points_abs

    def get_enemy_path_to_core(self, enemy_spawn_grid_pos):
        return self.enemy_paths_to_core.get(enemy_spawn_grid_pos, [])

    def get_path_cells_abs(self):
        path_cells = []
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                # Path cells are 0, 'C', 'T', or 'U'
                if tile_type != 1: 
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    path_cells.append((center_x_abs, center_y_abs))
        return path_cells

    def get_random_path_cell_center_abs(self):
        path_cells = self.get_path_cells_abs()
        return random.choice(path_cells) if path_cells else None


if __name__ == '__main__':
    pygame.init()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger_main = logging.getLogger(__name__ + ".main_test")

    screen_width = gs.get_game_setting("WIDTH", 1920) 
    screen_height = gs.get_game_setting("HEIGHT", 1080) 
    
    test_maze_pixel_width = MazeChapter2.COLS * TILE_SIZE
    if test_maze_pixel_width > screen_width :
         screen_width = test_maze_pixel_width + 20 

    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("MazeChapter2 Test (Open Map Debug)")
    clock = pygame.time.Clock()

    class MockGameController:
        def __init__(self):
            self.game_area_x_offset = (screen_width - (MazeChapter2.COLS * TILE_SIZE)) // 2 
            if self.game_area_x_offset < 0: self.game_area_x_offset = 0 
            
            self.turrets_group = pygame.sprite.Group() 
            class MockDroneSystem:
                def __init__(self): self.player_cores = 2000 
                def get_player_cores(self): return self.player_cores
                def spend_player_cores(self, amount):
                    if self.player_cores >= amount: self.player_cores -= amount; return True
                    return False
            self.drone_system = MockDroneSystem()
            self.sounds = {} 
        def play_sound(self, sound_name, volume=1.0):
            logger_main.debug(f"MockGC: Play sound '{sound_name}'")

    mock_gc = MockGameController()
    maze = MazeChapter2(game_area_x_offset=mock_gc.game_area_x_offset) 
    
    class MockTurret(pygame.sprite.Sprite): 
        def __init__(self, x, y):
            super().__init__()
            self.image = pygame.Surface((TILE_SIZE * 0.5, TILE_SIZE * 0.5))
            self.image.fill(gs.YELLOW)
            self.rect = self.image.get_rect(center=(x,y))

    class MockCombatController: 
        def __init__(self, gc_ref, maze_ref):
            self.game_controller = gc_ref
            self.maze = maze_ref
            self.turrets_group = gc_ref.turrets_group 
        
        def try_place_turret(self, screen_pos):
            grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / TILE_SIZE)
            grid_r = int(screen_pos[1] / TILE_SIZE)
            

            if self.maze.can_place_turret(grid_r, grid_c): 
                turret_cost = getattr(gs, 'TURRET_BASE_COST', 50) 
                if self.game_controller.drone_system.spend_player_cores(turret_cost): 
                    abs_turret_x, abs_turret_y = self.maze._grid_to_pixel_center(grid_r, grid_c)
                    
                    new_turret = MockTurret(abs_turret_x, abs_turret_y) 
                    self.turrets_group.add(new_turret)
                    self.maze.mark_turret_spot_as_occupied(grid_r, grid_c) 
                    return True
                else:
                    logger_main.warning(f"MockCombat: Insufficient cores to place turret. Have: {self.game_controller.drone_system.get_player_cores()}, Need: {turret_cost}")
            else:
                logger_main.warning(f"MockCombat: Cannot place turret at grid ({grid_r},{grid_c}) as per maze.can_place_turret.")
            return False

    mock_combat_ctrl = MockCombatController(mock_gc, maze)

    font = pygame.font.Font(None, 24)
    running = True
    while running:
        dt = clock.tick(30) / 1000.0 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN: 
                if event.key == pygame.K_ESCAPE: 
                    running = False
                if event.key == pygame.K_d: 
                    maze.toggle_debug()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    mouse_pos = pygame.mouse.get_pos()
                    mock_combat_ctrl.try_place_turret(mouse_pos)


        screen.fill(BLACK)
        maze.draw(screen) 
        mock_gc.turrets_group.draw(screen) 

        if maze.core_reactor_abs_spawn_pos:
            pygame.draw.circle(screen, gs.CYAN, (int(maze.core_reactor_abs_spawn_pos[0]), int(maze.core_reactor_abs_spawn_pos[1])), TILE_SIZE // 3)

        currency_surf = font.render(f"Cores: {mock_gc.drone_system.get_player_cores()}", True, WHITE)
        screen.blit(currency_surf, (10, 10))
        
        turret_count_surf = font.render(f"Turrets: {len(mock_gc.turrets_group)}", True, WHITE)
        screen.blit(turret_count_surf, (10, 30))
        
        debug_text_surf = font.render(f"Debug Paths: {'ON' if maze.debug_mode else 'OFF'} (Press D)", True, WHITE)
        screen.blit(debug_text_surf, (10, 50))


        pygame.display.flip()
    pygame.quit()

