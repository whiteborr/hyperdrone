# entities/bullet.py
import math
import random
import pygame
import os
import logging

# Import from settings_manager for settings access
from settings_manager import get_setting
from constants import PLAYER_BULLET_COLOR, RED, MISSILE_COLOR, LIGHTNING_COLOR, WHITE

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
        # Create a completely transparent surface
        surface_dim = max(1, self.size * 2)
        self.image = pygame.Surface([surface_dim, surface_dim], pygame.SRCALPHA)
        self.image.fill((0,0,0,0))
        # Draw the bullet
        draw_radius = max(1, self.size)
        try:
            pygame.draw.circle(self.image, self.color, (surface_dim // 2, surface_dim // 2), draw_radius)
        except TypeError:
            pygame.draw.circle(self.image, RED, (surface_dim // 2, surface_dim // 2), draw_radius)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def _ensure_drawable_state(self):
        # This method is no longer used, initialization is done directly in __init__
        pass

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
        if self.alive:
            if not collided_this_step or self.frames_existed <= 1: self.x, self.y = potential_next_x, potential_next_y
        self.rect.center = (int(self.x), int(self.y)); self.lifetime -= 1
        if self.lifetime <= 0: self.alive = False
        if self.alive:
            # Use dynamic height from settings
            game_play_area_height = get_setting("display", "HEIGHT", 1080)
            min_x_bound, max_x_bound = game_area_x_offset, get_setting("display", "WIDTH", 1920)
            min_y_bound, max_y_bound = 0, game_play_area_height
            center_x, center_y, half_size = self.rect.centerx, self.rect.centery, self.size
            if not (min_x_bound < center_x - half_size and center_x + half_size < max_x_bound and \
                    min_y_bound < center_y - half_size and center_y + half_size < max_y_bound):
                self.alive = False 
        if not self.alive: self.kill()
        
        # Only recreate the bullet image if it's necessary (first frame or after bouncing)
        if self.alive and (self.frames_existed == 1 or self.bounces_done > 0):
            surface_dim = max(1, self.size * 2)
            self.image = pygame.Surface([surface_dim, surface_dim], pygame.SRCALPHA)
            self.image.fill((0,0,0,0))
            draw_radius = max(1, self.size)
            try:
                pygame.draw.circle(self.image, self.color, (surface_dim // 2, surface_dim // 2), draw_radius)
            except TypeError:
                pygame.draw.circle(self.image, RED, (surface_dim // 2, surface_dim // 2), draw_radius)

    def draw(self, surface, camera=None):
        if self.alive and self.image and self.rect:
            if camera:
                surface.blit(self.image, camera.apply_to_rect(self.rect))
            else:
                surface.blit(self.image, self.rect)


class Missile(pygame.sprite.Sprite): 
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.id = id(self) 
        self.x, self.y, self.angle, self.target_angle = float(x), float(y), float(initial_angle), float(initial_angle)
        self.speed = get_setting("weapons", "MISSILE_SPEED", 5); self.lifetime = get_setting("weapons", "MISSILE_LIFETIME", 3000); self.damage = damage
        self.enemies_group = enemies_group; self.target, self.turn_rate = None, get_setting("weapons", "MISSILE_TURN_RATE", 8)
        self.alive, self.frames_existed = True, 0; self.is_sliding, self.slide_direction_attempts, self.MAX_SLIDE_ATTEMPTS = False, 0, 3
        missile_size = get_setting("weapons", "MISSILE_SIZE", 8)
        missile_w, missile_h = missile_size*1.5, missile_size*2.5; self.original_image_surface = pygame.Surface([missile_w, missile_h], pygame.SRCALPHA)
        points = [(missile_w*0.5,0),(0,missile_h),(missile_w,missile_h)]; pygame.draw.polygon(self.original_image_surface,MISSILE_COLOR,points)
        self.original_image = pygame.transform.rotate(self.original_image_surface,-90); self.image = self.original_image
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))); self._update_image_and_rect() 

    def _update_image_and_rect(self):
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _find_target(self): 
        if not self.enemies_group: return None
        closest_enemy, min_dist_sq = None, float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive: continue
            if not hasattr(enemy, 'rect'): continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2 
            if dist_sq < min_dist_sq: min_dist_sq, closest_enemy = dist_sq, enemy
        return closest_enemy
        
    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle): 
        collision_width = self.rect.width * 0.6 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        collision_height = self.rect.height * 0.6 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        current_rad_angle = math.radians(self.angle)
        for da_deg in [30, 60, 45, 75, 90]: 
            for sign in [1, -1]: 
                angle_rad = current_rad_angle + math.radians(da_deg * sign)
                s_dx, s_dy = math.cos(angle_rad) * self.speed, math.sin(angle_rad) * self.speed
                if not maze.is_wall(self.x+s_dx, self.y+s_dy, collision_width,collision_height) and \
                   not maze.is_wall(self.x+s_dx*1.5, self.y+s_dy*1.5, collision_width,collision_height):
                    self.angle = math.degrees(math.atan2(s_dy, s_dx)); return s_dx, s_dy
        return None

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): 
        if not self.alive: return
        self.frames_existed +=1
        if enemies_group_updated is not None: self.enemies_group = enemies_group_updated 
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive): 
            self.target = self._find_target(); self.is_sliding = False 
        effective_angle_rad = math.radians(self.angle) 
        if self.target: 
            target_x, target_y = self.target.rect.center; dx_to_target, dy_to_target = target_x - self.x, target_y - self.y
            turn_this_frame_val = 0.0 
            if dx_to_target != 0 or dy_to_target != 0: self.target_angle = math.degrees(math.atan2(dy_to_target, dx_to_target))
            else: self.target_angle = self.angle 
            if not self.is_sliding:
                angle_diff = (self.target_angle - self.angle + 180)%360 - 180 
                turn_this_frame_val = max(-self.turn_rate, min(self.turn_rate, angle_diff)) 
                self.angle = (self.angle + turn_this_frame_val + 360)%360
            effective_angle_rad = math.radians(self.angle) 
        potential_dx,potential_dy=math.cos(effective_angle_rad)*self.speed,math.sin(effective_angle_rad)*self.speed
        next_x,next_y=self.x+potential_dx,self.y+potential_dy; collided_this_frame=False
        if maze and self.frames_existed > 1: 
            collision_check_width = self.rect.width*0.7 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
            collision_check_height = self.rect.height*0.7 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
            if maze.is_wall(next_x,next_y,collision_check_width,collision_check_height):
                collided_this_frame=True
                if self.slide_direction_attempts < self.MAX_SLIDE_ATTEMPTS:
                    slide_mov = self._attempt_slide(maze,next_x,next_y,effective_angle_rad)
                    if slide_mov: next_x,next_y=self.x+slide_mov[0],self.y+slide_mov[1]; self.is_sliding=True; self.slide_direction_attempts+=1; collided_this_frame=False
                    else: self.alive=False
                else: self.alive=False
            else: self.is_sliding,self.slide_direction_attempts=False,0
        if self.alive and not collided_this_frame: self.x,self.y=next_x,next_y
        self._update_image_and_rect() 
        self.lifetime-=1; out_of_bounds=True
        if self.rect: out_of_bounds=not(game_area_x_offset-self.rect.width < self.rect.centerx < get_setting("display", "WIDTH", 1920)+self.rect.width and -self.rect.height < self.rect.centery < get_setting("display", "HEIGHT", 1080)+self.rect.height)
        if self.lifetime<=0 or out_of_bounds: self.alive=False
        if not self.alive: self.kill()

    def draw(self, surface, camera=None):
        if self.alive and self.image and self.rect:
            if camera:
                surface.blit(self.image, camera.apply_to_rect(self.rect))
            else:
                surface.blit(self.image, self.rect)


class LightningZap(pygame.sprite.Sprite):
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None):
        super().__init__()
        self.id = id(self) 
        self.player_ref = player_ref
        self.initial_target_ref = initial_target_enemy_ref 
        self.maze_ref = maze_ref
        self.game_area_x_offset = game_area_x_offset
        self.game_controller_ref = getattr(player_ref, 'game_controller_ref', None)
        
        self.damage = damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_existed = 0 
        self.alive = True
        self.color = color_override if color_override is not None else LIGHTNING_COLOR
        self.damage_applied = False

        self.current_start_pos = self.player_ref.rect.center if self.player_ref and hasattr(self.player_ref, 'rect') else (0,0)
        self.initial_target_pos_snapshot = self.initial_target_ref.rect.center if self.initial_target_ref and hasattr(self.initial_target_ref, 'rect') else None
        
        self.current_target_pos = self._calculate_potential_target_pos() 
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.current_target_pos) 
        self.hit_wall_at_end = (self.current_target_pos != self._calculate_potential_target_pos(ignore_snapshot=True)) 

        self.image = pygame.Surface((1,1), pygame.SRCALPHA) 
        self.rect = self.image.get_rect(center=self.current_start_pos)
        self._update_rect_for_collision() 

    def _get_wall_collision_point(self, start_point, end_point):
        if not self.maze_ref: return end_point
        dx, dy = end_point[0] - start_point[0], end_point[1] - start_point[1]
        distance = math.hypot(dx, dy)
        if distance == 0: return start_point
        dir_x, dir_y = dx / distance, dy / distance
        
        current_pos = list(start_point)
        for _ in range(int(distance)):
            if self.maze_ref.is_wall(current_pos[0], current_pos[1], 1, 1):
                return tuple(current_pos)
            current_pos[0] += dir_x
            current_pos[1] += dir_y
        return end_point

    def _calculate_potential_target_pos(self, ignore_snapshot=False): 
        if self.initial_target_ref and hasattr(self.initial_target_ref, 'alive') and self.initial_target_ref.alive:
            return self.initial_target_ref.rect.center
        if self.initial_target_pos_snapshot and not ignore_snapshot: 
            return self.initial_target_pos_snapshot
        start_x, start_y = self.current_start_pos 
        angle_rad = math.radians(self.player_ref.angle)
        lightning_zap_range = get_setting("weapons", "LIGHTNING_ZAP_RANGE", 250)
        return (start_x + math.cos(angle_rad) * lightning_zap_range, start_y + math.sin(angle_rad) * lightning_zap_range)

    def _update_rect_for_collision(self): 
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)
        padding = get_setting("weapons", "LIGHTNING_MAX_OFFSET", 18) + get_setting("weapons", "LIGHTNING_BASE_THICKNESS", 5) 
        self.rect = pygame.Rect(int(min_x-padding), int(min_y-padding), int(max_x-min_x+2*padding), int(max_y-min_y+2*padding))

    def update(self, current_time_ms): 
        if not self.alive: self.kill(); return
        if not self.player_ref or not self.player_ref.alive: self.alive=False; self.kill(); return
        
        self.frames_existed +=1 
        if self.frames_existed >= self.lifetime_frames: self.alive=False; self.kill(); return
        
        self.current_start_pos=self.player_ref.rect.center
        self.current_target_pos=self._get_wall_collision_point(self.current_start_pos, self._calculate_potential_target_pos())
        self._update_rect_for_collision()

    def kill(self): 
        super().kill(); self.alive = False 

    def _draw_lightning_bolt(self, surface, p1, p2, color, alpha):
        # Generate lightning bolt points
        points = [p1]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 10:  # Too short for a lightning bolt
            pygame.draw.line(surface, (*color[:3], alpha), p1, p2, 2)
            return
            
        # Calculate perpendicular direction for offsets
        nx, ny = -dy/dist, dx/dist
        
        # Number of segments
        segments = get_setting("weapons", "LIGHTNING_SEGMENTS", 12)
        segment_length = dist / segments
        
        # Generate zigzag points
        current = p1
        for i in range(1, segments):
            # Calculate position along the line
            percent = i / segments
            mid_x = p1[0] + dx * percent
            mid_y = p1[1] + dy * percent
            
            # Add random offset perpendicular to the line
            max_offset = get_setting("weapons", "LIGHTNING_MAX_OFFSET", 18)
            offset = random.uniform(-max_offset, max_offset)
            mid_x += nx * offset
            mid_y += ny * offset
            
            points.append((mid_x, mid_y))
            
        points.append(p2)
        
        # Draw the main lightning bolt
        thickness = get_setting("weapons", "LIGHTNING_BASE_THICKNESS", 5)
        if len(points) > 1:
            pygame.draw.lines(surface, (*color[:3], alpha), False, points, thickness)
            
        # Draw the inner core (brighter)
        core_thickness = int(thickness * get_setting("weapons", "LIGHTNING_CORE_THICKNESS_RATIO", 0.4))
        if core_thickness > 0:
            core_color = get_setting("weapons", "LIGHTNING_CORE_COLOR", (255, 255, 255))
            pygame.draw.lines(surface, (*core_color[:3], alpha), False, points, core_thickness)

    def draw(self, surface, camera=None):
        if self.alive:
            alpha = int(255 * (1.0 - (self.frames_existed / self.lifetime_frames)))
            if alpha > 5:
                self._draw_lightning_bolt(surface, self.current_start_pos, self.current_target_pos, self.color, alpha)

class LaserBeam(pygame.sprite.Sprite):
    """A persistent laser beam fired by the Maze Guardian."""
    def __init__(self, start_pos, angle):
        super().__init__()
        self.start_pos = start_pos
        self.angle = angle
        self.length = get_setting("display", "WIDTH", 1920) * 1.5
        self.width = get_setting("bosses", "MAZE_GUARDIAN_LASER_WIDTH", 10)
        self.damage = get_setting("bosses", "MAZE_GUARDIAN_LASER_DAMAGE", 2)
        self.lifetime = get_setting("bosses", "MAZE_GUARDIAN_LASER_LIFETIME_MS", 1000)
        self.creation_time = pygame.time.get_ticks()
        self.alive = True

        # Visual properties
        self.outer_color = (*get_setting("colors", "RED", (255, 0, 0)), 100)
        self.inner_color = (*get_setting("colors", "WHITE", (255, 255, 255)), 200)
        self.inner_width_ratio = 0.4

        # Create the visual representation of the laser
        self.original_image = self._create_laser_surface()
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=self.start_pos)

    def _create_laser_surface(self):
        """Creates the surface for the laser with a glowing effect."""
        laser_surface = pygame.Surface((self.length, self.width), pygame.SRCALPHA)
        
        # Outer glow/beam
        outer_rect = pygame.Rect(0, 0, self.length, self.width)
        pygame.draw.rect(laser_surface, self.outer_color, outer_rect, border_radius=int(self.width/2))

        # Inner core
        inner_width = self.width * self.inner_width_ratio
        inner_height = self.width * self.inner_width_ratio
        inner_rect = pygame.Rect(0, (self.width - inner_height) / 2, self.length, inner_height)
        pygame.draw.rect(laser_surface, self.inner_color, inner_rect, border_radius=int(inner_height/2))
        
        return laser_surface

    def update(self):
        """The laser fades out over its lifetime."""
        if not self.alive:
            return
            
        time_elapsed = pygame.time.get_ticks() - self.creation_time
        if time_elapsed > self.lifetime:
            self.alive = False
            self.kill()
            return

        # Fade out effect
        life_ratio = 1.0 - (time_elapsed / self.lifetime)
        alpha = int(255 * life_ratio)
        self.image.set_alpha(alpha)

    def draw(self, surface, camera=None):
        """Draws the laser beam."""
        if self.alive and self.image:
            # We assume camera is not used or is static for the boss fight
            surface.blit(self.image, self.rect)
