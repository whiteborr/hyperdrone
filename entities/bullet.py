# entities/bullet.py

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
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0): 
        super().__init__() 
        self.x = float(x) 
        self.y = float(y) 
        self.angle = float(angle) 
        self.speed = float(speed) 
        self.lifetime = int(lifetime) 
        self.size = int(size) # Radius
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

        wall_hit = False
        if maze:
            # Use the bullet's diameter for collision checking with maze.is_wall
            bullet_diameter = self.size * 2 
            if maze.is_wall(self.x, self.y, bullet_diameter, bullet_diameter):
                wall_hit = True
        
        if wall_hit:
            if self.bounces_done < self.max_bounces:
                self.x, self.y = prev_x, prev_y # Revert to pre-collision position for bounce
                
                # A common approach for bouncing off lines is to reflect based on an estimated normal
                # or simplify by checking if a predominantly horizontal or vertical wall was hit.
                # For simplicity, let's try reflecting both components if line normal isn't easily available.
                # A more accurate bounce would require knowing the orientation of the specific line segment hit.
                
                # Try moving only in X, check collision, then only in Y
                temp_rect_x_move = pygame.Rect(0,0, bullet_diameter, bullet_diameter)
                temp_rect_x_move.center = (self.x + self.dx, self.y)

                temp_rect_y_move = pygame.Rect(0,0, bullet_diameter, bullet_diameter)
                temp_rect_y_move.center = (self.x, self.y + self.dy)

                hit_x_wall = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
                hit_y_wall = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)

                if hit_x_wall and not hit_y_wall: # Primarily hit a vertical surface
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360
                elif hit_y_wall and not hit_x_wall: # Primarily hit a horizontal surface
                    self.dy *= -1
                    self.angle = (-self.angle) % 360
                else: # Hit a corner or direct hit, reflect both (simplification)
                    self.dx *= -1
                    self.dy *= -1
                    self.angle = (self.angle + 180) % 360
                
                self.bounces_done += 1
                # Move with new direction for this frame
                self.x += self.dx
                self.y += self.dy
                self.rect.center = (int(self.x), int(self.y))
            else:
                self.alive = False
            return

        # Screen Boundary Checks
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT

        if self.rect.left < min_x_bound or self.rect.right > max_x_bound or \
           self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
            if self.bounces_done < self.max_bounces:
                self.x, self.y = prev_x, prev_y # Revert for boundary bounce
                bounced_on_boundary = False
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360
                    bounced_on_boundary = True
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
                    self.dy *= -1
                    self.angle = (-self.angle) % 360
                    if bounced_on_boundary: self.angle = (self.angle + 180) % 360 # Corner
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

# --- Missile Class (ensure it also uses maze.is_wall() if needed) ---
class Missile(pygame.sprite.Sprite): #
    def __init__(self, x, y, initial_angle, damage, enemies_group): #
        super().__init__() #
        self.x = float(x) #
        self.y = float(y) #
        self.angle = float(initial_angle) #
        self.speed = MISSILE_SPEED #
        self.lifetime = MISSILE_LIFETIME #
        self.damage = damage #
        self.enemies_group = enemies_group #
        self.target = None #
        self.turn_rate = MISSILE_TURN_RATE #
        self.alive = True #

        self.original_image_surface = pygame.Surface([MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5], pygame.SRCALPHA) #
        points = [
            (MISSILE_SIZE * 0.75, 0), 
            (0, MISSILE_SIZE * 2.5), 
            (MISSILE_SIZE * 1.5, MISSILE_SIZE * 2.5) 
        ] #
        pygame.draw.polygon(self.original_image_surface, MISSILE_COLOR, points) #
        
        self.original_image = pygame.transform.rotate(self.original_image_surface, 90) #

        self.image = pygame.transform.rotate(self.original_image, -self.angle) #
        self.rect = self.image.get_rect(center=(self.x, self.y)) #

    def _find_target(self): #
        if not self.enemies_group: #
            return None #
        closest_enemy = None #
        min_dist_sq = float('inf') #

        for enemy in self.enemies_group: #
            if hasattr(enemy, 'alive') and not enemy.alive: #
                continue #
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2 #
            if dist_sq < min_dist_sq: #
                min_dist_sq = dist_sq #
                closest_enemy = enemy #
        return closest_enemy #

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): #
        if not self.alive: #
            self.kill() #
            return #

        if enemies_group_updated is not None: #
            self.enemies_group = enemies_group_updated #

        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive): #
            self.target = self._find_target() #

        if self.target: #
            target_x, target_y = self.target.rect.center #
            dx_to_target = target_x - self.x #
            dy_to_target = target_y - self.y #
            
            angle_to_target_rad = math.atan2(dy_to_target, dx_to_target) #
            angle_to_target_deg = math.degrees(angle_to_target_rad) #

            current_angle_norm = self.angle % 360 #
            target_angle_norm = (angle_to_target_deg + 360) % 360 #

            angle_diff = target_angle_norm - current_angle_norm #
            if angle_diff > 180: #
                angle_diff -= 360 #
            elif angle_diff < -180: #
                angle_diff += 360 #

            turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff)) #
            self.angle = (self.angle + turn_this_frame) % 360 #
        
        rad_current_angle = math.radians(self.angle) #
        self.x += math.cos(rad_current_angle) * self.speed #
        self.y += math.sin(rad_current_angle) * self.speed #
        
        self.image = pygame.transform.rotate(self.original_image, -self.angle) #
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) #

        self.lifetime -= 1 #
        min_x_bound = game_area_x_offset #
        max_x_bound = WIDTH #
        min_y_bound = 0 #
        max_y_bound = GAME_PLAY_AREA_HEIGHT #
        if self.lifetime <= 0 or \
           not (min_x_bound < self.rect.centerx < max_x_bound and 
                min_y_bound < self.rect.centery < max_y_bound): #
            self.alive = False #

        if maze and self.alive: #
            # For missiles, use their rect's width/height for is_wall, or a fraction if preferred
            if maze.is_wall(self.x, self.y, self.rect.width * 0.7, self.rect.height * 0.7): 
                self.alive = False #

    def draw(self, surface): #
        if self.alive: #
            surface.blit(self.image, self.rect) #


class LightningZap(pygame.sprite.Sprite): #
    def __init__(self, start_pos, target_pos, damage, lifetime_frames): #
        super().__init__() #
        self.start_pos = start_pos #
        self.target_pos = target_pos if target_pos else (start_pos[0] + LIGHTNING_ZAP_RANGE, start_pos[1]) #
        
        self.damage = damage #
        self.lifetime_frames = int(lifetime_frames) #
        self.frames_elapsed = 0 #
        self.alive = True #
        self.color = LIGHTNING_COLOR #

        all_x = [self.start_pos[0], self.target_pos[0]] #
        all_y = [self.start_pos[1], self.target_pos[1]] #
        min_x, max_x = min(all_x), max(all_x) #
        min_y, max_y = min(all_y), max(all_y) #

        rect_width = max(1, max_x - min_x) #
        rect_height = max(1, max_y - min_y) #
        self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA) #
        self.rect = self.image.get_rect(topleft=(min_x, min_y)) #
        
        self.local_start = (self.start_pos[0] - min_x, self.start_pos[1] - min_y) #
        self.local_target = (self.target_pos[0] - min_x, self.target_pos[1] - min_y) #

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

        # --- Wall Collision Check using maze.is_wall() ---
        wall_hit = False
        if maze:
            bullet_diameter = self.size * 2
            if maze.is_wall(self.x, self.y, bullet_diameter, bullet_diameter):
                wall_hit = True
        
        if wall_hit:
            # ALL bullets (including piercing) stop or bounce on walls.
            # Piercing is for enemies.
            if self.bounces_done < self.max_bounces:
                self.x, self.y = prev_x, prev_y # Revert to pre-collision position
                
                # Simplified bounce logic (as from previous iteration)
                # A more accurate bounce would need line normal from maze.is_wall
                temp_rect_x_move = pygame.Rect(0,0, bullet_diameter, bullet_diameter)
                temp_rect_x_move.center = (self.x + self.dx, self.y)
                temp_rect_y_move = pygame.Rect(0,0, bullet_diameter, bullet_diameter)
                temp_rect_y_move.center = (self.x, self.y + self.dy)

                # Check if hypothetical moves would also collide to guess wall orientation
                # This logic might need refinement for perfect bounces off arbitrary line segments
                hit_x_wall = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
                hit_y_wall = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)

                bounced_this_frame = False
                if hit_x_wall and not hit_y_wall: # Primarily hit a vertical surface
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360
                    bounced_this_frame = True
                elif hit_y_wall and not hit_x_wall: # Primarily hit a horizontal surface
                    self.dy *= -1
                    self.angle = (-self.angle) % 360
                    bounced_this_frame = True
                
                if not bounced_this_frame: # If both (corner) or neither (stuck/glitch), reflect both
                    self.dx *= -1
                    self.dy *= -1
                    self.angle = (self.angle + 180) % 360
                
                self.bounces_done += 1
                # Nudge based on new direction
                self.x += self.dx * 0.1 
                self.y += self.dy * 0.1
                self.rect.center = (int(self.x), int(self.y))
            else:
                # If not a bouncing bullet, or out of bounces, it's destroyed by the wall.
                # This applies to standard bullets AND piercing bullets.
                self.alive = False
            return # Collision with wall processed

        # --- Screen Boundary Checks (if not hit an internal wall) ---
        min_x_bound = game_area_x_offset
        max_x_bound = WIDTH
        min_y_bound = 0
        max_y_bound = GAME_PLAY_AREA_HEIGHT

        if self.rect.left < min_x_bound or self.rect.right > max_x_bound or \
           self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
            if self.bounces_done < self.max_bounces: # Bouncing bullets can also bounce off screen edges
                self.x, self.y = prev_x, prev_y # Revert for boundary bounce
                
                bounced_on_boundary = False
                if self.rect.left < min_x_bound or self.rect.right > max_x_bound:
                    self.dx *= -1
                    self.angle = (180 - self.angle) % 360
                    bounced_on_boundary = True
                if self.rect.top < min_y_bound or self.rect.bottom > max_y_bound:
                    self.dy *= -1
                    self.angle = (-self.angle) % 360
                    if bounced_on_boundary : # Corner hit on boundary
                        self.angle = (self.angle + 180) % 360 
                    bounced_on_boundary = True
                
                if bounced_on_boundary:
                    self.bounces_done += 1
                    self.x += self.dx # Apply new direction
                    self.y += self.dy
                    self.rect.center = (int(self.x), int(self.y))
                else: # Should ideally not happen if out of bounds
                    self.alive = False 
            else: # Not a bouncing bullet or out of bounces
                self.alive = False
            return

    def draw(self, surface): #
        if self.alive: #
            current_alpha = 255 * (1 - (self.frames_elapsed / self.lifetime_frames)**2) #
            current_alpha = int(max(0, min(255, current_alpha))) #
            
            if current_alpha > 0: #
                self._draw_jagged_line(surface, self.start_pos, self.target_pos, self.color, current_alpha, 3, 5, 10) #

    def _draw_jagged_line(self, surface, p1, p2, color, alpha, thickness, num_segments=5, max_offset=10): #
        points = [p1] #
        dx_total = p2[0] - p1[0] #
        dy_total = p2[1] - p1[1] #

        for i in range(1, num_segments): #
            t = i / num_segments #
            base_x = p1[0] + dx_total * t #
            base_y = p1[1] + dy_total * t #
            
            offset_x = (random.random() - 0.5) * 2 * max_offset #
            offset_y = (random.random() - 0.5) * 2 * max_offset #
            points.append((base_x + offset_x, base_y + offset_y)) #
        
        points.append(p2) #

        if len(points) > 1: #
            try: #
                pygame.draw.lines(surface, (*color[:3], alpha), False, points, thickness) #
            except TypeError: #
                 pygame.draw.lines(surface, color, False, points, thickness) #