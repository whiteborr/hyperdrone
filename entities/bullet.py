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
    class Particle(pygame.sprite.Sprite):
        def __init__(self, x, y, color_list, min_speed, max_speed, min_size, max_size, gravity=0.1, shrink_rate=0.1, lifetime_frames=30, base_angle_deg=None, spread_angle_deg=360, x_offset=0, y_offset=0, blast_mode=False):
            super().__init__()
            surface_dimension = max(1, int(max_size * 2))
            self.image = pygame.Surface([surface_dimension, surface_dimension], pygame.SRCALPHA)
            fill_color = random.choice(color_list) if color_list else (255,0,0)
            pygame.draw.circle(self.image, fill_color, (surface_dimension // 2, surface_dimension // 2), max(1, int(max_size)))
            self.rect = self.image.get_rect(center=(x,y))
            self.lifetime = lifetime_frames; self.x = float(x); self.y = float(y)
            angle = math.radians(random.uniform(0,360) if base_angle_deg is None else random.uniform(base_angle_deg-spread_angle_deg/2,base_angle_deg+spread_angle_deg/2))
            speed = random.uniform(min_speed,max_speed)
            self.dx = math.cos(angle)*speed; self.dy = math.sin(angle)*speed
            self.gravity, self.shrink_rate, self.current_size = gravity, shrink_rate, float(max_size)
        def update(self): # Added self
            self.lifetime-=1
            if self.lifetime<=0: self.kill(); return
            self.dy+=self.gravity; self.x+=self.dx; self.y+=self.dy; self.rect.center=(int(self.x),int(self.y))
            self.current_size-=self.shrink_rate
            if self.current_size<=0: self.kill(); return


logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False):
        super().__init__()
        self.x, self.y, self.angle, self.speed = float(x), float(y), float(angle), float(speed)
        self.lifetime, self.initial_lifetime, self.size = int(lifetime), int(lifetime), max(1, int(size))
        self.color = color if color else PLAYER_BULLET_COLOR # Ensure color has a fallback
        self.damage = int(damage)
        self.max_bounces, self.bounces_done = int(max_bounces), 0
        self.max_pierces, self.pierces_done = int(max_pierces), 0
        self.can_pierce_walls = can_pierce_walls
        self.alive, self.frames_existed = True, 0

        self._ensure_drawable_state() # Call after attributes are set

        rad_angle = math.radians(self.angle)
        self.dx = math.cos(rad_angle) * self.speed
        self.dy = math.sin(rad_angle) * self.speed

    def _ensure_drawable_state(self):
        """Ensures self.image and self.rect are valid for drawing."""
        surface_dim = max(1, self.size * 2)
        self.image = pygame.Surface([surface_dim, surface_dim], pygame.SRCALPHA)
        draw_radius = max(1, self.size)
        # Ensure self.color is a valid color tuple
        try:
            pygame.draw.circle(self.image, self.color, (surface_dim // 2, surface_dim // 2), draw_radius)
        except TypeError: # Fallback if self.color is invalid (e.g. None or wrong type)
            pygame.draw.circle(self.image, gs.RED, (surface_dim // 2, surface_dim // 2), draw_radius)
            logger.warning(f"Bullet ID {id(self)} used fallback color for drawing due to TypeError with {self.color}")

        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if not self.image: logger.error(f"Bullet ID {id(self)} _ensure_drawable_state: Image is still None after creation attempt.")
        if not self.rect: logger.error(f"Bullet ID {id(self)} _ensure_drawable_state: Rect is still None after creation attempt.")


    def update(self, maze=None, game_area_x_offset=0):
        if not self.alive: return

        self.frames_existed += 1
        current_x, current_y = self.x, self.y
        potential_next_x, potential_next_y = current_x + self.dx, current_y + self.dy
        collided_this_step = False

        if maze and not self.can_pierce_walls and self.frames_existed > 1:
            bullet_diameter = self.size * 2
            if maze.is_wall(potential_next_x, potential_next_y, bullet_diameter, bullet_diameter):
                collided_this_step = True
                if self.bounces_done < self.max_bounces:
                    self.bounces_done += 1
                    hit_x_wall = maze.is_wall(current_x + self.dx, current_y, bullet_diameter, bullet_diameter)
                    hit_y_wall = maze.is_wall(current_x, current_y + self.dy, bullet_diameter, bullet_diameter)
                    if hit_x_wall and hit_y_wall: self.dx *= -1; self.dy *= -1
                    elif hit_x_wall: self.dx *= -1
                    elif hit_y_wall: self.dy *= -1
                    else: self.dx *= -1; self.dy *= -1
                    self.angle = math.degrees(math.atan2(self.dy, self.dx))
                else: self.alive = False
        
        if self.alive:
            if not collided_this_step or self.frames_existed <= 1: self.x, self.y = potential_next_x, potential_next_y
        
        self.rect.center = (int(self.x), int(self.y)) # Update rect position
        self.lifetime -= 1
        if self.lifetime <= 0: self.alive = False

        if self.alive:
            min_x_bound, max_x_bound = game_area_x_offset, WIDTH
            min_y_bound, max_y_bound = 0, GAME_PLAY_AREA_HEIGHT
            center_x, center_y, half_size = self.rect.centerx, self.rect.centery, self.size
            hit_boundary = False
            if not (min_x_bound < center_x - half_size and center_x + half_size < max_x_bound and \
                    min_y_bound < center_y - half_size and center_y + half_size < max_y_bound):
                # Simplified boundary collision: just kill if out of major bounds for now
                # More complex bounce logic for boundaries can be added if needed like wall bounces
                self.alive = False 
                hit_boundary = True # To avoid double-kill() call
        
        if not self.alive: self.kill()


    def draw(self, surface):
        if self.alive:
            # Actual Bullet Image Drawing
            if self.image and self.rect:
               surface.blit(self.image, self.rect)


class Missile(pygame.sprite.Sprite): # Inherits from Sprite, not Bullet, to manage its own image/rect more clearly
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.x, self.y, self.angle, self.target_angle = float(x), float(y), float(initial_angle), float(initial_angle)
        self.speed = gs.MISSILE_SPEED
        self.lifetime = gs.MISSILE_LIFETIME
        self.damage = damage
        self.enemies_group = enemies_group
        self.target, self.turn_rate = None, gs.MISSILE_TURN_RATE
        self.alive, self.frames_existed = True, 0
        self.is_sliding, self.slide_direction_attempts, self.MAX_SLIDE_ATTEMPTS = False, 0, 3

        # Image and Rect setup
        missile_w, missile_h = gs.MISSILE_SIZE * 1.5, gs.MISSILE_SIZE * 2.5
        self.original_image_surface = pygame.Surface([missile_w, missile_h], pygame.SRCALPHA)
        points = [(missile_w * 0.5, 0), (0, missile_h), (missile_w, missile_h)]
        pygame.draw.polygon(self.original_image_surface, gs.MISSILE_COLOR, points)
        self.original_image = pygame.transform.rotate(self.original_image_surface, -90)
        self._update_image_and_rect() # Initial image rotation and rect creation

    def _update_image_and_rect(self):
        """Rotates original_image to self.image and updates self.rect."""
        current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=current_center)

    def _find_target(self): # Same as before
        if not self.enemies_group: return None
        closest_enemy, min_dist_sq = None, float('inf')
        for enemy in self.enemies_group:
            if hasattr(enemy, 'alive') and not enemy.alive: continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq: min_dist_sq, closest_enemy = dist_sq, enemy
        return closest_enemy

    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle): # Same as before
        collision_width, collision_height = self.rect.width * 0.6, self.rect.height * 0.6
        current_rad_angle = math.radians(self.angle)
        for da_deg in [30, 60, 45, 75, 90]:
            for sign in [1, -1]:
                angle_rad = current_rad_angle + math.radians(da_deg * sign)
                s_dx, s_dy = math.cos(angle_rad) * self.speed, math.sin(angle_rad) * self.speed
                if not maze.is_wall(self.x + s_dx, self.y + s_dy, collision_width, collision_height) and \
                   not maze.is_wall(self.x + s_dx * 1.5, self.y + s_dy * 1.5, collision_width, collision_height):
                    self.angle = math.degrees(math.atan2(s_dy, s_dx))
                    return s_dx, s_dy
        return None

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0): # Same as before
        if not self.alive: return
        self.frames_existed +=1
        if enemies_group_updated is not None: self.enemies_group = enemies_group_updated
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target(); self.is_sliding = False

        effective_angle_rad = math.radians(self.angle)
        if self.target:
            target_x, target_y = self.target.rect.center
            dx_to_target, dy_to_target = target_x - self.x, target_y - self.y
            self.target_angle = math.degrees(math.atan2(dy_to_target, dx_to_target))
            if not self.is_sliding:
                angle_diff = (self.target_angle - self.angle + 180) % 360 - 180
                turn_this_frame = max(-self.turn_rate, min(self.turn_rate, angle_diff))
                self.angle = (self.angle + turn_this_frame + 360) % 360
            effective_angle_rad = math.radians(self.angle)

        potential_dx, potential_dy = math.cos(effective_angle_rad) * self.speed, math.sin(effective_angle_rad) * self.speed
        next_x, next_y = self.x + potential_dx, self.y + potential_dy
        collided_this_frame = False
        if maze and self.frames_existed > 1:
            if maze.is_wall(next_x, next_y, self.rect.width*0.7, self.rect.height*0.7):
                collided_this_frame = True
                if self.slide_direction_attempts < self.MAX_SLIDE_ATTEMPTS:
                    slide_mov = self._attempt_slide(maze, next_x, next_y, effective_angle_rad)
                    if slide_mov: next_x, next_y = self.x + slide_mov[0], self.y + slide_mov[1]; self.is_sliding = True; self.slide_direction_attempts += 1; collided_this_frame = False
                    else: self.alive = False
                else: self.alive = False
            else: self.is_sliding, self.slide_direction_attempts = False, 0
        if self.alive and not collided_this_frame: self.x, self.y = next_x, next_y
        
        self._update_image_and_rect() # Call after x,y and angle are updated

        self.lifetime -= 1
        if self.lifetime <= 0 or not (game_area_x_offset < self.rect.centerx < WIDTH and 0 < self.rect.centery < GAME_PLAY_AREA_HEIGHT):
            self.alive = False
        if not self.alive: self.kill()

    def draw(self, surface):
        if self.alive:
            if self.image and self.rect:
                surface.blit(self.image, self.rect)
            # Fallback for visibility - Uncomment if needed
            # elif self.rect: pygame.draw.circle(surface, gs.GREEN, self.rect.center, gs.MISSILE_SIZE)


class LightningZap(pygame.sprite.Sprite): # Inherits from Sprite
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None):
        super().__init__()
        self.player_ref = player_ref
        self.initial_target_ref = initial_target_enemy_ref
        self.initial_target_pos_snapshot = self.initial_target_ref.rect.center if self.initial_target_ref and hasattr(self.initial_target_ref, 'rect') else None
        self.maze_ref, self.game_area_x_offset = maze_ref, game_area_x_offset
        self.game_controller_ref = getattr(player_ref, 'game_controller_ref', getattr(getattr(player_ref, 'drone_system', None), 'game_controller', None))

        self.damage, self.lifetime_frames = damage, int(lifetime_frames)
        self.frames_existed, self.alive, self.damage_applied = 0, True, False
        self.color = color_override if color_override is not None else gs.LIGHTNING_COLOR
        if not isinstance(self.color, tuple) or len(self.color) < 3: # Ensure color is a tuple for slicing
            logger.warning(f"LightningZap ID={id(self)} received invalid color {self.color}. Defaulting to CYAN.")
            self.color = gs.CYAN

        self.current_start_pos = self.player_ref.rect.center
        self.potential_end_pos_no_wall = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.potential_end_pos_no_wall)
        self.hit_wall_at_end = (self.current_target_pos != self.potential_end_pos_no_wall)
        
        # For sprite group management, it needs an image and rect, even if not directly blitted.
        # The rect should encompass the line to allow for broad phase collision if needed by other systems.
        self._update_rect_for_collision()

    def _get_wall_collision_point(self, start_point, end_point, steps_override=None): # Same as before
        if not self.maze_ref or not hasattr(self.maze_ref, 'grid') or not self.maze_ref.grid: return end_point
        dx_total, dy_total = end_point[0] - start_point[0], end_point[1] - start_point[1]
        distance = math.hypot(dx_total, dy_total)
        if distance == 0: return start_point
        dir_x, dir_y = dx_total / distance, dy_total / distance
        step_size, ray_check_size = TILE_SIZE / 4, TILE_SIZE * 0.4
        num_steps = steps_override if steps_override is not None else int(distance / step_size) + 1
        current_x, current_y = start_point; last_safe_x, last_safe_y = start_point
        for i in range(num_steps):
            if self.maze_ref.is_wall(current_x, current_y, ray_check_size, ray_check_size): return last_safe_x, last_safe_y
            last_safe_x, last_safe_y = current_x, current_y
            if i < num_steps - 1: current_x += dir_x * step_size; current_y += dir_y * step_size
            if math.hypot(current_x - start_point[0], current_y - start_point[1]) > distance: break
        return last_safe_x, last_safe_y if self.maze_ref.is_wall(end_point[0], end_point[1], ray_check_size, ray_check_size) else end_point

    def _calculate_potential_target_pos(self): # Same as before
        if self.initial_target_ref and hasattr(self.initial_target_ref, 'alive') and self.initial_target_ref.alive and hasattr(self.initial_target_ref, 'rect'):
            self.initial_target_pos_snapshot = self.initial_target_ref.rect.center; return self.initial_target_pos_snapshot
        if self.initial_target_pos_snapshot: return self.initial_target_pos_snapshot
        angle_rad = math.radians(self.player_ref.angle)
        return (self.current_start_pos[0] + math.cos(angle_rad) * LIGHTNING_ZAP_RANGE, self.current_start_pos[1] + math.sin(angle_rad) * LIGHTNING_ZAP_RANGE)

    def _update_rect_for_collision(self): # Same as before, for broadphase/group management
        all_x, all_y = [self.current_start_pos[0], self.current_target_pos[0]], [self.current_start_pos[1], self.current_target_pos[1]]
        min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)
        padding = gs.get_game_setting("LIGHTNING_MAX_OFFSET", 18)
        rect_x, rect_y = int(min_x - padding), int(min_y - padding)
        rect_width, rect_height = max(1, int(max_x - min_x + 2 * padding)), max(1, int(max_y - min_y + 2 * padding))
        try: self.image = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
        except pygame.error: self.image = pygame.Surface((1,1), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(rect_x, rect_y))

    def update(self, current_time_ms): # Same as before
        if not self.alive or not self.player_ref or not hasattr(self.player_ref, 'alive') or not self.player_ref.alive:
            if self.alive: self.alive = False; self.kill(); return
        self.frames_existed += 1
        if self.frames_existed >= self.lifetime_frames:
            if self.alive: logger.debug(f"LightningZap ID={id(self)} lifetime expired ({self.frames_existed}/{self.lifetime_frames})."); self.alive = False; self.kill(); return
        self.current_start_pos = self.player_ref.rect.center
        self.potential_end_pos_no_wall = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.potential_end_pos_no_wall)
        self.hit_wall_at_end = (self.current_target_pos != self.potential_end_pos_no_wall)
        if not self.initial_target_ref:
            dist_sq = (self.current_target_pos[0]-self.current_start_pos[0])**2 + (self.current_target_pos[1]-self.current_start_pos[1])**2
            if dist_sq > LIGHTNING_ZAP_RANGE**2:
                angle_rad = math.atan2(self.current_target_pos[1]-self.current_start_pos[1], self.current_target_pos[0]-self.current_start_pos[0])
                capped_x, capped_y = self.current_start_pos[0] + math.cos(angle_rad)*LIGHTNING_ZAP_RANGE, self.current_start_pos[1] + math.sin(angle_rad)*LIGHTNING_ZAP_RANGE
                self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, (capped_x, capped_y))
                self.hit_wall_at_end = (self.current_target_pos != (capped_x, capped_y))
        self._update_rect_for_collision()

    def _draw_wall_crawl_effect(self, surface, impact_point, incident_vector_normalized, alpha): # Same as before
        if not self.game_controller_ref or not hasattr(self.game_controller_ref, 'explosion_particles_group'): return
        num_sparks = random.randint(gs.get_game_setting("LIGHTNING_WALL_CRAWL_MIN_TENDRILS",1), gs.get_game_setting("LIGHTNING_WALL_CRAWL_MAX_TENDRILS",2))
        for _ in range(num_sparks):
            angle_offset_spark = math.radians(random.uniform(-70, 70))
            base_reflect_x, base_reflect_y = -incident_vector_normalized[0], -incident_vector_normalized[1]
            c_reflect, s_reflect = math.cos(angle_offset_spark), math.sin(angle_offset_spark)
            final_spark_dx, final_spark_dy = base_reflect_x*c_reflect - base_reflect_y*s_reflect, base_reflect_x*s_reflect + base_reflect_y*c_reflect
            spark_angle_deg = math.degrees(math.atan2(final_spark_dy, final_spark_dx))
            try:
                # Ensure self.color is a tuple for slicing; use fallback if not
                color_rgb_tuple = self.color[:3] if isinstance(self.color, tuple) and len(self.color) >=3 else gs.CYAN[:3]
                spark = Particle(x=impact_point[0], y=impact_point[1], color_list=[WHITE,YELLOW,(*color_rgb_tuple,alpha)],min_speed=1.0,max_speed=2.5,min_size=1,max_size=3,gravity=0.02,shrink_rate=0.2,lifetime_frames=random.randint(5,10),base_angle_deg=spark_angle_deg,spread_angle_deg=30)
                self.game_controller_ref.explosion_particles_group.add(spark)
            except Exception as e: logger.error(f"LightningZap: Error creating wall crawl particle: {e}")

    def _draw_lightning_bolt_effect(self, surface, p1, p2, base_bolt_color, alpha): # Same as before
        num_segments, outer_max_offset, outer_thickness = gs.get_game_setting("LIGHTNING_SEGMENTS",12), gs.get_game_setting("LIGHTNING_MAX_OFFSET",18), gs.get_game_setting("LIGHTNING_BASE_THICKNESS",5)
        inner_core_thickness, core_color_rgb = max(1,int(outer_thickness*gs.get_game_setting("LIGHTNING_CORE_THICKNESS_RATIO",0.4))), LIGHTNING_CORE_COLOR[:3]
        branch_chance, branch_max_segments, branch_max_offset, branch_thickness = gs.get_game_setting("LIGHTNING_BRANCH_CHANCE",0.25),gs.get_game_setting("LIGHTNING_BRANCH_MAX_SEGMENTS",5),gs.get_game_setting("LIGHTNING_BRANCH_MAX_OFFSET",10),max(1,int(inner_core_thickness*gs.get_game_setting("LIGHTNING_BRANCH_THICKNESS_RATIO",0.5)))
        dx_total, dy_total, dist_total = p2[0]-p1[0], p2[1]-p1[1], math.hypot(p2[0]-p1[0],p2[1]-p1[1])
        if dist_total == 0: return
        perp_dx, perp_dy = -dy_total/dist_total, dx_total/dist_total
        points_outer, points_inner = [p1], [p1]
        target_pull, jitter_reduct = 0.7, 0.4
        apply_bend = self.initial_target_ref and hasattr(self.initial_target_ref,'alive') and self.initial_target_ref.alive and hasattr(self.initial_target_ref,'rect')
        max_offset_outer_curr = outer_max_offset * (1.0 - jitter_reduct if apply_bend else 1.0)
        target_pos_actual = self.initial_target_ref.rect.center if apply_bend else (0,0)
        for i in range(1, num_segments + 1):
            t, straight_x, straight_y = i/num_segments, p1[0]+dx_total*t, p1[1]+dy_total*t
            rand_f, mid_f = (random.random()-0.5)*2, math.sin(t*math.pi)
            jit_out_x, jit_out_y = perp_dx*max_offset_outer_curr*rand_f*mid_f, perp_dy*max_offset_outer_curr*rand_f*mid_f
            max_offset_inner_curr = outer_max_offset*gs.get_game_setting("LIGHTNING_CORE_OFFSET_RATIO",0.3)*(1.0-jitter_reduct if apply_bend else 1.0)
            jit_in_x, jit_in_y = perp_dx*max_offset_inner_curr*rand_f*mid_f, perp_dy*max_offset_inner_curr*rand_f*mid_f
            final_out_x,final_out_y,final_in_x,final_in_y = straight_x+jit_out_x,straight_y+jit_out_y,straight_x+jit_in_x,straight_y+jit_in_y
            if apply_bend:
                vec_sl_target_x,vec_sl_target_y=target_pos_actual[0]-straight_x,target_pos_actual[1]-straight_y
                bend_disp_f=target_pull*mid_f; shift_x,shift_y=vec_sl_target_x*bend_disp_f,vec_sl_target_y*bend_disp_f
                final_out_x,final_out_y=straight_x+shift_x+jit_out_x,straight_y+shift_y+jit_out_y
                final_in_x,final_in_y=straight_x+shift_x+jit_in_x,straight_y+shift_y+jit_in_y
            points_outer.append((final_out_x,final_out_y)); points_inner.append((final_in_x,final_in_y))
        points_outer[-1],points_inner[-1]=p2,p2
        # Ensure base_bolt_color is a tuple for slicing
        bolt_rgb = base_bolt_color[:3] if isinstance(base_bolt_color, tuple) and len(base_bolt_color) >=3 else gs.CYAN[:3]
        if len(points_outer)>1 and outer_thickness>0: pygame.draw.lines(surface,(*bolt_rgb,int(alpha*0.65)),False,points_outer,outer_thickness)
        if len(points_inner)>1 and inner_core_thickness>0: pygame.draw.lines(surface,(*core_color_rgb,alpha),False,points_inner,inner_core_thickness)
        for i in range(len(points_inner)-1):
            if random.random()<branch_chance:
                branch_start=points_inner[i]; seg_dx,seg_dy=points_inner[i+1][0]-branch_start[0],points_inner[i+1][1]-branch_start[1]; seg_len=math.hypot(seg_dx,seg_dy)
                if seg_len==0:continue
                b_perp_dx,b_perp_dy=-seg_dy/seg_len,seg_dx/seg_len; angle_p=random.uniform(-math.pi/3,math.pi/3); c,s=math.cos(angle_p),math.sin(angle_p)
                f_branch_dx,f_branch_dy=b_perp_dx*c-b_perp_dy*s,b_perp_dx*s+b_perp_dy*c
                if random.random()<0.5: f_branch_dx*=-1; f_branch_dy*=-1
                branch_pts=[branch_start]; cur_b_pos=list(branch_start); b_seg_len_base=dist_total/num_segments*random.uniform(0.3,0.7)
                for j in range(random.randint(1,branch_max_segments)):
                    cur_b_seg_len=b_seg_len_base*(1-(j/branch_max_segments)*0.5); cur_b_pos[0]+=f_branch_dx*cur_b_seg_len; cur_b_pos[1]+=f_branch_dy*cur_b_seg_len
                    b_offset_mag=random.uniform(-branch_max_offset,branch_max_offset)*math.sin(((j+1)/branch_max_segments)*math.pi)
                    b_jag_x,b_jag_y=perp_dx*b_offset_mag,perp_dy*b_offset_mag; branch_pts.append((cur_b_pos[0]+b_jag_x,cur_b_pos[1]+b_jag_y))
                    if len(branch_pts)>branch_max_segments:break
                if len(branch_pts)>1 and branch_thickness>0: pygame.draw.lines(surface,(*core_color_rgb,int(alpha*0.8)),False,branch_pts,branch_thickness)
        if self.hit_wall_at_end:
            inc_vec_x,inc_vec_y=self.potential_end_pos_no_wall[0]-p2[0],self.potential_end_pos_no_wall[1]-p2[1]; len_inc=math.hypot(inc_vec_x,inc_vec_y)
            if len_inc>0: self._draw_wall_crawl_effect(surface,p2,(inc_vec_x/len_inc,inc_vec_y/len_inc),alpha)

    def draw(self, surface):
        if self.alive:
            current_alpha_perc = 1.0 - (self.frames_existed / self.lifetime_frames)
            current_alpha = int(255 * (current_alpha_perc ** 1.5))
            current_alpha = int(max(0, min(255, current_alpha)))
            if current_alpha > 5:
                self._draw_lightning_bolt_effect(surface, self.current_start_pos, self.current_target_pos, self.color, current_alpha)
            # Fallback debug draw (blue line) - Uncomment if needed
            # elif self.rect:
            #     try: fallback_color_tuple = (*self.color[:3], 100) if isinstance(self.color, tuple) and len(self.color) >=3 else gs.CYAN
            #     except TypeError: fallback_color_tuple = gs.CYAN
            #     pygame.draw.line(surface, fallback_color_tuple, self.current_start_pos, self.current_target_pos, 3)
