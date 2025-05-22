import math
import random
import os
import heapq # For A* priority queue

import pygame

from .bullet import Bullet # Assuming Bullet is in the same directory

import game_settings as gs
from game_settings import (
    TILE_SIZE, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_COLOR,
    ENEMY_BULLET_SPEED, ENEMY_BULLET_COOLDOWN, ENEMY_BULLET_LIFETIME,
    ENEMY_BULLET_COLOR, ENEMY_BULLET_DAMAGE,
    PLAYER_DEFAULT_BULLET_SIZE,
    WIDTH, GAME_PLAY_AREA_HEIGHT
)

# --- A* Node and Heuristic (from Step 1) ---
class AStarNode:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g_cost = 0
        self.h_cost = 0
        self.f_cost = 0

    def __eq__(self, other):
        return self.position == other.position

    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __hash__(self):
        return hash(self.position)

def heuristic(node_pos, goal_pos):
    return abs(node_pos[0] - goal_pos[0]) + abs(node_pos[1] - goal_pos[1])

# --- A* Search Function (from Step 2) ---
def a_star_search(maze_grid, start_pos_grid, end_pos_grid, maze_rows, maze_cols):
    if not maze_grid or \
       not (0 <= start_pos_grid[0] < maze_rows and 0 <= start_pos_grid[1] < maze_cols) or \
       not (0 <= end_pos_grid[0] < maze_rows and 0 <= end_pos_grid[1] < maze_cols):
        # print(f"A* Invalid input: Start {start_pos_grid}, End {end_pos_grid}, Rows {maze_rows}, Cols {maze_cols}")
        return None

    start_node = AStarNode(start_pos_grid)
    end_node = AStarNode(end_pos_grid)

    open_list = []
    closed_set = set()
    heapq.heappush(open_list, start_node)

    while open_list:
        current_node = heapq.heappop(open_list)
        
        if current_node.position == end_node.position:
            path = []
            current = current_node
            while current:
                path.append(current.position)
                current = current.parent
            return path[::-1]

        closed_set.add(current_node.position)

        # Check neighbors (Up, Down, Left, Right)
        for new_position_offset in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            node_position = (current_node.position[0] + new_position_offset[0],
                             current_node.position[1] + new_position_offset[1])

            if not (0 <= node_position[0] < maze_rows and 0 <= node_position[1] < maze_cols):
                continue
            if maze_grid[node_position[0]][node_position[1]] != 0: # 0 is path
                continue
            if node_position in closed_set:
                continue
            
            # Check if already in open list with a better path
            found_in_open = False
            for open_node_idx, open_node_item in enumerate(open_list):
                if open_node_item.position == node_position:
                    found_in_open = True
                    if current_node.g_cost + 1 < open_node_item.g_cost:
                        open_list.pop(open_node_idx) # Remove old one
                        heapq.heapify(open_list)
                        # Add new better path to this node
                        new_node = AStarNode(node_position, current_node)
                        new_node.g_cost = current_node.g_cost + 1
                        new_node.h_cost = heuristic(new_node.position, end_node.position)
                        new_node.f_cost = new_node.g_cost + new_node.h_cost
                        heapq.heappush(open_list, new_node)
                    break # Stop searching open_list for this neighbor
            
            if not found_in_open:
                new_node = AStarNode(node_position, current_node)
                new_node.g_cost = current_node.g_cost + 1
                new_node.h_cost = heuristic(new_node.position, end_node.position)
                new_node.f_cost = new_node.g_cost + new_node.h_cost
                heapq.heappush(open_list, new_node)
    return None


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.speed = gs.ENEMY_SPEED
        self.health = gs.ENEMY_HEALTH
        self.max_health = gs.ENEMY_HEALTH
        self.alive = True
        self.shoot_sound = shoot_sound
        self.player_ref = target_player_ref # Store player reference

        self.original_image = None
        self.image = None
        self.rect = None
        self.collision_rect = None
        self._load_sprite(sprite_path)

        self.bullets = pygame.sprite.Group()
        self.last_shot_time = pygame.time.get_ticks() + random.randint(0, int(ENEMY_BULLET_COOLDOWN))
        self.shoot_cooldown = ENEMY_BULLET_COOLDOWN
        self.enemy_bullet_size = int(player_bullet_size_base // 1.5) if player_bullet_size_base else 3

        # A* Pathfinding attributes
        self.path = []  # List of (row, col) tuples or (x,y) pixel waypoints
        self.current_path_index = 0
        self.target_grid_cell = None # (row, col)
        self.last_path_recalc_time = 0
        self.PATH_RECALC_INTERVAL = 1000 # Recalculate path every 1 second (milliseconds)
        self.WAYPOINT_THRESHOLD = TILE_SIZE * 0.3 # How close to get to a waypoint

    def _pixel_to_grid(self, pixel_x, pixel_y, game_area_x_offset=0):
        # Note: In your Maze class, grid coordinates seem to be relative to the maze drawing area
        # which might already account for game_area_x_offset internally when grid is made.
        # For A*, we usually pass the maze's own grid.
        # The enemy's x,y are absolute screen coordinates.
        # The maze.grid is [row][col]
        col = int((pixel_x - game_area_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _grid_to_pixel_center(self, grid_row, grid_col, game_area_x_offset=0):
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
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center

    def update(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        if not self.alive:
            if not self.bullets:
                self.kill()
            self.bullets.update(maze, game_area_x_offset)
            return

        # AI and Pathfinding Update
        self._update_ai_with_astar(player_pos_pixels, maze, current_time, game_area_x_offset)
        
        # Movement based on path
        self._update_movement_along_path(maze, game_area_x_offset) # Pass maze for boundary checks

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) # Cast to int for rect
        self.collision_rect.center = self.rect.center

        self.bullets.update(maze, game_area_x_offset)

        if player_pos_pixels and (current_time - self.last_shot_time > self.shoot_cooldown):
            dx_player = player_pos_pixels[0] - self.x
            dy_player = player_pos_pixels[1] - self.y
            distance_to_player = math.hypot(dx_player, dy_player)
            shooting_range = TILE_SIZE * 10
            if distance_to_player < shooting_range:
                # Aim directly at player when shooting, regardless of path
                angle_to_player = math.degrees(math.atan2(dy_player, dx_player))
                self.shoot(angle_to_player) # Pass the direct angle to player
                self.last_shot_time = current_time

    def _update_ai_with_astar(self, player_pos_pixels, maze, current_time, game_area_x_offset):
        if not player_pos_pixels or not maze:
            self.path = [] # Clear path if no player or maze
            return

        # Recalculate path if enough time has passed or if path is empty/finished
        if current_time - self.last_path_recalc_time > self.PATH_RECALC_INTERVAL or not self.path:
            self.last_path_recalc_time = current_time

            enemy_grid_pos = self._pixel_to_grid(self.x, self.y, game_area_x_offset)
            player_grid_pos = self._pixel_to_grid(player_pos_pixels[0], player_pos_pixels[1], game_area_x_offset)

            # Ensure grid positions are valid for the maze grid
            if not (0 <= enemy_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= enemy_grid_pos[1] < maze.actual_maze_cols and \
                    0 <= player_grid_pos[0] < maze.actual_maze_rows and \
                    0 <= player_grid_pos[1] < maze.actual_maze_cols):
                # print(f"Pathfinding: Invalid grid positions. Enemy: {enemy_grid_pos}, Player: {player_grid_pos}")
                self.path = []
                return

            # Check if target is a wall, if so, try to find nearest path cell (simplification: just clear path for now)
            if maze.grid[player_grid_pos[0]][player_grid_pos[1]] != 0:
                # print(f"Pathfinding: Player target {player_grid_pos} is a wall. Clearing path.")
                self.path = [] # Target is a wall, clear path or find alternative
                return


            # print(f"Recalculating path from {enemy_grid_pos} to {player_grid_pos}")
            # Path is a list of (row, col) grid cells
            grid_path = a_star_search(maze.grid, enemy_grid_pos, player_grid_pos, maze.actual_maze_rows, maze.actual_maze_cols)

            if grid_path and len(grid_path) > 1: # Need at least current and next cell
                # Convert grid path to pixel waypoints (centers of cells)
                self.path = [self._grid_to_pixel_center(r, c, game_area_x_offset) for r, c in grid_path]
                self.current_path_index = 1 # Start moving towards the second waypoint (first is current cell)
                # print(f"Path found: {self.path}")
            else:
                self.path = []
                # print("No path found or path too short.")
        
        # If no path, enemy might revert to simpler behavior (e.g., hold position or simple chase)
        if not self.path and player_pos_pixels:
            # Fallback: simple turn towards player if very close, but don't move if no path
            dx = player_pos_pixels[0] - self.x
            dy = player_pos_pixels[1] - self.y
            self.angle = math.degrees(math.atan2(dy, dx))


    def _update_movement_along_path(self, maze, game_area_x_offset=0):
        if not self.path or self.current_path_index >= len(self.path):
            # No path to follow, or path completed
            # Enemy can stop, or revert to a simpler movement if desired
            return

        target_waypoint_pixels = self.path[self.current_path_index]
        dx = target_waypoint_pixels[0] - self.x
        dy = target_waypoint_pixels[1] - self.y
        distance_to_waypoint = math.hypot(dx, dy)

        if distance_to_waypoint < self.WAYPOINT_THRESHOLD:
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                self.path = [] # Path completed
                return
            # Update target for the next iteration
            target_waypoint_pixels = self.path[self.current_path_index]
            dx = target_waypoint_pixels[0] - self.x
            dy = target_waypoint_pixels[1] - self.y
            distance_to_waypoint = math.hypot(dx, dy)


        if distance_to_waypoint > 0: # Avoid division by zero
            self.angle = math.degrees(math.atan2(dy, dx)) # Orient towards waypoint
            
            move_x_component = (dx / distance_to_waypoint) * self.speed
            move_y_component = (dy / distance_to_waypoint) * self.speed

            # Basic boundary checks (should ideally not be needed if path is valid)
            next_x = self.x + move_x_component
            next_y = self.y + move_y_component
            
            # Update position
            self.x = next_x
            self.y = next_y

        # Keep enemy within game boundaries (this is a simplified boundary check)
        # More robust boundary checks might be needed if using collision_rect
        half_width = self.rect.width / 2 if self.rect else TILE_SIZE * 0.35
        half_height = self.rect.height / 2 if self.rect else TILE_SIZE * 0.35
        
        min_x_bound = game_area_x_offset + half_width
        max_x_bound = WIDTH - half_width
        min_y_bound = half_height
        max_y_bound = GAME_PLAY_AREA_HEIGHT - half_height

        self.x = max(min_x_bound, min(self.x, max_x_bound))
        self.y = max(min_y_bound, min(self.y, max_y_bound))
        
        if self.rect: # Ensure rect is updated for drawing
             self.rect.center = (int(self.x), int(self.y))
        if self.collision_rect:
             self.collision_rect.center = self.rect.center


    def shoot(self, direct_angle_to_target): # Modified to accept a specific angle
        if not self.alive:
            return

        rad_fire_angle = math.radians(direct_angle_to_target) # Use the direct angle for shooting
        tip_offset_distance = self.rect.width / 2 if self.rect else TILE_SIZE * 0.35
        
        fire_origin_x = self.x + math.cos(rad_fire_angle) * tip_offset_distance
        fire_origin_y = self.y + math.sin(rad_fire_angle) * tip_offset_distance
        
        new_bullet = Bullet(
            x=fire_origin_x, y=fire_origin_y, angle=direct_angle_to_target, # Use direct_angle_to_target
            speed=ENEMY_BULLET_SPEED,
            lifetime=ENEMY_BULLET_LIFETIME,
            size=self.enemy_bullet_size,
            color=ENEMY_BULLET_COLOR,
            damage=ENEMY_BULLET_DAMAGE
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

    def draw(self, surface):
        if self.alive:
            surface.blit(self.image, self.rect)
            # For debugging path:
            # if self.path:
            #     for i in range(self.current_path_index -1, len(self.path) -1):
            #         if i >= 0 and i+1 < len(self.path):
            #             start_p = self.path[i]
            #             end_p = self.path[i+1]
            #             pygame.draw.line(surface, (255, 0, 255), start_p, end_p, 1)
            #     if self.current_path_index < len(self.path):
            #          pygame.draw.circle(surface, (0,255,0), (int(self.path[self.current_path_index][0]), int(self.path[self.current_path_index][1])), 3)


        self.bullets.draw(surface)