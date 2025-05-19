import math
import random

import pygame

from game_settings import (
    TILE_SIZE,
    PLAYER_BULLET_LIFETIME, PLAYER_BULLET_SPEED,
    WHITE as DEFAULT_BULLET_COLOR,
    MISSILE_LIFETIME, MISSILE_SPEED, MISSILE_COLOR, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_COLOR
)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed=None, color=None, lifetime=None, size=6,
                 bounces=0, pierce_count=0, damage=25, owner=None, maze=None):
        super().__init__()
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed if speed is not None else PLAYER_BULLET_SPEED
        self.color = color if color is not None else DEFAULT_BULLET_COLOR
        self.lifetime = lifetime if lifetime is not None else PLAYER_BULLET_LIFETIME
        self.size = size
        self.alive = True
        self.damage = damage
        self.owner = owner
        self.maze = maze
        self.max_bounces = bounces
        self.bounces_done = 0
        self.max_pierces = pierce_count
        self.pierces_done = 0
        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self):
        if not self.alive:
            return
        old_x, old_y = self.x, self.y
        dx = math.cos(math.radians(self.angle)) * self.speed
        dy = math.sin(math.radians(self.angle)) * self.speed
        self.x += dx
        self.y += dy
        self.rect.center = (int(self.x), int(self.y))
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            self.kill()
            return
        if self.maze:
            collided_with_wall = self.maze.is_wall(self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height)
            if collided_with_wall:
                if self.max_pierces > 0 and self.pierces_done < self.max_pierces:
                    self.pierces_done += 1
                elif self.max_bounces > 0 and self.bounces_done < self.max_bounces:
                    self.bounces_done += 1
                    self.x, self.y = old_x, old_y
                    reflected = False
                    test_rect_x = self.rect.copy()
                    test_rect_x.center = (old_x + dx, old_y)
                    if self.maze.is_wall(test_rect_x.centerx, test_rect_x.centery, test_rect_x.width, test_rect_x.height):
                        self.angle = 180 - self.angle
                        reflected = True
                    test_rect_y = self.rect.copy()
                    test_rect_y.center = (old_x, old_y + dy)
                    if self.maze.is_wall(test_rect_y.centerx, test_rect_y.centery, test_rect_y.width, test_rect_y.height):
                        self.angle = 360 - self.angle
                        reflected = True
                    if not reflected:
                        self.angle = (self.angle + 180) % 360
                    self.angle %= 360
                    self.x += math.cos(math.radians(self.angle)) * self.speed * 0.1
                    self.y += math.sin(math.radians(self.angle)) * self.speed * 0.1
                    self.rect.center = (int(self.x), int(self.y))
                else:
                    self.alive = False; self.kill(); return
    def draw(self, surface):
        if self.alive:
            surface.blit(self.image, self.rect.topleft)

class Missile(pygame.sprite.Sprite):
    def __init__(self, x, y, initial_angle, enemies_group, maze, damage=None):
        super().__init__()
        self.x, self.y, self.angle = x, y, initial_angle
        self.speed, self.color, self.lifetime = MISSILE_SPEED, MISSILE_COLOR, MISSILE_LIFETIME
        self.size, self.turn_rate = MISSILE_SIZE, MISSILE_TURN_RATE
        self.alive, self.enemies_group, self.maze = True, enemies_group, maze
        self.damage = damage if damage is not None else 50
        self.image_orig = pygame.Surface([self.size*2, self.size*1.5], pygame.SRCALPHA)
        pygame.draw.polygon(self.image_orig, self.color, [(self.size*2, self.size*0.75), (0,0), (0,self.size*1.5)])
        self.image, self.rect = self.image_orig.copy(), self.image_orig.get_rect(center=(int(x),int(y)))
        self.target, self.is_wall_sliding, self.last_wall_check_pos = None, False, (None,None)

    def update(self):
        if not self.alive: return
        self.lifetime -= 1
        if self.lifetime <= 0: self.alive = False; self.kill(); return
        if self.target is None or not self.target.alive: self.target = self._find_closest_enemy()

        desired_angle = self.angle
        AVOIDANCE_FEELER_LENGTH, AVOIDANCE_TURN_ANGLE_STEP, MAX_AVOIDANCE_CHECKS_PER_SIDE = TILE_SIZE*0.7, 30, 3
        wall_directly_ahead, alternative_path_angle = False, None

        if self.maze:
            feeler_main_x = self.x + math.cos(math.radians(self.angle)) * AVOIDANCE_FEELER_LENGTH
            feeler_main_y = self.y + math.sin(math.radians(self.angle)) * AVOIDANCE_FEELER_LENGTH
            wall_directly_ahead = self.maze.is_wall(feeler_main_x, feeler_main_y, self.rect.width*0.5, self.rect.height*0.5)
            if wall_directly_ahead:
                self.is_wall_sliding = True
                for i in range(1, MAX_AVOIDANCE_CHECKS_PER_SIDE + 1):
                    for turn_dir in [1, -1]:
                        angle_to_check = (self.angle + i * AVOIDANCE_TURN_ANGLE_STEP * turn_dir + 360) % 360
                        feeler_x = self.x + math.cos(math.radians(angle_to_check)) * AVOIDANCE_FEELER_LENGTH
                        feeler_y = self.y + math.sin(math.radians(angle_to_check)) * AVOIDANCE_FEELER_LENGTH
                        if not self.maze.is_wall(feeler_x, feeler_y, self.rect.width*0.5, self.rect.height*0.5):
                            alternative_path_angle = angle_to_check; break
                    if alternative_path_angle: break
                desired_angle = alternative_path_angle if alternative_path_angle else (self.angle + 90) % 360
            else: self.is_wall_sliding = False

        if not self.is_wall_sliding and self.target:
            dx_target, dy_target = self.target.rect.centerx - self.x, self.target.rect.centery - self.y
            if not (dx_target == 0 and dy_target == 0): desired_angle = math.degrees(math.atan2(dy_target, dx_target))

        self.angle = (self.angle % 360)
        desired_angle = (desired_angle % 360)
        angle_diff = (desired_angle - self.angle + 180) % 360 - 180
        if abs(angle_diff) < self.turn_rate: self.angle = desired_angle
        else: self.angle += self.turn_rate * (1 if angle_diff > 0 else -1)
        self.angle %= 360

        self.image = pygame.transform.rotate(self.image_orig, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        prev_x, prev_y = self.x, self.y
        next_x_pos = self.x + math.cos(math.radians(self.angle)) * self.speed
        next_y_pos = self.y + math.sin(math.radians(self.angle)) * self.speed
        temp_next_rect = self.rect.copy(); temp_next_rect.center = (int(next_x_pos), int(next_y_pos))

        collided_on_move = self.maze and self.maze.is_wall(temp_next_rect.centerx, temp_next_rect.centery, temp_next_rect.width, temp_next_rect.height)
        if collided_on_move:
            self.x, self.y = prev_x, prev_y
            self.angle = (self.angle + 45 * random.choice([-1,1])) % 360
        else:
            self.x, self.y = next_x_pos, next_y_pos
        self.rect.center = (int(self.x), int(self.y))
        if self.last_wall_check_pos == (round(self.x,1), round(self.y,1)) and collided_on_move: pass
        self.last_wall_check_pos = (round(self.x,1), round(self.y,1))

    def _find_closest_enemy(self):
        closest_enemy, min_dist_sq = None, float('inf')
        if not self.enemies_group: return None
        for enemy in self.enemies_group:
            if enemy.alive:
                dist_sq = (self.x - enemy.rect.centerx)**2 + (self.y - enemy.rect.centery)**2
                if dist_sq < min_dist_sq: min_dist_sq, closest_enemy = dist_sq, enemy
        return closest_enemy

    def draw(self, surface):
        if self.alive: surface.blit(self.image, self.rect.topleft)


class LightningBullet(pygame.sprite.Sprite):
    def __init__(self, origin_pos, target_enemy=None, end_point=None, 
                 damage=LIGHTNING_DAMAGE,
                 lifetime=LIGHTNING_LIFETIME,
                 color=LIGHTNING_COLOR,
                 owner=None, maze=None):
        super().__init__()
        self.origin_pos = pygame.math.Vector2(origin_pos) 
        self.target_enemy = target_enemy
        self.maze = maze
        self.owner = owner 

        if self.target_enemy:
            self.target_pos = pygame.math.Vector2(self.target_enemy.rect.center)
            if hasattr(self.target_enemy, 'take_damage') and self.target_enemy.alive:
                self.target_enemy.take_damage(damage)
        elif end_point:
            self.target_pos = pygame.math.Vector2(end_point)
        else:
            self.target_pos = pygame.math.Vector2(origin_pos[0] + 1, origin_pos[1]) # Corrected to use tuple access for origin_pos

        self.damage = damage
        self.lifetime = lifetime
        self.initial_lifetime = max(1, lifetime)
        self.color = color
        self.line_thickness = 2
        self.alive = True

        tm_min_x = min(self.origin_pos.x, self.target_pos.x)
        tm_min_y = min(self.origin_pos.y, self.target_pos.y)
        tm_max_x = max(self.origin_pos.x, self.target_pos.x)
        tm_max_y = max(self.origin_pos.y, self.target_pos.y)
        tm_width = max(1, tm_max_x - tm_min_x)
        tm_height = max(1, tm_max_y - tm_min_y)
        self.image = pygame.Surface((tm_width, tm_height), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(tm_min_x, tm_min_y))

    def update(self):
        if not self.alive:
            self.kill(); return

        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            self.kill()
            return

        if self.owner and hasattr(self.owner, 'get_tip_position'):
            new_origin_tuple = self.owner.get_tip_position()
            self.origin_pos.x = new_origin_tuple[0]
            self.origin_pos.y = new_origin_tuple[1]

        if self.target_enemy and self.target_enemy.alive:
            self.target_pos.update(self.target_enemy.rect.center)

        current_end_point_for_rect = self.target_pos
        if self.target_enemy and self.target_enemy.alive: 
            current_end_point_for_rect = pygame.math.Vector2(self.target_enemy.rect.center)
        
        min_x = min(self.origin_pos.x, current_end_point_for_rect.x)
        min_y = min(self.origin_pos.y, current_end_point_for_rect.y)
        max_x = max(self.origin_pos.x, current_end_point_for_rect.x)
        max_y = max(self.origin_pos.y, current_end_point_for_rect.y)
        
        buffer = self.line_thickness + 2 
        
        self.rect.x = min_x - buffer
        self.rect.y = min_y - buffer
        self.rect.width = max(1, (max_x - min_x) + 2 * buffer)
        self.rect.height = max(1, (max_y - min_y) + 2 * buffer)

    def draw(self, surface):
        if not self.alive:
            return
        
        current_draw_target_pos = self.target_pos
        if self.target_enemy and self.target_enemy.alive:
             current_draw_target_pos = pygame.math.Vector2(self.target_enemy.rect.center)
        
        current_alpha = int(255 * (self.lifetime / self.initial_lifetime)**2) 
        current_alpha = max(0, min(255, current_alpha))
        if current_alpha == 0: return

        points = [self.origin_pos] 
        num_segments = random.randint(4, 7)

        # MODIFIED: Removed the special handling for distance < 5
        # Now, the jagged line logic will always attempt to draw.
        # if self.origin_pos.distance_to(current_draw_target_pos) < 5: 
        #      # ... this block is removed ...
        #      return

        # Check if distance is too small for meaningful segmentation, draw straight line if so
        # This check can be kept if desired, or tuned. Forcing jagged lines for very short distances might look odd.
        # For now, let's keep the principle of drawing something meaningful.
        # A very small distance might still benefit from a direct line rather than multiple segments on top of each other.
        if self.origin_pos.distance_to(current_draw_target_pos) < self.line_thickness * 2: # If length is less than ~twice thickness
             try:
                rgb_color = self.color[:3] if len(self.color) == 4 else self.color
                line_color_with_alpha = (*rgb_color, current_alpha)
                pygame.draw.line(surface, line_color_with_alpha, self.origin_pos, current_draw_target_pos, self.line_thickness)
             except (ValueError, TypeError):
                 temp_line_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                 pygame.draw.line(temp_line_surf, self.color, self.origin_pos, current_draw_target_pos, self.line_thickness)
                 temp_line_surf.set_alpha(current_alpha)
                 surface.blit(temp_line_surf, (0,0))
             return # Return after drawing the simplified short line

        # Proceed with jagged line if distance is sufficient
        dx_segment = (current_draw_target_pos.x - self.origin_pos.x) / num_segments
        dy_segment = (current_draw_target_pos.y - self.origin_pos.y) / num_segments
        max_perpendicular_offset = self.line_thickness * 2.5

        for i in range(1, num_segments):
            base_x = self.origin_pos.x + dx_segment * i
            base_y = self.origin_pos.y + dy_segment * i
            perp_dx = -dy_segment
            perp_dy = dx_segment
            len_perp = math.hypot(perp_dx, perp_dy)
            if len_perp > 0:
                perp_dx /= len_perp
                perp_dy /= len_perp
            rand_offset_magnitude = random.uniform(-max_perpendicular_offset, max_perpendicular_offset)
            offset_x = perp_dx * rand_offset_magnitude
            offset_y = perp_dy * rand_offset_magnitude
            points.append(pygame.math.Vector2(base_x + offset_x, base_y + offset_y))

        points.append(current_draw_target_pos)

        if len(points) >= 2:
            try:
                rgb_color = self.color[:3] if len(self.color) == 4 else self.color
                line_color_with_alpha = (*rgb_color, current_alpha)
                pygame.draw.lines(surface, line_color_with_alpha, False, points, self.line_thickness)
            except (ValueError, TypeError):
                 temp_line_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                 pygame.draw.lines(temp_line_surf, self.color, False, points, self.line_thickness)
                 temp_line_surf.set_alpha(current_alpha)
                 surface.blit(temp_line_surf, (0,0))