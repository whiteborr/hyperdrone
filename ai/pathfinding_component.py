# ai/pathfinding_component.py
from math import hypot, degrees, atan2, cos, sin
from random import choice, uniform
import logging
from pygame import Rect

from hyperdrone_core.pathfinding import a_star_search, find_wall_follow_target, find_alternative_target
from settings_manager import get_setting

logger = logging.getLogger(__name__)

class PathfinderComponent:
    def __init__(self, enemy):
        self.enemy = enemy

        self.path = []
        self.current_path_index = 0
        self.last_path_recalc_time = 0

        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.PATH_RECALC_INTERVAL = 800  # Reduced from 1000ms
        self.WAYPOINT_THRESHOLD = tile_size * 0.5  # Increased from 0.3

        self.stuck_timer = 0
        self.last_pos_check = (enemy.x, enemy.y)
        self.STUCK_TIME_THRESHOLD_MS = 2500
        self.STUCK_MOVE_THRESHOLD = 0.5
        self.alternative_target = None
        self.alternative_target_timer = 0
        self.ALTERNATIVE_TARGET_TIMEOUT = 5000

    def set_target(self, target_pos, maze, current_time_ms, game_area_x_offset=0):
        if not target_pos or not maze:
            self.path = []
            return
        self._recalculate_path(target_pos, maze, current_time_ms, game_area_x_offset)

    def _recalculate_path(self, target_pos, maze, current_time_ms, game_area_x_offset=0):
        if not target_pos or not maze:
            self.path = []
            return

        if self.alternative_target and current_time_ms - self.alternative_target_timer < self.ALTERNATIVE_TARGET_TIMEOUT:
            target_pos = self._grid_to_pixel_center(self.alternative_target[0], self.alternative_target[1], game_area_x_offset)
        else:
            self.alternative_target = None

        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms
            enemy_grid = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
            target_grid = self._pixel_to_grid(target_pos[0], target_pos[1], game_area_x_offset)

            if not (0 <= enemy_grid[0] < maze.actual_maze_rows and 0 <= enemy_grid[1] < maze.actual_maze_cols and 
                    0 <= target_grid[0] < maze.actual_maze_rows and 0 <= target_grid[1] < maze.actual_maze_cols):
                self.path = []
                return

            if hasattr(maze, 'grid') and maze.grid[target_grid[0]][target_grid[1]] == 1:
                self.path = []
                return

            grid_path = a_star_search(maze.grid, enemy_grid, target_grid, maze.actual_maze_rows, maze.actual_maze_cols)

            if grid_path and len(grid_path) > 1:
                self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path]
                self.current_path_index = 1
                if not self.alternative_target:
                    self.alternative_target = None
            else:
                if not self.alternative_target:
                    alt_target = find_alternative_target(maze, enemy_grid, target_grid, maze.actual_maze_rows, maze.actual_maze_cols)
                    if alt_target:
                        self.alternative_target = alt_target
                        self.alternative_target_timer = current_time_ms
                        alt_path = a_star_search(maze.grid, enemy_grid, alt_target, maze.actual_maze_rows, maze.actual_maze_cols)
                        if alt_path and len(alt_path) > 1:
                            self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in alt_path]
                            self.current_path_index = 1
                            return
                self.path = []

        if not self.path and target_pos:
            dx, dy = target_pos[0] - self.enemy.x, target_pos[1] - self.enemy.y
            if hypot(dx, dy) > 0:
                self.enemy.angle = degrees(atan2(dy, dx))

    def update_movement(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, speed_override=None):
        is_stuck = self._handle_stuck_logic(current_time_ms, delta_time_ms, maze, game_area_x_offset)
        if is_stuck:
            self.last_path_recalc_time = 0  # Force re-path
            return True

        effective_speed = speed_override if speed_override is not None else self.enemy.speed
        if not self.path or self.current_path_index >= len(self.path):
            return False

        target = self.path[self.current_path_index]
        dx, dy = target[0] - self.enemy.x, target[1] - self.enemy.y
        dist = hypot(dx, dy)

        if dist < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                self.path = []
                return False

        target = self.path[self.current_path_index]
        dx, dy = target[0] - self.enemy.x, target[1] - self.enemy.y
        dist = hypot(dx, dy)

        if dist > 0:
            self.enemy.angle = degrees(atan2(dy, dx))
            move_x, move_y = (dx/dist)*effective_speed, (dy/dist)*effective_speed
            next_x, next_y = self.enemy.x + move_x, self.enemy.y + move_y

            if not (maze and self.enemy.collision_rect and maze.is_wall(next_x, next_y, self.enemy.collision_rect.width, self.enemy.collision_rect.height)):
                self.enemy.x, self.enemy.y = next_x, next_y

        self.enemy.rect.center = (self.enemy.x, self.enemy.y)
        game_play_area_height = get_setting("display", "HEIGHT", 1080)
        self.enemy.rect.clamp_ip(Rect(game_area_x_offset, 0, get_setting("display", "WIDTH", 1920) - game_area_x_offset, game_play_area_height))
        self.enemy.x, self.enemy.y = self.enemy.rect.centerx, self.enemy.rect.centery
        if self.enemy.collision_rect:
            self.enemy.collision_rect.center = self.enemy.rect.center
        return False

    def _handle_stuck_logic(self, current_time_ms, delta_time_ms, maze, game_area_x_offset):
        dist_moved = hypot(self.enemy.x - self.last_pos_check[0], self.enemy.y - self.last_pos_check[1])
        if dist_moved < self.STUCK_MOVE_THRESHOLD:
            self.stuck_timer += delta_time_ms
        else:
            self.stuck_timer = 0
            self.last_pos_check = (self.enemy.x, self.enemy.y)

        if self.stuck_timer > self.STUCK_TIME_THRESHOLD_MS:
            logger.warning(f"Enemy {id(self.enemy)} stuck at ({self.enemy.x:.1f}, {self.enemy.y:.1f}) trying to reach {self.path[-1] if self.path else 'None'}")

            if maze and hasattr(maze, 'grid'):
                current_grid_pos = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
                wall_follow_target = find_wall_follow_target(maze, current_grid_pos, maze.actual_maze_rows, maze.actual_maze_cols)
                if wall_follow_target:
                    target_pixel = self._grid_to_pixel_center(wall_follow_target[0], wall_follow_target[1], game_area_x_offset)
                    self.path = []
                    self.last_path_recalc_time = 0
                    self._recalculate_path(target_pixel, maze, current_time_ms, game_area_x_offset)
                    self.stuck_timer = 0
                    return True

            walkable_tiles = []
            if hasattr(maze, 'get_walkable_tiles_abs'):
                walkable_tiles = maze.get_walkable_tiles_abs()

            if walkable_tiles:
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                viable_tiles = [p for p in walkable_tiles if tile_size * 3 < hypot(p[0] - self.enemy.x, p[1] - self.enemy.y) < tile_size * 12]
                if viable_tiles:
                    unstick_target = choice(viable_tiles)
                    self.path = []
                    self.last_path_recalc_time = 0
                    self._recalculate_path(unstick_target, maze, current_time_ms, game_area_x_offset)
                    self.stuck_timer = 0
                    return True

            angle = uniform(0, 2 * 3.14159)
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            self.enemy.x += cos(angle) * tile_size * 2
            self.enemy.y += sin(angle) * tile_size * 2
            self.enemy.rect.center = (self.enemy.x, self.enemy.y)
            self.enemy.collision_rect.center = self.enemy.rect.center
            self.stuck_timer = 0
            return True
        return False

    def _pixel_to_grid(self, px, py, offset=0):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return int(py / tile_size), int((px - offset) / tile_size)

    def _grid_to_pixel_center(self, r, c, offset=0):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return (c * tile_size) + (tile_size / 2) + offset, (r * tile_size) + (tile_size / 2)
