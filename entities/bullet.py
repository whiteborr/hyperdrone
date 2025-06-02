# entities/bullet.py

import math
import random
import pygame
import os 

import game_settings as gs
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
    WIDTH, GAME_PLAY_AREA_HEIGHT, TILE_SIZE, WHITE, RED, YELLOW # Added YELLOW for sparks
)
# Ensure Particle is imported for the wall spark effect
try:
    from .particle import Particle
except ImportError:
    # Minimal placeholder if Particle class is not found
    class Particle(pygame.sprite.Sprite):
        def __init__(self, x, y, color_list, min_speed, max_speed, min_size, max_size, gravity=0.1, shrink_rate=0.1, lifetime_frames=30, base_angle_deg=None, spread_angle_deg=360, x_offset=0, y_offset=0, blast_mode=False):
            super().__init__(); self.image = pygame.Surface([max_size*2,max_size*2]); self.image.fill(random.choice(color_list) if color_list else (255,0,0)); self.rect = self.image.get_rect(center=(x,y)); self.lifetime = lifetime_frames
        def update(self): 
            self.lifetime -= 1
            if self.lifetime <=0: 
                self.kill()


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle) # Degrees
        self.speed = float(speed)
        self.lifetime = int(lifetime)
        self.initial_lifetime = int(lifetime) 
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
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def update(self, maze=None, game_area_x_offset=0):
        if not self.alive:
            self.kill() 
            return

        prev_x_pixel, prev_y_pixel = self.x, self.y 

        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            self.kill()
            return
        
        if maze and not self.can_pierce_walls:
            bullet_diameter = self.size * 2 
            
            if maze.is_wall(self.x, self.y, bullet_diameter, bullet_diameter):
                if self.bounces_done < self.max_bounces:
                    self.bounces_done += 1
                    self.x, self.y = prev_x_pixel, prev_y_pixel
                    self.rect.center = (int(self.x), int(self.y))

                    collided_x_only = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
                    collided_y_only = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)

                    bounced = False
                    if collided_x_only and not collided_y_only: 
                        self.dx *= -1
                        bounced = True
                    elif collided_y_only and not collided_x_only: 
                        self.dy *= -1
                        bounced = True
                    elif collided_x_only and collided_y_only: 
                        self.dx *= -1
                        self.dy *= -1
                        bounced = True
                    
                    if bounced:
                        self.angle = math.degrees(math.atan2(self.dy, self.dx))
                        self.x += self.dx * 0.1 
                        self.y += self.dy * 0.1
                        self.rect.center = (int(self.x), int(self.y))
                    else:
                        self.alive = False 
                else: 
                    self.alive = False
        
        if not self.alive: 
            self.kill()
            return

        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH 
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT 

        hit_boundary = False
        if self.rect.left < min_x_bound:
            self.x = min_x_bound + self.size 
            self.dx *= -1
            hit_boundary = True
        elif self.rect.right > max_x_bound:
            self.x = max_x_bound - self.size 
            self.dx *= -1
            hit_boundary = True
        
        if self.rect.top < min_y_bound:
            self.y = min_y_bound + self.size 
            self.dy *= -1
            hit_boundary = True
        elif self.rect.bottom > max_y_bound:
            self.y = max_y_bound - self.size 
            self.dy *= -1
            hit_boundary = True

        if hit_boundary:
            if self.bounces_done < self.max_bounces:
                self.bounces_done += 1
                self.angle = math.degrees(math.atan2(self.dy, self.dx)) 
            else: 
                self.alive = False
        
        if not self.alive:
            self.kill()
            return
            
        self.rect.center = (int(self.x), int(self.y))


    def draw(self, surface):
        if self.alive and self.image and self.rect:
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
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

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

    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle):
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
        max_x_bound = WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT
        if self.lifetime <= 0 or \
           not (min_x_bound < self.rect.centerx < max_x_bound and
                min_y_bound < self.rect.centery < max_y_bound):
            self.alive = False
            self.kill()

    def draw(self, surface):
        if self.alive and self.image and self.rect:
            surface.blit(self.image, self.rect)

class LightningZap(pygame.sprite.Sprite):
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None):
        super().__init__()
        self.player_ref = player_ref 
        self.locked_target_enemy = initial_target_enemy_ref
        self.maze_ref = maze_ref
        self.game_area_x_offset = game_area_x_offset
        # Attempt to get game_controller_ref from player_ref (which could be PlayerDrone or Turret)
        self.game_controller_ref = getattr(player_ref, 'game_controller_ref', None) 
        if not self.game_controller_ref and hasattr(player_ref, 'drone_system') and hasattr(player_ref.drone_system, 'game_controller'): # Fallback for PlayerDrone
            self.game_controller_ref = player_ref.drone_system.game_controller


        self.damage = damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_elapsed = 0
        self.alive = True
        self.color = color_override if color_override is not None else gs.LIGHTNING_COLOR
        self.damage_applied = False 

        self.current_start_pos = self.player_ref.rect.center
        self.potential_end_pos_no_wall = self._calculate_potential_target_pos() 
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.potential_end_pos_no_wall)
        self.hit_wall_at_end = (self.current_target_pos != self.potential_end_pos_no_wall)

        self._update_rect_for_collision()


    def _pixel_to_grid_coords(self, pixel_x, pixel_y):
        if not self.maze_ref: return None, None
        current_maze_x_offset = getattr(self.maze_ref, 'game_area_x_offset', self.game_area_x_offset)
        col = int((pixel_x - current_maze_x_offset) / TILE_SIZE)
        row = int(pixel_y / TILE_SIZE)
        return row, col

    def _get_wall_collision_point(self, start_point, end_point, steps_override=None):
        if not self.maze_ref or not hasattr(self.maze_ref, 'grid') or not self.maze_ref.grid:
            return end_point

        dx_total = end_point[0] - start_point[0]
        dy_total = end_point[1] - start_point[1]
        distance = math.hypot(dx_total, dy_total)

        if distance == 0: return start_point

        dir_x = dx_total / distance
        dir_y = dy_total / distance

        step_size = TILE_SIZE / 4 
        num_steps = steps_override if steps_override is not None else int(distance / step_size) + 1
        if num_steps <= 0 : num_steps = 1

        current_x, current_y = start_point
        last_safe_x, last_safe_y = start_point

        for i in range(num_steps):
            if self.maze_ref.is_wall(current_x, current_y, TILE_SIZE*0.1, TILE_SIZE*0.1):
                return last_safe_x, last_safe_y 

            last_safe_x, last_safe_y = current_x, current_y

            if i < num_steps - 1: 
                current_x += dir_x * step_size
                current_y += dir_y * step_size
                if math.hypot(current_x - start_point[0], current_y - start_point[1]) > distance:
                    break 
        
        if self.maze_ref.is_wall(end_point[0], end_point[1], TILE_SIZE*0.1, TILE_SIZE*0.1):
             return last_safe_x, last_safe_y 
        return end_point 

    def _calculate_potential_target_pos(self):
        """Calculates the ideal end point of the lightning, aiming at target or forward."""
        if self.locked_target_enemy and self.locked_target_enemy.alive:
            return self.locked_target_enemy.rect.center
        else:
            self.locked_target_enemy = None 
            angle_rad = math.radians(self.player_ref.angle) 
            return (
                self.current_start_pos[0] + math.cos(angle_rad) * gs.LIGHTNING_ZAP_RANGE,
                self.current_start_pos[1] + math.sin(angle_rad) * gs.LIGHTNING_ZAP_RANGE
            )

    def _update_rect_for_collision(self):
        """Updates self.rect to encompass the lightning bolt for broad-phase collision."""
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        padding = gs.get_game_setting("LIGHTNING_BASE_THICKNESS", 5) * 1.5 
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding

        rect_width = max(1, int(max_x - min_x))
        rect_height = max(1, int(max_y - min_y))
        
        if not hasattr(self, 'image') or self.image is None or \
           self.image.get_width() < rect_width or self.image.get_height() < rect_height:
            self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
        
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))


    def update(self, current_time_ms):
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
        self.potential_end_pos_no_wall = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.potential_end_pos_no_wall)
        self.hit_wall_at_end = (self.current_target_pos != self.potential_end_pos_no_wall)
        
        self._update_rect_for_collision() 

    def _draw_lightning_bolt_effect(self, surface, p1, p2, base_bolt_color, alpha):
        """Draws the jagged lightning bolt effect between two points."""
        num_segments = gs.get_game_setting("LIGHTNING_SEGMENTS", 12)
        outer_max_offset_base = gs.get_game_setting("LIGHTNING_MAX_OFFSET", 18)
        outer_thickness = gs.get_game_setting("LIGHTNING_BASE_THICKNESS", 5)

        inner_core_thickness = max(1, int(outer_thickness * gs.get_game_setting("LIGHTNING_CORE_THICKNESS_RATIO", 0.4)))
        inner_max_offset_base = outer_max_offset_base * gs.get_game_setting("LIGHTNING_CORE_OFFSET_RATIO", 0.3)
        core_color = gs.LIGHTNING_CORE_COLOR

        branch_chance = gs.get_game_setting("LIGHTNING_BRANCH_CHANCE", 0.25)
        branch_max_segments = gs.get_game_setting("LIGHTNING_BRANCH_MAX_SEGMENTS", 5)
        branch_max_offset = gs.get_game_setting("LIGHTNING_BRANCH_MAX_OFFSET", 10)
        branch_thickness = max(1, int(inner_core_thickness * gs.get_game_setting("LIGHTNING_BRANCH_THICKNESS_RATIO", 0.5)))

        dx_total = p2[0] - p1[0]
        dy_total = p2[1] - p1[1]

        dist_total = math.hypot(dx_total, dy_total)
        if dist_total == 0: return

        perp_dx = -dy_total / dist_total
        perp_dy = dx_total / dist_total

        main_points_outer = [p1]
        main_points_inner = [p1]

        # Adjust jaggedness based on target lock for "bending" effect
        current_outer_max_offset = outer_max_offset_base
        current_inner_max_offset = inner_max_offset_base
        target_pull_strength = 0.3 # How much the lightning "bends" towards target. Range 0.0 to 1.0

        if self.locked_target_enemy and self.locked_target_enemy.alive:
            current_outer_max_offset *= 0.6 # Make bolt less erratic when locked on
            current_inner_max_offset *= 0.6

        for i in range(1, num_segments + 1):
            t = i / num_segments 
            base_x = p1[0] + dx_total * t
            base_y = p1[1] + dy_total * t
            segment_rand_factor = (random.random() - 0.5) * 2 
            mid_factor = math.sin(t * math.pi) 
            
            offset_pull_x, offset_pull_y = 0, 0
            if self.locked_target_enemy and self.locked_target_enemy.alive:
                vec_to_target_x = self.locked_target_enemy.rect.centerx - base_x
                vec_to_target_y = self.locked_target_enemy.rect.centery - base_y
                dist_to_target_from_point = math.hypot(vec_to_target_x, vec_to_target_y)
                if dist_to_target_from_point > 0:
                    # Normalized vector towards target from current point on the straight line
                    pull_dir_x = vec_to_target_x / dist_to_target_from_point
                    pull_dir_y = vec_to_target_y / dist_to_target_from_point
                    # Strength of pull (e.g., stronger in the middle of the bolt)
                    pull_magnitude = current_outer_max_offset * target_pull_strength * mid_factor
                    offset_pull_x = pull_dir_x * pull_magnitude
                    offset_pull_y = pull_dir_y * pull_magnitude


            offset_outer_x = perp_dx * current_outer_max_offset * segment_rand_factor * mid_factor + offset_pull_x
            offset_outer_y = perp_dy * current_outer_max_offset * segment_rand_factor * mid_factor + offset_pull_y
            main_points_outer.append((base_x + offset_outer_x, base_y + offset_outer_y))

            offset_inner_x = perp_dx * current_inner_max_offset * segment_rand_factor * mid_factor + offset_pull_x * 0.5
            offset_inner_y = perp_dy * current_inner_max_offset * segment_rand_factor * mid_factor + offset_pull_y * 0.5
            main_points_inner.append((base_x + offset_inner_x, base_y + offset_inner_y))

        main_points_outer[-1] = p2 
        main_points_inner[-1] = p2

        outer_color_with_alpha = (*base_bolt_color[:3], int(alpha * 0.65))
        if len(main_points_outer) > 1 and outer_thickness > 0:
            pygame.draw.lines(surface, outer_color_with_alpha, False, main_points_outer, outer_thickness)

        inner_color_with_alpha = (*core_color[:3], alpha)
        if len(main_points_inner) > 1 and inner_core_thickness > 0:
            pygame.draw.lines(surface, inner_color_with_alpha, False, main_points_inner, inner_core_thickness)

        for i in range(len(main_points_inner) - 1): 
            if random.random() < branch_chance:
                branch_start_point = main_points_inner[i]
                seg_dx = main_points_inner[i+1][0] - branch_start_point[0]
                seg_dy = main_points_inner[i+1][1] - branch_start_point[1]
                seg_len = math.hypot(seg_dx, seg_dy)
                if seg_len == 0: continue

                branch_perp_dx = -seg_dy / seg_len 
                branch_perp_dy = seg_dx / seg_len
                angle_perturb = random.uniform(-math.pi / 3, math.pi / 3) 
                c, s = math.cos(angle_perturb), math.sin(angle_perturb)
                final_branch_dir_x = branch_perp_dx * c - branch_perp_dy * s
                final_branch_dir_y = branch_perp_dx * s + branch_perp_dy * c
                
                if random.random() < 0.5:
                    final_branch_dir_x *= -1
                    final_branch_dir_y *= -1

                branch_points = [branch_start_point]
                current_branch_pos = list(branch_start_point)
                branch_segment_len_base = dist_total / num_segments * random.uniform(0.3, 0.7) 

                for j in range(random.randint(1, branch_max_segments)):
                    current_segment_len = branch_segment_len_base * (1 - (j / branch_max_segments) * 0.5)
                    current_branch_pos[0] += final_branch_dir_x * current_segment_len
                    current_branch_pos[1] += final_branch_dir_y * current_segment_len
                    
                    branch_offset_mag = random.uniform(-branch_max_offset, branch_max_offset) * math.sin(((j+1)/branch_max_segments) * math.pi)
                    branch_jag_x = perp_dx * branch_offset_mag 
                    branch_jag_y = perp_dy * branch_offset_mag

                    branch_points.append((current_branch_pos[0] + branch_jag_x, current_branch_pos[1] + branch_jag_y))
                    if len(branch_points) > branch_max_segments : break 

                if len(branch_points) > 1 and branch_thickness > 0:
                    branch_alpha = int(alpha * 0.8) 
                    branch_color_with_alpha = (*core_color[:3], branch_alpha) 
                    pygame.draw.lines(surface, branch_color_with_alpha, False, branch_points, branch_thickness)
        
        if self.hit_wall_at_end and self.game_controller_ref and hasattr(self.game_controller_ref, 'explosion_particles'):
            num_sparks = random.randint(4, 7) # More sparks for wall hit
            impact_point = self.current_target_pos
            
            # Determine approximate wall normal (vector from impact point to where bolt *would have* gone)
            normal_approx_x = self.potential_end_pos_no_wall[0] - impact_point[0]
            normal_approx_y = self.potential_end_pos_no_wall[1] - impact_point[1]
            len_normal = math.hypot(normal_approx_x, normal_approx_y)

            if len_normal > 0:
                # Wall surface direction is perpendicular to this normal
                wall_dir_x1 = -normal_approx_y / len_normal
                wall_dir_y1 = normal_approx_x / len_normal
                wall_dir_x2 = normal_approx_y / len_normal
                wall_dir_y2 = -normal_approx_x / len_normal

                for _ in range(num_sparks):
                    # Choose one of the two directions along the wall
                    if random.random() < 0.5:
                        spark_dir_x, spark_dir_y = wall_dir_x1, wall_dir_y1
                    else:
                        spark_dir_x, spark_dir_y = wall_dir_x2, wall_dir_y2
                    
                    # Add a small random spread to the chosen wall direction
                    angle_offset_spark = math.radians(random.uniform(-25, 25))
                    final_spark_dx = spark_dir_x * math.cos(angle_offset_spark) - spark_dir_y * math.sin(angle_offset_spark)
                    final_spark_dy = spark_dir_x * math.sin(angle_offset_spark) + spark_dir_y * math.cos(angle_offset_spark)
                    
                    spark_angle_deg = math.degrees(math.atan2(final_spark_dy, final_spark_dx))

                    spark = Particle(
                        x=impact_point[0], y=impact_point[1],
                        color_list=[WHITE, YELLOW, self.color[:3]], 
                        min_speed=1.5, max_speed=3.5, # Slightly faster sparks
                        min_size=1, max_size=4,       # Slightly larger sparks
                        gravity=0.03, shrink_rate=0.25, lifetime_frames=random.randint(8, 15), # Shorter life
                        base_angle_deg=spark_angle_deg, spread_angle_deg=15 # Tighter spread along wall
                    )
                    self.game_controller_ref.explosion_particles.add(spark)


    def draw(self, surface):
        if self.alive:
            current_alpha_perc = 1.0 - (self.frames_elapsed / self.lifetime_frames)
            current_alpha = int(255 * (current_alpha_perc ** 1.5)) 
            current_alpha = int(max(0, min(255, current_alpha)))

            if current_alpha > 5: 
                self._draw_lightning_bolt_effect(surface, self.current_start_pos, self.current_target_pos,
                                                 self.color, 
                                                 current_alpha)
