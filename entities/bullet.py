# whiteborr/hyperdrone/hyperdrone-e30601dab2e5a5306ae5410d9796700369b67256/entities/bullet.py

import math
import random
import pygame

import game_settings as gs 
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
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
                    
                    if not bounced_this_frame: 
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
        max_x_bound = WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT

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
                    self.angle = (-self.angle) % 360 if not bounced_on_boundary else (self.angle + 180) % 360 
                    bounced_on_boundary = True
                
                if bounced_on_boundary:
                    self.bounces_done += 1
                    self.x += self.dx 
                    self.y += self.dy
                    self.rect.center = (int(self.x), int(self.y))
                else: 
                    self.alive = False
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
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0): 
        super().__init__()
        self.player_ref = player_ref
        self.locked_target_enemy = initial_target_enemy_ref
        self.maze_ref = maze_ref 
        self.game_area_x_offset = game_area_x_offset
        
        self.damage = damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_elapsed = 0
        self.alive = True 
        self.color = LIGHTNING_COLOR
        self.damage_applied = False

        self.current_start_pos = self.player_ref.rect.center
        
        # CORRECTED THE METHOD NAME HERE
        self.current_target_pos = self._calculate_potential_target_pos() # Was _calculate_initial_target_pos

        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.current_target_pos)
        self._update_rect_and_image()

    def _pixel_to_grid_coords(self, pixel_x, pixel_y):
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
        
        step_size = TILE_SIZE / 3 
        num_steps = steps_override if steps_override is not None else int(distance / step_size) + 1
        if num_steps <= 0 : num_steps = 1


        current_x, current_y = start_point
        last_safe_x, last_safe_y = start_point

        for i in range(num_steps):
            grid_r, grid_c = self._pixel_to_grid_coords(current_x, current_y)

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
                    # Check the original end_point for wall
                    grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
                    if (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
                        0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
                        self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
                        return last_safe_x, last_safe_y 
                    return end_point 
        
        grid_r_end, grid_c_end = self._pixel_to_grid_coords(end_point[0], end_point[1])
        if (0 <= grid_r_end < self.maze_ref.actual_maze_rows and \
            0 <= grid_c_end < self.maze_ref.actual_maze_cols and \
            self.maze_ref.grid[grid_r_end][grid_c_end] == 1):
            return last_safe_x, last_safe_y 
            
        return end_point


    def _calculate_potential_target_pos(self): # This is the correctly named method
        if self.locked_target_enemy and self.locked_target_enemy.alive:
            return self.locked_target_enemy.rect.center
        else: 
            self.locked_target_enemy = None 
            angle_rad = math.radians(self.player_ref.angle)
            return (
                self.current_start_pos[0] + math.cos(angle_rad) * LIGHTNING_ZAP_RANGE,
                self.current_start_pos[1] + math.sin(angle_rad) * LIGHTNING_ZAP_RANGE
            )

    def _update_rect_and_image(self):
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        padding = 15 
        min_x, max_x = min(all_x) - padding, max(all_x) + padding
        min_y, max_y = min(all_y) - padding, max(all_y) + padding
        rect_width = max(1, int(max_x - min_x))
        rect_height = max(1, int(max_y - min_y))
        
        if not hasattr(self, 'image') or self.image is None or self.image.get_size() != (rect_width, rect_height):
            self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(int(min_x), int(min_y)))

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
        self._update_rect_and_image()

    def draw(self, surface): 
        if self.alive:
            current_alpha_perc = 1.0 - (self.frames_elapsed / self.lifetime_frames)
            current_alpha = int(255 * (current_alpha_perc ** 0.5))
            current_alpha = int(max(0, min(255, current_alpha))) 
            
            if current_alpha > 5:
                self._draw_jagged_line(surface, self.current_start_pos, self.current_target_pos, self.color, current_alpha, 3, 5, 10)

    def _draw_jagged_line(self, surface, p1, p2, color, alpha, thickness, num_segments=5, max_offset=10):
        points = [p1]
        dx_total = p2[0] - p1[0]
        dy_total = p2[1] - p1[1]

        for i in range(1, num_segments):
            t = i / num_segments
            base_x = p1[0] + dx_total * t
            base_y = p1[1] + dy_total * t
            norm_dx, norm_dy = -dy_total, dx_total
            dist_norm = math.hypot(norm_dx, norm_dy)
            if dist_norm == 0: dist_norm = 1
            norm_dx /= dist_norm
            norm_dy /= dist_norm
            offset_magnitude = (random.random() - 0.5) * 2 * max_offset * (math.sin(t * math.pi))
            offset_x = norm_dx * offset_magnitude
            offset_y = norm_dy * offset_magnitude
            points.append((base_x + offset_x, base_y + offset_y))
        points.append(p2)

        if len(points) > 1:
            final_color_tuple = (*color[:3], alpha) if len(color) == 3 else (*color[:3], min(alpha, color[3] if len(color) > 3 else alpha))
            try:
                pygame.draw.lines(surface, final_color_tuple, False, points, thickness)
            except Exception:
                 pygame.draw.lines(surface, (LIGHTNING_COLOR[0],LIGHTNING_COLOR[1],LIGHTNING_COLOR[2],alpha), False, points, thickness)