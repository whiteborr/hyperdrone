# entities/maze_chapter3.py
from pygame.draw import rect, circle, lines
from pygame import Surface, SRCALPHA
from random import choice
from heapq import heappush, heappop
from math import sin
from logging import getLogger, basicConfig, info, error, DEBUG

from settings_manager import get_setting
from constants import BLACK, BLUE, RED, GREEN, YELLOW, CYAN

logger = getLogger(__name__)
if not logger.hasHandlers():
    basicConfig(level=DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class MazeChapter3:
    # --- RELATIVE POSITIONS FOR DYNAMIC PLACEMENT ---
    CORE_POS_RELATIVE = (0.5, 0.5)
    TURRET_POSITIONS_RELATIVE = [
        (0.25, 0.4), (0.25, 0.6),
        (0.75, 0.4), (0.75, 0.6),
        (0.5, 0.3)
    ]
    ENEMY_SPAWN_POSITIONS_RELATIVE = [
        (0, 0.5), (1, 0.5), (0.5, 0), (0.5, 1)
    ]

    def __init__(self, game_area_x_offset=0, maze_type="chapter3_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        
        self._initialize_dimensions()
        self._initialize_positions()
        self._initialize_colors()
        self._build_maze()
        self._initialize_debug_settings()
        self._log_initialization_status()
    
    def _initialize_dimensions(self):
        height = get_setting("display", "HEIGHT", 1080)
        width = get_setting("display", "WIDTH", 1920)
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        self.actual_maze_rows = height // tile_size
        self.actual_maze_cols = (width - self.game_area_x_offset) // tile_size
    
    def _initialize_positions(self):
        self.CORE_POS = (0, 0)
        self.TURRET_POSITIONS = []
        self.ENEMY_SPAWN_GRID_POSITIONS = []
        
        self.core_reactor_grid_pos = None
        self.core_reactor_abs_spawn_pos = None
        self.enemy_spawn_points_abs = []
        self.enemy_paths_to_core = {}
    
    def _initialize_colors(self):
        self.wall_color = get_setting("display", "ARCHITECT_VAULT_WALL_COLOR", BLUE)
        self.path_color = BLACK
        self.turret_spot_color = (0, 100, 0, 150)
        self.used_turret_spot_color = (50, 50, 50, 100)
    
    def _build_maze(self):
        self.grid = self._build_tilemap()
        self._find_core_reactor_spawn()
        self._calculate_enemy_paths_and_spawn_points()
    
    def _initialize_debug_settings(self):
        self.debug_mode = False
        self.initial_zoom_level = 0.4
    
    def _log_initialization_status(self):
        core_status = f"Core found at {self.core_reactor_grid_pos}" if self.core_reactor_grid_pos else "Core NOT found"
        info(f"MazeChapter3 post-init (id: {id(self)}). Type: {self.maze_type}, Offset: {self.game_area_x_offset}, Grid: {self.actual_maze_rows}x{self.actual_maze_cols}. {core_status}. Enemy spawns: {len(self.enemy_spawn_points_abs)}")
        
        if not self.core_reactor_grid_pos:
            error(f"MazeChapter3 CRITICAL INIT CHECK: 'C' was NOT found in the generated grid. Check _build_tilemap and CORE_POS.")

    def _build_tilemap(self):
        grid = [[0 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]
        
        self._place_core(grid)
        self._place_turrets(grid)
        self._place_enemy_spawns(grid)
        self._carve_paths_to_core(grid)
        
        return grid
    
    def _place_core(self, grid):
        core_r = int(self.actual_maze_rows * self.CORE_POS_RELATIVE[0])
        core_c = int(self.actual_maze_cols * self.CORE_POS_RELATIVE[1])
        
        if self._is_valid_position(core_r, core_c):
            self.CORE_POS = (core_r, core_c)
        else:
            self.CORE_POS = (self.actual_maze_rows // 2, self.actual_maze_cols // 2)
        
        grid[self.CORE_POS[0]][self.CORE_POS[1]] = 'C'
    
    def _place_turrets(self, grid):
        for rel_r, rel_c in self.TURRET_POSITIONS_RELATIVE:
            r_turret = int(self.actual_maze_rows * rel_r)
            c_turret = int(self.actual_maze_cols * rel_c)
            
            if self._is_valid_position(r_turret, c_turret):
                grid[r_turret][c_turret] = 'T'
                self.TURRET_POSITIONS.append((r_turret, c_turret))
    
    def _place_enemy_spawns(self, grid):
        for rel_r, rel_c in self.ENEMY_SPAWN_POSITIONS_RELATIVE:
            r_spawn = int((self.actual_maze_rows - 1) * rel_r)
            c_spawn = int((self.actual_maze_cols - 1) * rel_c)
            
            r_spawn = max(0, min(r_spawn, self.actual_maze_rows - 1))
            c_spawn = max(0, min(c_spawn, self.actual_maze_cols - 1))
            
            if grid[r_spawn][c_spawn] == 0:
                self.ENEMY_SPAWN_GRID_POSITIONS.append((r_spawn, c_spawn))
    
    def _carve_paths_to_core(self, grid):
        for r_spawn, c_spawn in self.ENEMY_SPAWN_GRID_POSITIONS:
            self._carve_path(grid, (r_spawn, c_spawn), (r_spawn, self.CORE_POS[1]))
            self._carve_path(grid, (r_spawn, self.CORE_POS[1]), self.CORE_POS)
    
    def _is_valid_position(self, r, c):
        return 0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols

    def _carve_path(self, grid, start_pos, end_pos):
        r1, c1 = start_pos
        r2, c2 = end_pos
        
        if r1 == r2:
            self._carve_horizontal_path(grid, r1, c1, c2)
        elif c1 == c2:
            self._carve_vertical_path(grid, c1, r1, r2)
    
    def _carve_horizontal_path(self, grid, row, c1, c2):
        for c in range(min(c1, c2), max(c1, c2) + 1):
            if self._is_valid_position(row, c) and grid[row][c] == 0:
                grid[row][c] = 0
    
    def _carve_vertical_path(self, grid, col, r1, r2):
        for r in range(min(r1, r2), max(r1, r2) + 1):
            if self._is_valid_position(r, col) and grid[r][col] == 0:
                grid[r][col] = 0
    
    def _find_core_reactor_spawn(self):
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                    center_x_abs = c_idx * tile_size + tile_size // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * tile_size + tile_size // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    return 

    def _calculate_enemy_paths_and_spawn_points(self):
        self.enemy_spawn_points_abs = []
        self.enemy_paths_to_core = {}
        if not self.core_reactor_grid_pos:
            return

        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        for r, c in self.ENEMY_SPAWN_GRID_POSITIONS:
            center_x_abs = c * tile_size + tile_size // 2 + self.game_area_x_offset
            center_y_abs = r * tile_size + tile_size // 2
            self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))

            path_grid_coords = self.find_path_astar((r, c), self.core_reactor_grid_pos)
            if path_grid_coords:
                pixel_path = [self._grid_to_pixel_center(gr, gc) for gr, gc in path_grid_coords]
                self.enemy_paths_to_core[(r, c)] = pixel_path

    def _grid_to_pixel_center(self, grid_row, grid_col):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        pixel_x = (grid_col * tile_size) + (tile_size // 2) + self.game_area_x_offset
        pixel_y = (grid_row * tile_size) + (tile_size // 2)
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
        open_set_hash = {start_grid_pos}
        came_from = {}
        
        g_score, f_score = self._initialize_scores(start_grid_pos, end_grid_pos)
        
        while open_set:
            current_pos = self._get_next_position(open_set, open_set_hash)
            if not current_pos:
                continue
            
            if current_pos == end_grid_pos:
                return self._reconstruct_path(came_from, current_pos, start_grid_pos)
            
            self._process_neighbors(current_pos, end_grid_pos, open_set, open_set_hash, 
                                  came_from, g_score, f_score)
        
        return None
    
    def _initialize_scores(self, start_pos, end_pos):
        g_score = {(r, c): float('inf') for r in range(self.actual_maze_rows) 
                  for c in range(self.actual_maze_cols)}
        f_score = {(r, c): float('inf') for r in range(self.actual_maze_rows) 
                  for c in range(self.actual_maze_cols)}
        
        g_score[start_pos] = 0
        f_score[start_pos] = self.manhattan_distance(start_pos, end_pos)
        
        return g_score, f_score
    
    def _get_next_position(self, open_set, open_set_hash):
        _, current_pos = heappop(open_set)
        if current_pos not in open_set_hash:
            return None
        open_set_hash.remove(current_pos)
        return current_pos
    
    def _reconstruct_path(self, came_from, current_pos, start_pos):
        path = []
        temp = current_pos
        while temp in came_from:
            path.append(temp)
            temp = came_from[temp]
        path.append(start_pos)
        return path[::-1]
    
    def _process_neighbors(self, current_pos, end_pos, open_set, open_set_hash, 
                          came_from, g_score, f_score):
        for neighbor_pos in self.get_neighbors(current_pos):
            tentative_g_score = g_score[current_pos] + 1
            
            if tentative_g_score < g_score[neighbor_pos]:
                came_from[neighbor_pos] = current_pos
                g_score[neighbor_pos] = tentative_g_score
                f_score[neighbor_pos] = tentative_g_score + self.manhattan_distance(neighbor_pos, end_pos)
                
                if neighbor_pos not in open_set_hash:
                    heappush(open_set, (f_score[neighbor_pos], neighbor_pos))
                    open_set_hash.add(neighbor_pos) 

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width, obj_height):
        corner_points = self._get_object_corners(obj_center_x_abs, obj_center_y_abs, obj_width, obj_height)
        
        for px, py in corner_points:
            if self._is_point_in_wall(px, py):
                return True
        
        return False
    
    def _get_object_corners(self, center_x, center_y, width, height):
        half_width = width / 2
        half_height = height / 2
        
        return [
            (center_x - half_width, center_y - half_height),
            (center_x + half_width, center_y - half_height),
            (center_x - half_width, center_y + half_height),
            (center_x + half_width, center_y + half_height)
        ]
    
    def _is_point_in_wall(self, px, py):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        grid_c = int((px - self.game_area_x_offset) / tile_size)
        grid_r = int(py / tile_size)
        
        if not self._is_valid_position(grid_r, grid_c):
            return True
        
        return self.grid[grid_r][grid_c] == 1

    def can_place_turret(self, grid_r, grid_c):
        return (self._is_valid_position(grid_r, grid_c) and 
                self.grid[grid_r][grid_c] == 'T')
    
    def mark_turret_spot_as_occupied(self, grid_r, grid_c):
        if not self._is_valid_position(grid_r, grid_c):
            return False
        
        if self.grid[grid_r][grid_c] == 'T':
            self.grid[grid_r][grid_c] = 'U'
            return True
        
        return False

    def draw(self, surface, camera=None):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        self._draw_tiles(surface, camera, tile_size)
        
        if self.debug_mode:
            self._draw_debug_info(surface, camera, tile_size)
    
    def _draw_tiles(self, surface, camera, tile_size):
        for r_idx, row_data in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row_data):
                tile_rect = self._calculate_tile_rect(r_idx, c_idx, tile_size, camera)
                self._draw_tile(surface, tile_type, tile_rect, camera, tile_size)
    
    def _calculate_tile_rect(self, r_idx, c_idx, tile_size, camera):
        x = c_idx * tile_size + self.game_area_x_offset
        y = r_idx * tile_size
        
        if camera:
            rect_pos = camera.apply_to_pos((x, y))
            return (rect_pos[0], rect_pos[1], 
                   tile_size * camera.zoom_level, tile_size * camera.zoom_level)
        else:
            return (x, y, tile_size, tile_size)
    
    def _draw_tile(self, surface, tile_type, tile_rect, camera, tile_size):
        if tile_type == 1:
            rect(surface, self.wall_color, tile_rect)
        elif tile_type in [0, 'U']:
            rect(surface, self.path_color, tile_rect)
        elif tile_type == 'C':
            self._draw_core_tile(surface, tile_rect, camera, tile_size)
        elif tile_type == 'T':
            self._draw_turret_tile(surface, tile_rect, camera, tile_size)
    
    def _draw_core_tile(self, surface, tile_rect, camera, tile_size):
        rect(surface, self.path_color, tile_rect)
        
        x, y = tile_rect[0], tile_rect[1]
        center_pos = (x + tile_size // 2, y + tile_size // 2)
        
        if camera:
            center_pos = camera.apply_to_pos(center_pos)
            radius = int((tile_size // 3) * camera.zoom_level)
        else:
            radius = tile_size // 3
        
        circle(surface, CYAN, center_pos, radius)
    
    def _draw_turret_tile(self, surface, tile_rect, camera, tile_size):
        rect(surface, self.path_color, tile_rect)
        
        # Draw turret spot overlay
        if camera:
            overlay_size = (int(tile_size * camera.zoom_level), int(tile_size * camera.zoom_level))
        else:
            overlay_size = (tile_size, tile_size)
        
        temp_surface = Surface(overlay_size, SRCALPHA)
        temp_surface.fill(self.turret_spot_color)
        surface.blit(temp_surface, (tile_rect[0], tile_rect[1]))
        
        rect(surface, GREEN, tile_rect, 1)
    
    def _draw_debug_info(self, surface, camera, tile_size):
        self._draw_spawn_points(surface, camera, tile_size)
        self._draw_enemy_paths(surface, camera)
    
    def _draw_spawn_points(self, surface, camera, tile_size):
        for r_spawn, c_spawn in self.ENEMY_SPAWN_GRID_POSITIONS:
            abs_spawn_x, abs_spawn_y = self._grid_to_pixel_center(r_spawn, c_spawn)
            
            if camera:
                spawn_pos = camera.apply_to_pos((abs_spawn_x, abs_spawn_y))
                radius = int((tile_size // 4) * camera.zoom_level)
            else:
                spawn_pos = (int(abs_spawn_x), int(abs_spawn_y))
                radius = tile_size // 4
            
            circle(surface, (255, 0, 255), spawn_pos, radius)
    
    def _draw_enemy_paths(self, surface, camera):
        for (spawn_r, spawn_c), path_pixel_coords in self.enemy_paths_to_core.items():
            if not path_pixel_coords or len(path_pixel_coords) <= 1:
                continue
            
            if camera:
                transformed_path = [camera.apply_to_pos(pos) for pos in path_pixel_coords]
                line_width = max(1, int(2 * camera.zoom_level))
                lines(surface, (255, 165, 0), False, transformed_path, line_width)
            else:
                lines(surface, (255, 165, 0), False, path_pixel_coords, 2) 

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode
        status = 'enabled' if self.debug_mode else 'disabled'
        logger.info(f"MazeChapter3: Debug mode {status}.")

    def get_core_reactor_spawn_position_abs(self):
        return self.core_reactor_abs_spawn_pos

    def get_enemy_spawn_points_abs(self):
        return self.enemy_spawn_points_abs

    def get_enemy_path_to_core(self, enemy_spawn_grid_pos):
        return self.enemy_paths_to_core.get(enemy_spawn_grid_pos, [])

    def get_path_cells_abs(self):
        path_cells = []
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                if tile_type != 1:
                    center_pos = self._grid_to_pixel_center(r_idx, c_idx)
                    path_cells.append(center_pos)
        
        return path_cells

    def get_random_path_cell_center_abs(self):
        path_cells = self.get_path_cells_abs()
        return choice(path_cells) if path_cells else None
