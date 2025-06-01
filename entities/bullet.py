# entities/bullet.py

import math
import random
import pygame

import game_settings as gs 
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, # Original lightning settings
    # New visual settings for lightning will be accessed via gs.LIGHTNING_...
    WIDTH, GAME_PLAY_AREA_HEIGHT, TILE_SIZE
)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle) # Angle in degrees
        self.speed = float(speed)
        self.lifetime = int(lifetime) # In frames
        self.size = int(size) # Radius of the bullet
        self.color = color
        self.damage = int(damage)
        self.max_bounces = int(max_bounces)
        self.bounces_done = 0
        self.max_pierces = int(max_pierces)
        self.pierces_done = 0
        self.can_pierce_walls = can_pierce_walls # If true, bullet goes through walls
        self.alive = True

        # Create the bullet's visual representation
        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA) # Diameter for surface
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size) # Draw circle centered
        self.rect = self.image.get_rect(center=(self.x, self.y))

        # Pre-calculate movement components
        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def update(self, maze=None, game_area_x_offset=0):
        if not self.alive:
            self.kill() # Ensure it's removed from groups if not alive
            return

        prev_x, prev_y = self.x, self.y # Store previous position for bounce logic

        # Update position
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

        # Decrease lifetime
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return

        # Wall collision and bouncing logic
        if not self.can_pierce_walls: # Only check wall collision if not piercing walls
            wall_hit = False
            if maze:
                # Use bullet diameter for collision check with maze.is_wall
                bullet_diameter = self.size * 2 
                if maze.is_wall(self.x, self.y, bullet_diameter, bullet_diameter):
                    wall_hit = True
            
            if wall_hit:
                if self.bounces_done < self.max_bounces:
                    self.x, self.y = prev_x, prev_y # Revert to pre-collision position
                    
                    # More precise bounce reflection (simple version)
                    # Check which axis primarily caused collision to reflect velocity component
                    # This is a basic approach; more complex physics could be used.
                    bullet_diameter = self.size * 2 # Recalculate for clarity
                    hit_x_wall = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
                    hit_y_wall = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)

                    bounced_this_frame = False
                    if hit_x_wall and not hit_y_wall: # Primarily hit a vertical wall segment
                        self.dx *= -1
                        self.angle = (180 - self.angle) % 360
                        bounced_this_frame = True
                    elif hit_y_wall and not hit_x_wall: # Primarily hit a horizontal wall segment
                        self.dy *= -1
                        self.angle = (-self.angle) % 360
                        bounced_this_frame = True
                    
                    # If it's a corner hit (both would be true), a simple reversal might be okay,
                    # or more complex reflection logic. For now, this handles distinct axis hits.
                    if not bounced_this_frame and (hit_x_wall and hit_y_wall): # Corner hit, simple reverse
                        self.dx *= -1
                        self.dy *= -1
                        self.angle = (self.angle + 180) % 360
                    
                    self.bounces_done += 1
                    # Move slightly after bounce to ensure it clears the wall
                    self.x += self.dx * 0.1 
                    self.y += self.dy * 0.1
                    self.rect.center = (int(self.x), int(self.y))
                else: # No bounces left
                    self.alive = False
                return # Collision handled (bounced or died)
            

        # Screen boundary checks (bullets die if they go off-screen, unless they bounce)
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH # Use gs.WIDTH if imported and used consistently
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT # Use gs.GAME_PLAY_AREA_HEIGHT

        if self.rect.left < min_x_bound or self.rect.right > max_x_bound or \
           self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
            # Handle screen boundary bounce if applicable
            if self.bounces_done < self.max_bounces: 
                self.x, self.y = prev_x, prev_y # Revert position
                
                bounced_on_boundary = False
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360 # Reflect angle for horizontal bounce
                    bounced_on_boundary = True
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
                    self.dy *= -1
                    # Adjust angle correctly if it already bounced on x-axis this frame
                    self.angle = (-self.angle) % 360 if not bounced_on_boundary else (self.angle + 180 + (-2 * self.angle)) % 360
                    bounced_on_boundary = True # Ensure this is set
                
                if bounced_on_boundary:
                    self.bounces_done += 1
                    self.x += self.dx # Move slightly after bounce to clear boundary
                    self.y += self.dy
                    self.rect.center = (int(self.x), int(self.y))
                else: 
                    # This case should ideally not be reached if boundary conditions are met and bounce occurs
                    self.alive = False 
            else: # No bounces left, bullet dies
                self.alive = False
            return
    
    def draw(self, surface): 
        if self.alive:
            surface.blit(self.image, self.rect)

class Missile(pygame.sprite.Sprite):
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(initial_angle) # Current angle of the missile
        self.target_angle = float(initial_angle) # Angle towards the current target
        self.speed = MISSILE_SPEED
        self.lifetime = MISSILE_LIFETIME
        self.damage = damage
        self.enemies_group = enemies_group # Reference to the group of enemies for targeting
        self.target = None # Current enemy target
        self.turn_rate = MISSILE_TURN_RATE # How quickly the missile can turn (degrees per frame)
        self.alive = True

        # Create missile sprite (e.g., a small triangle)
        self.original_image_surface = pygame.Surface([MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5], pygame.SRCALPHA)
        # Define points for a triangular shape pointing "up" (0 degrees in Pygame's default orientation)
        points = [
            (MISSILE_SIZE * 0.75, 0),                            # Tip
            (0, MISSILE_SIZE * 2.5),                             # Bottom-left
            (MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5)             # Bottom-right
        ]
        pygame.draw.polygon(self.original_image_surface, MISSILE_COLOR, points)
        # Rotate the original sprite so that 0 degrees points right (standard for math.atan2)
        self.original_image = pygame.transform.rotate(self.original_image_surface, -90) 
        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Initial rotation
        self.rect = self.image.get_rect(center=(self.x, self.y))

        # For wall sliding behavior
        self.is_sliding = False
        self.slide_direction_attempts = 0
        self.MAX_SLIDE_ATTEMPTS = 3 # How many times to try sliding before giving up

    def _find_target(self):
        """Finds the closest living enemy."""
        if not self.enemies_group:
            return None
        closest_enemy = None
        min_dist_sq = float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive: # Check if enemy is alive
                continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        return closest_enemy

    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle):
        """Attempts to find a sliding direction along a wall."""
        collision_width = self.rect.width * 0.6 # Use a smaller collision box for sliding
        collision_height = self.rect.height * 0.6
        
        slide_options = []
        current_rad_angle = math.radians(self.angle) # Current actual facing angle
        
        # Try deflecting by various angles relative to current facing
        deflection_angles_deg = [30, 60, 45, 75, 90] # Angles to try deflecting by
        for da_deg in deflection_angles_deg:
            # Try deflecting left and right
            angle_left_rad = current_rad_angle + math.radians(da_deg)
            angle_right_rad = current_rad_angle - math.radians(da_deg)
            slide_options.append((math.cos(angle_left_rad) * self.speed, math.sin(angle_left_rad) * self.speed))
            slide_options.append((math.cos(angle_right_rad) * self.speed, math.sin(angle_right_rad) * self.speed))

        for s_dx, s_dy in slide_options:
            slide_next_x = self.x + s_dx
            slide_next_y = self.y + s_dy
            # Check a bit further along the slide path to ensure it's clear
            check_further_x = self.x + s_dx * 1.5 
            check_further_y = self.y + s_dy * 1.5

            if not maze.is_wall(slide_next_x, slide_next_y, collision_width, collision_height) and \
               not maze.is_wall(check_further_x, check_further_y, collision_width, collision_height) :
                self.angle = math.degrees(math.atan2(s_dy, s_dx)) # Update missile's angle to slide direction
                return s_dx, s_dy # Return the valid slide movement vector
        
        return None # No valid slide direction found

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0):
        if not self.alive:
            self.kill()
            return

        if enemies_group_updated is not None: # Update enemy list if provided
            self.enemies_group = enemies_group_updated

        # Re-target if no target or current target is dead
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target()
            self.is_sliding = False # Reset sliding state when re-targeting

        effective_angle_rad = math.radians(self.angle) # Default to current angle

        # Homing logic
        if self.target:
            target_x, target_y = self.target.rect.center
            dx_to_target = target_x - self.x
            dy_to_target = target_y - self.y
            self.target_angle = math.degrees(math.atan2(dy_to_target, dx_to_target))

            if not self.is_sliding: # Only adjust homing if not currently sliding along a wall
                current_angle_norm = self.angle % 360
                target_angle_norm = (self.target_angle + 360) % 360 # Normalize target angle
                
                angle_diff = target_angle_norm - current_angle_norm
                # Ensure shortest turn direction
                if angle_diff > 180: angle_diff -= 360
                elif angle_diff < -180: angle_diff += 360
                
                turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff))
                self.angle = (self.angle + turn_this_frame) % 360
            
            effective_angle_rad = math.radians(self.angle) # Update effective angle after turning

        # Calculate potential next position
        potential_dx = math.cos(effective_angle_rad) * self.speed
        potential_dy = math.sin(effective_angle_rad) * self.speed
        next_x = self.x + potential_dx
        next_y = self.y + potential_dy

        final_dx, final_dy = potential_dx, potential_dy # Assume direct movement initially

        # Wall collision and sliding logic
        if maze:
            collision_width = self.rect.width * 0.7 # Use a slightly smaller collision box for missiles
            collision_height = self.rect.height * 0.7

            if maze.is_wall(next_x, next_y, collision_width, collision_height):
                if self.slide_direction_attempts < self.MAX_SLIDE_ATTEMPTS:
                    slide_movement = self._attempt_slide(maze, next_x, next_y, effective_angle_rad)
                    if slide_movement:
                        final_dx, final_dy = slide_movement
                        self.is_sliding = True 
                        self.slide_direction_attempts += 1
                    else: # Failed to find a slide path
                        self.alive = False 
                else: # Max slide attempts reached
                     self.alive = False
            else: # No collision, not sliding
                self.is_sliding = False 
                self.slide_direction_attempts = 0 # Reset attempts if path is clear
        
        # Apply movement if still alive
        if self.alive:
            self.x += final_dx
            self.y += final_dy
        else:
            self.kill()
            return

        # Rotate sprite and update rect
        self.image = pygame.transform.rotate(self.original_image, -self.angle) # Pygame rotates counter-clockwise
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        # Lifetime and boundary checks
        self.lifetime -= 1
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH 
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT 
        if self.lifetime <= 0 or \
           not (min_x_bound < self.rect.centerx < max_x_bound and 
                min_y_bound < self.rect.centery < max_y_bound):
            self.alive = False
            self.kill()
            
    def draw(self, surface):
        if self.alive:
            surface.blit(self.image, self.rect)

class LightningZap(pygame.sprite.Sprite):
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None): 
        super().__init__()
        self.player_ref = player_ref # The entity firing the lightning (PlayerDrone or MazeGuardian)
        self.locked_target_enemy = initial_target_enemy_ref # Initial enemy target, can be None
        self.maze_ref = maze_ref # Reference to the maze for wall collision
        self.game_area_x_offset = game_area_x_offset
        
        self.damage = damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_elapsed = 0
        self.alive = True 
        self.color = color_override if color_override is not None else gs.LIGHTNING_COLOR 
        self.damage_applied = False # Flag to ensure damage is applied only once per zap

        # Initial positions for the bolt
        self.current_start_pos = self.player_ref.rect.center
        self.current_target_pos = self._calculate_potential_target_pos() # Calculate initial end point
        # Adjust target position if it hits a wall
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.current_target_pos)
        
        # The rect for LightningZap is primarily for group collision detection.
        # The visual representation is drawn directly.
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        rect_width = max(1, int(max_x - min_x)) 
        rect_height = max(1, int(max_y - min_y)) 
        self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA) # Transparent surface
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))


    def _pixel_to_grid_coords(self, pixel_x, pixel_y):
        """Converts absolute pixel coordinates to grid coordinates relative to the maze."""
        if not self.maze_ref: return None, None 
        # game_area_x_offset is already part of maze_ref if it's the procedural Maze,
        # or self.game_area_x_offset if it's MazeChapter2 (passed from GameController)
        current_maze_x_offset = getattr(self.maze_ref, 'game_area_x_offset', self.game_area_x_offset)

        col = int((pixel_x - current_maze_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _get_wall_collision_point(self, start_point, end_point, steps_override=None):
        """
        Checks for wall collision along a line segment from start_point to end_point.
        Returns the point of collision or end_point if no collision.
        """
        if not self.maze_ref or not hasattr(self.maze_ref, 'grid') or not self.maze_ref.grid:
            return end_point # No maze or grid to check against

        dx_total = end_point[0] - start_point[0]
        dy_total = end_point[1] - start_point[1]
        distance = math.hypot(dx_total, dy_total)

        if distance == 0: return start_point

        dir_x = dx_total / distance
        dir_y = dy_total / distance
        
        step_size = TILE_SIZE / 4 # Check every quarter tile for collision
        num_steps = steps_override if steps_override is not None else int(distance / step_size) + 1
        if num_steps <= 0 : num_steps = 1

        current_x, current_y = start_point
        last_safe_x, last_safe_y = start_point

        for i in range(num_steps):
            grid_r, grid_c = self._pixel_to_grid_coords(current_x, current_y)

            if grid_r is None: return last_safe_x, last_safe_y # Should not happen if maze_ref exists

            # Check boundaries
            if not (0 <= grid_r < self.maze_ref.actual_maze_rows and \
                    0 <= grid_c < self.maze_ref.actual_maze_cols):
                return last_safe_x, last_safe_y # Hit edge of map

            # Check for wall (tile type 1). '0' and 'C' are walkable.
            if self.maze_ref.grid[grid_r][grid_c] == 1: 
                return last_safe_x, last_safe_y # Hit a wall tile
            
            last_safe_x, last_safe_y = current_x, current_y # This point is safe
            
            # Move to next check point, but don't overshoot the original end_point
            if i < num_steps - 1:
                current_x += dir_x * step_size
                current_y += dir_y * step_size
                # If we've moved past the original intended distance, check the original end_point directly
                if math.hypot(current_x - start_point[0], current_y - start_point[1]) > distance:
                    grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
                    if grid_r_end is not None and \
                       (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
                        0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
                        self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
                        return last_safe_x, last_safe_y # Original end was a wall
                    return end_point # Original end was clear
        
        # Final check at the exact end_point if all steps were clear
        grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
        if grid_r_end is not None and \
           (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
            0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
            self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
            return last_safe_x, last_safe_y # Original end was a wall
            
        return end_point # Path to end_point is clear

    def _calculate_potential_target_pos(self):
        """Calculates the potential end point of the lightning, either an enemy or max range."""
        if self.locked_target_enemy and self.locked_target_enemy.alive:
            return self.locked_target_enemy.rect.center
        else: # If no locked target, fire in player's facing direction up to max range
            self.locked_target_enemy = None # Clear target if it died
            angle_rad = math.radians(self.player_ref.angle) # Use player's current angle
            return (
                self.current_start_pos[0] + math.cos(angle_rad) * gs.LIGHTNING_ZAP_RANGE,
                self.current_start_pos[1] + math.sin(angle_rad) * gs.LIGHTNING_ZAP_RANGE
            )

    def _update_rect_for_collision(self):
        """Updates self.rect to encompass the current lightning bolt for broad-phase collision."""
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        padding = gs.LIGHTNING_BASE_THICKNESS # Add padding based on visual thickness
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding

        rect_width = max(1, int(max_x - min_x))
        rect_height = max(1, int(max_y - min_y))
        
        self.rect.x = int(min_x)
        self.rect.y = int(min_y)
        self.rect.width = rect_width
        self.rect.height = rect_height


    def update(self, current_time_ms): # current_time_ms is not directly used here, but good for consistency
        """Updates the lightning zap's state and position each frame."""
        if not self.alive or not self.player_ref.alive: # If player died, zap should fade
            self.alive = False
            self.kill()
            return

        self.frames_elapsed += 1
        if self.frames_elapsed >= self.lifetime_frames:
            self.alive = False
            self.kill()
            return

        # Update start and end points (e.g., if player or target moved)
        self.current_start_pos = self.player_ref.rect.center
        potential_target_pos = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, potential_target_pos)
        self._update_rect_for_collision() # Update the bounding box for collision detection

    def _draw_lightning_bolt_effect(self, surface, p1, p2, base_bolt_color, alpha):
        """Draws a multi-layered, jagged lightning bolt between two points."""
        
        num_segments = gs.get_game_setting("LIGHTNING_SEGMENTS", 12)
        outer_max_offset = gs.get_game_setting("LIGHTNING_MAX_OFFSET", 18)
        outer_thickness = gs.get_game_setting("LIGHTNING_BASE_THICKNESS", 5)
        
        inner_core_thickness = max(1, int(outer_thickness * gs.get_game_setting("LIGHTNING_CORE_THICKNESS_RATIO", 0.4)))
        inner_max_offset = outer_max_offset * gs.get_game_setting("LIGHTNING_CORE_OFFSET_RATIO", 0.3)
        core_color = gs.LIGHTNING_CORE_COLOR # This is a tuple like (R,G,B)
        
        branch_chance = gs.get_game_setting("LIGHTNING_BRANCH_CHANCE", 0.25)
        branch_max_segments = gs.get_game_setting("LIGHTNING_BRANCH_MAX_SEGMENTS", 5)
        branch_max_offset = gs.get_game_setting("LIGHTNING_BRANCH_MAX_OFFSET", 10)
        branch_thickness = max(1, int(inner_core_thickness * gs.get_game_setting("LIGHTNING_BRANCH_THICKNESS_RATIO", 0.5)))

        dx_total = p2[0] - p1[0]
        dy_total = p2[1] - p1[1]
        
        dist_total = math.hypot(dx_total, dy_total)
        if dist_total == 0: return # Cannot draw a zero-length line

        # Normalized perpendicular vector for offsets
        perp_dx = -dy_total / dist_total
        perp_dy = dx_total / dist_total

        # --- Main Bolt Path Generation (Outer and Inner) ---
        main_points_outer = [p1]
        main_points_inner = [p1]

        for i in range(1, num_segments + 1): 
            t = i / num_segments # Progress along the main line segment (0 to 1)
            
            base_x = p1[0] + dx_total * t
            base_y = p1[1] + dy_total * t

            segment_rand_factor = (random.random() - 0.5) * 2 # Random factor between -1 and 1
            mid_factor = math.sin(t * math.pi) # Sinusoidal modulation (0 at ends, 1 at middle)

            offset_outer = outer_max_offset * segment_rand_factor * mid_factor
            main_points_outer.append((base_x + perp_dx * offset_outer, base_y + perp_dy * offset_outer))
            
            offset_inner = inner_max_offset * segment_rand_factor * mid_factor
            main_points_inner.append((base_x + perp_dx * offset_inner, base_y + perp_dy * offset_inner))

        main_points_outer[-1] = p2 # Ensure last point is exactly the target
        main_points_inner[-1] = p2
        
        # --- Draw Outer Glow/Main Bolt ---
        outer_color_with_alpha = (*base_bolt_color[:3], int(alpha * 0.65)) 
        if len(main_points_outer) > 1 and outer_thickness > 0:
            pygame.draw.lines(surface, outer_color_with_alpha, False, main_points_outer, outer_thickness)

        # --- Draw Inner Core Bolt ---
        inner_color_with_alpha = (*core_color[:3], alpha) 
        if len(main_points_inner) > 1 and inner_core_thickness > 0:
            pygame.draw.lines(surface, inner_color_with_alpha, False, main_points_inner, inner_core_thickness)

        # --- Draw Branches ---
        for i in range(len(main_points_inner) - 1): 
            if random.random() < branch_chance:
                branch_start_point = main_points_inner[i]
                
                seg_dx = main_points_inner[i+1][0] - branch_start_point[0]
                seg_dy = main_points_inner[i+1][1] - branch_start_point[1]
                seg_len = math.hypot(seg_dx, seg_dy)
                if seg_len == 0: continue

                branch_perp_dx = -seg_dy / seg_len
                branch_perp_dy = seg_dx / seg_len
                
                angle_perturb = random.uniform(-math.pi / 4, math.pi / 4)
                c, s = math.cos(angle_perturb), math.sin(angle_perturb)
                final_branch_dir_x = branch_perp_dx * c - branch_perp_dy * s
                final_branch_dir_y = branch_perp_dx * s + branch_perp_dy * c
                
                if random.random() < 0.5: # Randomly flip direction
                    final_branch_dir_x *= -1
                    final_branch_dir_y *= -1

                branch_points = [branch_start_point]
                current_branch_pos = list(branch_start_point)
                # Branches are shorter than main segments
                branch_segment_len = dist_total / num_segments * random.uniform(0.3, 0.7) 

                for j in range(random.randint(1, branch_max_segments)):
                    current_branch_pos[0] += final_branch_dir_x * branch_segment_len * (1 - (j / branch_max_segments) * 0.5) # Tapering
                    current_branch_pos[1] += final_branch_dir_y * branch_segment_len * (1 - (j / branch_max_segments) * 0.5)
                    
                    branch_offset_mag = random.uniform(-branch_max_offset, branch_max_offset) * math.sin(((j+1)/branch_max_segments) * math.pi)
                    branch_jag_x = perp_dx * branch_offset_mag 
                    branch_jag_y = perp_dy * branch_offset_mag
                    
                    branch_points.append((current_branch_pos[0] + branch_jag_x, current_branch_pos[1] + branch_jag_y))
                    if len(branch_points) > branch_max_segments : break


                if len(branch_points) > 1 and branch_thickness > 0:
                    branch_alpha = int(alpha * 0.8) 
                    branch_color_with_alpha = (*core_color[:3], branch_alpha) 
                    pygame.draw.lines(surface, branch_color_with_alpha, False, branch_points, branch_thickness)


    def draw(self, surface): 
        """Draws the lightning bolt effect."""
        if self.alive:
            # Calculate alpha based on lifetime for fade-out effect
            current_alpha_perc = 1.0 - (self.frames_elapsed / self.lifetime_frames)
            current_alpha = int(255 * (current_alpha_perc ** 1.5)) # Slightly faster fade
            current_alpha = int(max(0, min(255, current_alpha))) 
            
            if current_alpha > 5: # Only draw if somewhat visible
                self._draw_lightning_bolt_effect(surface, self.current_start_pos, self.current_target_pos, 
                                                 self.color, # Base color for the outer glow
                                                 current_alpha)

