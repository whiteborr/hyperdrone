# entities/tr3b_enemy.py
from math import hypot
from random import random, randint
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
    def __init__(self, x, y, asset_manager, config, target_player_ref=None):
        super().__init__(x, y, asset_manager, config, target_player_ref)
        
        # Patrol attributes
        self.spawn_point = (x, y)
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        stats = self.config.get("stats", {})
        self.patrol_radius = tile_size * stats.get("patrol_radius_tiles", 8)
        
        # Movement attributes
        ai_config = self.config.get("ai", {})
        dash_speed_multiplier = ai_config.get("dash_speed_multiplier", 3.0)
        self.dash_speed = self.speed * dash_speed_multiplier
        self.dash_cooldown = 0
        self.dash_cooldown_min = ai_config.get("dash_cooldown_min", 3000)
        self.dash_cooldown_max = ai_config.get("dash_cooldown_max", 5000)
        
        # Pathfinding improvements
        self.PATH_RECALC_INTERVAL = 800  # More frequent path recalculation
        self.STUCK_TIME_THRESHOLD_MS = 1500  # Detect being stuck faster
        self.WAYPOINT_THRESHOLD = tile_size * 0.4  # More precise waypoint targeting
        
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
            self.dash_cooldown <= 0 and random() < 0.01):
            
            player_dist = hypot(self.x - self.player_ref.x, self.y - self.player_ref.y)
            if player_dist < self.aggro_radius:
                # Set dash behavior
                self.dash_cooldown = randint(self.dash_cooldown_min, self.dash_cooldown_max)
                self.set_behavior(TRBDashBehavior(self, self.player_ref.rect.center))
        
        # Use the parent class update method which will call the current behavior
        super().update(primary_target_pos_pixels, maze, current_time_ms, delta_time_ms, game_area_x_offset, is_defense_mode)