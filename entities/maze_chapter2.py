import pygame
import os
import random
from heapq import heappush, heappop
import math
import logging
import copy

import game_settings as gs
from game_settings import TILE_SIZE, BLUE, BLACK, RED, WHITE, GREEN, DARK_GREY

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class MazeChapter2:
    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset, self.maze_type = game_area_x_offset, maze_type
        self.grid, self.actual_maze_rows, self.actual_maze_cols = [], 0, 0
        self.enemy_spawn_grid_positions, self.turret_positions = [], []
        self.core_reactor_grid_pos, self.core_reactor_abs_spawn_pos = None, None
        self.enemy_spawn_points_abs, self.enemy_paths_to_core = [], {}
        self.debug_mode = False
        self.wall_color = gs.get_game_setting("ARCHITECT_VAULT_WALL_COLOR", BLUE)
        self.path_color, self.turret_spot_color = BLACK, (*GREEN[:3], 150)
        self.used_turret_spot_color = (*DARK_GREY[:3], 100)
        
        self._generate_procedural_map(40, 22)

        if self.core_reactor_grid_pos:
            self.core_reactor_abs_spawn_pos = self._grid_to_pixel_center(*self.core_reactor_grid_pos)
        else:
            logger.error("CRITICAL: Core 'C' not generated in the map.")
        
        self.enemy_spawn_points_abs = [self._grid_to_pixel_center(r, c) for r, c in self.enemy_spawn_grid_positions]
        self._calculate_all_enemy_paths()
        logger.info(f"MazeChapter2 initialized. Core at {self.core_reactor_grid_pos}. Found {len(self.enemy_spawn_grid_positions)} spawns.")

    def _generate_procedural_map(self, width, height):
        self.actual_maze_rows, self.actual_maze_cols = height, width
        grid = [[0 for _ in range(width)] for _ in range(height)]
        for r in range(4, height - 4):
            for c in range(4, width - 4):
                if (5 <= r <= 8 or 13 <= r <= 16) and (5 <= c <= 14 or 25 <= c <= 34):
                    grid[r][c] = 1
        core_pos = (height // 2, width // 2)
        self.core_reactor_grid_pos = core_pos
        bunker_size = 1
        for r_offset in range(-bunker_size, bunker_size + 1):
            for c_offset in range(-bunker_size, bunker_size + 1):
                grid[core_pos[0] + r_offset][core_pos[1] + c_offset] = 1
        grid[core_pos[0]][core_pos[1]] = 'C'
        grid[core_pos[0] - bunker_size][core_pos[1]] = 0
        grid[core_pos[0] + bunker_size][core_pos[1]] = 0
        grid[core_pos[0]][core_pos[1] - bunker_size] = 0
        grid[core_pos[0]][core_pos[1] + bunker_size] = 0
        spawns = [(0, 0), (0, width - 1), (height - 1, 0), (height - 1, width - 1)]
        for r, c in spawns:
            grid[r][c] = 'S'; self.enemy_spawn_grid_positions.append((r,c))
        turrets = [(2, 7), (2, 32), (height - 3, 7), (height - 3, 32), (9, 10), (9, 29), (12, 10), (12, 29), (7, 17), (7, 22), (14, 17), (14, 22), (height // 2, 2), (height // 2, width - 3)]
        for r,c in turrets:
            if 0 <= r < height and 0 <= c < width: grid[r][c] = 'T'; self.turret_positions.append((r,c))
        self.grid = grid

    def _calculate_all_enemy_paths(self):
        if not self.core_reactor_grid_pos: return
        for spawn_pos in self.enemy_spawn_grid_positions:
            path = self.find_path_astar(spawn_pos, self.core_reactor_grid_pos)
            if path: self.enemy_paths_to_core[spawn_pos] = [self._grid_to_pixel_center(r, c) for r, c in path]
            else: logger.warning(f"No A* path found from spawn {spawn_pos} to core {self.core_reactor_grid_pos}.")

    def _grid_to_pixel_center(self, r, c):
        return (c * TILE_SIZE) + (TILE_SIZE//2) + self.game_area_x_offset, (r * TILE_SIZE) + (TILE_SIZE//2)

    def get_neighbors(self, grid_pos):
        r, c = grid_pos; neighbors = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0), (-1,-1), (-1,1), (1,-1), (1,1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.actual_maze_rows and 0 <= nc < self.actual_maze_cols and self.grid[nr][nc] != 1: neighbors.append((nr, nc))
        return neighbors

    def find_path_astar(self, start, end):
        open_set = []
        heappush(open_set, (0, start))
        came_from = {}
        g_score = { (r,c): float('inf') for r in range(self.actual_maze_rows) for c in range(self.actual_maze_cols) }
        g_score[start] = 0
        open_set_hash = {start}
        while open_set:
            current = heappop(open_set)[1]
            if current == end:
                path = [];
                while current in came_from: path.append(current); current = came_from[current]
                path.append(start); return path[::-1]
            open_set_hash.remove(current)
            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + math.hypot(current[0]-neighbor[0], current[1]-neighbor[1])
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score = tentative_g_score + math.hypot(neighbor[0]-end[0], neighbor[1]-end[1])
                    if neighbor not in open_set_hash:
                        heappush(open_set, (f_score, neighbor)); open_set_hash.add(neighbor)
        return None

    def is_wall(self, x_abs, y_abs, width, height):
        points = [(x_abs-width/2, y_abs-height/2), (x_abs+width/2, y_abs-height/2), (x_abs-width/2, y_abs+height/2), (x_abs+width/2, y_abs+height/2)]
        for px, py in points:
            c = int((px - self.game_area_x_offset) / TILE_SIZE); r = int(py / TILE_SIZE)
            if not (0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols): return True
            if self.grid[r][c] == 1: return True
        return False

    def can_place_turret(self, r, c):
        return 0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols and self.grid[r][c] == 'T'

    def mark_turret_spot_as_occupied(self, r, c):
        if self.can_place_turret(r, c): self.grid[r][c] = 'U'; return True
        return False

    def draw(self, surface, camera):
        if not camera: return
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                world_rect = pygame.Rect(c*TILE_SIZE + self.game_area_x_offset, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                screen_rect = camera.apply_to_rect(world_rect)
                if not screen_rect.colliderect(surface.get_rect()): continue
                if tile != 1: pygame.draw.rect(surface, self.path_color, screen_rect)
                if tile == 1: pygame.draw.rect(surface, self.wall_color, screen_rect)
                elif tile == 'C': pygame.draw.circle(surface, gs.CYAN, screen_rect.center, int(TILE_SIZE/3 * camera.zoom_level))
                elif tile in ('T', 'U'):
                    overlay_color = self.turret_spot_color if tile == 'T' else self.used_turret_spot_color
                    border_color = GREEN if tile == 'T' else DARK_GREY
                    if (scaled_size := int(TILE_SIZE * camera.zoom_level)) > 0:
                        temp_surf = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
                        temp_surf.fill(overlay_color); surface.blit(temp_surf, screen_rect.topleft)
                        pygame.draw.rect(surface, border_color, screen_rect, 1)

    def toggle_debug(self): self.debug_mode = not self.debug_mode; logger.info(f"MazeChapter2: Debug mode {'enabled' if self.debug_mode else 'disabled'}.")
    def get_core_reactor_spawn_position_abs(self): return self.core_reactor_abs_spawn_pos
    def get_enemy_spawn_points_abs(self): return self.enemy_spawn_points_abs
    def get_enemy_path_to_core(self, spawn_pos): return self.enemy_paths_to_core.get(spawn_pos, [])
    def get_path_cells_abs(self): return [self._grid_to_pixel_center(r, c) for r, row in enumerate(self.grid) for c, tile in enumerate(row) if tile != 1]