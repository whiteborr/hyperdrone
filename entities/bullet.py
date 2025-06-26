# entities/bullet.py
from math import radians, cos, sin, degrees, atan2, hypot
from random import uniform
from pygame import Surface, SRCALPHA
from pygame.draw import circle, polygon, rect as draw_rect
from pygame.time import get_ticks
from pygame.transform import rotate
from logging import getLogger, error

# Import from settings_manager for settings access
from settings_manager import get_setting
from constants import PLAYER_BULLET_COLOR, RED, MISSILE_COLOR, LIGHTNING_COLOR, WHITE

try:
    from .particle import Particle
except ImportError:
    error("Bullet: Could not import Particle from .particle. Using placeholder.")
    from pygame.sprite import Sprite
    class Particle(Sprite): pass

logger = getLogger(__name__)


from pygame.sprite import Sprite

class Bullet(Sprite):
    def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False, bullet_type=None):
        super().__init__()
        self.x, self.y, self.angle, self.speed = float(x), float(y), float(angle), float(speed)
        self.lifetime, self.initial_lifetime, self.size = int(lifetime), int(lifetime), max(1, int(size))
        self.color = color if color else PLAYER_BULLET_COLOR
        # Apply 3x damage multiplier for 'Big Shot' bullets
        if bullet_type == 'Big Shot':
            self.damage = int(damage) * 4
        else:
            self.damage = int(damage)
        self.max_bounces, self.bounces_done = int(max_bounces), 0
        self.max_pierces, self.pierces_done = int(max_pierces), 0
        self.can_pierce_walls = can_pierce_walls
        self.alive, self.frames_existed = True, 0
        # Create a completely transparent surface
        surface_dim = max(1, self.size * 2)
        self.image = Surface([surface_dim, surface_dim], SRCALPHA)
        self.image.fill((0,0,0,0))
        # Draw the bullet
        draw_radius = max(1, self.size)
        try:
            circle(self.image, self.color, (surface_dim // 2, surface_dim // 2), draw_radius)
        except TypeError:
            circle(self.image, RED, (surface_dim // 2, surface_dim // 2), draw_radius)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        rad_angle = radians(self.angle)
        self.dx = cos(rad_angle) * self.speed
        self.dy = sin(rad_angle) * self.speed

    def _ensure_drawable_state(self):
        # This method is no longer used, initialization is done directly in __init__
        pass

    def update(self, maze=None, game_area_x_offset=0, shmup_mode=False):
        if not self.alive:
            return
        
        self.frames_existed += 1
        next_pos = self._calculate_next_position()
        collided = self._handle_wall_collision(maze, next_pos)
        
        if self.alive and not collided:
            self.x, self.y = next_pos
        
        self.rect.center = (int(self.x), int(self.y))
        self._update_lifetime(shmup_mode)
        self._check_bounds(game_area_x_offset)
        self._update_image_if_needed()
        
        if not self.alive:
            self.kill()
    
    def _calculate_next_position(self):
        return (self.x + self.dx, self.y + self.dy)
    
    def _handle_wall_collision(self, maze, next_pos):
        if not maze or self.can_pierce_walls:
            return False
        
        bullet_diameter = self.size * 2
        if not maze.is_wall(next_pos[0], next_pos[1], bullet_diameter, bullet_diameter):
            return False
        
        if self.bounces_done >= self.max_bounces:
            self.alive = False
            return True
        
        self._bounce_off_wall(maze, bullet_diameter)
        return True
    
    def _bounce_off_wall(self, maze, bullet_diameter):
        self.bounces_done += 1
        hit_x_wall = maze.is_wall(self.x + self.dx, self.y, bullet_diameter, bullet_diameter)
        hit_y_wall = maze.is_wall(self.x, self.y + self.dy, bullet_diameter, bullet_diameter)
        
        if hit_x_wall:
            self.dx *= -1
        if hit_y_wall:
            self.dy *= -1
        if not hit_x_wall and not hit_y_wall:
            self.dx *= -1
            self.dy *= -1
        
        self.angle = degrees(atan2(self.dy, self.dx))
    
    def _update_lifetime(self, shmup_mode):
        if not shmup_mode:
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.alive = False
    
    def _check_bounds(self, game_area_x_offset):
        if not self.alive:
            return
        
        game_height = get_setting("display", "HEIGHT", 1080)
        game_width = get_setting("display", "WIDTH", 1920)
        
        center_x, center_y = self.rect.centerx, self.rect.centery
        half_size = self.size
        
        in_x_bounds = game_area_x_offset < center_x - half_size and center_x + half_size < game_width
        in_y_bounds = 0 < center_y - half_size and center_y + half_size < game_height
        
        if not (in_x_bounds and in_y_bounds):
            self.alive = False
    
    def _update_image_if_needed(self):
        if not self.alive or not (self.frames_existed == 1 or self.bounces_done > 0):
            return
        
        surface_dim = max(1, self.size * 2)
        self.image = Surface([surface_dim, surface_dim], SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        
        draw_radius = max(1, self.size)
        center = (surface_dim // 2, surface_dim // 2)
        
        try:
            circle(self.image, self.color, center, draw_radius)
        except TypeError:
            circle(self.image, RED, center, draw_radius)

    def draw(self, surface, camera=None):
        if self.alive and self.image and self.rect:
            if camera:
                surface.blit(self.image, camera.apply_to_rect(self.rect))
            else:
                surface.blit(self.image, self.rect)


class Missile(Sprite):
    def __init__(self, x, y, initial_angle, damage, enemies_group):
        super().__init__()
        self.id = id(self)
        self.x = float(x)
        self.y = float(y)
        self.angle = float(initial_angle)
        self.target_angle = float(initial_angle)
        
        self.speed = get_setting("weapons", "MISSILE_SPEED", 5)
        self.lifetime = get_setting("weapons", "MISSILE_LIFETIME", 3000)
        self.damage = get_setting("weapons", "MISSILE_DAMAGE", damage)
        self.turn_rate = get_setting("weapons", "MISSILE_TURN_RATE", 8)
        
        self.enemies_group = enemies_group
        self.target = None
        self.alive = True
        self.frames_existed = 0
        
        self.is_sliding = False
        self.slide_direction_attempts = 0
        self.MAX_SLIDE_ATTEMPTS = 3
        
        self._create_missile_image()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._update_image_and_rect()
    
    def _create_missile_image(self):
        missile_size = get_setting("weapons", "MISSILE_SIZE", 8)
        missile_w = missile_size * 1.5
        missile_h = missile_size * 3
        
        self.original_image_surface = Surface([missile_w, missile_h], SRCALPHA)
        
        self._draw_exhaust_flame(missile_w, missile_h)
        self._draw_rocket_body(missile_w, missile_h)
        self._draw_nose_cone(missile_w, missile_h)
        self._draw_fins(missile_w, missile_h)
        
        self.original_image = rotate(self.original_image_surface, -90)
        self.image = self.original_image
    
    def _draw_exhaust_flame(self, missile_w, missile_h):
        flame_points = [
            (missile_w * 0.5, missile_h),
            (missile_w * 0.2, missile_h * 0.8),
            (missile_w * 0.8, missile_h * 0.8)
        ]
        polygon(self.original_image_surface, (255, 100, 0), flame_points)
        
        inner_flame_points = [
            (missile_w * 0.5, missile_h * 0.95),
            (missile_w * 0.35, missile_h * 0.8),
            (missile_w * 0.65, missile_h * 0.8)
        ]
        polygon(self.original_image_surface, (255, 200, 0), inner_flame_points)
    
    def _draw_rocket_body(self, missile_w, missile_h):
        from pygame import Rect as PygameRect
        body_rect = PygameRect(
            missile_w * 0.25,
            missile_h * 0.15,
            missile_w * 0.5,
            missile_h * 0.65
        )
        draw_rect(self.original_image_surface, WHITE, body_rect)
    
    def _draw_nose_cone(self, missile_w, missile_h):
        nose_points = [
            (missile_w * 0.5, 0),
            (missile_w * 0.25, missile_h * 0.15),
            (missile_w * 0.75, missile_h * 0.15)
        ]
        polygon(self.original_image_surface, WHITE, nose_points)
    
    def _draw_fins(self, missile_w, missile_h):
        left_fin = [
            (missile_w * 0.1, missile_h * 0.7),
            (missile_w * 0.25, missile_h * 0.6),
            (missile_w * 0.25, missile_h * 0.8)
        ]
        right_fin = [
            (missile_w * 0.9, missile_h * 0.7),
            (missile_w * 0.75, missile_h * 0.6),
            (missile_w * 0.75, missile_h * 0.8)
        ]
        polygon(self.original_image_surface, WHITE, left_fin)
        polygon(self.original_image_surface, WHITE, right_fin) 

    def _update_image_and_rect(self):
        self.image = rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _find_target(self):
        if not self.enemies_group:
            return None
        
        closest_enemy = None
        min_dist_sq = float('inf')
        
        for enemy in self.enemies_group:
            if not self._is_valid_target(enemy):
                continue
            
            dist_sq = (enemy.rect.centerx - self.x) ** 2 + (enemy.rect.centery - self.y) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        
        return closest_enemy
    
    def _is_valid_target(self, enemy):
        if hasattr(enemy, 'alive') and not enemy.alive:
            return False
        if not hasattr(enemy, 'rect'):
            return False
        return True
        
    def _attempt_slide(self, maze, next_x_direct, next_y_direct, direct_rad_angle):
        collision_width = self.rect.width * 0.6 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        collision_height = self.rect.height * 0.6 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        current_rad_angle = radians(self.angle)
        
        for da_deg in [30, 60, 45, 75, 90]:
            for sign in [1, -1]:
                angle_rad = current_rad_angle + radians(da_deg * sign)
                s_dx = cos(angle_rad) * self.speed
                s_dy = sin(angle_rad) * self.speed
                
                if self._can_slide_to_position(maze, s_dx, s_dy, collision_width, collision_height):
                    self.angle = degrees(atan2(s_dy, s_dx))
                    return s_dx, s_dy
        
        return None
    
    def _can_slide_to_position(self, maze, s_dx, s_dy, collision_width, collision_height):
        pos1_clear = not maze.is_wall(self.x + s_dx, self.y + s_dy, collision_width, collision_height)
        pos2_clear = not maze.is_wall(self.x + s_dx * 1.5, self.y + s_dy * 1.5, collision_width, collision_height)
        return pos1_clear and pos2_clear

    def update(self, enemies_group_updated=None, maze=None, game_area_x_offset=0, shmup_mode=False):
        if not self.alive:
            return
        
        self.frames_existed += 1
        
        if enemies_group_updated is not None:
            self.enemies_group = enemies_group_updated
        
        self._update_target()
        self._update_angle_towards_target()
        
        next_pos = self._calculate_next_position()
        collided = self._handle_collision(maze, next_pos)
        
        if self.alive and not collided:
            self.x, self.y = next_pos
        
        self._update_image_and_rect()
        self._update_lifetime_and_bounds(shmup_mode, game_area_x_offset)
        
        if not self.alive:
            self.kill()
    
    def _update_target(self):
        if not self.target or (hasattr(self.target, 'alive') and not self.target.alive):
            self.target = self._find_target()
            self.is_sliding = False
    
    def _update_angle_towards_target(self):
        if not self.target or self.is_sliding:
            return
        
        target_x, target_y = self.target.rect.center
        dx_to_target = target_x - self.x
        dy_to_target = target_y - self.y
        
        if dx_to_target != 0 or dy_to_target != 0:
            self.target_angle = degrees(atan2(dy_to_target, dx_to_target))
        else:
            self.target_angle = self.angle
        
        angle_diff = (self.target_angle - self.angle + 180) % 360 - 180
        turn_amount = max(-self.turn_rate, min(self.turn_rate, angle_diff))
        self.angle = (self.angle + turn_amount + 360) % 360
    
    def _calculate_next_position(self):
        effective_angle_rad = radians(self.angle)
        potential_dx = cos(effective_angle_rad) * self.speed
        potential_dy = sin(effective_angle_rad) * self.speed
        return (self.x + potential_dx, self.y + potential_dy)
    
    def _handle_collision(self, maze, next_pos):
        if not maze:
            return False
        
        collision_width = self.rect.width * 0.7 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        collision_height = self.rect.height * 0.7 if self.rect else get_setting("weapons", "MISSILE_SIZE", 8)
        
        if not maze.is_wall(next_pos[0], next_pos[1], collision_width, collision_height):
            self.is_sliding = False
            self.slide_direction_attempts = 0
            return False
        
        return self._attempt_slide_or_die(maze, next_pos)
    
    def _attempt_slide_or_die(self, maze, next_pos):
        if self.slide_direction_attempts >= self.MAX_SLIDE_ATTEMPTS:
            self.alive = False
            return True
        
        slide_movement = self._attempt_slide(maze, next_pos[0], next_pos[1], radians(self.angle))
        if slide_movement:
            self.x += slide_movement[0]
            self.y += slide_movement[1]
            self.is_sliding = True
            self.slide_direction_attempts += 1
            return False
        else:
            self.alive = False
            return True
    
    def _update_lifetime_and_bounds(self, shmup_mode, game_area_x_offset):
        if not shmup_mode:
            self.lifetime -= 1
        
        out_of_bounds = self._is_out_of_bounds(game_area_x_offset)
        
        if (not shmup_mode and self.lifetime <= 0) or out_of_bounds:
            self.alive = False
    
    def _is_out_of_bounds(self, game_area_x_offset):
        if not self.rect:
            return True
        
        game_width = get_setting("display", "WIDTH", 1920)
        game_height = get_setting("display", "HEIGHT", 1080)
        
        x_in_bounds = game_area_x_offset - self.rect.width < self.rect.centerx < game_width + self.rect.width
        y_in_bounds = -self.rect.height < self.rect.centery < game_height + self.rect.height
        
        return not (x_in_bounds and y_in_bounds)

    def draw(self, surface, camera=None):
        if self.alive and self.image and self.rect:
            if camera:
                surface.blit(self.image, camera.apply_to_rect(self.rect))
            else:
                surface.blit(self.image, self.rect)


class LightningZap(Sprite):
    def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None, enemies_group=None):
        super().__init__()
        self.id = id(self)
        
        self._initialize_references(player_ref, initial_target_enemy_ref, maze_ref, enemies_group)
        self._initialize_properties(damage, lifetime_frames, color_override, game_area_x_offset)
        self._initialize_positions()
        self._build_chain()
        self._finalize_initialization()
    
    def _initialize_references(self, player_ref, initial_target_enemy_ref, maze_ref, enemies_group):
        self.player_ref = player_ref
        self.initial_target_ref = initial_target_enemy_ref
        self.maze_ref = maze_ref
        self.enemies_group = enemies_group
        self.game_controller_ref = getattr(player_ref, 'game_controller_ref', None)
    
    def _initialize_properties(self, damage, lifetime_frames, color_override, game_area_x_offset):
        self.damage = 9999  # One-shot kill damage
        self.lifetime_frames = int(lifetime_frames)
        self.frames_existed = 0
        self.alive = True
        self.color = color_override if color_override is not None else LIGHTNING_COLOR
        self.game_area_x_offset = game_area_x_offset
        
        self.damage_applied = False
        self.chain_targets = []
        self.chain_range = get_setting("weapons", "LIGHTNING_CHAIN_RANGE", 150)
        self.chain_damage_applied = False
    
    def _initialize_positions(self):
        self.current_start_pos = self._get_player_position()
        self.initial_target_pos_snapshot = self._get_initial_target_position()
    
    def _get_player_position(self):
        if self.player_ref and hasattr(self.player_ref, 'rect'):
            return self.player_ref.rect.center
        return (0, 0)
    
    def _get_initial_target_position(self):
        if self.initial_target_ref and hasattr(self.initial_target_ref, 'rect'):
            return self.initial_target_ref.rect.center
        return None
    
    def _finalize_initialization(self):
        self.current_target_pos = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, self.current_target_pos)
        self.hit_wall_at_end = (self.current_target_pos != self._calculate_potential_target_pos(ignore_snapshot=True))
        
        self.image = Surface((1, 1), SRCALPHA)
        self.rect = self.image.get_rect(center=self.current_start_pos)
        self._update_rect_for_collision() 

    def _get_wall_collision_point(self, start_point, end_point):
        if not self.maze_ref:
            return end_point
        
        dx, dy = end_point[0] - start_point[0], end_point[1] - start_point[1]
        distance = hypot(dx, dy)
        
        if distance == 0:
            return start_point
        
        dir_x, dir_y = dx / distance, dy / distance
        current_pos = list(start_point)
        
        for _ in range(int(distance)):
            if self.maze_ref.is_wall(current_pos[0], current_pos[1], 1, 1):
                return tuple(current_pos)
            current_pos[0] += dir_x
            current_pos[1] += dir_y
        
        return end_point

    def _calculate_potential_target_pos(self, ignore_snapshot=False):
        if self._has_living_initial_target():
            return self.initial_target_ref.rect.center
        
        if self.initial_target_pos_snapshot and not ignore_snapshot:
            return self.initial_target_pos_snapshot
        
        return self._calculate_fallback_position()
    
    def _has_living_initial_target(self):
        return (self.initial_target_ref and 
                hasattr(self.initial_target_ref, 'alive') and 
                self.initial_target_ref.alive)
    
    def _calculate_fallback_position(self):
        start_x, start_y = self.current_start_pos
        angle_rad = radians(self.player_ref.angle)
        lightning_range = get_setting("weapons", "LIGHTNING_ZAP_RANGE", 250)
        
        end_x = start_x + cos(angle_rad) * lightning_range
        end_y = start_y + sin(angle_rad) * lightning_range
        
        return (end_x, end_y)

    def _update_rect_for_collision(self):
        all_x = [self.current_start_pos[0], self.current_target_pos[0]]
        all_y = [self.current_start_pos[1], self.current_target_pos[1]]
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        padding = (get_setting("weapons", "LIGHTNING_MAX_OFFSET", 18) + 
                  get_setting("weapons", "LIGHTNING_BASE_THICKNESS", 5))
        
        from pygame import Rect as PygameRect
        self.rect = PygameRect(
            int(min_x - padding),
            int(min_y - padding),
            int(max_x - min_x + 2 * padding),
            int(max_y - min_y + 2 * padding)
        )

    def _build_chain(self):
        """Build chain of lightning targets"""
        if not self.initial_target_ref or not self.enemies_group:
            return
        
        visited = set()
        current_target = self.initial_target_ref
        
        while current_target and current_target not in visited:
            if self._is_boss_enemy(current_target):
                break
            
            visited.add(current_target)
            self.chain_targets.append(current_target)
            current_target = self._find_next_chain_target(current_target, visited)
    
    def _is_boss_enemy(self, enemy):
        if hasattr(enemy, 'enemy_type') and 'boss' in enemy.enemy_type.lower():
            return True
        if hasattr(enemy, '__class__') and 'guardian' in enemy.__class__.__name__.lower():
            return True
        return False
    
    def _find_next_chain_target(self, current_target, visited):
        next_target = None
        min_dist = float('inf')
        current_pos = current_target.rect.center
        
        for enemy in self.enemies_group:
            if not self._is_valid_chain_target(enemy, visited):
                continue
            
            dist = self._calculate_distance(enemy.rect.center, current_pos)
            if dist < self.chain_range and dist < min_dist:
                min_dist = dist
                next_target = enemy
        
        return next_target
    
    def _is_valid_chain_target(self, enemy, visited):
        if enemy in visited or not enemy.alive:
            return False
        if self._is_boss_enemy(enemy):
            return False
        return True
    
    def _calculate_distance(self, pos1, pos2):
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return hypot(dx, dy)
    
    def _apply_chain_damage(self):
        """Apply damage to all targets in the chain"""
        for target in self.chain_targets:
            if target.alive:
                target.health -= self.damage
                if target.health <= 0:
                    target.alive = False
    
    def update(self, current_time_ms):
        if not self.alive:
            self.kill()
            return
        
        if not self._is_player_alive():
            self.alive = False
            self.kill()
            return
        
        self.frames_existed += 1
        
        self._apply_damage_on_first_frame()
        
        if self._is_lifetime_expired():
            self.alive = False
            self.kill()
            return
        
        self._update_positions()
    
    def _is_player_alive(self):
        return self.player_ref and self.player_ref.alive
    
    def _apply_damage_on_first_frame(self):
        if self.frames_existed == 1 and not self.chain_damage_applied:
            self._apply_chain_damage()
            self.chain_damage_applied = True
    
    def _is_lifetime_expired(self):
        return self.frames_existed >= self.lifetime_frames
    
    def _update_positions(self):
        self.current_start_pos = self.player_ref.rect.center
        target_pos = self._calculate_potential_target_pos()
        self.current_target_pos = self._get_wall_collision_point(self.current_start_pos, target_pos)
        self._update_rect_for_collision()

    def kill(self):
        super().kill()
        self.alive = False 

    def _draw_lightning_bolt(self, surface, p1, p2, color, alpha):
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        dist = hypot(dx, dy)
        
        if dist < 10:
            self._draw_simple_line(surface, p1, p2, color, alpha)
            return
        
        points = self._generate_lightning_points(p1, p2, dx, dy, dist)
        self._draw_lightning_lines(surface, points, color, alpha)
    
    def _draw_simple_line(self, surface, p1, p2, color, alpha):
        from pygame.draw import line
        line(surface, (*color[:3], alpha), p1, p2, 2)
    
    def _generate_lightning_points(self, p1, p2, dx, dy, dist):
        points = [p1]
        
        # Calculate perpendicular direction for offsets
        nx, ny = -dy / dist, dx / dist
        segments = get_setting("weapons", "LIGHTNING_SEGMENTS", 12)
        max_offset = get_setting("weapons", "LIGHTNING_MAX_OFFSET", 18)
        
        for i in range(1, segments):
            percent = i / segments
            mid_x = p1[0] + dx * percent
            mid_y = p1[1] + dy * percent
            
            offset = uniform(-max_offset, max_offset)
            mid_x += nx * offset
            mid_y += ny * offset
            
            points.append((mid_x, mid_y))
        
        points.append(p2)
        return points
    
    def _draw_lightning_lines(self, surface, points, color, alpha):
        if len(points) <= 1:
            return
        
        from pygame.draw import lines
        thickness = get_setting("weapons", "LIGHTNING_BASE_THICKNESS", 5)
        
        # Draw main lightning bolt
        lines(surface, (*color[:3], alpha), False, points, thickness)
        
        # Draw inner core
        core_thickness_ratio = get_setting("weapons", "LIGHTNING_CORE_THICKNESS_RATIO", 0.4)
        core_thickness = int(thickness * core_thickness_ratio)
        
        if core_thickness > 0:
            core_color = get_setting("weapons", "LIGHTNING_CORE_COLOR", (255, 255, 255))
            lines(surface, (*core_color[:3], alpha), False, points, core_thickness)

    def draw(self, surface, camera=None):
        if not self.alive:
            return
        
        alpha = self._calculate_alpha()
        if alpha <= 5:
            return
        
        self._draw_main_lightning(surface, alpha)
        self._draw_chain_lightning(surface, alpha)
    
    def _calculate_alpha(self):
        fade_ratio = 1.0 - (self.frames_existed / self.lifetime_frames)
        return int(255 * fade_ratio)
    
    def _draw_main_lightning(self, surface, alpha):
        if self.chain_targets and self.chain_targets[0].alive:
            target_pos = self.chain_targets[0].rect.center
        else:
            target_pos = self.current_target_pos
        
        self._draw_lightning_bolt(surface, self.current_start_pos, target_pos, self.color, alpha)
    
    def _draw_chain_lightning(self, surface, alpha):
        chain_alpha = alpha // 2
        
        for i in range(len(self.chain_targets) - 1):
            current_target = self.chain_targets[i]
            next_target = self.chain_targets[i + 1]
            
            if current_target.alive and next_target.alive:
                start_pos = current_target.rect.center
                end_pos = next_target.rect.center
                self._draw_lightning_bolt(surface, start_pos, end_pos, self.color, chain_alpha)

class LaserBeam(Sprite):
    """A persistent laser beam fired by the Maze Guardian."""
    def __init__(self, start_pos, angle):
        super().__init__()
        self.start_pos = start_pos
        self.angle = angle
        self.length = get_setting("display", "WIDTH", 1920) * 1.5
        self.width = get_setting("bosses", "MAZE_GUARDIAN_LASER_WIDTH", 10)
        self.damage = get_setting("bosses", "MAZE_GUARDIAN_LASER_DAMAGE", 2)
        self.lifetime = get_setting("bosses", "MAZE_GUARDIAN_LASER_LIFETIME_MS", 1000)
        self.creation_time = get_ticks()
        self.alive = True

        # Visual properties
        self.outer_color = (*get_setting("colors", "RED", (255, 0, 0)), 100)
        self.inner_color = (*get_setting("colors", "WHITE", (255, 255, 255)), 200)
        self.inner_width_ratio = 0.4

        # Create the visual representation of the laser
        self.original_image = self._create_laser_surface()
        self.image = rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=self.start_pos)

    def _create_laser_surface(self):
        """Creates the surface for the laser with a glowing effect."""
        laser_surface = Surface((self.length, self.width), SRCALPHA)
        
        # Outer glow/beam
        from pygame import Rect as PygameRect
        outer_rect = PygameRect(0, 0, self.length, self.width)
        draw_rect(laser_surface, self.outer_color, outer_rect, border_radius=int(self.width/2))

        # Inner core
        inner_width = self.width * self.inner_width_ratio
        inner_height = self.width * self.inner_width_ratio
        inner_rect = PygameRect(0, (self.width - inner_height) / 2, self.length, inner_height)
        draw_rect(laser_surface, self.inner_color, inner_rect, border_radius=int(inner_height/2))
        
        return laser_surface

    def update(self):
        """The laser fades out over its lifetime."""
        if not self.alive:
            return
            
        time_elapsed = get_ticks() - self.creation_time
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
