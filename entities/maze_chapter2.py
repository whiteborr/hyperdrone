import pygame
import os
import random
from heapq import heappush, heappop
import math
import logging 
import copy # Import the copy module

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
    MAZE_TILEMAP = [ # Using the restructured map
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], # 0
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # 1
        [1,0,'T',0,0,1,1,1,0,0,0,1,1,1,0,0,'T',0,0,1], # 2
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # 3
        [1,0,0,0,0,1,0,0,0,'C',0,0,0,1,0,0,0,0,0,1], # 4 Core at (4,9)
        [1,0,0,0,0,1,0,'T',0,0,0,'T',0,1,0,0,0,0,0,1], # 5
        [1,0,'T',0,0,1,0,0,0,0,0,0,0,1,0,0,'T',0,0,1], # 6
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # 7
        [1,0,1,1,0,0,'T',0,1,1,1,0,'T',0,0,1,1,0,0,1], # 8
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # 9
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1], # 10
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], # 11
    ]
    ENEMY_SPAWN_GRID_POSITIONS = [(1, 1), (1, 18), (10, 1), (10, 18)] 

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type 
        
        self.grid = copy.deepcopy(self.MAZE_TILEMAP) 
        logger.info(f"MazeChapter2 initialized (id: {id(self)}). self.grid has been deepcopied from MAZE_TILEMAP.")
        
        self.actual_maze_rows = len(self.grid)
        self.actual_maze_cols = len(self.grid[0]) if self.actual_maze_rows > 0 else 0
        
        self.wall_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", BLUE) 
        self.path_color = BLACK
        self.turret_spot_color = (0, 100, 0, 150) 

        self.core_reactor_grid_pos = None
        self.core_reactor_abs_spawn_pos = None 
        self._find_core_reactor_spawn() 

        self.enemy_spawn_points_abs = [] 
        self.enemy_paths_to_core = {} 
        self._calculate_enemy_paths_and_spawn_points()

        self.debug_mode = False 
        logger.info(f"MazeChapter2 post-init (id: {id(self)}). Type: {maze_type}, Offset: {game_area_x_offset}, Grid rows: {self.actual_maze_rows}, cols: {self.actual_maze_cols}")

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
        logger.warning("MazeChapter2 WARNING: Core reactor 'C' not found in MAZE_TILEMAP.")

    def _calculate_enemy_paths_and_spawn_points(self):
        self.enemy_spawn_points_abs = []
        self.enemy_paths_to_core = {}
        if not self.core_reactor_grid_pos:
            logger.error("MazeChapter2 ERROR: Cannot calculate enemy paths, core reactor position unknown.")
            return

        for r, c in self.ENEMY_SPAWN_GRID_POSITIONS:
            if not (0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols):
                logger.warning(f"MazeChapter2 WARNING: Enemy spawn ({r},{c}) is out of bounds.")
                continue
            if self.grid[r][c] == 1: 
                logger.warning(f"MazeChapter2 WARNING: Enemy spawn ({r},{c}) is on a wall tile (current grid).")
                continue
            
            center_x_abs = c * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
            center_y_abs = r * TILE_SIZE + TILE_SIZE // 2
            self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))

            path_grid_coords = self.find_path_astar((r, c), self.core_reactor_grid_pos)
            if path_grid_coords:
                pixel_path = [self._grid_to_pixel_center(gr, gc) for gr, gc in path_grid_coords]
                self.enemy_paths_to_core[(r, c)] = pixel_path
            else:
                logger.warning(f"MazeChapter2 WARNING: No path found from enemy spawn ({r},{c}) to core at {self.core_reactor_grid_pos} (current grid state).")

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
        
        g_score = {pos: float('inf') for r_idx in range(self.actual_maze_rows) for c_idx in range(self.actual_maze_cols) for pos in [(r_idx,c_idx)]}
        g_score[start_grid_pos] = 0
        
        f_score = {pos: float('inf') for r_idx in range(self.actual_maze_rows) for c_idx in range(self.actual_maze_cols) for pos in [(r_idx,c_idx)]}
        f_score[start_grid_pos] = self.manhattan_distance(start_grid_pos, end_grid_pos)

        open_set_hash = {start_grid_pos} 

        while open_set:
            _, current_pos = heappop(open_set)
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
                    # This detailed log includes the MAZE_TILEMAP value for comparison
                    logger.debug(f"Maze.is_wall (id:{id(self)}): COLLISION at point ({px:.1f},{py:.1f}) -> Grid ({grid_r},{grid_c}), self.grid value '{tile_value}', MAZE_TILEMAP value '{self.MAZE_TILEMAP[grid_r][grid_c]}'. Is wall? True")
                    return True 
            else:
                logger.debug(f"Maze.is_wall (id:{id(self)}): Point ({px:.1f},{py:.1f}) -> Grid ({grid_r},{grid_c}) is OUT OF BOUNDS. Returning True.")
                return True 
        
        return False

    def can_place_turret(self, grid_r, grid_c):
        # Turrets can ONLY be placed on 'T' (turret spot) tiles.
        if not (0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols):
            logger.debug(f"can_place_turret (id:{id(self)}): ({grid_r},{grid_c}) is out of bounds.")
            return False 

        # Check the CURRENT value in self.grid. If it's 'T', it's an available spot.
        if self.grid[grid_r][grid_c] != 'T':
            logger.debug(f"can_place_turret (id:{id(self)}): Attempt to place turret at ({grid_r},{grid_c}). Tile is '{self.grid[grid_r][grid_c]}', not 'T'.")
            return False 

        original_tile_in_current_grid = self.grid[grid_r][grid_c] # Should be 'T'
        self.grid[grid_r][grid_c] = 1 # Temporarily mark as wall for path check
        
        all_paths_blocked = True
        if self.core_reactor_grid_pos: 
            for spawn_r_loop, spawn_c_loop in self.ENEMY_SPAWN_GRID_POSITIONS:
                if not (0 <= spawn_r_loop < self.actual_maze_rows and 0 <= spawn_c_loop < self.actual_maze_cols):
                    continue
                # Check original MAZE_TILEMAP for spawn validity to ensure spawn points themselves aren't blocked by definition
                # Also ensure the current grid state for spawn is not 1 unless it's the spot we are testing.
                if self.MAZE_TILEMAP[spawn_r_loop][spawn_c_loop] == 1 and (spawn_r_loop, spawn_c_loop) != (grid_r, grid_c) :
                     continue
                # Ensure the spawn point in the *live* grid (before this potential turret placement) is not a wall.
                # This check is tricky because self.grid is already modified temporarily.
                # We must check the original_tile_in_current_grid if the spawn is the tile we are testing.
                # Otherwise, check the live grid.
                spawn_tile_current_value = self.grid[spawn_r_loop][spawn_c_loop] if (spawn_r_loop, spawn_c_loop) != (grid_r, grid_c) else original_tile_in_current_grid
                if spawn_tile_current_value == 1 : # If already a wall (ignoring the one we are testing)
                    continue


                if self.find_path_astar((spawn_r_loop, spawn_c_loop), self.core_reactor_grid_pos):
                    all_paths_blocked = False 
                    break 
        else: 
            all_paths_blocked = False 
            logger.warning(f"can_place_turret (id:{id(self)}): Core reactor position unknown, cannot check path blocking accurately.")

        self.grid[grid_r][grid_c] = original_tile_in_current_grid # Revert change

        if all_paths_blocked:
            logger.info(f"MazeChapter2 (id:{id(self)}): Cannot place turret at ({grid_r},{grid_c}), it would block all enemy paths.")
            return False
            
        logger.info(f"MazeChapter2 (id:{id(self)}): can_place_turret: Allowing placement at ({grid_r},{grid_c}).")
        return True

    def mark_turret_spot_as_occupied(self, grid_r, grid_c):
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            original_value_in_current_grid = self.grid[grid_r][grid_c]
            # IMPORTANT: Only mark 'T' spots as occupied by changing them to 1.
            if original_value_in_current_grid == 'T': # Check against current grid state
                self.grid[grid_r][grid_c] = 1 
                logger.info(f"MazeChapter2 (id:{id(self)}): Turret spot ({grid_r},{grid_c}) marked as occupied (value changed from '{original_value_in_current_grid}' to 1).")
                self._calculate_enemy_paths_and_spawn_points() 
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

                if tile_type == 1: 
                    pygame.draw.rect(surface, self.wall_color, rect)
                elif tile_type == 0: 
                    pygame.draw.rect(surface, self.path_color, rect)
                elif tile_type == 'C': 
                    pygame.draw.rect(surface, self.path_color, rect) 
                    pygame.draw.circle(surface, gs.CYAN, (x + TILE_SIZE // 2, y + TILE_SIZE // 2), TILE_SIZE // 3)
                elif tile_type == 'T': # Unoccupied turret spot
                    pygame.draw.rect(surface, self.path_color, rect) 
                    temp_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                    temp_surface.fill(self.turret_spot_color)
                    surface.blit(temp_surface, (x,y))
                    pygame.draw.rect(surface, GREEN, rect, 1) 

        if self.debug_mode:
            for sp_x, sp_y in self.enemy_spawn_points_abs:
                pygame.draw.circle(surface, (255, 0, 255), (int(sp_x), int(sp_y)), TILE_SIZE // 4) 
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

    screen_width = gs.get_game_setting("WIDTH", 1280) 
    screen_height = gs.get_game_setting("HEIGHT", 720)
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("MazeChapter2 Test")
    clock = pygame.time.Clock()

    class MockGameController:
        def __init__(self):
            self.game_area_x_offset = 50 
            self.turrets_group = pygame.sprite.Group() 
            class MockDroneSystem:
                def __init__(self): self.player_cores = 200
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
    
    class MockCombatController:
        def __init__(self, gc, m):
            self.game_controller = gc
            self.maze = m
            self.turrets_group = gc.turrets_group 
        
        def try_place_turret(self, screen_pos):
            grid_c = int((screen_pos[0] - self.maze.game_area_x_offset) / TILE_SIZE)
            grid_r = int(screen_pos[1] / TILE_SIZE)
            
            if self.maze.can_place_turret(grid_r, grid_c): 
                if self.game_controller.drone_system.spend_player_cores(50): 
                    turret_sprite = pygame.sprite.Sprite()
                    turret_sprite.image = pygame.Surface((TILE_SIZE*0.6, TILE_SIZE*0.6))
                    turret_sprite.image.fill(gs.YELLOW)
                    turret_sprite.rect = turret_sprite.image.get_rect(
                        center=self.maze._grid_to_pixel_center(grid_r, grid_c)
                    )
                    self.turrets_group.add(turret_sprite)
                    self.maze.mark_turret_spot_as_occupied(grid_r, grid_c) 
                    logger_main.info(f"MockCombat: Turret placed at ({grid_r},{grid_c})")
                    return True
            logger_main.warning(f"MockCombat: Failed to place turret at ({grid_r},{grid_c})")
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
            if maze.core_reactor_abs_spawn_pos: # Added a check for existence
                pygame.draw.circle(screen, gs.RED, (int(maze.core_reactor_abs_spawn_pos[0]), int(maze.core_reactor_abs_spawn_pos[1])), TILE_SIZE // 3)

        currency_surf = font.render(f"Cores: {mock_gc.drone_system.get_player_cores()}", True, WHITE)
        screen.blit(currency_surf, (10, 10))
        
        turret_count_surf = font.render(f"Turrets: {len(mock_gc.turrets_group)}", True, WHITE)
        screen.blit(turret_count_surf, (10, 30))


        pygame.display.flip()
    pygame.quit()
