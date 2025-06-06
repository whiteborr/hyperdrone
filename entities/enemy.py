# entities/enemy.py
import math
import random
import os
import heapq # For A* priority queue
import logging

import pygame

# Assuming Bullet class is in the same directory or accessible via entities.bullet
try:
    from .bullet import Bullet 
except ImportError:
    # Minimal placeholder if Bullet class is not found
    class Bullet(pygame.sprite.Sprite): 
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, bounces=0, pierces=0, can_pierce_walls=False):
            super().__init__()
            self.image = pygame.Surface([size*2,size*2]); self.image.fill(color)
            self.rect = self.image.get_rect(center=(x,y)); self.alive = True; self.lifetime = lifetime
            self.damage = damage 
        def update(self, maze, offset): self.lifetime -=1; _ = maze; _ = offset; 
        def draw(self, surface): surface.blit(self.image, self.rect)


import game_settings as gs
from game_settings import (
    TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR,
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME,
    ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE,
    PLAYER_DEFAULT_BULLET_SIZE, 
    WIDTH, GAME_PLAY_AREA_HEIGHT, WHITE, GREEN, RED, YELLOW # <<< FIXED: Added RED and YELLOW
)

logger = logging.getLogger(__name__)

# --- A* Node and Heuristic ---
class AStarNode:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g_cost = 0; self.h_cost = 0; self.f_cost = 0
    def __eq__(self, other): return self.position == other.position
    def __lt__(self, other): return self.f_cost < other.f_cost
    def __hash__(self): return hash(self.position)

def heuristic(node_pos, goal_pos):
    return abs(node_pos[0] - goal_pos[0]) + abs(node_pos[1] - goal_pos[1])

# --- A* Search Function ---
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    if not maze_grid or \
       not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or \
       not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols):
        return None

    start_node = AStarNode(start_pos_grid); end_node = AStarNode(end_pos_grid)
    open_list = []; closed_set = set(); heapq.heappush(open_list, (0, start_node))
    g_score = { (r,c): float('inf') for r in range(maze_rows) for c in range(maze_cols) }
    g_score[start_pos_grid] = 0
    f_score = { (r,c): float('inf') for r in range(maze_rows) for c in range(maze_cols) }
    f_score[start_pos_grid] = heuristic(start_pos_grid, end_pos_grid)
    open_set_hash = {start_pos_grid} 

    while open_list:
        _, current_node = heapq.heappop(open_list)
        if current_node.position not in open_set_hash: continue
        open_set_hash.remove(current_node.position)

        if current_node.position == end_node.position:
            path = []
            temp = current_node
            while temp: path.append(temp.position); temp = temp.parent
            return path[::-1]

        closed_set.add(current_node.position)

        for new_pos_offset in [(0, -1), (0, 1), (-1, 0), (1, 0)]: 
            node_pos = (current_node.position[0] + new_pos_offset[0], current_node.position[1] + new_pos_offset[1])
            if not (0 <= node_pos[0] < maze_rows and 0 <= node_pos[1] < maze_cols): continue
            if maze_grid[node_pos[0]][node_pos[1]] == 1: continue 
            if node_pos in closed_set: continue
            
            neighbor = AStarNode(node_pos, current_node)
            neighbor.g_cost = current_node.g_cost + 1
            neighbor.h_cost = heuristic(neighbor.position, end_node.position)
            neighbor.f_cost = neighbor.g_cost + neighbor.h_cost

            if not any(n[1] == neighbor and neighbor.g_cost >= n[1].g_cost for n in open_list):
                heapq.heappush(open_list, (neighbor.f_cost, neighbor))
                open_set_hash.add(neighbor.position)
    return None


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0 
        self.speed = gs.get_game_setting("ENEMY_SPEED", 1.5) 
        self.health = gs.get_game_setting("ENEMY_HEALTH", 100)
        self.max_health = gs.get_game_setting("ENEMY_HEALTH", 100)
        self.alive = True
        
        # Store asset manager and asset keys
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.shoot_sound_key = shoot_sound_key
        
        self.player_ref = target_player_ref

        self.is_in_defense_mode = False 
        self.defense_target = None
        self.contact_damage = 25

        self.original_image = None 
        self.image = None          
        self.rect = None           
        self.collision_rect = None 
        self._load_sprite() # Load sprite using AssetManager and key

        self.bullets = pygame.sprite.Group() 
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500))) 
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500)
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3

        self.path = []
        self.current_path_index = 0 
        self.target_grid_cell = None
        self.last_path_recalc_time = 0 
        self.PATH_RECALC_INTERVAL = 1000
        self.WAYPOINT_THRESHOLD = TILE_SIZE * 0.3

    def _pixel_to_grid(self, pixel_x, pixel_y, game_area_x_offset=0):
        col = int((pixel_x - game_area_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _grid_to_pixel_center(self, grid_row, grid_col, game_area_x_offset=0):
        pixel_x = (grid_col * TILE_SIZE) + (TILE_SIZE / 2) + game_area_x_offset
        pixel_y = (grid_row * TILE_SIZE) + (TILE_SIZE / 2)
        return pixel_x, pixel_y

    def _load_sprite(self):
        """Loads the enemy's sprite using the AssetManager."""
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) 
        
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)

        if loaded_image:
            try:
                self.original_image = pygame.transform.smoothscale(loaded_image, default_size)
            except pygame.error as e:
                logger.error(f"Enemy: Error scaling sprite for key '{self.sprite_asset_key}': {e}. Using fallback.")
                self.original_image = None
        else:
            logger.warning(f"Enemy: Sprite for key '{self.sprite_asset_key}' not found in AssetManager.")
            self.original_image = None

        if self.original_image is None: 
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill(ENEMY_COLOR) 

        self.image = self.original_image.copy() 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def update(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # (Update logic remains the same, as asset loading is done in __init__)
        if not self.alive:
            if not self.bullets: self.kill()
            self.bullets.update(maze, game_area_x_offset)
            return

        actual_target_for_pathfinding_pixels = primary_target_pos_pixels
        if is_defense_mode and self.defense_target and self.defense_target.alive:
            actual_target_for_pathfinding_pixels = self.defense_target.rect.center
        
        self._update_ai_with_astar(actual_target_for_pathfinding_pixels, maze, current_time_ms, game_area_x_offset)
        self._update_movement_along_path(maze, game_area_x_offset) 

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.collision_rect: self.collision_rect.center = self.rect.center

        self.bullets.update(maze, game_area_x_offset)

        shooting_target_pos_for_aiming = None
        if self.player_ref and self.player_ref.alive: 
            shooting_target_pos_for_aiming = self.player_ref.rect.center

        if shooting_target_pos_for_aiming and (current_time_ms - self.last_shot_time > self.shoot_cooldown):
            dx_shoot_target = shooting_target_pos_for_aiming[0] - self.x
            dy_shoot_target = shooting_target_pos_for_aiming[1] - self.y
            distance_to_shoot_target = math.hypot(dx_shoot_target, dy_shoot_target)
            
            shooting_range = TILE_SIZE * 8
            if distance_to_shoot_target < shooting_range:
                angle_to_shoot_target = math.degrees(math.atan2(dy_shoot_target, dx_shoot_target))
                self.shoot(angle_to_shoot_target)
                self.last_shot_time = current_time_ms

    def _update_ai_with_astar(self, target_pos_for_pathfinding_pixels, maze, current_time_ms, game_area_x_offset):
        # (This method's logic remains the same)
        if not target_pos_for_pathfinding_pixels or not maze:
            self.path = []; return

        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms

            enemy_grid_pos = self._pixel_to_grid(self.x, self.y, game_area_x_offset) 
            target_grid_pos = self._pixel_to_grid(target_pos_for_pathfinding_pixels[0], target_pos_for_pathfinding_pixels[1], game_area_x_offset)

            if not (0 <= enemy_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= enemy_grid_pos[1] < maze.actual_maze_cols and \
                    0 <= target_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= target_grid_pos[1] < maze.actual_maze_cols):
                self.path = []; return

            if maze.grid[target_grid_pos[0]][target_grid_pos[1]] == 1:
                self.path = []; return

            grid_path = a_star_search(maze.grid, enemy_grid_pos, target_grid_pos, maze.actual_maze_rows, maze.actual_maze_cols)

            if grid_path and len(grid_path) > 1:
                self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path] 
                self.current_path_index = 1
            else:
                self.path = []
        
        if not self.path and target_pos_for_pathfinding_pixels:
            dx = target_pos_for_pathfinding_pixels[0] - self.x
            dy = target_pos_for_pathfinding_pixels[1] - self.y
            if math.hypot(dx, dy) > 0:
                self.angle = math.degrees(math.atan2(dy, dx))


    def _update_movement_along_path(self, maze, game_area_x_offset=0): 
        # (This method's logic remains the same)
        if not self.path or self.current_path_index >= len(self.path):
            if self.is_in_defense_mode and self.defense_target and self.defense_target.alive:
                dx = self.defense_target.rect.centerx - self.x
                dy = self.defense_target.rect.centery - self.y
                distance_to_target = math.hypot(dx, dy)
                if distance_to_target > TILE_SIZE * 0.2:
                    self.angle = math.degrees(math.atan2(dy, dx))
                    self.x += (dx / distance_to_target) * self.speed
                    self.y += (dy / distance_to_target) * self.speed
            return

        target_waypoint_pixels = self.path[self.current_path_index]
        dx = target_waypoint_pixels[0] - self.x
        dy = target_waypoint_pixels[1] - self.y
        distance_to_waypoint = math.hypot(dx, dy)

        if distance_to_waypoint < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                self.path = []; return
            target_waypoint_pixels = self.path[self.current_path_index]
            dx = target_waypoint_pixels[0] - self.x
            dy = target_waypoint_pixels[1] - self.y
            distance_to_waypoint = math.hypot(dx, dy)

        if distance_to_waypoint > 0:
            self.angle = math.degrees(math.atan2(dy, dx))
            move_x_component = (dx / distance_to_waypoint) * self.speed
            move_y_component = (dy / distance_to_waypoint) * self.speed
            next_x = self.x + move_x_component
            next_y = self.y + move_y_component
            self.x = next_x; self.y = next_y

        if self.rect:
            half_width = self.rect.width / 2; half_height = self.rect.height / 2
            min_x_bound = game_area_x_offset + half_width; max_x_bound = WIDTH - half_width
            min_y_bound = half_height; max_y_bound = GAME_PLAY_AREA_HEIGHT - half_height
            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))
            self.rect.center = (int(self.x), int(self.y))
            if self.collision_rect: self.collision_rect.center = self.rect.center


    def shoot(self, direct_angle_to_target): 
        """Fires a bullet towards the given angle."""
        if not self.alive: return

        rad_fire_angle = math.radians(direct_angle_to_target) 
        tip_offset_distance = (self.rect.width / 2) if self.rect else (TILE_SIZE * 0.35)
        fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance
        fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=direct_angle_to_target, 
            speed=gs.get_game_setting("ENEMY_BULLET_SPEED", 5),
            lifetime=gs.get_game_setting("ENEMY_BULLET_LIFETIME", 75),
            size=self.enemy_bullet_size,
            color=gs.get_game_setting("ENEMY_BULLET_COLOR", (255,165,0)),
            damage=gs.get_game_setting("ENEMY_BULLET_DAMAGE", 10)
        )
        self.bullets.add(new_bullet)
        
        # Play sound using the sound key and AssetManager
        if self.shoot_sound_key and self.asset_manager:
            shoot_sound = self.asset_manager.get_sound(self.shoot_sound_key)
            if shoot_sound:
                shoot_sound.play()

    def take_damage(self, amount):
        # (No change to this method's logic)
        if not self.alive: return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw(self, surface):
        """Draws the enemy and its bullets."""
        if self.alive and self.image and self.rect:
            surface.blit(self.image, self.rect)
        self.bullets.draw(surface)

    def _draw_health_bar(self, surface):
        """Draws the enemy's health bar above it."""
        if self.alive and self.rect:
            bar_width = self.rect.width * 0.8
            bar_height = 5
            bar_x = self.rect.centerx - bar_width / 2
            bar_y = self.rect.top - bar_height - 2
            
            health_percentage = self.health / self.max_health if self.max_health > 0 else 0
            filled_width = bar_width * health_percentage
            
            pygame.draw.rect(surface, (80,0,0), (bar_x, bar_y, bar_width, bar_height)) 
            if filled_width > 0:
                fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED
                pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(filled_width), bar_height)) 
            pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1) 


class SentinelDrone(Enemy): 
    """A specialized enemy type that inherits from Enemy."""
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        # Call the parent constructor with the new parameters
        super().__init__(x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key, target_player_ref)
        
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0)
        self.health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75)
        self.max_health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75)
        self.shoot_cooldown = int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7)

    def _load_sprite(self): 
        """Overrides the parent _load_sprite to potentially use a different size or fallback."""
        default_size = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6)) 
        
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)

        if loaded_image:
            try:
                self.original_image = pygame.transform.smoothscale(loaded_image, default_size)
            except (ValueError, pygame.error) as e:
                logger.error(f"SentinelDrone: Error scaling sprite for key '{self.sprite_asset_key}': {e}. Using fallback.")
                self.original_image = None
        else:
            logger.warning(f"SentinelDrone: Sprite for key '{self.sprite_asset_key}' not found in AssetManager.")
            self.original_image = None

        if self.original_image is None:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            points = [(default_size[0] // 2, 0), (default_size[0], default_size[1] // 2), (default_size[0] // 2, default_size[1]), (0, default_size[1] // 2)]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points) 
            pygame.draw.polygon(self.original_image, WHITE, points, 1)

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.rect: 
            self.collision_rect_width = self.rect.width * 0.8
            self.collision_rect_height = self.rect.height * 0.8
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else:
            self.collision_rect = pygame.Rect(self.x - default_size[0]*0.4, self.y - default_size[1]*0.4, default_size[0]*0.8, default_size[1]*0.8)


    def update(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # SentinelDrone can have its own unique update logic in the future.
        # For now, it uses the base Enemy's update logic.
        super().update(primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset, is_defense_mode)
