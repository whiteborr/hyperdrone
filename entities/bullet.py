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
        self.angle = float(angle)
        self.speed = float(speed)
        self.lifetime = int(lifetime)
        self.size = int(size) 
        self.color = color
        self.damage = int(damage)
        self.max_bounces = int(max_bounces)
        self.bounces_done = 0
        self.max_pierces = int(max_pierces)
        self.pierces_done = 0
        self.can_pierce_walls = can_pierce_walls
        self.alive = True

        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def update(self, maze=None, game_area_x_offset=0):
        if not self.alive:
            self.kill()
            return

        prev_x, prev_y = self.x, self.y

        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return

        if not self.can_pierce_walls:
            wall_hit = False
            if maze:
                bullet_diameter = self.size * 2
                if maze.is_wall(self.x, self.y, bullet_diameter, bullet_diameter):
                    wall_hit = True
            
            if wall_hit:
                if self.bounces_done < self.max_bounces:
                    self.x, self.y = prev_x, prev_y 
                    
                    bullet_diameter = self.size * 2 
                    hit_x_wall = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
                    hit_y_wall = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)

                    bounced_this_frame = False
                    if hit_x_wall and not hit_y_wall: 
                        self.dx *= -1
                        self.angle = (180 - self.angle) % 360
                        bounced_this_frame = True
                    elif hit_y_wall and not hit_x_wall: 
                        self.dy *= -1
                        self.angle = (-self.angle) % 360
                        bounced_this_frame = True
                    
                    if not bounced_this_frame and (hit_x_wall and hit_y_wall): # Corner hit, simple reverse
                        self.dx *= -1
                        self.dy *= -1
                        self.angle = (self.angle + 180) % 360
                    
                    self.bounces_done += 1
                    self.x += self.dx * 0.1 
                    self.y += self.dy * 0.1
                    self.rect.center = (int(self.x), int(self.y))
                else:
                    self.alive = False
                return 

        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH # Use gs.WIDTH if imported and used consistently
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT # Use gs.GAME_PLAY_AREA_HEIGHT

        if self.rect.left < min_x_bound or self.rect.right > max_x_bound or \
           self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
            if self.bounces_done < self.max_bounces: 
                self.x, self.y = prev_x, prev_y 
                
                bounced_on_boundary = False
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360
                    bounced_on_boundary = True
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
                    self.dy *= -1
                    # Adjust angle correctly if it already bounced on x-axis
                    self.angle = (-self.angle) % 360 if not bounced_on_boundary else (self.angle + 180 + (-2 * self.angle)) % 360
                    bounced_on_boundary = True # Ensure this is set
                
                if bounced_on_boundary:
                    self.bounces_done += 1
                    self.x += self.dx # Move slightly after bounce to clear boundary
                    self.y += self.dy
                    self.rect.center = (int(self.x), int(self.y))
                else: 
                    self.alive = False # Should not happen if boundary conditions are met
            else:
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
        self.angle = float(initial_angle) 
        self.target_angle = float(initial_angle) 
        self.speed = MISSILE_SPEED
        self.lifetime = MISSILE_LIFETIME
        self.damage = damage
        self.enemies_group = enemies_group 
        self.target = None 
        self.turn_rate = MISSILE_TURN_RATE
        self.alive = True

        self.original_image_surface = pygame.Surface([MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5], pygame.SRCALPHA)
        points = [
            (MISSILE_SIZE * 0.75, 0),                            
            (0, MISSILE_SIZE * 2.5),                             
            (MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5)             
        ]
        pygame.draw.polygon(self.original_image_surface, MISSILE_COLOR, points)
        self.original_image = pygame.transform.rotate(self.original_image_surface, -90) 
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        self.is_sliding = False
        self.slide_direction_attempts = 0
        self.MAX_SLIDE_ATTEMPTS = 3 

    def _find_target(self):
        if not self.enemies_group:
            return None
        closest_enemy = None
        min_dist_sq = float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive:
                continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        return closest_enemy

    def _attempt_slide(self, maze, next_x, next_y, direct_rad_angle):
        collision_width = self.rect.width * 0.6 
        collision_height = self.rect.height * 0.6
        
        slide_options = []
        current_rad_angle = math.radians(self.angle) 
        
        deflection_angles_deg = [30, 60, 45, 75, 90] 
        for da_deg in deflection_angles_deg:
            angle_left_rad = current_rad_angle + math.radians(da_deg)
            angle_right_rad = current_rad_angle - math.radians(da_deg)
            slide_options.append((math.cos(angle_left_rad) * self.speed, math.sin(angle_left_rad) * self.speed))
            slide_options.append((math.cos(angle_right_rad) * self.speed, math.sin(angle_right_rad) * self.speed))

        for s_dx, s_dy in slide_options:
            slide_next_x = self.x + s_dx
            slide_next_y = self.y + s_dy
            check_further_x = self.x + s_dx * 1.5 
            check_further_y = self.y + s_dy * 1.5

            if not maze.is_wall(slide_next_x, slide_next_y, collision_width, collision_height) and \
               not maze.is_wall(check_further_x, check_further_y, collision_width, collision_height) :
                self.angle = math.degrees(math.atan2(s_dy, s_dx)) 
                return s_dx, s_dy
        
        return None 

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0):
        if not self.alive:
            self.kill()
            return

        if enemies_group_updated is not None: 
            self.enemies_group = enemies_group_updated

        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target()
            self.is_sliding = False 

        effective_angle_rad = math.radians(self.angle) 

        if self.target:
            target_x, target_y = self.target.rect.center
            dx_to_target = target_x - self.x
            dy_to_target = target_y - self.y
            self.target_angle = math.degrees(math.atan2(dy_to_target, dx_to_target))

            if not self.is_sliding: 
                current_angle_norm = self.angle % 360
                target_angle_norm = (self.target_angle + 360) % 360
                angle_diff = target_angle_norm - current_angle_norm
                if angle_diff > 180: angle_diff -= 360
                elif angle_diff < -180: angle_diff += 360
                turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff))
                self.angle = (self.angle + turn_this_frame) % 360
            
            effective_angle_rad = math.radians(self.angle)

        potential_dx = math.cos(effective_angle_rad) * self.speed
        potential_dy = math.sin(effective_angle_rad) * self.speed
        next_x = self.x + potential_dx
        next_y = self.y + potential_dy

        final_dx, final_dy = potential_dx, potential_dy

        if maze:
            collision_width = self.rect.width * 0.7 
            collision_height = self.rect.height * 0.7

            if maze.is_wall(next_x, next_y, collision_width, collision_height):
                if self.slide_direction_attempts < self.MAX_SLIDE_ATTEMPTS:
                    slide_movement = self._attempt_slide(maze, next_x, next_y, effective_angle_rad)
                    if slide_movement:
                        final_dx, final_dy = slide_movement
                        self.is_sliding = True 
                        self.slide_direction_attempts += 1
                    else:
                        self.alive = False 
                else: 
                     self.alive = False
            else: 
                self.is_sliding = False 
                self.slide_direction_attempts = 0
        
        if self.alive:
            self.x += final_dx
            self.y += final_dy
        else:
            self.kill()
            return

        self.image = pygame.transform.rotate(self.original_image, -self.angle) 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        self.lifetime -= 1
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH # Use gs.WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT # Use gs.GAME_PLAY_AREA_HEIGHT
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
        self.player_ref = player_ref
        self.locked_target_enemy = initial_target_enemy_ref
        self.maze_ref = maze_ref 
        self.game_area_x_offset = game_area_x_offset
        
        self.damage = damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_elapsed = 0
        self.alive = True 
        self.color = color_override if color_override is not None else gs.LIGHTNING_COLOR # Use override or default
        self.damage_applied = False

        self.current_start_pos = self.player_ref.rect.center
        self.current_target_pos = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.current_target_pos)
        
        # Initial rect calculation based on start/end points for collision detection
        # The visual representation will be drawn directly, not blitted from self.image
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        rect_width = max(1, int(max_x - min_x)) # Ensure width is at least 1
        rect_height = max(1, int(max_y - min_y)) # Ensure height is at least 1
        self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA) # Transparent surface
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))


    def _pixel_to_grid_coords(self, pixel_x, pixel_y):
        if not self.maze_ref: return None, None # Guard against no maze_ref
        col = int((pixel_x - self.maze_ref.game_area_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _get_wall_collision_point(self, start_point, end_point, steps_override=None):
        if not self.maze_ref or not hasattr(self.maze_ref, 'grid') or not self.maze_ref.grid:
            return end_point

        dx_total = end_point[0] - start_point[0]
        dy_total = end_point[1] - start_point[1]
        distance = math.hypot(dx_total, dy_total)

        if distance == 0:
            return start_point

        dir_x = dx_total / distance
        dir_y = dy_total / distance
        
        step_size = TILE_SIZE / 4 # Increased granularity for collision checking
        num_steps = steps_override if steps_override is not None else int(distance / step_size) + 1
        if num_steps <= 0 : num_steps = 1

        current_x, current_y = start_point
        last_safe_x, last_safe_y = start_point

        for i in range(num_steps):
            grid_r, grid_c = self._pixel_to_grid_coords(current_x, current_y)

            if grid_r is None: # Should not happen if maze_ref exists
                return last_safe_x, last_safe_y

            if not (0 <= grid_r < self.maze_ref.actual_maze_rows and \
                    0 <= grid_c < self.maze_ref.actual_maze_cols):
                return last_safe_x, last_safe_y 

            if self.maze_ref.grid[grid_r][grid_c] == 1: 
                return last_safe_x, last_safe_y 
            
            last_safe_x, last_safe_y = current_x, current_y
            
            if i < num_steps - 1:
                current_x += dir_x * step_size
                current_y += dir_y * step_size
                if math.hypot(current_x - start_point[0], current_y - start_point[1]) > distance:
                    grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
                    if grid_r_end is not None and \
                       (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
                        0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
                        self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
                        return last_safe_x, last_safe_y 
                    return end_point 
        
        grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
        if grid_r_end is not None and \
           (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
            0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
            self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
            return last_safe_x, last_safe_y 
            
        return end_point

    def _calculate_potential_target_pos(self):
        if self.locked_target_enemy and self.locked_target_enemy.alive:
            return self.locked_target_enemy.rect.center
        else: 
            self.locked_target_enemy = None 
            # Use player_ref's angle (which could be a drone or the MazeGuardian boss)
            angle_rad = math.radians(self.player_ref.angle)
            return (
                self.current_start_pos[0] + math.cos(angle_rad) * gs.LIGHTNING_ZAP_RANGE,
                self.current_start_pos[1] + math.sin(angle_rad) * gs.LIGHTNING_ZAP_RANGE
            )

    def _update_rect_for_collision(self):
        """Updates the self.rect to encompass the current lightning bolt for collision purposes."""
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Add padding based on lightning thickness for better collision coverage
        padding = gs.LIGHTNING_BASE_THICKNESS 
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
        # self.image is not used for blitting, so its size doesn't need to match rect exactly.
        # However, if you were to blit self.image for debug, you might want to resize it.
        # self.image = pygame.transform.scale(self.image, (rect_width, rect_height))


    def update(self, current_time): 
        if not self.alive or not self.player_ref.alive:
            self.alive = False
            self.kill()
            return

        self.frames_elapsed += 1
        if self.frames_elapsed >= self.lifetime_frames:
            self.alive = False
            self.kill()
            return

        self.current_start_pos = self.player_ref.rect.center
        potential_target_pos = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, potential_target_pos)
        self._update_rect_for_collision() # Update rect for collision detection

    def _draw_lightning_bolt_effect(self, surface, p1, p2, base_bolt_color, alpha):
        """Draws a multi-layered, jagged lightning bolt."""
        
        num_segments = gs.LIGHTNING_SEGMENTS
        outer_max_offset = gs.LIGHTNING_MAX_OFFSET
        outer_thickness = gs.LIGHTNING_BASE_THICKNESS
        
        inner_core_thickness = max(1, int(outer_thickness * gs.LIGHTNING_CORE_THICKNESS_RATIO))
        inner_max_offset = outer_max_offset * gs.LIGHTNING_CORE_OFFSET_RATIO
        core_color = gs.LIGHTNING_CORE_COLOR
        
        branch_chance = gs.LIGHTNING_BRANCH_CHANCE
        branch_max_segments = gs.LIGHTNING_BRANCH_MAX_SEGMENTS
        branch_max_offset = gs.LIGHTNING_BRANCH_MAX_OFFSET
        branch_thickness = max(1, int(inner_core_thickness * gs.LIGHTNING_BRANCH_THICKNESS_RATIO))

        dx_total = p2[0] - p1[0]
        dy_total = p2[1] - p1[1]
        
        dist_total = math.hypot(dx_total, dy_total)
        if dist_total == 0: return

        # Normalized perpendicular vector
        perp_dx = -dy_total / dist_total
        perp_dy = dx_total / dist_total

        # --- Main Bolt Path Generation (Outer and Inner) ---
        main_points_outer = [p1]
        main_points_inner = [p1]

        for i in range(1, num_segments + 1): # Iterate to create num_segments
            t = i / num_segments # Progress along the main line segment
            
            base_x = p1[0] + dx_total * t
            base_y = p1[1] + dy_total * t

            # Common random factor for this segment to make outer and inner somewhat correlated but still distinct
            segment_rand_factor = (random.random() - 0.5) * 2 
            # Sinusoidal modulation for more natural bulging in the middle
            mid_factor = math.sin(t * math.pi) 

            # Outer bolt point
            offset_outer = outer_max_offset * segment_rand_factor * mid_factor
            # Corrected line:
            main_points_outer.append((base_x + perp_dx * offset_outer, base_y + perp_dy * offset_outer))
            
            # Inner core point (less offset)
            offset_inner = inner_max_offset * segment_rand_factor * mid_factor # Can use a different rand_factor if desired
            main_points_inner.append((base_x + perp_dx * offset_inner, base_y + perp_dy * offset_inner))

        # Ensure the very last point is exactly p2 for both
        main_points_outer[-1] = p2
        main_points_inner[-1] = p2
        
        # --- Draw Outer Glow/Main Bolt ---
        outer_color_with_alpha = (*base_bolt_color[:3], int(alpha * 0.65)) # Outer part more transparent
        if len(main_points_outer) > 1:
            pygame.draw.lines(surface, outer_color_with_alpha, False, main_points_outer, outer_thickness)

        # --- Draw Inner Core Bolt ---
        inner_color_with_alpha = (*core_color[:3], alpha) # Core is brighter
        if len(main_points_inner) > 1 and inner_core_thickness > 0:
            pygame.draw.lines(surface, inner_color_with_alpha, False, main_points_inner, inner_core_thickness)

        # --- Draw Branches ---
        for i in range(len(main_points_inner) - 1): # Iterate through segments of the core bolt
            if random.random() < branch_chance:
                branch_start_point = main_points_inner[i]
                
                # Branch direction: roughly perpendicular to the segment, with some randomness
                seg_dx = main_points_inner[i+1][0] - branch_start_point[0]
                seg_dy = main_points_inner[i+1][1] - branch_start_point[1]
                seg_len = math.hypot(seg_dx, seg_dy)
                if seg_len == 0: continue

                # Perpendicular to current segment
                branch_perp_dx = -seg_dy / seg_len
                branch_perp_dy = seg_dx / seg_len
                
                # Add some randomness to the main direction of the branch
                angle_perturb = random.uniform(-math.pi / 4, math.pi / 4) # Deviate up to 45 degrees
                c, s = math.cos(angle_perturb), math.sin(angle_perturb)
                final_branch_dir_x = branch_perp_dx * c - branch_perp_dy * s
                final_branch_dir_y = branch_perp_dx * s + branch_perp_dy * c
                
                # Ensure branches tend to go outwards
                if random.random() < 0.5:
                    final_branch_dir_x *= -1
                    final_branch_dir_y *= -1

                branch_points = [branch_start_point]
                current_branch_pos = list(branch_start_point)
                branch_segment_len = dist_total / num_segments * 0.7 # Branches are shorter

                for j in range(random.randint(1, branch_max_segments)):
                    # Move along the main branch direction
                    current_branch_pos[0] += final_branch_dir_x * branch_segment_len * (1 - j*0.1) # Branches get shorter
                    current_branch_pos[1] += final_branch_dir_y * branch_segment_len * (1 - j*0.1)
                    
                    # Add jaggedness to the branch segment
                    branch_offset_mag = random.uniform(-branch_max_offset, branch_max_offset) * math.sin(((j+1)/branch_max_segments) * math.pi)
                    # Perpendicular to the branch's main direction for this segment's jaggedness
                    # (using the overall lightning bolt's perpendicular for simplicity here, or could recalculate for branch dir)
                    branch_jag_x = perp_dx * branch_offset_mag 
                    branch_jag_y = perp_dy * branch_offset_mag
                    
                    branch_points.append((current_branch_pos[0] + branch_jag_x, current_branch_pos[1] + branch_jag_y))
                    if len(branch_points) > branch_max_segments : break


                if len(branch_points) > 1:
                    branch_alpha = int(alpha * 0.8) # Branches slightly less opaque
                    branch_color_with_alpha = (*core_color[:3], branch_alpha) # Branches use core color
                    pygame.draw.lines(surface, branch_color_with_alpha, False, branch_points, branch_thickness)


    def draw(self, surface): 
        if self.alive:
            current_alpha_perc = 1.0 - (self.frames_elapsed / self.lifetime_frames)
            # Make fade out quicker or more pronounced
            current_alpha = int(255 * (current_alpha_perc ** 2.0)) # Faster fade with power 2.0
            current_alpha = int(max(0, min(255, current_alpha))) 
            
            if current_alpha > 5: # Lower threshold to draw for longer, but alpha handles fade
                self._draw_lightning_bolt_effect(surface, self.current_start_pos, self.current_target_pos, 
                                                 self.color, # This is LIGHTNING_COLOR from game_settings
                                                 current_alpha)

