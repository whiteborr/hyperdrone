# entities/tr3b_enemy.py
import math
import random
import pygame
import logging
from .enemy import Enemy

import game_settings as gs

logger = logging.getLogger(__name__)

class TR3BEnemy(Enemy):
    """
    TR-3B enemy with patrol behavior:
    - Patrols within a defined radius
    - Occasionally hovers in place
    - Can perform quick dashes
    """
    def __init__(self, x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key=None, target_player_ref=None):
        super().__init__(x, y, player_bullet_size_base, asset_manager, sprite_asset_key, shoot_sound_key, target_player_ref)
        
        # TR-3B specific attributes
        self.speed = gs.get_game_setting("TR3B_SPEED", 2.0)
        self.health = gs.get_game_setting("TR3B_HEALTH", 150)
        self.max_health = self.health
        self.shoot_cooldown = gs.get_game_setting("TR3B_BULLET_COOLDOWN", 1200)
        self.aggro_radius = gs.TILE_SIZE * 12  # Increased detection range
        
        # Patrol attributes
        self.spawn_point = (x, y)
        self.patrol_radius = gs.TILE_SIZE * 8  # 8 tiles patrol radius
        self.current_patrol_point = None
        self.patrol_point_reached = True
        self.patrol_wait_time = 0
        self.patrol_wait_duration = random.randint(500, 1500)
        
        # Movement attributes
        self.hover_time = 0
        self.hover_duration = random.randint(500, 1500)
        self.dash_cooldown = 0
        self.dash_duration = 0
        self.dash_speed = self.speed * 3
        self.is_dashing = False
        self.dash_direction = (0, 0)
        
        # Pathfinding improvements
        self.PATH_RECALC_INTERVAL = 800  # More frequent path recalculation
        self.STUCK_TIME_THRESHOLD_MS = 1500  # Detect being stuck faster
        self.WAYPOINT_THRESHOLD = gs.TILE_SIZE * 0.4  # More precise waypoint targeting
        
    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        if not self.alive:
            self.bullets.update(maze, game_area_x_offset)
            if not self.bullets:
                self.kill()
            return

        # Handle dash cooldown and duration
        if self.dash_cooldown > 0:
            self.dash_cooldown -= delta_time_ms
        
        if self.is_dashing:
            self.dash_duration -= delta_time_ms
            if self.dash_duration <= 0:
                self.is_dashing = False
        
        # If we're stuck, force a new patrol point
        is_stuck = self._handle_stuck_logic(current_time_ms, delta_time_ms, maze, game_area_x_offset)
        if is_stuck:
            self.path = []
            self.current_patrol_point = None
            self.patrol_point_reached = True
            self.patrol_wait_time = self.patrol_wait_duration  # Force immediate new point selection
        
        target_pos, current_speed, can_shoot = None, self.speed, False
        
        # Handle targeting and aggro
        if self.player_ref and self.player_ref.alive:
            player_dist = math.hypot(self.x - self.player_ref.x, self.y - self.player_ref.y)
            
            # Determine if we can shoot based on distance
            if player_dist < self.aggro_radius:
                can_shoot = True
                
                # Chance to dash toward or away from player when in aggro range
                if not self.is_dashing and self.dash_cooldown <= 0 and random.random() < 0.01:
                    self._initiate_dash(self.player_ref.rect.center, player_dist)
        
        # Handle movement
        if self.is_dashing:
            self._move_during_dash(maze, game_area_x_offset)
        else:
            # Patrol behavior
            self._patrol_movement(maze, current_time_ms, game_area_x_offset)
        
        # Update sprite rotation and position
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect.center = self.rect.center
        
        # Update bullets
        self.bullets.update(maze, game_area_x_offset)
        
        # Handle shooting
        if can_shoot and (current_time_ms - self.last_shot_time > self.shoot_cooldown):
            dx, dy = self.player_ref.rect.centerx - self.x, self.player_ref.rect.centery - self.y
            self.shoot(math.degrees(math.atan2(dy, dx)), maze)
            self.last_shot_time = current_time_ms

    def _patrol_movement(self, maze, current_time_ms, game_area_x_offset):
        """Handle patrol movement within a radius of spawn point"""
        # Check if we need a new patrol point
        if not self.current_patrol_point or not self.path:
            self._select_new_patrol_point(maze, current_time_ms, game_area_x_offset)
            self.patrol_point_reached = False
            return
            
        # If we're waiting at a patrol point
        if not self.patrol_point_reached:
            # Check if we've reached the current patrol point
            if self.path and self.current_path_index >= len(self.path):
                self.patrol_point_reached = True
                self.patrol_wait_time = 0
                return
                
            # Check if we're stuck (no progress on path)
            if self.path and self.current_path_index < len(self.path) and random.random() < 0.01:
                # Occasionally check distance to target to detect being stuck
                target = self.path[self.current_path_index]
                dist = math.hypot(self.x - target[0], self.y - target[1])
                if dist > gs.TILE_SIZE * 3:
                    # We might be stuck, try a new path
                    self.path = []
                    self._update_ai_with_astar(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)
                
            # Continue moving to the patrol point
            self._update_movement_along_path(maze, game_area_x_offset, self.speed)
        else:
            # We're at a patrol point, wait for a bit
            self.patrol_wait_time += 16  # Approximate milliseconds per frame
            
            if self.patrol_wait_time >= self.patrol_wait_duration:
                # Time to move to a new patrol point
                self._select_new_patrol_point(maze, current_time_ms, game_area_x_offset)
                self.patrol_wait_time = 0
                self.patrol_wait_duration = random.randint(500, 1500)
                self.patrol_point_reached = False
            else:
                # Hover in place while waiting
                self._hover_movement(16, maze, game_area_x_offset)

    def _select_new_patrol_point(self, maze, current_time_ms, game_area_x_offset):
        """Select a new patrol point within the patrol radius"""
        # Get walkable tiles from maze
        walkable_tiles = []
        if hasattr(maze, 'get_walkable_tiles_abs'):
            walkable_tiles = maze.get_walkable_tiles_abs()
        
        if walkable_tiles:
            # Filter tiles within patrol radius
            valid_tiles = []
            for tile in walkable_tiles:
                dist_to_spawn = math.hypot(tile[0] - self.spawn_point[0], tile[1] - self.spawn_point[1])
                if dist_to_spawn <= self.patrol_radius:
                    valid_tiles.append(tile)
            
            # If we have valid tiles, choose one
            if valid_tiles:
                self.current_patrol_point = random.choice(valid_tiles)
                self.path = []  # Clear current path
                self.last_path_recalc_time = 0  # Force path recalculation
                self._update_ai_with_astar(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)
                return
        
        # Fallback: use a simple point near current position
        angle = random.uniform(0, 2 * math.pi)
        distance = gs.TILE_SIZE * 2  # Shorter distance for fallback
        self.current_patrol_point = (
            self.x + math.cos(angle) * distance,
            self.y + math.sin(angle) * distance
        )
        self.path = []  # Clear current path
        self.last_path_recalc_time = 0  # Force path recalculation
        self._update_ai_with_astar(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)

    def _hover_movement(self, delta_time_ms, maze, game_area_x_offset):
        """Hover in place with slight random movement"""
        # Small random movements while hovering
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, 0.5)
        move_x = math.cos(angle) * distance
        move_y = math.sin(angle) * distance
        
        next_x, next_y = self.x + move_x, self.y + move_y
        if not (maze and maze.is_wall(next_x, next_y, self.collision_rect.width, self.collision_rect.height)):
            self.x, self.y = next_x, next_y
            self.rect.center = (self.x, self.y)
            self.collision_rect.center = self.rect.center

    def _initiate_dash(self, target_pos, player_dist):
        """Start a dash movement either toward or away from the player"""
        self.is_dashing = True
        self.dash_duration = random.randint(200, 400)
        self.dash_cooldown = random.randint(3000, 5000)
        
        dx, dy = target_pos[0] - self.x, target_pos[1] - self.y
        angle = math.atan2(dy, dx)
        
        # Dash toward player if far, away if close
        if player_dist > gs.TILE_SIZE * 5:
            # Dash toward player
            self.dash_direction = (math.cos(angle), math.sin(angle))
        else:
            # Dash away from player
            self.dash_direction = (-math.cos(angle), -math.sin(angle))
            
        # Update angle for visual rotation
        self.angle = math.degrees(math.atan2(self.dash_direction[1], self.dash_direction[0]))

    def _move_during_dash(self, maze, game_area_x_offset):
        """Handle movement during a dash"""
        move_x = self.dash_direction[0] * self.dash_speed
        move_y = self.dash_direction[1] * self.dash_speed
        
        next_x, next_y = self.x + move_x, self.y + move_y
        
        # Check for collision with walls
        if not (maze and maze.is_wall(next_x, next_y, self.collision_rect.width, self.collision_rect.height)):
            self.x, self.y = next_x, next_y
        else:
            # End dash early if we hit a wall
            self.is_dashing = False
            
        # Keep within game bounds
        self.rect.center = (self.x, self.y)
        game_play_area_height = gs.get_game_setting("HEIGHT")
        self.rect.clamp_ip(pygame.Rect(game_area_x_offset, 0, 
                                      gs.get_game_setting("WIDTH") - game_area_x_offset, 
                                      game_play_area_height))
        self.x, self.y = self.rect.centerx, self.rect.centery
        self.collision_rect.center = self.rect.center