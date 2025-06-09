# entities/bullet.py
import math
import random
import pygame
import os
import logging

import game_settings as gs
from game_settings import (
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    MISSILE_COLOR, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_SIZE, MISSILE_TURN_RATE,
    LIGHTNING_COLOR, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE, LIGHTNING_CORE_COLOR,
    WIDTH, GAME_PLAY_AREA_HEIGHT, TILE_SIZE, WHITE, RED, YELLOW, MAGENTA, GREEN, CYAN
)
try:
    from .particle import Particle
except ImportError:
    logging.error("Bullet: Could not import Particle from .particle. Using placeholder.")
    class Particle(pygame.sprite.Sprite): pass

logger = logging.getLogger(__name__)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False):
        super().__init__()
        self.x, self.y, self.angle, self.speed = float(x), float(y), float(angle), float(speed)
        self.lifetime, self.initial_lifetime, self.size = int(lifetime), int(lifetime), max(1, int(size))
        self.color = color if color else PLAYER_BULLET_COLOR 
        self.damage = int(damage)
        self.max_bounces, self.bounces_done = int(max_bounces), 0
        self.max_pierces, self.pierces_done = int(max_pierces), 0
        self.can_pierce_walls = can_pierce_walls
        self.alive, self.frames_existed = True, 0
        self._ensure_drawable_state() 
        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def _ensure_drawable_state(self):
        surface_dim = max(1, self.size * 2)
        self.image = pygame.Surface([surface_dim, surface_dim], pygame.SRCALPHA)
        draw_radius = max(1, self.size)
        try: pygame.draw.circle(self.image, self.color, (surface_dim // 2, surface_dim // 2), draw_radius)
        except TypeError: pygame.draw.circle(self.image, gs.RED, (surface_dim // 2, surface_dim // 2), draw_radius)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self, maze=None, game_area_x_offset=0):
        if not self.alive: return
        self.frames_existed += 1; current_x, current_y = self.x, self.y
        potential_next_x, potential_next_y = current_x + self.dx, current_y + self.dy
        collided_this_step = False
        if maze and not self.can_pierce_walls and self.frames_existed > 1:
            bullet_diameter = self.size * 2
            if maze.is_wall(potential_next_x, potential_next_y, bullet_diameter, bullet_diameter):
                collided_this_step = True
                if self.bounces_done < self.max_bounces:
                    self.bounces_done += 1; hit_x_wall = maze.is_wall(current_x + self.dx, current_y, bullet_diameter, bullet_diameter)
                    hit_y_wall = maze.is_wall(current_x, current_y + self.dy, bullet_diameter, bullet_diameter)
                    if hit_x_wall and hit_y_wall: self.dx *= -1; self.dy *= -1
                    elif hit_x_wall: self.dx *= -1
                    elif hit_y_wall: self.dy *= -1
                    else: self.dx *= -1; self.dy *= -1
                    self.angle = math.degrees(math.atan2(self.dy, self.dx))
                else: self.alive = False
        if self.alive and (not collided_this_step or self.frames_existed <= 1): self.x, self.y = potential_next_x, potential_next_y
        self.rect.center = (int(self.x), int(self.y)); self.lifetime -= 1
        if self.lifetime <= 0: self.alive = False
        if self.alive:
            min_x_bound, max_x_bound = game_area_x_offset, WIDTH; min_y_bound, max_y_bound = 0, GAME_PLAY_AREA_HEIGHT
            center_x, center_y, half_size = self.rect.centerx, self.rect.centery, self.size
            if not (min_x_bound < center_x - half_size and center_x + half_size < max_x_bound and min_y_bound < center_y - half_size and center_y + half_size < max_y_bound):
                self.alive = False 
        if not self.alive: self.kill()

    def draw(self, surface, camera=None):
        if not self.alive or not self.image or not self.rect: return
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            # Since the bullet is a simple circle, we can redraw it at the scaled size
            # for perfect clarity at any zoom level.
            scaled_radius = self.size * camera.zoom_level
            if scaled_radius >= 1:
                pygame.draw.circle(surface, self.color, screen_rect.center, scaled_radius)
        else:
            surface.blit(self.image, self.rect)


class Missile(pygame.sprite.Sprite): 
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__(); self.id = id(self) 
        self.x, self.y, self.angle, self.target_angle = float(x), float(y), float(initial_angle), float(initial_angle)
        self.speed, self.lifetime, self.damage = gs.MISSILE_SPEED, gs.MISSILE_LIFETIME, damage
        self.enemies_group, self.target, self.turn_rate = enemies_group, None, gs.MISSILE_TURN_RATE
        self.alive, self.frames_existed, self.is_sliding, self.slide_direction_attempts, self.MAX_SLIDE_ATTEMPTS = True, 0, False, 0, 3
        missile_w, missile_h = gs.MISSILE_SIZE*1.5, gs.MISSILE_SIZE*2.5; self.original_image_surface = pygame.Surface([missile_w, missile_h], pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image_surface, gs.MISSILE_COLOR, [(missile_w*0.5,0),(0,missile_h),(missile_w,missile_h)])
        self.original_image = pygame.transform.rotate(self.original_image_surface,-90); self.image = self.original_image
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))); self._update_image_and_rect() 

    def _update_image_and_rect(self):
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _find_target(self): 
        if not self.enemies_group: return None
        closest_enemy, min_dist_sq = None, float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive or not hasattr(enemy, 'rect'): continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2 
            if dist_sq < min_dist_sq: min_dist_sq, closest_enemy = dist_sq, enemy
        return closest_enemy
        
    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle): 
        collision_width, collision_height = (self.rect.width * 0.6, self.rect.height * 0.6) if self.rect else (gs.MISSILE_SIZE, gs.MISSILE_SIZE)
        current_rad_angle = math.radians(self.angle)
        for da_deg in [30, 60, 45, 75, 90]: 
            for sign in [1, -1]: 
                angle_rad = current_rad_angle + math.radians(da_deg * sign); s_dx, s_dy = math.cos(angle_rad) * self.speed, math.sin(angle_rad) * self.speed
                if not maze.is_wall(self.x+s_dx, self.y+s_dy, collision_width,collision_height) and not maze.is_wall(self.x+s_dx*1.5, self.y+s_dy*1.5, collision_width,collision_height):
                    self.angle = math.degrees(math.atan2(s_dy, s_dx)); return s_dx, s_dy
        return None

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): 
        if not self.alive: return
        self.frames_existed +=1
        if enemies_group_updated: self.enemies_group = enemies_group_updated 
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive): self.target = self._find_target(); self.is_sliding = False 
        effective_angle_rad = math.radians(self.angle) 
        if self.target: 
            target_x, target_y = self.target.rect.center; dx, dy = target_x - self.x, target_y - self.y
            self.target_angle = math.degrees(math.atan2(dy, dx)) if dx != 0 or dy != 0 else self.angle 
            if not self.is_sliding:
                angle_diff = (self.target_angle - self.angle + 180)%360 - 180; self.angle = (self.angle + max(-self.turn_rate, min(self.turn_rate, angle_diff)) + 360)%360
            effective_angle_rad = math.radians(self.angle) 
        dx, dy = math.cos(effective_angle_rad)*self.speed, math.sin(effective_angle_rad)*self.speed
        next_x, next_y = self.x+dx, self.y+dy; collided = False
        if maze and self.frames_existed > 1: 
            if maze.is_wall(next_x, next_y, self.rect.width*0.7, self.rect.height*0.7):
                collided = True
                if self.slide_direction_attempts < self.MAX_SLIDE_ATTEMPTS:
                    if slide_mov := self._attempt_slide(maze,next_x,next_y,effective_angle_rad):
                        next_x, next_y = self.x+slide_mov[0], self.y+slide_mov[1]; self.is_sliding=True; self.slide_direction_attempts+=1; collided=False
                    else: self.alive=False
                else: self.alive=False
            else: self.is_sliding, self.slide_direction_attempts = False, 0
        if self.alive and not collided: self.x, self.y = next_x, next_y
        self._update_image_and_rect(); self.lifetime-=1
        if self.lifetime<=0 or (self.rect and not (game_area_x_offset-self.rect.width < self.rect.centerx < WIDTH+self.rect.width and -self.rect.height < self.rect.centery < GAME_PLAY_AREA_HEIGHT+self.rect.height)): self.alive = False
        if not self.alive: self.kill()

    def draw(self, surface, camera=None):
        if not self.alive or not self.image or not self.rect: return
        if camera:
            scaled_size = (int(self.rect.width * camera.zoom_level), int(self.rect.height * camera.zoom_level))
            if scaled_size[0] > 0 and scaled_size[1] > 0:
                scaled_image = pygame.transform.smoothscale(self.image, scaled_size)
                screen_rect = camera.apply_to_rect(self.rect)
                surface.blit(scaled_image, screen_rect)
        else:
            surface.blit(self.image, self.rect)


class LightningZap(pygame.sprite.Sprite):
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None):
        super().__init__(); self.id, self.player_ref = id(self), player_ref
        self.initial_target_ref, self.maze_ref = initial_target_enemy_ref, maze_ref
        self.game_area_x_offset = game_area_x_offset
        self.game_controller_ref = getattr(player_ref, 'game_controller_ref', getattr(getattr(player_ref, 'drone_system', None), 'game_controller', None))
        self.damage, self.lifetime_frames, self.frames_existed, self.alive = damage, int(lifetime_frames), 0, True
        self.color = color_override if isinstance(color_override, tuple) else gs.LIGHTNING_COLOR
        self.damage_applied = False
        self.current_start_pos = self.player_ref.rect.center if hasattr(self.player_ref, 'rect') else (0,0)
        self.initial_target_pos_snapshot = self.initial_target_ref.rect.center if hasattr(self.initial_target_ref, 'rect') else None
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self._calculate_potential_target_pos()) 
        self.hit_wall_at_end = (self.current_target_pos != self._calculate_potential_target_pos(ignore_snapshot=True)) 
        self.image = pygame.Surface((1,1), pygame.SRCALPHA); self.rect = self.image.get_rect(center=self.current_start_pos)
        self._update_rect_for_collision()

    def _get_wall_collision_point(self, start, end): 
        if not self.maze_ref: return end
        dx, dy = end[0] - start[0], end[1] - start[1]; dist = math.hypot(dx, dy)
        if dist == 0: return start
        dir_x, dir_y = dx / dist, dy / dist; step = TILE_SIZE / 4; steps = int(dist / step) + 1
        x, y = start; last_safe = x, y
        for _ in range(steps):
            if self.maze_ref.is_wall(x, y, TILE_SIZE*0.4, TILE_SIZE*0.4): return last_safe
            last_safe = x,y; x += dir_x * step; y += dir_y * step
        return end if not self.maze_ref.is_wall(end[0], end[1], TILE_SIZE*0.4, TILE_SIZE*0.4) else last_safe

    def _calculate_potential_target_pos(self, ignore_snapshot=False): 
        if self.initial_target_ref and hasattr(self.initial_target_ref, 'alive') and self.initial_target_ref.alive: return self.initial_target_ref.rect.center
        if hasattr(self, 'initial_target_pos_snapshot') and self.initial_target_pos_snapshot and not ignore_snapshot: return self.initial_target_pos_snapshot
        start_x, start_y = self.current_start_pos; angle_rad = math.radians(self.player_ref.angle)
        return (start_x + math.cos(angle_rad) * LIGHTNING_ZAP_RANGE, start_y + math.sin(angle_rad) * LIGHTNING_ZAP_RANGE)

    def _update_rect_for_collision(self): 
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]; all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)
        pad = gs.get_game_setting("LIGHTNING_MAX_OFFSET",18) + gs.get_game_setting("LIGHTNING_BASE_THICKNESS",5) 
        self.rect = pygame.Rect(int(min_x-pad), int(min_y-pad), max(1,int(max_x-min_x+2*pad)), max(1,int(max_y-min_y+2*pad)))

    def update(self,current_time_ms): 
        if not self.alive or not (self.player_ref and hasattr(self.player_ref,'alive') and self.player_ref.alive): self.kill(); return
        self.frames_existed +=1 
        if self.frames_existed >= self.lifetime_frames: self.kill(); return
        self.current_start_pos=self.player_ref.rect.center
        self.current_target_pos=self._get_wall_collision_point(self.current_start_pos,self._calculate_potential_target_pos())
        unobstructed_target = self._calculate_potential_target_pos(ignore_snapshot=True)
        self.hit_wall_at_end = (self.current_target_pos != unobstructed_target and self.current_target_pos != (self.initial_target_ref.rect.center if self.initial_target_ref and hasattr(self.initial_target_ref, 'rect') else None))
        if not self.initial_target_ref and math.hypot(self.current_target_pos[0]-self.current_start_pos[0], self.current_target_pos[1]-self.current_start_pos[1]) > LIGHTNING_ZAP_RANGE:
            angle_rad = math.atan2(self.current_target_pos[1]-self.current_start_pos[1], self.current_target_pos[0]-self.current_start_pos[0])
            capped_x, capped_y = self.current_start_pos[0]+math.cos(angle_rad)*LIGHTNING_ZAP_RANGE, self.current_start_pos[1]+math.sin(angle_rad)*LIGHTNING_ZAP_RANGE
            self.current_target_pos = self._get_wall_collision_point(self.current_start_pos,(capped_x,capped_y))
            self.hit_wall_at_end = (self.current_target_pos != (capped_x, capped_y))
        self._update_rect_for_collision()

    def kill(self): self.alive = False; super().kill()

    def _draw_lightning_bolt_effect(self, surface, p1, p2, base_bolt_color, alpha, zoom=1.0):
        # This method is complex and doesn't need modification if p1,p2 are already screen coordinates.
        # However, we should scale thickness by zoom.
        base_outer_thickness = gs.get_game_setting("LIGHTNING_BASE_THICKNESS", 5) + 2
        outer_thickness = max(1, int(base_outer_thickness * zoom))
        inner_core_thickness = max(1, int(outer_thickness * gs.get_game_setting("LIGHTNING_CORE_THICKNESS_RATIO", 0.4)))
        # ... (rest of the drawing logic remains the same, using the passed-in points and new thickness) ...
        dx_total, dy_total = p2[0]-p1[0], p2[1]-p1[1]; dist_total = math.hypot(dx_total,dy_total)
        if dist_total < outer_thickness: return # Too short to draw
        perp_dx,perp_dy = -dy_total/dist_total,dx_total/dist_total
        points_outer,points_inner = [p1],[p1]
        num_segments = gs.get_game_setting("LIGHTNING_SEGMENTS", 12)
        max_offset = gs.get_game_setting("LIGHTNING_MAX_OFFSET", 18) * zoom
        for i in range(1,num_segments+1):
            t = i/num_segments; rand_f = (random.random()-0.5)*2; mid_f = math.sin(t*math.pi)
            offset = max_offset * rand_f * mid_f
            points_outer.append((p1[0] + dx_total*t + perp_dx*offset, p1[1] + dy_total*t + perp_dy*offset))
            points_inner.append((p1[0] + dx_total*t + perp_dx*offset*0.3, p1[1] + dy_total*t + perp_dy*offset*0.3))
        points_outer[-1], points_inner[-1] = p2, p2
        bolt_rgb = base_bolt_color[:3]; core_rgb = LIGHTNING_CORE_COLOR[:3]
        if len(points_outer)>1: pygame.draw.lines(surface, (*bolt_rgb, int(alpha*0.75)), False, points_outer, outer_thickness)
        if len(points_inner)>1: pygame.draw.lines(surface, (*core_rgb, alpha), False, points_inner, inner_core_thickness)

    def draw(self, surface, camera=None):
        if not self.alive: return
        
        current_alpha_perc = 1.0 - (self.frames_existed / self.lifetime_frames if self.lifetime_frames > 0 else 1.0)
        current_alpha = int(255 * (current_alpha_perc ** 1.5))
        current_alpha = max(0, min(255, current_alpha))

        if current_alpha > 5:
            if camera:
                screen_p1 = camera.apply_to_pos(self.current_start_pos)
                screen_p2 = camera.apply_to_pos(self.current_target_pos)
                self._draw_lightning_bolt_effect(surface, screen_p1, screen_p2, self.color, current_alpha, camera.zoom_level)
            else:
                self._draw_lightning_bolt_effect(surface, self.current_start_pos, self.current_target_pos, self.color, current_alpha)