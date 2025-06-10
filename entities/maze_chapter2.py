# entities/maze_chapter2.py
import pygame
import os
import random
from heapq import heappush, heappop
import math
import logging 
import copy

import game_settings as gs

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class MazeChapter2:
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

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        
        # --- DYNAMIC DIMENSION CALCULATION ---
        height = gs.get_game_setting("HEIGHT")
        width = gs.get_game_setting("WIDTH")
        tile_size = gs.get_game_setting("TILE_SIZE")
        
        self.actual_maze_rows = height // tile_size
        self.actual_maze_cols = (width - self.game_area_x_offset) // tile_size
        
        self.CORE_POS = (0, 0)
        self.TURRET_POSITIONS = []
        self.ENEMY_SPAWN_GRID_POSITIONS = []
        
        self.grid = self._build_tilemap()
        
        self.wall_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", gs.BLUE) 
        self.path_color = gs.BLACK 
        self.turret_spot_color = (0, 100, 0, 150) 
        self.used_turret_spot_color = (50, 50, 50, 100)

        self.core_reactor_grid_pos = None 
        self.core_reactor_abs_spawn_pos = None 
        self._find_core_reactor_spawn() 

        self.enemy_spawn_points_abs = [] 
        self.enemy_paths_to_core = {} 
        self._calculate_enemy_paths_and_spawn_points() 

        self.debug_mode = False 
        
        core_status_message = f"Core found at {self.core_reactor_grid_pos}" if self.core_reactor_grid_pos else "Core NOT found"
        logger.info(f"MazeChapter2 post-init (id: {id(self)}). Type: {maze_type}, Offset: {game_area_x_offset}, Grid: {self.actual_maze_rows}x{self.actual_maze_cols}. {core_status_message}. Enemy spawns: {len(self.enemy_spawn_points_abs)}")
        
        if not self.core_reactor_grid_pos :
             logger.error(f"MazeChapter2 CRITICAL INIT CHECK: 'C' was NOT found in the generated grid. Check _build_tilemap and CORE_POS.")

    def _build_tilemap(self):
        grid = [[0 for _ in range(self.actual_maze_cols)] for _ in range(self.actual_maze_rows)]

        core_r = int(self.actual_maze_rows * self.CORE_POS_RELATIVE[0])
        core_c = int(self.actual_maze_cols * self.CORE_POS_RELATIVE[1])
        if 0 <= core_r < self.actual_maze_rows and 0 <= core_c < self.actual_maze_cols:
            grid[core_r][core_c] = 'C'
            self.CORE_POS = (core_r, core_c)
        else:
            self.CORE_POS = (self.actual_maze_rows // 2, self.actual_maze_cols // 2)
            grid[self.CORE_POS[0]][self.CORE_POS[1]] = 'C'

        for rel_r, rel_c in self.TURRET_POSITIONS_RELATIVE:
            r_turret = int(self.actual_maze_rows * rel_r)
            c_turret = int(self.actual_maze_cols * rel_c)
            if 0 <= r_turret < self.actual_maze_rows and 0 <= c_turret < self.actual_maze_cols:
                grid[r_turret][c_turret] = 'T'
                self.TURRET_POSITIONS.append((r_turret, c_turret))

        for rel_r, rel_c in self.ENEMY_SPAWN_POSITIONS_RELATIVE:
            r_spawn = int((self.actual_maze_rows - 1) * rel_r)
            c_spawn = int((self.actual_maze_cols - 1) * rel_c)
            r_spawn = max(0, min(r_spawn, self.actual_maze_rows - 1))
            c_spawn = max(0, min(c_spawn, self.actual_maze_cols - 1))
            if grid[r_spawn][c_spawn] == 0:
                 self.ENEMY_SPAWN_GRID_POSITIONS.append((r_spawn, c_spawn))

        for r_spawn, c_spawn in self.ENEMY_SPAWN_GRID_POSITIONS:
            self._carve_path(grid, (r_spawn, c_spawn), (r_spawn, self.CORE_POS[1]))
            self._carve_path(grid, (r_spawn, self.CORE_POS[1]), self.CORE_POS)
        
        return grid

    def _carve_path(self, grid, start_pos, end_pos):
        r1, c1 = start_pos
        r2, c2 = end_pos
        if r1 == r2:
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if 0 <= r1 < self.actual_maze_rows and 0 <= c < self.actual_maze_cols: 
                    if grid[r1][c] == 0: grid[r1][c] = 0
        elif c1 == c2:
            for r in range(min(r1, r2), max(r1, r2) + 1):
                if 0 <= r < self.actual_maze_rows and 0 <= c1 < self.actual_maze_cols: 
                    if grid[r][c1] == 0: grid[r][c1] = 0
    
    def _find_core_reactor_spawn(self):
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    center_x_abs = c_idx * gs.TILE_SIZE + gs.TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * gs.TILE_SIZE + gs.TILE_SIZE // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    return 

    def _calculate_enemy_paths_and_spawn_points(self):
        self.enemy_spawn_points_abs = []
        self.enemy_paths_to_core = {}
        if not self.core_reactor_grid_pos:
            return

        for r, c in self.ENEMY_SPAWN_GRID_POSITIONS:
            center_x_abs = c * gs.TILE_SIZE + gs.TILE_SIZE // 2 + self.game_area_x_offset
            center_y_abs = r * gs.TILE_SIZE + gs.TILE_SIZE // 2
            self.enemy_spawn_points_abs.append((center_x_abs, center_y_abs))

            path_grid_coords = self.find_path_astar((r, c), self.core_reactor_grid_pos)
            if path_grid_coords:
                pixel_path = [self._grid_to_pixel_center(gr, gc) for gr, gc in path_grid_coords]
                self.enemy_paths_to_core[(r, c)] = pixel_path

    def _grid_to_pixel_center(self, grid_row, grid_col):
        pixel_x = (grid_col * gs.TILE_SIZE) + (gs.TILE_SIZE // 2) + self.game_area_x_offset
        pixel_y = (grid_row * gs.TILE_SIZE) + (gs.TILE_SIZE // 2)
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
        points_to_check = [
            (obj_center_x_abs - obj_width / 2, obj_center_y_abs - obj_height / 2), 
            (obj_center_x_abs + obj_width / 2, obj_center_y_abs - obj_height / 2), 
            (obj_center_x_abs - obj_width / 2, obj_center_y_abs + obj_height / 2), 
            (obj_center_x_abs + obj_width / 2, obj_center_y_abs + obj_height / 2)
        ]

        for px, py in points_to_check:
            grid_c = int((px - self.game_area_x_offset) / gs.TILE_SIZE)
            grid_r = int(py / gs.TILE_SIZE)
            if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
                if self.grid[grid_r][grid_c] == 1: return True
            else: return True 
        return False

    def can_place_turret(self, grid_r, grid_c):
        if not (0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols):
            return False 
        if self.grid[grid_r][grid_c] != 'T':
            return False
        return True

    def mark_turret_spot_as_occupied(self, grid_r, grid_c):
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            if self.grid[grid_r][grid_c] == 'T':
                self.grid[grid_r][grid_c] = 'U' 
                return True
        return False

    def draw(self, surface, camera=None):
        tile_size = gs.get_game_setting("TILE_SIZE")
        for r_idx, row_data in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row_data):
                x = c_idx * tile_size + self.game_area_x_offset
                y = r_idx * tile_size
                rect = (x, y, tile_size, tile_size)

                if tile_type == 1:
                    pygame.draw.rect(surface, self.wall_color, rect)
                elif tile_type == 0:
                    pygame.draw.rect(surface, self.path_color, rect)
                elif tile_type == 'C':
                    pygame.draw.rect(surface, self.path_color, rect)
                    pygame.draw.circle(surface, gs.CYAN, (x + tile_size // 2, y + tile_size // 2), tile_size // 3)
                elif tile_type == 'T':
                    pygame.draw.rect(surface, self.path_color, rect)
                    temp_surface_for_turret_spot = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                    temp_surface_for_turret_spot.fill(self.turret_spot_color)
                    surface.blit(temp_surface_for_turret_spot, (x,y))
                    pygame.draw.rect(surface, gs.GREEN, rect, 1)
                elif tile_type == 'U':
                    pygame.draw.rect(surface, self.path_color, rect)

        if self.debug_mode:
            for r_spawn, c_spawn in self.ENEMY_SPAWN_GRID_POSITIONS:
                 abs_spawn_x, abs_spawn_y = self._grid_to_pixel_center(r_spawn, c_spawn)
                 pygame.draw.circle(surface, (255, 0, 255), (int(abs_spawn_x), int(abs_spawn_y)), tile_size // 4)
            
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
                    center_x_abs = c_idx * gs.TILE_SIZE + gs.TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * gs.TILE_SIZE + gs.TILE_SIZE // 2
                    path_cells.append((center_x_abs, center_y_abs))
        return path_cells

    def get_random_path_cell_center_abs(self):
        path_cells = self.get_path_cells_abs()
        return random.choice(path_cells) if path_cells else None