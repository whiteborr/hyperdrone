import math
import random

import pygame

import game_settings as gs
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE, 
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE, 
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, 
    WIDTH, GAME_PLAY_AREA_HEIGHT 
)


class Bullet(pygame.sprite.Sprite): 
    """Represents a standard projectile."""
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0): 
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
        self.alive = True 

        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA) 
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size) 
        self.rect = self.image.get_rect(center=(self.x, self.y)) 

        rad_angle = math.radians(self.angle) 
        self.dx = math.cos(rad_angle) * self.speed 
        self.dy = math.sin(rad_angle) * self.speed 

    def update(self, maze=None, game_area_x_offset=0): 
        """Updates the bullet's position and state."""
        if not self.alive: 
            self.kill() 
            return 

        self.x += self.dx 
        self.y += self.dy 
        self.rect.center = (int(self.x), int(self.y)) 

        self.lifetime -= 1 
        if self.lifetime <= 0: 
            self.alive = False 
            return 

        min_x_bound = game_area_x_offset 
        max_x_bound = WIDTH 
        min_y_bound = 0 
        max_y_bound = GAME_PLAY_AREA_HEIGHT 

        is_out_of_bounds = not (min_x_bound < self.rect.centerx < max_x_bound and \
                                min_y_bound < self.rect.centery < max_y_bound) 

        wall_hit = False
        if maze:
            # Check for wall collision first, regardless of bounce properties
            if maze.is_wall(self.x, self.y, self.size, self.size):
                wall_hit = True

        if wall_hit:
            if self.bounces_done < self.max_bounces:
                # Bounce logic (existing code)
                prev_x_check = self.x - self.dx * 0.1 
                prev_y_check = self.y - self.dy * 0.1 
                hit_vertical_wall = False 
                hit_horizontal_wall = False 

                if maze.is_wall(self.x, prev_y_check, self.size, self.size): 
                    hit_vertical_wall = True 
                if maze.is_wall(prev_x_check, self.y, self.size, self.size): 
                    hit_horizontal_wall = True 

                if hit_vertical_wall and not hit_horizontal_wall: 
                    self.dx *= -1 
                    self.angle = (180 - self.angle) % 360 
                elif hit_horizontal_wall and not hit_vertical_wall: 
                    self.dy *= -1 
                    self.angle = (-self.angle) % 360 
                else: 
                    # Hit a corner or a complex intersection, reflect both
                    self.dx *= -1 
                    self.dy *= -1 
                    self.angle = (self.angle + 180) % 360 
                        
                self.bounces_done += 1 
                # Move slightly out of the wall to prevent getting stuck
                self.x += self.dx * 0.1 
                self.y += self.dy * 0.1 
                self.rect.center = (int(self.x), int(self.y)) 
            else: # Not a bouncing bullet or out of bounces, so destroy it
                self.alive = False
            return # Processed wall hit, exit update for this frame

        # If not hit a wall, then check for out of bounds
        if is_out_of_bounds: 
            # For bouncing bullets, boundary check acts like a wall bounce
            if self.bounces_done < self.max_bounces: 
                bounced_on_boundary = False 
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound: 
                    self.dx *= -1 
                    self.angle = (180 - self.angle) % 360 
                    bounced_on_boundary = True 
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound: 
                    self.dy *= -1 
                    self.angle = (-self.angle) % 360 
                    bounced_on_boundary = True 
                
                if bounced_on_boundary: 
                    self.bounces_done += 1 
                    # Nudge back into bounds
                    self.x = max(min_x_bound + self.size, min(self.x, max_x_bound - self.size)) 
                    self.y = max(min_y_bound + self.size, min(self.y, max_y_bound - self.size)) 
                    self.rect.center = (int(self.x), int(self.y)) 
                else: 
                    # Should not happen if is_out_of_bounds is true and one of the conditions above isn't met
                    self.alive = False 
            else: # Not a bouncing bullet or out of bounces
                self.alive = False 
            return 
    
    def draw(self, surface): 
        """Draws the bullet on the given surface."""
        if self.alive: 
            surface.blit(self.image, self.rect) 


class Missile(pygame.sprite.Sprite): 
    """Represents a homing missile."""
    def __init__(self, x, y, initial_angle, damage, enemies_group): 
        super().__init__() 
        self.x = float(x) 
        self.y = float(y) 
        self.angle = float(initial_angle) 
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
        
        self.original_image = pygame.transform.rotate(self.original_image_surface, 90) 

        self.image = pygame.transform.rotate(self.original_image, -self.angle) 
        self.rect = self.image.get_rect(center=(self.x, self.y)) 

    def _find_target(self): 
        """Finds the closest living enemy to target."""
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

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): 
        """Updates the missile's position, orientation, and state."""
        if not self.alive: 
            self.kill() 
            return 

        if enemies_group_updated is not None: 
            self.enemies_group = enemies_group_updated 

        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive): 
            self.target = self._find_target() 

        if self.target: 
            target_x, target_y = self.target.rect.center 
            dx_to_target = target_x - self.x 
            dy_to_target = target_y - self.y 
            
            angle_to_target_rad = math.atan2(dy_to_target, dx_to_target) 
            angle_to_target_deg = math.degrees(angle_to_target_rad) 

            current_angle_norm = self.angle % 360 
            target_angle_norm = (angle_to_target_deg + 360) % 360 

            angle_diff = target_angle_norm - current_angle_norm 
            if angle_diff > 180: 
                angle_diff -= 360 
            elif angle_diff < -180: 
                angle_diff += 360 

            turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff)) 
            self.angle = (self.angle + turn_this_frame) % 360 
        
        rad_current_angle = math.radians(self.angle) 
        self.x += math.cos(rad_current_angle) * self.speed 
        self.y += math.sin(rad_current_angle) * self.speed 
        
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

        # Missiles typically explode or disappear on wall hit, not bounce by default.
        if maze and self.alive:
            if maze.is_wall(self.x, self.y, self.rect.width * 0.5, self.rect.height * 0.5): # Using smaller collision box for missile tip
                self.alive = False 


    def draw(self, surface): 
        """Draws the missile on the given surface."""
        if self.alive: 
            surface.blit(self.image, self.rect) 


class LightningZap(pygame.sprite.Sprite): 
    """Represents a lightning zap effect."""
    def __init__(self, start_pos, target_pos, damage, lifetime_frames): 
        super().__init__() 
        self.start_pos = start_pos 
        self.target_pos = target_pos if target_pos else (start_pos[0] + LIGHTNING_ZAP_RANGE, start_pos[1]) 
        
        self.damage = damage 
        self.lifetime_frames = int(lifetime_frames) 
        self.frames_elapsed = 0 
        self.alive = True 
        self.color = LIGHTNING_COLOR 

        all_x = [self.start_pos[0], self.target_pos[0]] 
        all_y = [self.start_pos[1], self.target_pos[1]] 
        min_x, max_x = min(all_x), max(all_x) 
        min_y, max_y = min(all_y), max(all_y) 

        rect_width = max(1, max_x - min_x) 
        rect_height = max(1, max_y - min_y) 
        self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA) 
        self.rect = self.image.get_rect(topleft=(min_x, min_y)) 
        
        self.local_start = (self.start_pos[0] - min_x, self.start_pos[1] - min_y) 
        self.local_target = (self.target_pos[0] - min_x, self.target_pos[1] - min_y) 

    def update(self, current_time_ticks=None): 
        """Updates the lightning zap's state (e.g., lifetime)."""
        if not self.alive: 
            self.kill() 
            return 

        self.frames_elapsed += 1 
        if self.frames_elapsed > self.lifetime_frames: 
            self.alive = False 
        else: 
            pass 

    def draw(self, surface): 
        """Draws the lightning zap on the given surface."""
        if self.alive: 
            current_alpha = 255 * (1 - (self.frames_elapsed / self.lifetime_frames)**2) 
            current_alpha = int(max(0, min(255, current_alpha))) 
            
            if current_alpha > 0: 
                self._draw_jagged_line(surface, self.start_pos, self.target_pos, self.color, current_alpha, 3, 5, 10) 


    def _draw_jagged_line(self, surface, p1, p2, color, alpha, thickness, num_segments=5, max_offset=10): 
        """Helper to draw a jagged line for a more electric look."""
        points = [p1] 
        dx_total = p2[0] - p1[0] 
        dy_total = p2[1] - p1[1] 

        for i in range(1, num_segments): 
            t = i / num_segments 
            base_x = p1[0] + dx_total * t 
            base_y = p1[1] + dy_total * t 
            
            offset_x = (random.random() - 0.5) * 2 * max_offset 
            offset_y = (random.random() - 0.5) * 2 * max_offset 
            points.append((base_x + offset_x, base_y + offset_y)) 
        
        points.append(p2) 

        if len(points) > 1: 
            try: 
                pygame.draw.lines(surface, (*color[:3], alpha), False, points, thickness) 
            except TypeError: 
                 pygame.draw.lines(surface, color, False, points, thickness)