import pygame
import os
import random
from heapq import heappush, heappop
import math

from .enemy import Enemy

import game_settings as gs
TILE_SIZE = gs.TILE_SIZE
BLUE = gs.BLUE
BLACK = gs.BLACK
RED = gs.RED
WHITE = gs.WHITE
GREEN = gs.GREEN
WIDTH = gs.WIDTH
HEIGHT = gs.HEIGHT


class CoreReactor(pygame.sprite.Sprite):
    def __init__(self, pos, health=100):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE * 0.7, TILE_SIZE * 0.7), pygame.SRCALPHA)
        pygame.draw.circle(self.image, RED, (TILE_SIZE * 0.35, TILE_SIZE * 0.35), TILE_SIZE * 0.35)
        pygame.draw.circle(self.image, WHITE, (TILE_SIZE * 0.35, TILE_SIZE * 0.35), TILE_SIZE * 0.35, 2)
        self.rect = self.image.get_rect(center=pos)
        self.health = health
        self.max_health = health
        self.alive = True

    def take_damage(self, amount):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                return True
        return False

    def draw_health_bar(self, surface):
        bar_width = TILE_SIZE
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.bottom + 10
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        pygame.draw.rect(surface, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0:
            pygame.draw.rect(surface, GREEN, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

class Turret(pygame.sprite.Sprite):
    def __init__(self, grid_r, grid_c, x_offset):
        super().__init__()
        self.grid_pos = (grid_r, grid_c)
        self.pos = (grid_c * TILE_SIZE + TILE_SIZE // 2 + x_offset, grid_r * TILE_SIZE + TILE_SIZE // 2)
        self.image = pygame.Surface((TILE_SIZE * 0.7, TILE_SIZE * 0.7), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 0), (TILE_SIZE * 0.35, TILE_SIZE * 0.35), TILE_SIZE * 0.35)
        self.rect = self.image.get_rect(center=self.pos)
        self.range = 3 * TILE_SIZE
        self.damage = 20
        self.fire_rate = 1
        self.time_since_last_shot = 0

    def update(self, dt, enemies):
        self.time_since_last_shot += dt
        if self.time_since_last_shot >= 1 / self.fire_rate:
            target = pygame.sprite.spritecollideany(self, enemies, collided=lambda s, e: math.hypot(s.rect.centerx - e.rect.centerx, s.rect.centery - e.rect.centery) <= self.range)
            if target and target.alive:
                if target.take_damage(self.damage):
                    target.kill()
                self.time_since_last_shot = 0

    def _load_sprite(self, sprite_path):
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7))
        if sprite_path and os.path.exists(sprite_path):
            try:
                self.image = pygame.image.load(sprite_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, default_size)
            except pygame.error:
                self.image = pygame.Surface(default_size, pygame.SRCALPHA)
                self.image.fill((0, 255, 255))
        else:
            self.image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.image.fill((0, 255, 255))
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self, maze, current_time_ms, game_area_x_offset, dt):
        if not self.alive:
            self.kill()
            return
        self._update_movement_along_path(maze, game_area_x_offset, dt)
        if self.is_in_defense_mode and self.defense_target and self.defense_target.alive:
            if self.rect.colliderect(self.defense_target.rect):
                if self.defense_target.take_damage(self.contact_damage):
                    print("Core destroyed!")
                self.alive = False
                self.path = []

    def _update_movement_along_path(self, maze, game_area_x_offset, dt):
        if not self.path or self.current_path_index >= len(self.path):
            return
        target = self.path[self.current_path_index]
        dx = target[0] - self.x
        dy = target[1] - self.y
        distance = math.hypot(dx, dy)
        if distance < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                self.path = []
                return
            target = self.path[self.current_path_index]
            dx = target[0] - self.x
            dy = target[1] - self.y
            distance = math.hypot(dx, dy)
        if distance > 0:
            move_x = (dx / distance) * self.speed * dt
            move_y = (dy / distance) * self.speed * dt
            next_x = self.x + move_x
            next_y = self.y + move_y
            if not maze.is_wall(next_x, next_y):
                self.x = next_x
                self.y = next_y
                self.rect.center = (int(self.x), int(self.y))

    def take_damage(self, amount):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                return True
        return False

    def draw_health_bar(self, surface):
        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 2
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        pygame.draw.rect(surface, (80, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0:
            pygame.draw.rect(surface, GREEN, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

class MazeChapter2:
    MAZE_TILEMAP = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # Top path
        [1,0,1,1,1,1,0,1,1,0,1,1,0,1,1,0,1,1,0,1],
        [1,0,1,0,0,0,0,'T',0,0,0,0,0,'T',0,0,0,0,0,1], # Turrets at (3,7), (3,13)
        [1,0,1,1,1,1,0,1,1,0,1,1,0,1,1,0,1,1,0,1],
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # Side paths
        [1,0,0,0,0,0,0,'T',0,'C',0,'T',0,0,0,0,0,0,0,1], # Core at (6,10), Turrets at (6,7), (6,13)
        [1,0,1,1,1,1,0,1,1,0,1,1,0,1,1,0,1,1,0,1],
        [1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        [1,0,1,1,1,1,0,1,1,'T',0,1,1,0,1,1,1,1,0,1], # Turret at (9,10)
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],  # Bottom path
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    ]

    ENEMY_SPAWN_GRID_POSITIONS = [(1, 1), (1, 18), (7, 1), (7, 18), (9, 3), (9, 16)]

    def __init__(self, game_area_x_offset=0, maze_type="chapter2_tilemap"):
        self.game_area_x_offset = game_area_x_offset
        self.maze_type = maze_type
        self.grid = self.MAZE_TILEMAP
        self.actual_maze_rows = len(self.grid)
        self.actual_maze_cols = len(self.grid[0]) if self.actual_maze_rows > 0 else 0
        self.wall_color = BLUE
        self.path_color = BLACK
        self.core_reactor_grid_pos = None
        self.core_reactor_abs_spawn_pos = None
        self.debug_mode = False
        self.turrets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.core_reactor = None
        self.wave_number = 0
        self.wave_cooldown = 0
        self.currency = 100
        self.turret_count = 0
        self.MAX_TURRETS = 5
        self._find_core_reactor_spawn()
        self.enemy_spawn_points_abs = []
        self.enemy_paths = {}
        self._calculate_enemy_spawn_points_abs()

    def _find_core_reactor_spawn(self):
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile in enumerate(row):
                if tile == 'C':
                    self.core_reactor_grid_pos = (r_idx, c_idx)
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    self.core_reactor_abs_spawn_pos = (center_x_abs, center_y_abs)
                    self.core_reactor = CoreReactor(self.core_reactor_abs_spawn_pos)
                    return
        print("Warning: Core reactor 'C' not found in maze")

    def get_neighbors(self, pos):
        r, c = pos
        directions = [(-1,0), (1,0), (0,-1), (0,1)]
        neighbors = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.actual_maze_rows and 0 <= nc < self.actual_maze_cols:
                if self.grid[nr][nc] != 1:
                    neighbors.append((nr, nc))
        return neighbors

    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def find_path(self, start_grid_pos, end_grid_pos):
        open_list = [(0, start_grid_pos)]
        came_from = {}
        g_score = {start_grid_pos: 0}
        f_score = {start_grid_pos: self.manhattan_distance(start_grid_pos, end_grid_pos)}
        while open_list:
            current_f, current = heappop(open_list)
            if current == end_grid_pos:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_grid_pos)
                return path[::-1]
            for neighbor in self.get_neighbors(current):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.manhattan_distance(neighbor, end_grid_pos)
                    heappush(open_list, (f_score[neighbor], neighbor))
        return None

    def _calculate_enemy_spawn_points_abs(self):
        self.enemy_spawn_points_abs = []
        self.enemy_paths = {}
        for r, c in self.ENEMY_SPAWN_GRID_POSITIONS:
            if not (0 <= r < self.actual_maze_rows and 0 <= c < self.actual_maze_cols):
                print(f"Warning: Spawn ({r},{c}) out of bounds")
                continue
            if self.grid[r][c] == 1:
                print(f"Warning: Spawn ({r},{c}) on wall")
                continue
            center_x = c * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
            center_y = r * TILE_SIZE + TILE_SIZE // 2
            self.enemy_spawn_points_abs.append((center_x, center_y))
            path = self.find_path((r, c), self.core_reactor_grid_pos)
            if path:
                self.enemy_paths[(r, c)] = [(c * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset,
                                            r * TILE_SIZE + TILE_SIZE // 2) for r, c in path]
            else:
                print(f"Warning: No path from spawn ({r},{c}) to core")

    def is_wall(self, obj_center_x_abs, obj_center_y_abs, obj_width=None, obj_height=None):
        grid_c = int((obj_center_x_abs - self.game_area_x_offset) / TILE_SIZE)
        grid_r = int(obj_center_y_abs / TILE_SIZE)
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            return self.grid[grid_r][grid_c] == 1
        return True

    def is_valid_turret_position(self, mouse_x, mouse_y):
        grid_c = int((mouse_x - self.game_area_x_offset) / TILE_SIZE)
        grid_r = int(mouse_y / TILE_SIZE)
        if 0 <= grid_r < self.actual_maze_rows and 0 <= grid_c < self.actual_maze_cols:
            return self.grid[grid_r][grid_c] == 'T'
        return False

    def can_place_turret(self, grid_r, grid_c):
        if self.turret_count >= self.MAX_TURRETS:
            print("Maximum turret limit reached (5 turrets)")
            return False
        if self.grid[grid_r][grid_c] != 'T':
            return False
        original_tile = self.grid[grid_r][grid_c]
        self.grid[grid_r][grid_c] = 1
        for spawn in self.ENEMY_SPAWN_GRID_POSITIONS:
            if not self.find_path(spawn, self.core_reactor_grid_pos):
                self.grid[grid_r][grid_c] = original_tile
                print("Cannot place turret: Blocks all paths to core")
                return False
        self.grid[grid_r][grid_c] = original_tile
        return True

    def place_turret(self, grid_r, grid_c):
        if self.currency >= 50 and self.can_place_turret(grid_r, grid_c):
            self.currency -= 50
            turret = Turret(grid_r, grid_c, self.game_area_x_offset)
            self.turrets.add(turret)
            self.grid[grid_r][grid_c] = 1
            self.turret_count += 1
            print(f"Turret placed at grid ({grid_r}, {grid_c}). Turrets: {self.turret_count}/5")
            return True
        return False

    def spawn_wave(self, wave_number, enemy_group, core_reactor):
        num_enemies = wave_number * 2
        for _ in range(num_enemies):
            spawn_pos = random.choice(self.enemy_spawn_points_abs)
            spawn_grid = (int(spawn_pos[1] // TILE_SIZE), int((spawn_pos[0] - self.game_area_x_offset) // TILE_SIZE))
            path = self.enemy_paths.get(spawn_grid, [])
            if path:
                enemy = Enemy(spawn_pos, path)
                enemy.is_in_defense_mode = True
                enemy.defense_target = core_reactor
                enemy_group.add(enemy)

    def update(self, dt, current_time_ms):
        self.wave_cooldown += dt
        if not self.enemies and self.wave_cooldown >= 10:
            self.wave_number += 1
            self.wave_cooldown = 0
            self.spawn_wave(self.wave_number, self.enemies, self.core_reactor)
        self.enemies.update(self, current_time_ms, self.game_area_x_offset, dt)
        self.turrets.update(dt, self.enemies)
        for enemy in self.enemies:
            if not enemy.alive:
                self.currency += 10  # Reward for defeating enemies
        return self.core_reactor.alive

    def draw(self, surface):
        for r_idx, row_data in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row_data):
                x = c_idx * TILE_SIZE + self.game_area_x_offset
                y = r_idx * TILE_SIZE
                if tile_type == 1:
                    pygame.draw.rect(surface, self.wall_color, (x, y, TILE_SIZE, TILE_SIZE))
                elif tile_type in (0, 'C', 'T'):
                    pygame.draw.rect(surface, self.path_color, (x, y, TILE_SIZE, TILE_SIZE))
                if tile_type == 'T':
                    pygame.draw.rect(surface, (0, 255, 0, 100), (x, y, TILE_SIZE, TILE_SIZE), 2)
        if self.debug_mode:
            for (x, y) in self.get_path_cells_abs():
                pygame.draw.circle(surface, (255, 255, 0), (int(x), int(y)), 3)
            for path in self.enemy_paths.values():
                for i in range(len(path) - 1):
                    pygame.draw.line(surface, (255, 165, 0), path[i], path[i + 1], 2)
        self.enemies.draw(surface)
        for enemy in self.enemies:
            enemy.draw_health_bar(surface)
        self.turrets.draw(surface)
        if self.core_reactor.alive:
            surface.blit(self.core_reactor.image, self.core_reactor.rect)
        self.core_reactor.draw_health_bar(surface)

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode

    def get_core_reactor_spawn_position_abs(self):
        return self.core_reactor_abs_spawn_pos

    def get_enemy_spawn_points_abs(self):
        return self.enemy_spawn_points_abs

    def get_path_cells_abs(self):
        path_cells_abs_centers = []
        for r_idx, row in enumerate(self.grid):
            for c_idx, tile_type in enumerate(row):
                if tile_type in (0, 'C'):
                    center_x_abs = c_idx * TILE_SIZE + TILE_SIZE // 2 + self.game_area_x_offset
                    center_y_abs = r_idx * TILE_SIZE + TILE_SIZE // 2
                    path_cells_abs_centers.append((center_x_abs, center_y_abs))
        return path_cells_abs_centers

    def get_random_path_cell_center_abs(self):
        path_cells_abs = self.get_path_cells_abs()
        return random.choice(path_cells_abs) if path_cells_abs else None

if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tower Defense Game - 5 Turret Spots")
    clock = pygame.time.Clock()
    maze = MazeChapter2(game_area_x_offset=50)
    font = pygame.font.Font(None, 36)
    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        current_time_ms = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_d:
                maze.toggle_debug()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                grid_c = int((mouse_x - maze.game_area_x_offset) / TILE_SIZE)
                grid_r = int(mouse_y / TILE_SIZE)
                if maze.place_turret(grid_r, grid_c):
                    pass  # Feedback handled in place_turret
        running = maze.update(dt, current_time_ms)
        screen.fill(BLACK)
        maze.draw(screen)
        wave_text = font.render(f"Wave: {maze.wave_number}", True, WHITE)
        currency_text = font.render(f"Currency: {maze.currency}", True, WHITE)
        turret_text = font.render(f"Turrets: {maze.turret_count}/{maze.MAX_TURRETS}", True, WHITE)
        screen.blit(wave_text, (10, 10))
        screen.blit(currency_text, (10, 50))
        screen.blit(turret_text, (10, 90))
        mouse_x, mouse_y = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 0, 0) if maze.is_wall(mouse_x, mouse_y) else (0, 255, 0), (mouse_x, mouse_y), 5)
        pygame.display.flip()
    pygame.quit()