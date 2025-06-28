# entities/maze_chapter3.py
from pygame.draw import rect, circle, lines
from pygame import Surface, SRCALPHA
from random import choice
from heapq import heappush, heappop
from logging import getLogger, basicConfig, info, error, DEBUG

from settings_manager import get_setting
from constants import BLACK, BLUE, RED, GREEN, YELLOW, CYAN

logger = getLogger(__name__)
if not logger.hasHandlers():
    basicConfig(level=DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


class MazeChapter3:
    CORE_POS_RELATIVE = (0.5, 0.5)
    TURRET_POSITIONS_RELATIVE = [
        (0.25, 0.4), (0.25, 0.6), (0.75, 0.4), (0.75, 0.6), (0.5, 0.3)
    ]
    ENEMY_SPAWN_POSITIONS_RELATIVE = [
        (0, 0.5), (1, 0.5), (0.5, 0), (0.5, 1)
    ]

    def __init__(self, game_area_x_offset=0, maze_type="chapter3_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        self.debug_mode = False
        
        self._setup_dimensions()
        self._setup_colors()
        self._build_maze()
        self._log_status()
    
    def _setup_dimensions(self):
        height = get_setting("display", "HEIGHT", 1080)
        width = get_setting("display", "WIDTH", 1920)
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        
        self.rows = height // self.tile_size
        self.cols = (width - self.game_area_x_offset) // self.tile_size
    
    def _setup_colors(self):
        self.wall_color = get_setting("display", "ARCHITECT_VAULT_WALL_COLOR", BLUE)
        self.path_color = BLACK
        self.turret_spot_color = (0, 100, 0, 150)
    
    def _build_maze(self):
        self.grid = self._create_grid()
        self.core_pos = self._place_core()
        self.turret_positions = self._place_turrets()
        self.enemy_spawns = self._place_enemy_spawns()
        self._create_paths()
        self._calculate_absolute_positions()
    
    def _log_status(self):
        core_found = "found" if self.core_pos else "NOT found"
        info(f"MazeChapter3 initialized: {self.rows}x{self.cols} grid, core {core_found}, {len(self.enemy_spawns)} enemy spawns")
        
        if not self.core_pos:
            error("CRITICAL: Core reactor position not found in grid")

    def _create_grid(self):
        return [[0 for _ in range(self.cols)] for _ in range(self.rows)]
    
    def _place_core(self):
        r = int(self.rows * self.CORE_POS_RELATIVE[0])
        c = int(self.cols * self.CORE_POS_RELATIVE[1])
        
        if not self._is_valid(r, c):
            r, c = self.rows // 2, self.cols // 2
        
        self.grid[r][c] = 'C'
        return (r, c)
    
    def _place_turrets(self):
        positions = []
        for rel_r, rel_c in self.TURRET_POSITIONS_RELATIVE:
            r = int(self.rows * rel_r)
            c = int(self.cols * rel_c)
            
            if self._is_valid(r, c):
                self.grid[r][c] = 'T'
                positions.append((r, c))
        return positions
    
    def _place_enemy_spawns(self):
        spawns = []
        for rel_r, rel_c in self.ENEMY_SPAWN_POSITIONS_RELATIVE:
            r = max(0, min(int((self.rows - 1) * rel_r), self.rows - 1))
            c = max(0, min(int((self.cols - 1) * rel_c), self.cols - 1))
            
            if self.grid[r][c] == 0:
                spawns.append((r, c))
        return spawns
    
    def _create_paths(self):
        for r, c in self.enemy_spawns:
            self._carve_path((r, c), (r, self.core_pos[1]))
            self._carve_path((r, self.core_pos[1]), self.core_pos)
    
    def _is_valid(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def _carve_path(self, start, end):
        r1, c1 = start
        r2, c2 = end
        
        if r1 == r2:  # Horizontal path
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if self._is_valid(r1, c) and self.grid[r1][c] == 0:
                    self.grid[r1][c] = 0
        elif c1 == c2:  # Vertical path
            for r in range(min(r1, r2), max(r1, r2) + 1):
                if self._is_valid(r, c1) and self.grid[r][c1] == 0:
                    self.grid[r][c1] = 0
    
    def _calculate_absolute_positions(self):
        self.core_abs_pos = self._to_pixel_center(*self.core_pos)
        self.enemy_spawn_abs = [self._to_pixel_center(r, c) for r, c in self.enemy_spawns]
        
        self.enemy_paths = {}
        for spawn in self.enemy_spawns:
            path = self.find_path_astar(spawn, self.core_pos)
            if path:
                self.enemy_paths[spawn] = [self._to_pixel_center(r, c) for r, c in path]

    def _to_pixel_center(self, r, c):
        x = c * self.tile_size + self.tile_size // 2 + self.game_area_x_offset
        y = r * self.tile_size + self.tile_size // 2
        return x, y

    def get_neighbors(self, pos):
        r, c = pos
        neighbors = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if self._is_valid(nr, nc) and self.grid[nr][nc] != 1:
                neighbors.append((nr, nc))
        return neighbors

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def find_path_astar(self, start, end):
        open_set = [(0, start)]
        open_hash = {start}
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.manhattan_distance(start, end)}
        
        while open_set:
            _, current = heappop(open_set)
            if current not in open_hash:
                continue
            open_hash.remove(current)
            
            if current == end:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current):
                tentative_g = g_score.get(current, float('inf')) + 1
                
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.manhattan_distance(neighbor, end)
                    
                    if neighbor not in open_hash:
                        heappush(open_set, (f_score[neighbor], neighbor))
                        open_hash.add(neighbor)
        
        return None
    
    def _reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return path[::-1] 

    def is_wall(self, center_x, center_y, width, height):
        half_w, half_h = width / 2, height / 2
        corners = [
            (center_x - half_w, center_y - half_h),
            (center_x + half_w, center_y - half_h),
            (center_x - half_w, center_y + half_h),
            (center_x + half_w, center_y + half_h)
        ]
        
        return any(self._is_point_wall(x, y) for x, y in corners)
    
    def _is_point_wall(self, x, y):
        c = int((x - self.game_area_x_offset) / self.tile_size)
        r = int(y / self.tile_size)
        
        if not self._is_valid(r, c):
            return True
        
        return self.grid[r][c] == 1

    def can_place_turret(self, r, c):
        return self._is_valid(r, c) and self.grid[r][c] == 'T'
    
    def mark_turret_occupied(self, r, c):
        if self._is_valid(r, c) and self.grid[r][c] == 'T':
            self.grid[r][c] = 'U'
            return True
        return False

    def draw(self, surface, camera=None):
        self._draw_tiles(surface, camera)
        if self.debug_mode:
            self._draw_debug(surface, camera)
    
    def _draw_tiles(self, surface, camera):
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                rect_data = self._get_tile_rect(r, c, camera)
                self._draw_tile(surface, tile, rect_data, camera)
    
    def _get_tile_rect(self, r, c, camera):
        x = c * self.tile_size + self.game_area_x_offset
        y = r * self.tile_size
        
        if camera:
            pos = camera.apply_to_pos((x, y))
            size = self.tile_size * camera.zoom_level
            return (*pos, size, size)
        return (x, y, self.tile_size, self.tile_size)
    
    def _draw_tile(self, surface, tile, rect_data, camera):
        if tile == 1:
            rect(surface, self.wall_color, rect_data)
        elif tile in [0, 'U']:
            rect(surface, self.path_color, rect_data)
        elif tile == 'C':
            self._draw_core(surface, rect_data, camera)
        elif tile == 'T':
            self._draw_turret_spot(surface, rect_data, camera)
    
    def _draw_core(self, surface, rect_data, camera):
        rect(surface, self.path_color, rect_data)
        
        x, y, w, h = rect_data
        center = (x + w // 2, y + h // 2)
        radius = int(w // 6) if camera else self.tile_size // 3
        
        circle(surface, CYAN, center, radius)
    
    def _draw_turret_spot(self, surface, rect_data, camera):
        rect(surface, self.path_color, rect_data)
        
        # Overlay
        overlay = Surface((rect_data[2], rect_data[3]), SRCALPHA)
        overlay.fill(self.turret_spot_color)
        surface.blit(overlay, rect_data[:2])
        
        rect(surface, GREEN, rect_data, 1)
    
    def _draw_debug(self, surface, camera):
        # Draw spawn points
        for spawn in self.enemy_spawns:
            pos = self._to_pixel_center(*spawn)
            if camera:
                pos = camera.apply_to_pos(pos)
                radius = int((self.tile_size // 4) * camera.zoom_level)
            else:
                radius = self.tile_size // 4
            circle(surface, (255, 0, 255), pos, radius)
        
        # Draw paths
        for spawn, path in self.enemy_paths.items():
            if len(path) > 1:
                if camera:
                    path = [camera.apply_to_pos(pos) for pos in path]
                    width = max(1, int(2 * camera.zoom_level))
                else:
                    width = 2
                lines(surface, (255, 165, 0), False, path, width) 

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode
        logger.info(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}")

    def get_core_position(self):
        return self.core_abs_pos

    def get_enemy_spawn_points(self):
        return self.enemy_spawn_abs

    def get_enemy_path(self, spawn_pos):
        return self.enemy_paths.get(spawn_pos, [])

    def get_path_cells(self):
        cells = []
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                if tile != 1:
                    cells.append(self._to_pixel_center(r, c))
        return cells

    def get_random_path_cell(self):
        cells = self.get_path_cells()
        return choice(cells) if cells else None
