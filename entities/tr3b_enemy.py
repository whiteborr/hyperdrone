# entities/tr3b_enemy.py
import math
import random
import pygame
import logging
from .enemy import Enemy
from settings_manager import get_setting
from ai.behaviors import TRBPatrolBehavior, TRBDashBehavior, ChasePlayerBehavior

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
        self.speed = get_setting("enemies", "TR3B_SPEED", 2.0)
        self.health = get_setting("enemies", "TR3B_HEALTH", 150)
        self.max_health = self.health
        self.shoot_cooldown = get_setting("enemies", "TR3B_BULLET_COOLDOWN", 1200)
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.aggro_radius = tile_size * 12  # Increased detection range
        
        # Patrol attributes
        self.spawn_point = (x, y)
        self.patrol_radius = tile_size * 8  # 8 tiles patrol radius
        
        # Movement attributes
        self.dash_speed = self.speed * 3
        self.dash_cooldown = 0
        
        # Pathfinding improvements
        self.PATH_RECALC_INTERVAL = 800  # More frequent path recalculation
        self.STUCK_TIME_THRESHOLD_MS = 1500  # Detect being stuck faster
        self.WAYPOINT_THRESHOLD = get_setting("gameplay", "TILE_SIZE", 80) * 0.4  # More precise waypoint targeting
        
        # Set default behavior to patrol
        self.default_behavior = TRBPatrolBehavior
        self.set_behavior(TRBPatrolBehavior(self))
        
    def update(self, primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # Update dash cooldown
        if self.dash_cooldown > 0:
            self.dash_cooldown -= delta_time_ms
            
        # Check for random dash chance when using patrol behavior
        if (isinstance(self.behavior, TRBPatrolBehavior) and 
            self.player_ref and self.player_ref.alive and 
            self.dash_cooldown <= 0 and random.random() < 0.01):
            
            player_dist = math.hypot(self.x - self.player_ref.x, self.y - self.player_ref.y)
            if player_dist < self.aggro_radius:
                # Set dash behavior
                self.dash_cooldown = random.randint(3000, 5000)
                self.set_behavior(TRBDashBehavior(self, self.player_ref.rect.center))
        
        # Use the parent class update method which will call the current behavior
        super().update(primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset, is_defense_mode)