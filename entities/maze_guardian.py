# entities/maze_guardian.py
import pygame
import math
import random
import os

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, GAME_PLAY_AREA_HEIGHT,
    MAZE_GUARDIAN_SPRITE_PATH, MAZE_GUARDIAN_COLOR,
    MAZE_GUARDIAN_SPEED, MAZE_GUARDIAN_HEALTH,
    MAZE_GUARDIAN_LASER_COOLDOWN, MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS,
    SENTINEL_DRONE_SPRITE_PATH, SENTINEL_DRONE_HEALTH, SENTINEL_DRONE_SPEED,
    RED, YELLOW, ORANGE, DARK_GREY, BLACK, WHITE, GOLD, GREEN
)
from .base_drone import BaseDrone
from .enemy import SentinelDrone

class MazeGuardian(BaseDrone):
    def __init__(self, x, y, player_ref, maze_ref, game_controller_ref, asset_manager):
        self.visual_size = (int(TILE_SIZE * 2.8), int(TILE_SIZE * 2.8))
        super().__init__(x, y, size=self.visual_size[0], speed=gs.get_game_setting("MAZE_GUARDIAN_SPEED"))

        self.player_ref = player_ref
        self.maze_ref = maze_ref
        self.game_controller_ref = game_controller_ref
        self.asset_manager = asset_manager # Store AssetManager
        self.total_health_points = gs.get_game_setting("MAZE_GUARDIAN_HEALTH")
        self.alive = True

        self.original_image = None
        self.image = None
        
        # The key must match the one defined in GameController's asset manifest
        self.sprite_asset_key = "maze_guardian_sprite_key"
        self._load_sprite() # Load sprite using AssetManager

        self.rect = self.image.get_rect(center=(x, y))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.1, -self.rect.height * 0.1)

        self.corner_size = (int(self.visual_size[0] * 0.25), int(self.visual_size[1] * 0.25))
        self.health_per_corner = self.total_health_points / 4
        self.corners = []
        self._initialize_corners()

        self.last_laser_time = pygame.time.get_ticks() + 3000
        self.laser_cooldown = gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN")
        self.laser_beams = pygame.sprite.Group()

        self.last_minion_spawn_time = pygame.time.get_ticks()
        self.minion_spawn_cooldown = gs.get_game_setting("MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS")
        
        self.target_pos = None
        self.move_timer = 0
        self.MOVE_INTERVAL = 3000

        self.bullets = pygame.sprite.Group()


    def _load_sprite(self):
        """Loads the boss sprite from the AssetManager."""
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        
        if loaded_image:
            try:
                self.original_image = pygame.transform.smoothscale(loaded_image, self.visual_size)
            except (ValueError, pygame.error) as e:
                print(f"MazeGuardian: Error scaling sprite for key '{self.sprite_asset_key}': {e}")
                self.original_image = None
        else:
            print(f"MazeGuardian: Sprite for key '{self.sprite_asset_key}' not found. Using fallback.")
            self.original_image = None
        
        if self.original_image is None: # Fallback if sprite loading failed
            self.original_image = pygame.Surface(self.visual_size, pygame.SRCALPHA)
            self.original_image.fill(gs.get_game_setting("MAZE_GUARDIAN_COLOR", (80,0,120)))
            pygame.draw.rect(self.original_image, WHITE, self.original_image.get_rect(), 3)
        
        self.image = self.original_image.copy()


    def _initialize_corners(self):
        # (This method's logic remains the same)
        self.corners = []
        half_main_w, half_main_h = self.rect.width / 2, self.rect.height / 2
        corner_half_w, corner_half_h = self.corner_size[0] / 2, self.corner_size[1] / 2
        offsets = [
            (-half_main_w + corner_half_w, -half_main_h + corner_half_h),
            ( half_main_w - corner_half_w, -half_main_h + corner_half_h),
            (-half_main_w + corner_half_w,  half_main_h - corner_half_h),
            ( half_main_w - corner_half_w,  half_main_h - corner_half_h)
        ]
        for i in range(4):
            corner_rect = pygame.Rect(0, 0, self.corner_size[0], self.corner_size[1])
            self.corners.append({
                'id': i, 'relative_offset': offsets[i], 'rect': corner_rect.copy(),
                'health': self.health_per_corner, 'max_health': self.health_per_corner,
                'status': 'intact', 'color': DARK_GREY
            })
        self._update_corner_positions()

    def _update_corner_positions(self):
        # (This method's logic remains the same)
        for corner in self.corners:
            offset_x, offset_y = corner['relative_offset']
            corner['rect'].center = (self.rect.centerx + offset_x, self.rect.centery + offset_y)

    def damage_corner(self, corner_id, damage_amount):
        # (This method's logic remains the same)
        if not self.alive: return False
        for corner in self.corners:
            if corner['id'] == corner_id:
                if corner['status'] == 'destroyed': return False
                corner['health'] -= damage_amount
                if self.game_controller_ref:
                    self.game_controller_ref.play_sound('boss_hit', 0.7)
                if corner['health'] <= 0:
                    corner['health'] = 0; corner['status'] = 'destroyed'; corner['color'] = BLACK
                    if self.game_controller_ref:
                         self.game_controller_ref._create_explosion(corner['rect'].centerx, corner['rect'].centery, num_particles=30, specific_sound_key='prototype_drone_explode')
                elif corner['status'] == 'intact':
                    corner['status'] = 'damaged'; corner['color'] = ORANGE
                elif corner['status'] == 'damaged':
                    health_perc = corner['health'] / corner['max_health']
                    if health_perc < 0.33: corner['color'] = RED
                    elif health_perc < 0.66: corner['color'] = YELLOW
                    else: corner['color'] = ORANGE
                return True
        return False

    def take_damage(self, amount, sound=None):
        # (This method remains effectively bypassed)
        pass

    def _choose_new_target_position(self, maze, game_area_x_offset):
        if not maze: return self.rect.center
        path_cells = []
        # --- START FIX ---
        # Corrected the method name check from 'get_path_cells_abs' to 'get_walkable_tiles_abs'
        if hasattr(maze, 'get_walkable_tiles_abs'):
            path_cells = maze.get_walkable_tiles_abs()
        # --- END FIX ---
        elif hasattr(maze, 'get_path_cells'):
            path_cells_rel = maze.get_path_cells()
            path_cells = [(x + game_area_x_offset, y) for x,y in path_cells_rel]

        if not path_cells: return self.rect.center
        attempts, max_attempts, min_dist_from_self = 0, 10, TILE_SIZE * 3
        while attempts < max_attempts:
            potential_target = random.choice(path_cells)
            if math.hypot(potential_target[0] - self.x, potential_target[1] - self.y) > min_dist_from_self:
                self.target_pos = potential_target
                return
            attempts += 1
        self.target_pos = random.choice(path_cells)

    def update(self, player_pos, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # (The rest of the method's logic remains the same)
        if not self.alive: return
        if self.target_pos is None or current_time_ms > self.move_timer:
            self._choose_new_target_position(maze, game_area_x_offset)
            self.move_timer = current_time_ms + self.MOVE_INTERVAL
        if self.target_pos:
            dx, dy = self.target_pos[0] - self.x, self.target_pos[1] - self.y
            dist = math.hypot(dx, dy)
            if dist > self.speed:
                self.x += (dx / dist) * self.speed; self.y += (dy / dist) * self.speed
            else:
                self.x, self.y = self.target_pos; self.target_pos = None
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect : self.collision_rect.center = self.rect.center
        min_x = game_area_x_offset + self.rect.width / 2; max_x = WIDTH - self.rect.width / 2
        min_y = self.rect.height / 2; max_y = GAME_PLAY_AREA_HEIGHT - self.rect.height / 2
        self.x = max(min_x, min(self.x, max_x)); self.y = max(min_y, min(self.y, max_y))
        self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect: self.collision_rect.center = self.rect.center
        self._update_corner_positions()
        if current_time_ms - self.last_laser_time > self.laser_cooldown:
            self.last_laser_time = current_time_ms
        if current_time_ms - self.last_minion_spawn_time > self.minion_spawn_cooldown:
            self.last_minion_spawn_time = current_time_ms
        if all(c['status'] == 'destroyed' for c in self.corners):
            self.alive = False
            if self.game_controller_ref:
                self.game_controller_ref.play_sound('boss_death', 1.0)

    def shoot_projectiles(self, target_pos):
        # (This method remains empty)
        pass

    def draw(self, surface):
        # (This method's logic remains the same)
        if not self.image or not self.rect: return
        surface.blit(self.image, self.rect)
        for corner in self.corners:
            pygame.draw.rect(surface, corner['color'], corner['rect'])
            border_color = WHITE if corner['status'] != 'destroyed' else DARK_GREY
            pygame.draw.rect(surface, border_color, corner['rect'], 2)
            if corner['status'] != 'destroyed' and corner['health'] < corner['max_health']:
                bar_width = corner['rect'].width * 0.8; bar_height = 4
                bar_x = corner['rect'].centerx - bar_width / 2
                bar_y = corner['rect'].top - bar_height - 2
                health_perc = corner['health'] / corner['max_health']
                filled_width = bar_width * health_perc
                fill_c = RED if health_perc < 0.33 else YELLOW if health_perc < 0.66 else GREEN
                pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height))
                if filled_width > 0: pygame.draw.rect(surface, fill_c, (bar_x, bar_y, filled_width, bar_height))
                pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
        self.laser_beams.draw(surface)
