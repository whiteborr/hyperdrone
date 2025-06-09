import math
import random
import os
import heapq 
import logging

import pygame

try:
    from .bullet import Bullet 
except ImportError:
    class Bullet(pygame.sprite.Sprite): pass

import game_settings as gs
from game_settings import (
    TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR,
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME,
    ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE,
    PLAYER_DEFAULT_BULLET_SIZE, 
    WIDTH, GAME_PLAY_AREA_HEIGHT, WHITE, GREEN, RED, YELLOW
)

logger = logging.getLogger(__name__)

class AStarNode:
    def __init__(self, position, parent=None):
        self.position = position; self.parent = parent; self.g_cost = 0; self.h_cost = 0; self.f_cost = 0
    def __eq__(self, other): return self.position == other.position
    def __lt__(self, other): return self.f_cost < other.f_cost
    def __hash__(self): return hash(self.position)

def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    if not maze_grid or not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols): return None
    start_node = AStarNode(start_pos_grid); end_node = AStarNode(end_pos_grid)
    open_list = []; closed_set = set(); heapq.heappush(open_list, (0, start_node))
    g_score = { (r,c): float('inf') for r in range(maze_rows) for c in range(maze_cols) }; g_score[start_pos_grid] = 0
    open_set_hash = {start_pos_grid}
    while open_list:
        _, current_node = heapq.heappop(open_list)
        if current_node.position not in open_set_hash: continue
        open_set_hash.remove(current_node.position)
        if current_node.position == end_node.position:
            path = []; temp = current_node
            while temp: path.append(temp.position); temp = temp.parent
            return path[::-1]
        closed_set.add(current_node.position)
        for new_pos_offset in [(0, -1), (0, 1), (-1, 0), (1, 0)]: 
            node_pos = (current_node.position[0] + new_pos_offset[0], current_node.position[1] + new_pos_offset[1])
            if not (0 <= node_pos[0] < maze_rows and 0 <= node_pos[1] < maze_cols) or maze_grid[node_pos[0]][node_pos[1]] == 1 or node_pos in closed_set: continue
            neighbor = AStarNode(node_pos, current_node); neighbor.g_cost = current_node.g_cost + 1; neighbor.h_cost = abs(neighbor.position[0] - end_node.position[0]) + abs(neighbor.position[1] - end_node.position[1]); neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
            if not any(n[1] == neighbor and neighbor.g_cost >= n[1].g_cost for n in open_list):
                heapq.heappush(open_list, (neighbor.f_cost, neighbor)); open_set_hash.add(neighbor.position)
    return None


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        super().__init__()
        self.x, self.y, self.angle = float(x), float(y), 0.0
        self.speed = gs.get_game_setting("ENEMY_SPEED", 1.5) 
        self.health = gs.get_game_setting("ENEMY_HEALTH", 100); self.max_health = self.health
        self.alive = True
        self.asset_manager, self.sprite_asset_key, self.shoot_sound_key = asset_manager, sprite_asset_key, shoot_sound_key
        self.player_ref = target_player_ref
        self.is_in_defense_mode, self.defense_target, self.contact_damage = False, None, 25
        self.aggro_radius = TILE_SIZE * 9
        self.original_image, self.image, self.rect, self.collision_rect = None, None, None, None
        self._load_sprite()
        self.bullets = pygame.sprite.Group() 
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, 1500) 
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500)
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3
        self.path, self.current_path_index, self.last_path_recalc_time = [], 0, 0
        self.PATH_RECALC_INTERVAL, self.WAYPOINT_THRESHOLD = 1000, TILE_SIZE * 0.3
        self.stuck_timer, self.last_pos_check = 0, (self.x, self.y)
        self.STUCK_TIME_THRESHOLD_MS, self.STUCK_MOVE_THRESHOLD = 2500, 0.5

    def _load_sprite(self):
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) 
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        if loaded_image:
            try: self.original_image = pygame.transform.smoothscale(loaded_image, default_size)
            except pygame.error as e: logger.error(f"Enemy: Error scaling sprite '{self.sprite_asset_key}': {e}"); self.original_image = None
        else: logger.warning(f"Enemy: Sprite '{self.sprite_asset_key}' not found."); self.original_image = None
        if self.original_image is None: self.original_image = pygame.Surface(default_size, pygame.SRCALPHA); self.original_image.fill(ENEMY_COLOR) 
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)

    def _pixel_to_grid(self, px, py, offset=0): return int(py / TILE_SIZE), int((px - offset) / TILE_SIZE)
    def _grid_to_pixel_center(self, r, c, offset=0): return (c*TILE_SIZE)+(TILE_SIZE/2)+offset, (r*TILE_SIZE)+(TILE_SIZE/2)

    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        if not self.alive:
            self.bullets.update(maze, game_area_x_offset)
            if not self.bullets: self.kill()
            return

        is_stuck = self._handle_stuck_logic(current_time_ms, delta_time_ms, maze, game_area_x_offset)
        
        target_pos, current_speed, can_shoot = None, self.speed, False
        
        if not is_stuck:
            if is_defense_mode:
                if self.defense_target and self.defense_target.alive: target_pos = self.defense_target.rect.center
            elif self.player_ref and self.player_ref.alive:
                player_dist = math.hypot(self.x - self.player_ref.x, self.y - self.player_ref.y)
                target_pos = self.player_ref.rect.center
                if player_dist < self.aggro_radius: can_shoot = True
                else: current_speed = self.speed * 0.5
        
        self._update_ai_with_astar(target_pos, maze, current_time_ms, game_area_x_offset)
        self._update_movement_along_path(maze, game_area_x_offset, current_speed) 
        
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))); self.collision_rect.center = self.rect.center
        self.bullets.update(maze, game_area_x_offset)
        
        if can_shoot and (current_time_ms - self.last_shot_time > self.shoot_cooldown):
            dx, dy = self.player_ref.rect.centerx - self.x, self.player_ref.rect.centery - self.y
            self.shoot(math.degrees(math.atan2(dy, dx))); self.last_shot_time = current_time_ms

    def _handle_stuck_logic(self, current_time_ms, delta_time_ms, maze, game_area_x_offset):
        dist_moved = math.hypot(self.x - self.last_pos_check[0], self.y - self.last_pos_check[1])
        if dist_moved < self.STUCK_MOVE_THRESHOLD: self.stuck_timer += delta_time_ms
        else: self.stuck_timer = 0; self.last_pos_check = (self.x, self.y)

        if self.stuck_timer > self.STUCK_TIME_THRESHOLD_MS:
            logger.warning(f"Enemy {id(self)} detected as stuck. Attempting to unstick.")
            if hasattr(maze, 'get_path_cells_abs'):
                nearby_tiles = [p for p in maze.get_path_cells_abs() if math.hypot(p[0] - self.x, p[1] - self.y) < TILE_SIZE * 4]
                if nearby_tiles:
                    unstick_target = random.choice(nearby_tiles)
                    self._update_ai_with_astar(unstick_target, maze, current_time_ms, game_area_x_offset)
            self.stuck_timer = 0; return True
        return False

    def _update_ai_with_astar(self, target_pos, maze, current_time_ms, game_area_x_offset):
        if not target_pos or not maze: self.path = []; return
        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms
            enemy_grid, target_grid = self._pixel_to_grid(self.x, self.y, game_area_x_offset), self._pixel_to_grid(target_pos[0], target_pos[1], game_area_x_offset)
            if not (0 <= enemy_grid[0] < maze.actual_maze_rows and 0 <= enemy_grid[1] < maze.actual_maze_cols and 0 <= target_grid[0] < maze.actual_maze_rows and 0 <= target_grid[1] < maze.actual_maze_cols and maze.grid[target_grid[0]][target_grid[1]] != 1):
                self.path = []; return
            grid_path = a_star_search(maze.grid, enemy_grid, target_grid, maze.actual_maze_rows, maze.actual_maze_cols)
            if grid_path and len(grid_path) > 1: self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path]; self.current_path_index = 1
            else: self.path = []
        if not self.path and target_pos:
            dx, dy = target_pos[0] - self.x, target_pos[1] - self.y
            if math.hypot(dx, dy) > 0: self.angle = math.degrees(math.atan2(dy, dx))

    def _update_movement_along_path(self, maze, game_area_x_offset=0, speed_override=None): 
        effective_speed = speed_override if speed_override is not None else self.speed
        if not self.path or self.current_path_index >= len(self.path): return
        target = self.path[self.current_path_index]; dx, dy = target[0] - self.x, target[1] - self.y; dist = math.hypot(dx, dy)
        if dist < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path): self.path = []; return
        target = self.path[self.current_path_index]; dx, dy = target[0] - self.x, target[1] - self.y; dist = math.hypot(dx, dy)
        if dist > 0:
            self.angle = math.degrees(math.atan2(dy, dx)); move_x, move_y = (dx/dist)*effective_speed, (dy/dist)*effective_speed
            next_x, next_y = self.x + move_x, self.y + move_y
            if not (maze and self.collision_rect and maze.is_wall(next_x, next_y, self.collision_rect.width, self.collision_rect.height)):
                self.x, self.y = next_x, next_y
        self.rect.center = (self.x, self.y)
        self.rect.clamp_ip(pygame.Rect(game_area_x_offset, 0, WIDTH - game_area_x_offset, GAME_PLAY_AREA_HEIGHT))
        self.x, self.y = self.rect.centerx, self.rect.centery; self.collision_rect.center = self.rect.center

    def shoot(self, angle): 
        if not self.alive: return
        rad, offset = math.radians(angle), self.rect.width/2
        self.bullets.add(Bullet(self.x+math.cos(rad)*offset, self.y+math.sin(rad)*offset, angle, gs.ENEMY_BULLET_SPEED, gs.ENEMY_BULLET_LIFETIME, self.enemy_bullet_size, gs.ENEMY_BULLET_COLOR, gs.ENEMY_BULLET_DAMAGE))
        if self.shoot_sound_key: self.asset_manager.get_sound(self.shoot_sound_key).play()

    def take_damage(self, amount):
        if self.alive: self.health -= amount
        if self.health <= 0: self.health = 0; self.alive = False

    def draw(self, surface, camera=None):
        if self.alive:
            if camera:
                screen_rect = camera.apply_to_rect(self.rect)
                if self.image.get_size() != screen_rect.size: self.image = pygame.transform.smoothscale(self.original_image, screen_rect.size)
                surface.blit(self.image, screen_rect)
            else: surface.blit(self.image, self.rect)
        for proj in self.bullets: proj.draw(surface, camera)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_w, bar_h = self.rect.width*0.8, 5
        screen_rect = camera.apply_to_rect(self.rect) if camera else self.rect
        bar_x, bar_y = screen_rect.centerx - bar_w/2, screen_rect.top - bar_h - 3
        fill_w = bar_w * (self.health / self.max_health)
        fill_color = GREEN if self.health/self.max_health > 0.6 else YELLOW if self.health/self.max_health > 0.3 else RED
        pygame.draw.rect(surface, (80,0,0), (bar_x, bar_y, bar_w, bar_h))
        if fill_w > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h)) 
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1) 

class SentinelDrone(Enemy): 
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        super().__init__(x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key, target_player_ref)
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0)
        self.health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75); self.max_health = self.health
        self.shoot_cooldown = int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7)

    def _load_sprite(self): 
        default_size = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6)) 
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        if loaded_image:
            try: self.original_image = pygame.transform.smoothscale(loaded_image, default_size)
            except (ValueError, pygame.error) as e: logger.error(f"Sentinel: Error scaling sprite '{self.sprite_asset_key}': {e}"); self.original_image = None
        else: logger.warning(f"Sentinel: Sprite '{self.sprite_asset_key}' not found."); self.original_image = None
        if self.original_image is None:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            points = [(default_size[0]//2,0),(default_size[0],default_size[1]//2),(default_size[0]//2,default_size[1]),(0,default_size[1]//2)]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points); pygame.draw.polygon(self.original_image, WHITE, points, 1)
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)

    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        super().update(primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset, is_defense_mode)