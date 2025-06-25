# ai/behaviors.py
from math import hypot, degrees, atan2, radians, cos, sin, pi
from random import randint, choice, random, uniform
from pygame import Rect
from logging import getLogger

# Import pathfinding module
from hyperdrone_core.pathfinding import a_star_search, find_wall_follow_target, find_alternative_target
from settings_manager import get_setting

logger = getLogger(__name__)

class BaseBehavior:
    """
    Base class for all enemy AI behaviors.
    
    Provides the interface that all enemy behaviors must implement. Behaviors
    define how enemies move, attack, and react to game conditions. The behavior
    system allows for complex AI through composition and state transitions.
    
    Attributes:
        enemy (Enemy): The enemy entity this behavior controls
    """
    def __init__(self, enemy):
        self.enemy = enemy

    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        """
        Execute the behavior logic for this frame.
        
        Called every frame to update the enemy's state based on this behavior.
        Implementations should handle movement, targeting, state transitions,
        and any behavior-specific logic.
        
        Args:
            maze (Maze): Current game maze for pathfinding and collision
            current_time_ms (int): Current game time in milliseconds
            delta_time_ms (int): Time elapsed since last frame
            game_area_x_offset (int): Horizontal offset for camera/viewport
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement this method.")

class WallFollowBehavior(BaseBehavior):
    """Behavior for sentinel drones to follow walls when not chasing the player"""
    def __init__(self, enemy):
        super().__init__(enemy)
        self.wall_follow_target = None
        self.last_target_update = 0
        self.target_update_interval = 2000  # Update target every 2 seconds
        self.direction_changed = False
        self.wall_follow_distance = get_setting("gameplay", "TILE_SIZE", 80) * 0.8
        
    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Check if player is in range and switch to chase behavior if so
        if self.enemy.player_ref and self.enemy.player_ref.alive:
            player_dist = hypot(self.enemy.x - self.enemy.player_ref.x, self.enemy.y - self.enemy.player_ref.y)
            if player_dist < self.enemy.aggro_radius:
                self.enemy.set_behavior(ChasePlayerBehavior(self.enemy))
                return
        
        # Update wall follow target periodically or if we've reached the current target
        if (current_time_ms - self.last_target_update > self.target_update_interval or 
            not self.wall_follow_target or 
            (self.enemy.pathfinder.path and self.enemy.pathfinder.current_path_index >= len(self.enemy.pathfinder.path))):
            
            self._find_wall_follow_target(maze, current_time_ms, game_area_x_offset)
            self.last_target_update = current_time_ms
        
        # Move along the wall
        if self.wall_follow_target:
            self.enemy.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset)
    
    def _find_wall_follow_target(self, maze, current_time_ms, game_area_x_offset):
        """Find a target position along a nearby wall"""
        if not maze or not hasattr(maze, 'grid'):
            return
            
        # Get current position in grid coordinates
        current_grid_pos = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
        
        # Find a target position along the wall
        wall_target = find_wall_follow_target(
            maze, 
            current_grid_pos, 
            maze.actual_maze_rows, 
            maze.actual_maze_cols
        )
        
        if wall_target:
            # Convert target back to pixel coordinates
            target_pixel = self._grid_to_pixel_center(wall_target[0], wall_target[1], game_area_x_offset)
            self.wall_follow_target = target_pixel
            self.enemy.pathfinder.set_target(target_pixel, maze, current_time_ms, game_area_x_offset)
        else:
            # Fallback: find any walkable tile near current position
            walkable_tiles = []
            if hasattr(maze, 'get_walkable_tiles_abs'):
                walkable_tiles = maze.get_walkable_tiles_abs()
            
            if walkable_tiles:
                # Choose a random walkable tile that's not too close to current position
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                viable_tiles = [p for p in walkable_tiles if tile_size * 3 < hypot(p[0] - self.enemy.x, p[1] - self.enemy.y) < tile_size * 8]
                if viable_tiles:
                    self.wall_follow_target = choice(viable_tiles)
                    self.enemy.pathfinder.set_target(self.wall_follow_target, maze, current_time_ms, game_area_x_offset)
    
    def _pixel_to_grid(self, px, py, offset=0):
        """Convert pixel coordinates to grid coordinates"""
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return int(py / tile_size), int((px - offset) / tile_size)
        
    def _grid_to_pixel_center(self, r, c, offset=0):
        """Convert grid coordinates to pixel coordinates (center of cell)"""
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return (c*tile_size)+(tile_size/2)+offset, (r*tile_size)+(tile_size/2)

class ChasePlayerBehavior(BaseBehavior):
    """
    Aggressive behavior that pursues the player using A* pathfinding.
    
    Uses sophisticated pathfinding to navigate around obstacles while chasing
    the player. Handles shooting when in range and transitions to other behaviors
    when the player moves out of aggro range. Includes special logic for different
    enemy types (e.g., ramming behavior for SentinelDrones).
    
    Features:
    - A* pathfinding for optimal route calculation
    - Dynamic target updating based on player movement
    - Range-based shooting for armed enemies
    - Speed boosts for close-range attacks
    - Automatic behavior transitions based on distance
    """
    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        if not self.enemy.player_ref or not self.enemy.player_ref.alive:
            return
            
        player_dist = hypot(self.enemy.x - self.enemy.player_ref.x, self.enemy.y - self.enemy.player_ref.y)
        
        # If player gets too far away, switch to wall following behavior
        if player_dist > self.enemy.aggro_radius * 1.2:
            # Check enemy class name instead of using isinstance
            if self.enemy.__class__.__name__ == "SentinelDrone":
                self.enemy.set_behavior(WallFollowBehavior(self.enemy))
            elif hasattr(self.enemy, 'default_behavior'):
                self.enemy.set_behavior(self.enemy.default_behavior(self.enemy))
            return
            
        # Set target and update movement using pathfinder component
        target_pos = self.enemy.player_ref.rect.center
        self.enemy.pathfinder.set_target(target_pos, maze, current_time_ms, game_area_x_offset)
        
        # For SentinelDrones, increase speed when close to player for ramming attack
        if self.enemy.__class__.__name__ == "SentinelDrone" and player_dist < self.enemy.aggro_radius * 0.5:
            # Use higher speed for ramming
            speed_boost = 1.5
            self.enemy.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset, 
                                                 speed_override=self.enemy.speed * speed_boost)
        else:
            # Normal movement
            self.enemy.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset)
        
        # Handle shooting if in range (only for non-SentinelDrone enemies)
        if self.enemy.__class__.__name__ != "SentinelDrone" and player_dist < self.enemy.aggro_radius and (current_time_ms - self.enemy.last_shot_time > self.enemy.shoot_cooldown):
            dx = self.enemy.player_ref.rect.centerx - self.enemy.x
            dy = self.enemy.player_ref.rect.centery - self.enemy.y
            # Only shoot if there's a clear line of sight to the player
            if self._has_line_of_sight(self.enemy.x, self.enemy.y, self.enemy.player_ref.rect.centerx, self.enemy.player_ref.rect.centery, maze):
                self.enemy.shoot(degrees(atan2(dy, dx)), maze)
                self.enemy.last_shot_time = current_time_ms
    
    def _has_line_of_sight(self, start_x, start_y, end_x, end_y, maze):
        """Check if there's a clear line of sight between two points"""
        if not maze:
            return True
        
        dx = end_x - start_x
        dy = end_y - start_y
        distance = hypot(dx, dy)
        
        if distance == 0:
            return True
        
        # Normalize direction
        step_x = dx / distance
        step_y = dy / distance
        
        # Check points along the line
        steps = int(distance / 5)  # Check every 5 pixels
        for i in range(1, steps):
            check_x = start_x + (step_x * i * 5)
            check_y = start_y + (step_y * i * 5)
            
            # Check if this point is inside a wall
            if maze.is_wall(check_x, check_y, 1, 1):
                return False
        
        return True

class TRBPatrolBehavior(BaseBehavior):
    """Behavior for TR3B enemy patrol movement"""
    def __init__(self, enemy):
        super().__init__(enemy)
        self.patrol_point_reached = True
        self.patrol_wait_time = 0
        self.patrol_wait_duration = randint(500, 1500)
        self.current_patrol_point = None

    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Check if player is in aggro range and switch to chase behavior if so
        if self.enemy.player_ref and self.enemy.player_ref.alive:
            player_dist = hypot(self.enemy.x - self.enemy.player_ref.x, self.enemy.y - self.enemy.player_ref.y)
            if player_dist < self.enemy.aggro_radius:
                self.enemy.set_behavior(ChasePlayerBehavior(self.enemy))
                return
        
        # Always ensure we have a patrol point and start moving immediately
        if not self.current_patrol_point:
            self._select_new_patrol_point(maze, current_time_ms, game_area_x_offset)
            self.patrol_point_reached = False
            return
            
        # If we're waiting at a patrol point
        if not self.patrol_point_reached:
            # Check if we've reached the current patrol point
            if self.enemy.pathfinder.path and self.enemy.pathfinder.current_path_index >= len(self.enemy.pathfinder.path):
                self.patrol_point_reached = True
                self.patrol_wait_time = 0
                return
                
            # Check if we're stuck (no progress on path)
            if self.enemy.pathfinder.path and self.enemy.pathfinder.current_path_index < len(self.enemy.pathfinder.path) and random() < 0.01:
                # Occasionally check distance to target to detect being stuck
                target = self.enemy.pathfinder.path[self.enemy.pathfinder.current_path_index]
                dist = hypot(self.enemy.x - target[0], self.enemy.y - target[1])
                tile_size = get_setting("gameplay", "TILE_SIZE", 80)
                if dist > tile_size * 3:
                    # We might be stuck, try a new path
                    self.enemy.pathfinder.set_target(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)
                
            # Continue moving to the patrol point
            self.enemy.pathfinder.update_movement(maze, current_time_ms, delta_time_ms, game_area_x_offset)
        else:
            # We're at a patrol point, wait for a bit
            self.patrol_wait_time += delta_time_ms
            
            if self.patrol_wait_time >= self.patrol_wait_duration:
                # Time to move to a new patrol point
                self._select_new_patrol_point(maze, current_time_ms, game_area_x_offset)
                self.patrol_wait_time = 0
                self.patrol_wait_duration = randint(500, 1500)
                self.patrol_point_reached = False
            else:
                # Hover in place while waiting
                self._hover_movement(delta_time_ms, maze, game_area_x_offset)
                
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
                dist_to_spawn = hypot(tile[0] - self.enemy.spawn_point[0], tile[1] - self.enemy.spawn_point[1])
                if dist_to_spawn <= self.enemy.patrol_radius:
                    valid_tiles.append(tile)
            
            # If we have valid tiles, choose one
            if valid_tiles:
                self.current_patrol_point = choice(valid_tiles)
                self.enemy.pathfinder.set_target(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)
                return
        
        # Fallback: use a simple point near spawn position
        angle = uniform(0, 2 * pi)
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        distance = min(self.enemy.patrol_radius, tile_size * 4)  # Use patrol radius or reasonable distance
        self.current_patrol_point = (
            self.enemy.spawn_point[0] + cos(angle) * distance,
            self.enemy.spawn_point[1] + sin(angle) * distance
        )
        self.enemy.pathfinder.set_target(self.current_patrol_point, maze, current_time_ms, game_area_x_offset)

    def _hover_movement(self, delta_time_ms, maze, game_area_x_offset):
        """Hover in place with slight random movement"""
        # Small random movements while hovering
        angle = uniform(0, 2 * pi)
        distance = uniform(0, 0.5)
        move_x = cos(angle) * distance
        move_y = sin(angle) * distance
        
        next_x, next_y = self.enemy.x + move_x, self.enemy.y + move_y
        if not (maze and maze.is_wall(next_x, next_y, self.enemy.collision_rect.width, self.enemy.collision_rect.height)):
            self.enemy.x, self.enemy.y = next_x, next_y
            self.enemy.rect.center = (self.enemy.x, self.enemy.y)
            self.enemy.collision_rect.center = self.enemy.rect.center

class TRBDashBehavior(BaseBehavior):
    """Behavior for TR3B enemy dash movement"""
    def __init__(self, enemy, target_pos=None, dash_duration=None):
        super().__init__(enemy)
        self.dash_duration = dash_duration or randint(200, 400)
        self.dash_time_remaining = self.dash_duration
        
        # Set dash direction
        if target_pos and self.enemy.player_ref:
            player_dist = hypot(self.enemy.x - self.enemy.player_ref.x, self.enemy.y - self.enemy.player_ref.y)
            dx, dy = target_pos[0] - self.enemy.x, target_pos[1] - self.enemy.y
            angle = atan2(dy, dx)
            
            # Dash toward player if far, away if close
            tile_size = get_setting("gameplay", "TILE_SIZE", 80)
            if player_dist > tile_size * 5:
                # Dash toward player
                self.dash_direction = (cos(angle), sin(angle))
            else:
                # Dash away from player
                self.dash_direction = (-cos(angle), -sin(angle))
        else:
            # Random direction if no target
            angle = uniform(0, 2 * pi)
            self.dash_direction = (cos(angle), sin(angle))
            
        # Update angle for visual rotation
        self.enemy.angle = degrees(atan2(self.dash_direction[1], self.dash_direction[0]))

    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # Update dash duration
        self.dash_time_remaining -= delta_time_ms
        
        # Check if dash is complete
        if self.dash_time_remaining <= 0:
            # Return to patrol or chase behavior
            if self.enemy.player_ref and self.enemy.player_ref.alive:
                player_dist = hypot(self.enemy.x - self.enemy.player_ref.x, self.enemy.y - self.enemy.player_ref.y)
                if player_dist < self.enemy.aggro_radius:
                    from ai.behaviors import ChasePlayerBehavior
                    self.enemy.set_behavior(ChasePlayerBehavior(self.enemy))
                    return
            
            # Default to patrol behavior
            self.enemy.set_behavior(TRBPatrolBehavior(self.enemy))
            return
            
        # Handle dash movement
        move_x = self.dash_direction[0] * self.enemy.dash_speed
        move_y = self.dash_direction[1] * self.enemy.dash_speed
        
        next_x, next_y = self.enemy.x + move_x, self.enemy.y + move_y
        
        # Check for collision with walls
        if not (maze and maze.is_wall(next_x, next_y, self.enemy.collision_rect.width, self.enemy.collision_rect.height)):
            self.enemy.x, self.enemy.y = next_x, next_y
        else:
            # End dash early if we hit a wall
            self.enemy.set_behavior(TRBPatrolBehavior(self.enemy))
            return
            
        # Keep within game bounds
        self.enemy.rect.center = (self.enemy.x, self.enemy.y)
        game_play_area_height = get_setting("display", "HEIGHT", 1080)
        self.enemy.rect.clamp_ip(Rect(game_area_x_offset, 0, 
                                           get_setting("display", "WIDTH", 1920) - game_area_x_offset, 
                                           game_play_area_height))
        self.enemy.x, self.enemy.y = self.enemy.rect.centerx, self.enemy.rect.centery
        self.enemy.collision_rect.center = self.enemy.rect.center


class RetreatBehavior(BaseBehavior):
    """
    Behavior for an enemy to retreat when health is low.
    It will attempt to find a safe, distant spot from the player.
    """
    def __init__(self, enemy):
        super().__init__(enemy)
        self.retreat_target = None
        self.last_retreat_attempt_time = 0
        self.retreat_recalc_interval = get_setting("enemies", "RETREAT_RECALC_INTERVAL_MS", 1000) # How often to recalculate retreat path
        self.min_retreat_distance = get_setting("enemies", "MIN_RETREAT_DISTANCE_TILES", 8) * get_setting("gameplay", "TILE_SIZE", 80) # Distance to retreat
        self.retreat_speed_multiplier = get_setting("enemies", "RETREAT_SPEED_MULTIPLIER", 1.2) # Faster movement when retreating

    def execute(self, maze, current_time_ms, delta_time_ms, game_area_x_offset=0):
        # If player is gone or enemy healed, revert to default behavior
        if not self.enemy.player_ref or not self.enemy.player_ref.alive or \
           self.enemy.health > self.enemy.max_health * get_setting("enemies", "RETREAT_HEALTH_THRESHOLD", 0.3):
            self.enemy.set_behavior(self.enemy.default_behavior(self.enemy))
            return

        # Recalculate retreat path periodically or if current path is invalid/finished
        if current_time_ms - self.last_retreat_attempt_time > self.retreat_recalc_interval or \
           not self.retreat_target or \
           not self.enemy.pathfinder.path or \
           self.enemy.pathfinder.current_path_index >= len(self.enemy.pathfinder.path):
            
            self._find_retreat_target(maze, current_time_ms, game_area_x_offset)
            self.last_retreat_attempt_time = current_time_ms
        
        # Move towards the retreat target
        if self.retreat_target:
            self.enemy.pathfinder.update_movement(
                maze, 
                current_time_ms, 
                delta_time_ms, 
                game_area_x_offset, 
                speed_override=self.enemy.speed * self.retreat_speed_multiplier
            )
        else:
            # If no retreat target found, just try to move away directly from player
            if self.enemy.player_ref:
                dx = self.enemy.x - self.enemy.player_ref.x
                dy = self.enemy.y - self.enemy.player_ref.y
                dist = hypot(dx, dy)
                if dist > 0:
                    self.enemy.angle = degrees(atan2(dy, dx))
                    self.enemy.pathfinder.update_movement(
                        maze, 
                        current_time_ms, 
                        delta_time_ms, 
                        game_area_x_offset, 
                        speed_override=self.enemy.speed * self.retreat_speed_multiplier
                    )

    def _find_retreat_target(self, maze, current_time_ms, game_area_x_offset):
        """Finds a distant, walkable target away from the player."""
        if not maze or not self.enemy.player_ref:
            self.retreat_target = None
            return

        walkable_tiles = maze.get_walkable_tiles_abs()
        if not walkable_tiles:
            self.retreat_target = None
            return

        # Sort walkable tiles by distance to player (farthest first)
        player_x, player_y = self.enemy.player_ref.x, self.enemy.player_ref.y
        
        # Consider a wider area for retreat targets
        search_radius_tiles = get_setting("enemies", "RETREAT_SEARCH_RADIUS_TILES", 20)
        search_radius_pixels = search_radius_tiles * get_setting("gameplay", "TILE_SIZE", 80)

        potential_targets = []
        for tile_x, tile_y in walkable_tiles:
            dist_to_player = hypot(tile_x - player_x, tile_y - player_y)
            # Only consider tiles that are sufficiently far from the player
            if dist_to_player > self.min_retreat_distance:
                # Prioritize tiles that are further away, and within a reasonable search area
                if dist_to_player < search_radius_pixels:
                    potential_targets.append((tile_x, tile_y, dist_to_player))
        
        if not potential_targets:
            self.retreat_target = None
            return

        # Sort by distance (farthest first)
        potential_targets.sort(key=lambda x: x[2], reverse=True)

        # Try to find a path to the farthest viable target
        found_path = False
        for target_x, target_y, _ in potential_targets:
            target_grid_pos = self._pixel_to_grid(target_x, target_y, game_area_x_offset)
            enemy_grid_pos = self._pixel_to_grid(self.enemy.x, self.enemy.y, game_area_x_offset)
            
            # Ensure target is walkable
            if not maze.is_wall(target_x, target_y, 1, 1): # Check a 1x1 area for wall
                path = a_star_search(
                    maze.grid, 
                    enemy_grid_pos, 
                    target_grid_pos, 
                    maze.actual_maze_rows, 
                    maze.actual_maze_cols
                )
                if path and len(path) > 1:
                    self.retreat_target = (target_x, target_y)
                    self.enemy.pathfinder.set_target(self.retreat_target, maze, current_time_ms, game_area_x_offset)
                    found_path = True
                    break
        
        if not found_path:
            self.retreat_target = None # No viable retreat path found

    def _pixel_to_grid(self, px, py, offset=0):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return int(py / tile_size), int((px - offset) / tile_size)
        
    def _grid_to_pixel_center(self, r, c, offset=0):
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        return (c*tile_size)+(tile_size/2)+offset, (r*tile_size)+(tile_size/2)
