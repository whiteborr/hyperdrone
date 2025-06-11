# entities/enemy.py
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

# Corrected import style
import game_settings as gs

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
        self.contact_damage = 25
        self.aggro_radius = gs.TILE_SIZE * 9
        self.original_image, self.image, self.rect, self.collision_rect = None, None, None, None
        self._load_sprite()
        self.bullets = pygame.sprite.Group() 
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, 1500) 
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500)
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3
        self.path, self.current_path_index, self.last_path_recalc_time = [], 0, 0
        self.PATH_RECALC_INTERVAL, self.WAYPOINT_THRESHOLD = 1000, gs.TILE_SIZE * 0.3
        self.stuck_timer, self.last_pos_check = 0, (self.x, self.y)
        self.STUCK_TIME_THRESHOLD_MS, self.STUCK_MOVE_THRESHOLD = 2500, 0.5

    def _load_sprite(self):
        default_size = (int(gs.TILE_SIZE * 0.7), int(gs.TILE_SIZE * 0.7)) 
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None: self.original_image = self.asset_manager._create_fallback_surface(size=default_size, color=gs.ENEMY_COLOR) 
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)

    def _pixel_to_grid(self, px, py, offset=0): return int(py / gs.TILE_SIZE), int((px - offset) / gs.TILE_SIZE)
    def _grid_to_pixel_center(self, r, c, offset=0): return (c*gs.TILE_SIZE)+(gs.TILE_SIZE/2)+offset, (r*gs.TILE_SIZE)+(gs.TILE_SIZE/2)

    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        if not self.alive:
            self.bullets.update(maze, game_area_x_offset);
            if not self.bullets: self.kill()
            return

        is_stuck = self._handle_stuck_logic(current_time_ms, delta_time_ms, maze, game_area_x_offset)
        
        target_pos, current_speed, can_shoot = None, self.speed, False
        
        if not is_stuck and self.player_ref and self.player_ref.alive:
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
            self.shoot(math.degrees(math.atan2(dy, dx)), maze); self.last_shot_time = current_time_ms

    def _handle_stuck_logic(self, current_time_ms, delta_time_ms, maze, game_area_x_offset):
        dist_moved = math.hypot(self.x - self.last_pos_check[0], self.y - self.last_pos_check[1])
        if dist_moved < self.STUCK_MOVE_THRESHOLD: self.stuck_timer += delta_time_ms
        else: self.stuck_timer = 0; self.last_pos_check = (self.x, self.y)

        if self.stuck_timer > self.STUCK_TIME_THRESHOLD_MS:
            logger.warning(f"Enemy {id(self)} detected as stuck. Attempting to unstick.")
            # Try to get walkable tiles from maze
            walkable_tiles = []
            if hasattr(maze, 'get_walkable_tiles_abs'):
                walkable_tiles = maze.get_walkable_tiles_abs()
            elif hasattr(maze, 'get_path_cells_abs'):
                walkable_tiles = maze.get_path_cells_abs()
                
            if walkable_tiles:
                # Find tiles that are not too close to current position
                viable_tiles = [p for p in walkable_tiles if gs.TILE_SIZE * 3 < math.hypot(p[0] - self.x, p[1] - self.y) < gs.TILE_SIZE * 8]
                if viable_tiles:
                    unstick_target = random.choice(viable_tiles)
                    # Force a new path calculation
                    self.path = []
                    self.last_path_recalc_time = 0
                    self._update_ai_with_astar(unstick_target, maze, current_time_ms, game_area_x_offset)
                else:
                    # If no viable tiles found, try a random direction
                    angle = random.uniform(0, 2 * math.pi)
                    self.x += math.cos(angle) * gs.TILE_SIZE
                    self.y += math.sin(angle) * gs.TILE_SIZE
            
            self.stuck_timer = 0
            return True
        return False

    def _update_ai_with_astar(self, target_pos, maze, current_time_ms, game_area_x_offset):
        if not target_pos or not maze: self.path = []; return
        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms
            enemy_grid, target_grid = self._pixel_to_grid(self.x, self.y, game_area_x_offset), self._pixel_to_grid(target_pos[0], target_pos[1], game_area_x_offset)
            if not (0 <= enemy_grid[0] < maze.actual_maze_rows and 0 <= enemy_grid[1] < maze.actual_maze_cols and 0 <= target_grid[0] < maze.actual_maze_rows and 0 <= target_grid[1] < maze.actual_maze_cols):
                self.path = []; return
            if hasattr(maze, 'grid') and maze.grid[target_grid[0]][target_grid[1]] == 1: self.path = []; return
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
        game_play_area_height = gs.get_game_setting("HEIGHT")
        self.rect.clamp_ip(pygame.Rect(game_area_x_offset, 0, gs.get_game_setting("WIDTH") - game_area_x_offset, game_play_area_height))
        self.x, self.y = self.rect.centerx, self.rect.centery
        if self.collision_rect: self.collision_rect.center = self.rect.center

    def shoot(self, direct_angle_to_target, maze): 
        if not self.alive: return
        rad_fire_angle = math.radians(direct_angle_to_target) 
        tip_offset_distance = (self.rect.width / 2) if self.rect else (gs.TILE_SIZE * 0.35)
        
        fire_origin_x, fire_origin_y = self.x, self.y
        raw_fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance
        raw_fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance

        if maze and not maze.is_wall(raw_fire_origin_x, raw_fire_origin_y, self.enemy_bullet_size, self.enemy_bullet_size):
            fire_origin_x, fire_origin_y = raw_fire_origin_x, raw_fire_origin_y
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=direct_angle_to_target, 
            speed=gs.get_game_setting("ENEMY_BULLET_SPEED", 5),
            lifetime=gs.get_game_setting("ENEMY_BULLET_LIFETIME", 75),
            size=self.enemy_bullet_size,
            color=gs.get_game_setting("ENEMY_BULLET_COLOR", (255,165,0)),
            damage=gs.get_game_setting("ENEMY_BULLET_DAMAGE", 10)
        )
        self.bullets.add(new_bullet)
        
        if self.shoot_sound_key and self.asset_manager:
            self.asset_manager.get_sound(self.shoot_sound_key).play()

    def take_damage(self, amount):
        if self.alive: 
            self.health -= amount
            # Create small hit effect
            if hasattr(self, 'rect') and self.rect:
                if random.random() < 0.3:  # 30% chance for spark on hit
                    x, y = self.rect.center
                    if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                        self.asset_manager.game_controller._create_explosion(x, y, 3, None)
            
            if self.health <= 0: 
                self.health = 0
                self.alive = False
                # Create explosion effect when enemy dies
                if hasattr(self, 'rect') and self.rect:
                    x, y = self.rect.center
                    if hasattr(self.asset_manager, 'game_controller') and self.asset_manager.game_controller:
                        # Create a larger explosion with more particles
                        self.asset_manager.game_controller._create_explosion(x, y, 40, 'enemy_shoot')
                        # Add a second explosion with different colors for more visual impact
                        self.asset_manager.game_controller._create_enemy_explosion(x, y)

    def draw(self, surface, camera=None):
        if self.alive and self.image:
            if camera:
                screen_rect = camera.apply_to_rect(self.rect)
                surface.blit(self.image, screen_rect)
            else: surface.blit(self.image, self.rect)
        for proj in self.bullets: proj.draw(surface, camera)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_w, bar_h = self.rect.width*0.8, 5
        screen_rect = camera.apply_to_rect(self.rect) if camera else self.rect
        bar_x, bar_y = screen_rect.centerx - bar_w/2, screen_rect.top - bar_h - 3
        fill_w = bar_w * (self.health / self.max_health if self.max_health > 0 else 0)
        fill_color = gs.GREEN if self.health/self.max_health > 0.6 else gs.YELLOW if self.health/self.max_health > 0.3 else gs.RED
        pygame.draw.rect(surface, (80,0,0), (bar_x, bar_y, bar_w, bar_h))
        if fill_w > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h)) 
        pygame.draw.rect(surface, gs.WHITE, (bar_x, bar_y, bar_w, bar_h), 1) 

class DefenseDrone(Enemy):
    def __init__(self, x, y, asset_manager, sprite_asset_key, path_to_core, **kwargs):
        super().__init__(x, y, 0, asset_manager, sprite_asset_key)
        self.path = path_to_core if path_to_core else []
        self.current_path_index = 1 if self.path and len(self.path) > 1 else -1

    def update(self, _, maze, __, ___, game_area_x_offset=0, is_defense_mode=True):
        if not self.alive: return
        self._update_movement_along_path(maze, game_area_x_offset)
        if self.image and self.original_image:
            self.image = pygame.transform.rotate(self.original_image, -self.angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect: self.collision_rect.center = self.rect.center

class SentinelDrone(Enemy): 
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        super().__init__(x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key, target_player_ref)
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0)
        self.health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75); self.max_health = self.health
        self.shoot_cooldown = int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7)

    def _load_sprite(self): 
        default_size = (int(gs.TILE_SIZE * 0.6), int(gs.TILE_SIZE * 0.6)) 
        self.original_image = self.asset_manager.get_image(self.sprite_asset_key, scale_to_size=default_size)
        if self.original_image is None:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            points = [(default_size[0]//2,0),(default_size[0],default_size[1]//2),(default_size[0]//2,default_size[1]),(0,default_size[1]//2)]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points); pygame.draw.polygon(self.original_image, gs.WHITE, points, 1)
        self.image = self.original_image.copy(); self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.rect: self.collision_rect = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)