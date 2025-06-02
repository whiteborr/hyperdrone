# entities/enemy.py
import math
import random
import os
import heapq # For A* priority queue

import pygame

# Assuming Bullet class is in the same directory or accessible via entities.bullet
try:
    from .bullet import Bullet 
except ImportError:
    # Minimal placeholder if Bullet class is not found (should not happen in full project)
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
    WIDTH, GAME_PLAY_AREA_HEIGHT, WHITE, GREEN # Added WHITE, GREEN for health bar
)

# --- A* Node and Heuristic ---
class AStarNode:
    def __init__(self, position, parent=None):
        self.position = position # (row, col) tuple
        self.parent = parent
        self.g_cost = 0 # Distance from start node
        self.h_cost = 0 # Heuristic distance to end node
        self.f_cost = 0 # g_cost + h_cost

    def __eq__(self, other):
        return self.position == other.position

    def __lt__(self, other): # For priority queue comparison
        return self.f_cost < other.f_cost
    
    def __hash__(self): # To add nodes to a set (closed_set)
        return hash(self.position)

def heuristic(node_pos, goal_pos):
    """Manhattan distance heuristic for A*."""
    return abs(node_pos[0] - goal_pos[0]) + abs(node_pos[1] - goal_pos[1])

# --- A* Search Function ---
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    """
    Performs A* pathfinding on a given grid.
    Args:
        maze_grid (list of lists): The maze layout (0 or 'C' for path, 1 for wall).
        start_pos_grid (tuple): (row, col) of the starting position.
        end_pos_grid (tuple): (row, col) of the target position.
        maze_rows (int): Total number of rows in the maze_grid.
        maze_cols (int): Total number of columns in the maze_grid.
    Returns:
        list: A list of (row, col) tuples representing the path from start to end,
              or None if no path is found.
    """
    # Basic validation of inputs
    if not maze_grid or \
       not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or \
       not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols):
        # print(f"A* Search: Invalid input. Start: {start_pos_grid}, End: {end_pos_grid}, Maze: {maze_rows}x{maze_cols}")
        return None

    start_node = AStarNode(start_pos_grid)
    end_node = AStarNode(end_pos_grid)

    open_list = [] # Priority queue of nodes to visit
    closed_set = set() # Set of positions already evaluated
    heapq.heappush(open_list, start_node) # Add start node to open list

    while open_list:
        current_node = heapq.heappop(open_list) # Get node with lowest f_cost
        
        if current_node.position == end_node.position: # Path found
            path = []
            current = current_node
            while current:
                path.append(current.position)
                current = current.parent
            return path[::-1] # Return reversed path

        closed_set.add(current_node.position) # Mark current node as evaluated

        # Explore neighbors (up, down, left, right)
        for new_position_offset in [(0, -1), (0, 1), (-1, 0), (1, 0)]: 
            node_position = (current_node.position[0] + new_position_offset[0],
                             current_node.position[1] + new_position_offset[1])

            # Check if neighbor is within maze boundaries
            if not (0 <= node_position[0] < maze_rows and 0 <= node_position[1] < maze_cols):
                continue 
            
            # Check if neighbor is a wall (tile type 1). '0' and 'C' are walkable.
            if maze_grid[node_position[0]][node_position[1]] == 1: 
                continue 
            
            # Check if neighbor is already in closed set
            if node_position in closed_set:
                continue 
            
            # Create neighbor node
            neighbor_node = AStarNode(node_position, current_node)
            neighbor_node.g_cost = current_node.g_cost + 1 # Cost to reach neighbor
            neighbor_node.h_cost = heuristic(neighbor_node.position, end_node.position) # Heuristic cost
            neighbor_node.f_cost = neighbor_node.g_cost + neighbor_node.h_cost

            # Check if neighbor is in open list and if current path is better
            in_open_list_better_g_cost = False
            for open_node_item in open_list:
                if neighbor_node == open_node_item and neighbor_node.g_cost >= open_node_item.g_cost:
                    in_open_list_better_g_cost = True
                    break
            
            if not in_open_list_better_g_cost:
                heapq.heappush(open_list, neighbor_node) # Add neighbor to open list
                
    # print(f"A* Search: No path found from {start_pos_grid} to {end_pos_grid}")
    return None # No path found


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0 
        self.speed = gs.get_game_setting("ENEMY_SPEED", 1.5) 
        self.health = gs.get_game_setting("ENEMY_HEALTH", 100)
        self.max_health = gs.get_game_setting("ENEMY_HEALTH", 100)
        self.alive = True
        self.shoot_sound = shoot_sound
        self.player_ref = target_player_ref # Reference to the player drone for shooting AI

        # --- Defense Mode Attributes ---
        self.is_in_defense_mode = False 
        self.defense_target = None      # Will be the CoreReactor object if in defense mode
        self.contact_damage = 25        # Default damage on contact with reactor

        self.original_image = None 
        self.image = None          
        self.rect = None           
        self.collision_rect = None 
        self._load_sprite(sprite_path) # Load sprite and initialize rects

        self.bullets = pygame.sprite.Group() 
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500))) 
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500)
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3

        # --- Pathfinding Attributes ---
        self.path = []  # List of (pixel_x, pixel_y) waypoints
        self.current_path_index = 0 
        self.target_grid_cell = None # The grid cell the enemy is currently moving towards
        self.last_path_recalc_time = 0 
        self.PATH_RECALC_INTERVAL = 1000 # Recalculate path every 1 second (milliseconds)
        self.WAYPOINT_THRESHOLD = TILE_SIZE * 0.3 # How close to get to a waypoint before moving to next

    def _pixel_to_grid(self, pixel_x, pixel_y, game_area_x_offset=0):
        """Converts absolute pixel coordinates to maze grid (row, col) coordinates."""
        col = int((pixel_x - game_area_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _grid_to_pixel_center(self, grid_row, grid_col, game_area_x_offset=0):
        """Converts maze grid (row, col) to absolute pixel center of the tile."""
        pixel_x = (grid_col * TILE_SIZE) + (TILE_SIZE / 2) + game_area_x_offset
        pixel_y = (grid_row * TILE_SIZE) + (TILE_SIZE / 2)
        return pixel_x, pixel_y

    def _load_sprite(self, sprite_path):
        default_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) 
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, default_size)
            except pygame.error as e:
                print(f"Error loading enemy sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: print(f"Warning: Enemy sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None: 
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill(ENEMY_COLOR) 

        self.image = self.original_image.copy() 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        
        # Initialize collision_rect based on the visual rect
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def update(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        """
        Updates the enemy's state, AI, movement, and shooting.
        """
        if not self.alive:
            if not self.bullets: # If no bullets left to update
                self.kill()
            self.bullets.update(maze, game_area_x_offset) # Update bullets even if enemy is dead
            return

        # Determine the actual target for pathfinding based on game mode
        actual_target_for_pathfinding_pixels = primary_target_pos_pixels
        if is_defense_mode and self.defense_target and self.defense_target.alive:
            actual_target_for_pathfinding_pixels = self.defense_target.rect.center
        
        # Update AI and pathfinding
        self._update_ai_with_astar(actual_target_for_pathfinding_pixels, maze, current_time_ms, game_area_x_offset)
        
        # Update movement along the calculated path
        self._update_movement_along_path(maze, game_area_x_offset) 

        # Rotate sprite to face movement direction (or target if not moving along path)
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.collision_rect: self.collision_rect.center = self.rect.center

        # Update bullets
        self.bullets.update(maze, game_area_x_offset)

        # Determine target for shooting (always player if player is alive and in range)
        shooting_target_pos_for_aiming = None
        if self.player_ref and self.player_ref.alive: 
            shooting_target_pos_for_aiming = self.player_ref.rect.center

        # Shooting logic
        if shooting_target_pos_for_aiming and (current_time_ms - self.last_shot_time > self.shoot_cooldown):
            dx_shoot_target = shooting_target_pos_for_aiming[0] - self.x
            dy_shoot_target = shooting_target_pos_for_aiming[1] - self.y
            distance_to_shoot_target = math.hypot(dx_shoot_target, dy_shoot_target)
            
            shooting_range = TILE_SIZE * 8 # Define a shooting range
            if distance_to_shoot_target < shooting_range:
                angle_to_shoot_target = math.degrees(math.atan2(dy_shoot_target, dx_shoot_target))
                self.shoot(angle_to_shoot_target) # Pass the calculated angle
                self.last_shot_time = current_time_ms

    def _update_ai_with_astar(self, target_pos_for_pathfinding_pixels, maze, current_time_ms, game_area_x_offset):
        """Handles A* pathfinding logic."""
        if not target_pos_for_pathfinding_pixels or not maze:
            self.path = [] # Clear path if no target or maze
            return

        # Recalculate path periodically or if no path exists
        if current_time_ms - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time_ms

            enemy_grid_pos = self._pixel_to_grid(self.x, self.y, game_area_x_offset) 
            target_grid_pos = self._pixel_to_grid(target_pos_for_pathfinding_pixels[0], target_pos_for_pathfinding_pixels[1], game_area_x_offset)

            # Validate grid positions before calling A*
            if not (0 <= enemy_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= enemy_grid_pos[1] < maze.actual_maze_cols and \
                    0 <= target_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= target_grid_pos[1] < maze.actual_maze_cols):
                self.path = []
                return

            # Ensure target grid cell is not a wall (1)
            if maze.grid[target_grid_pos[0]][target_grid_pos[1]] == 1:
                self.path = [] # Cannot pathfind to a wall
                return

            # Perform A* search
            # The maze.grid passed to a_star_search will be from Maze or MazeChapter2
            grid_path = a_star_search(maze.grid, enemy_grid_pos, target_grid_pos, maze.actual_maze_rows, maze.actual_maze_cols)

            if grid_path and len(grid_path) > 1: # If a valid path is found (more than just start node)
                # Convert grid path to pixel waypoints (centers of tiles)
                self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path] 
                self.current_path_index = 1 # Start moving towards the second node in the path
            else:
                self.path = [] # No path found or path is too short
        
        # If no path, face the primary target directly (for shooting or last resort movement)
        if not self.path and target_pos_for_pathfinding_pixels:
            dx = target_pos_for_pathfinding_pixels[0] - self.x
            dy = target_pos_for_pathfinding_pixels[1] - self.y
            if math.hypot(dx, dy) > 0: # Avoid division by zero if already at target
                self.angle = math.degrees(math.atan2(dy, dx))


    def _update_movement_along_path(self, maze, game_area_x_offset=0): 
        """Moves the enemy along the calculated A* path."""
        if not self.path or self.current_path_index >= len(self.path):
            # If no path, and in defense mode, might try to move directly to reactor (simple fallback)
            if self.is_in_defense_mode and self.defense_target and self.defense_target.alive:
                dx = self.defense_target.rect.centerx - self.x
                dy = self.defense_target.rect.centery - self.y
                distance_to_target = math.hypot(dx, dy)
                if distance_to_target > TILE_SIZE * 0.2: # Don't jitter if very close
                    self.angle = math.degrees(math.atan2(dy, dx))
                    self.x += (dx / distance_to_target) * self.speed
                    self.y += (dy / distance_to_target) * self.speed
            return # No path to follow

        # Get the current waypoint in pixel coordinates
        target_waypoint_pixels = self.path[self.current_path_index]
        dx = target_waypoint_pixels[0] - self.x
        dy = target_waypoint_pixels[1] - self.y
        distance_to_waypoint = math.hypot(dx, dy)

        # If close enough to the current waypoint, move to the next one
        if distance_to_waypoint < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path): # Reached end of path
                self.path = [] # Clear path, will be recalculated
                return
            # Update target to the new waypoint
            target_waypoint_pixels = self.path[self.current_path_index]
            dx = target_waypoint_pixels[0] - self.x
            dy = target_waypoint_pixels[1] - self.y
            distance_to_waypoint = math.hypot(dx, dy)


        # Move towards the current waypoint
        if distance_to_waypoint > 0: # Avoid division by zero if already at waypoint
            self.angle = math.degrees(math.atan2(dy, dx)) # Face the waypoint
            
            # Calculate movement components
            move_x_component = (dx / distance_to_waypoint) * self.speed
            move_y_component = (dy / distance_to_waypoint) * self.speed
            
            next_x = self.x + move_x_component
            next_y = self.y + move_y_component
            
            # Simple boundary check (more robust collision with maze.is_wall could be added here if needed)
            self.x = next_x
            self.y = next_y

        # Boundary checks for the game area (redundant if maze walls are perfect, but good for safety)
        if self.rect: # Ensure rect exists
            half_width = self.rect.width / 2 
            half_height = self.rect.height / 2
            
            min_x_bound = game_area_x_offset + half_width 
            max_x_bound = WIDTH - half_width # Assuming WIDTH is screen width
            min_y_bound = half_height
            max_y_bound = GAME_PLAY_AREA_HEIGHT - half_height # Assuming GAME_PLAY_AREA_HEIGHT

            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))
            
            self.rect.center = (int(self.x), int(self.y))
            if self.collision_rect: self.collision_rect.center = self.rect.center


    def shoot(self, direct_angle_to_target): 
        """Fires a bullet towards the given angle."""
        if not self.alive:
            return

        rad_fire_angle = math.radians(direct_angle_to_target) 
        # Calculate bullet spawn position (e.g., from the "nose" of the enemy)
        tip_offset_distance = (self.rect.width / 2) if self.rect else (TILE_SIZE * 0.35)
        
        fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance
        fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=direct_angle_to_target, 
            speed=gs.get_game_setting("ENEMY_BULLET_SPEED", 5),
            lifetime=gs.get_game_setting("ENEMY_BULLET_LIFETIME", 75),
            size=self.enemy_bullet_size, # Use calculated bullet size
            color=gs.get_game_setting("ENEMY_BULLET_COLOR", (255,165,0)), # Orange
            damage=gs.get_game_setting("ENEMY_BULLET_DAMAGE", 10)
        )
        self.bullets.add(new_bullet)
        if self.shoot_sound:
            self.shoot_sound.play()

    def take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            # Death animation/sound handled by EnemyManager or GameController

    def draw(self, surface):
        """Draws the enemy and its bullets."""
        if self.alive and self.image and self.rect: # Ensure image and rect are valid
            surface.blit(self.image, self.rect)
            
        self.bullets.draw(surface) # Draw bullets regardless of enemy alive status for lingering shots

    def _draw_health_bar(self, surface):
        """Draws the enemy's health bar above it."""
        if self.alive and self.rect: # Ensure rect is valid
            bar_width = self.rect.width * 0.8
            bar_height = 5
            bar_x = self.rect.centerx - bar_width / 2
            bar_y = self.rect.top - bar_height - 2 # Position above the enemy
            
            health_percentage = self.health / self.max_health if self.max_health > 0 else 0
            filled_width = bar_width * health_percentage
            
            # Background of the health bar (e.g., dark red or grey)
            pygame.draw.rect(surface, (80,0,0), (bar_x, bar_y, bar_width, bar_height)) 
            # Filled portion of the health bar
            if filled_width > 0:
                pygame.draw.rect(surface, GREEN, (bar_x, bar_y, int(filled_width), bar_height)) 
            # Border for the health bar
            pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1) 


class SentinelDrone(Enemy): 
    """
    A specialized enemy type, inherits from Enemy but can have different behaviors or stats.
    """
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        # Use the provided sprite_path or default to game_settings
        actual_sprite_path = sprite_path or gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH")
        super().__init__(x, y, player_bullet_size_base, shoot_sound, actual_sprite_path, target_player_ref)
        
        # Override stats specific to SentinelDrone
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED", 3.0)
        self.health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75)
        self.max_health = gs.get_game_setting("SENTINEL_DRONE_HEALTH", 75)
        self.shoot_cooldown = int(gs.get_game_setting("ENEMY_BULLET_COOLDOWN", 1500) * 0.7) # Faster shooting

    def _load_sprite(self, sprite_path): 
        # SentinelDrone might have a different default size or visual style
        default_size = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6)) 
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, default_size)
            except pygame.error as e:
                print(f"Error loading sentinel sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: print(f"Warning: Sentinel sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None: # Fallback visual for SentinelDrone
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            # Example: A diamond shape for Sentinel
            points = [
                (default_size[0] // 2, 0), (default_size[0], default_size[1] // 2),
                (default_size[0] // 2, default_size[1]), (0, default_size[1] // 2)
            ]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points) 
            pygame.draw.polygon(self.original_image, WHITE, points, 1) # White outline


        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        if self.rect: 
            self.collision_rect_width = self.rect.width * 0.8
            self.collision_rect_height = self.rect.height * 0.8
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: # Fallback if rect somehow not initialized (should not happen)
            self.collision_rect = pygame.Rect(self.x - default_size[0]*0.4, self.y - default_size[1]*0.4, default_size[0]*0.8, default_size[1]*0.8)


    def update(self, primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset=0, is_defense_mode=False):
        # SentinelDrone uses the same update logic as the base Enemy for now.
        # Specific behaviors could be added here if needed.
        super().update(primary_target_pos_pixels, maze, current_time_ms, game_area_x_offset, is_defense_mode)