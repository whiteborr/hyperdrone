# entities/player.py
import pygame
import math
import os
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, HEIGHT, GAME_PLAY_AREA_HEIGHT,
    WEAPON_MODES_SEQUENCE, INITIAL_WEAPON_MODE,
    PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BIG_BULLET_SIZE,
    PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN,
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES,
    MISSILE_COOLDOWN, MISSILE_DAMAGE,
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_ZAP_RANGE,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE,
    WEAPON_MODE_RAPID_TRI, WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE,
    WEAPON_MODE_PIERCE, WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING, POWERUP_TYPES,
    PHANTOM_CLOAK_ALPHA_SETTING, PHANTOM_CLOAK_DURATION_MS, PHANTOM_CLOAK_COOLDOWN_MS,
    GREEN, YELLOW, RED, WHITE, LIGHT_BLUE, ORANGE, CYAN, ELECTRIC_BLUE,
    PLAYER_SPEED, PLAYER_MAX_HEALTH, ROTATION_SPEED,
    PLAYER_BULLET_COLOR, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
    MISSILE_COLOR,
    LIGHTNING_COLOR, CORE_FRAGMENT_DETAILS,
    SPEED_BOOST_POWERUP_DURATION, SHIELD_POWERUP_DURATION,
    FLAME_COLORS,
    THRUST_PARTICLE_SPREAD_ANGLE,
    THRUST_PARTICLE_LIFETIME_BLAST,
    THRUST_PARTICLE_START_SIZE_BLAST_MIN,
    THRUST_PARTICLE_START_SIZE_BLAST_MAX,
    THRUST_PARTICLE_SPEED_MIN_BLAST,
    THRUST_PARTICLE_SPEED_MAX_BLAST,
    THRUST_PARTICLE_SHRINK_RATE_BLAST,
    get_game_setting
)
try:
    from .bullet import Bullet, Missile, LightningZap
    from .particle import Particle
except ImportError:
    # Minimal placeholder if these classes are not found (should not happen in full project)
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass
    class Particle(pygame.sprite.Sprite): pass


try:
    from .base_drone import BaseDrone
except ImportError:
    # Minimal placeholder for BaseDrone if not found
    class BaseDrone(pygame.sprite.Sprite):
        def __init__(self, x,y,speed, size=None):
            super().__init__()
            self.x = x
            self.y = y
            self.speed = speed
            self.angle = 0.0
            self.moving_forward = False
            self.alive = True
            self.size = size if size is not None else TILE_SIZE * 0.8
            self.rect = pygame.Rect(x - self.size / 2, y - self.size / 2, self.size, self.size)
            self.collision_rect = self.rect.copy()

        def update_movement(self, maze=None, game_area_x_offset=0):
            if self.moving_forward and self.alive:
                angle_rad = math.radians(self.angle)
                dx = math.cos(angle_rad) * self.speed
                dy = math.sin(angle_rad) * self.speed
                next_x = self.x + dx
                next_y = self.y + dy
                collided = False
                if maze and self.collision_rect: 
                    temp_collision_rect = self.collision_rect.copy()
                    temp_collision_rect.center = (next_x, next_y)
                    if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                    self.collision_rect.width, self.collision_rect.height):
                        collided = True
                if not collided:
                    self.x = next_x
                    self.y = next_y
                else:
                    self.moving_forward = False
            if self.collision_rect and self.rect: 
                half_col_width = self.collision_rect.width / 2
                half_col_height = self.collision_rect.height / 2
                min_x_bound = game_area_x_offset + half_col_width
                max_x_bound = WIDTH - half_col_width
                min_y_bound = half_col_height
                max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height
                self.x = max(min_x_bound, min(self.x, max_x_bound))
                self.y = max(min_y_bound, min(self.y, max_y_bound))
                self.rect.center = (int(self.x), int(self.y))
                self.collision_rect.center = self.rect.center


class PlayerDrone(BaseDrone): 
    def __init__(self, x, y, drone_id, drone_stats, drone_sprite_path, crash_sound, drone_system):
        base_speed_from_stats = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.drone_visual_size = (int(TILE_SIZE * 0.7), int(TILE_SIZE * 0.7)) 
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats)
        self.drone_id = drone_id
        self.drone_system = drone_system  
        self.x = float(x) 
        self.y = float(y)
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = base_speed_from_stats
        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")  
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0) 
        self.max_health = self.base_hp
        self.health = self.max_health
        self.current_speed = self.speed  
        self.rotation_speed = self.base_turn_speed
        self.original_image = None 
        self.image = None 
        self._load_sprite(drone_sprite_path)  
        initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self.bullets_group = pygame.sprite.Group() 
        self.missiles_group = pygame.sprite.Group() 
        self.lightning_zaps_group = pygame.sprite.Group() 
        self.last_shot_time = 0 
        self.last_missile_shot_time = 0 
        self.last_lightning_time = 0 
        self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN")
        self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN")
        self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        self._update_weapon_attributes() 
        self.active_powerup_type = None 
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = get_game_setting("SHIELD_POWERUP_DURATION")  
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) 
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.speed_boost_multiplier = POWERUP_TYPES.get("speed_boost", {}).get("multiplier", 1.8)
        self.original_speed_before_boost = self.speed 
        self.shield_tied_to_speed_boost = False 
        self.thrust_particles = pygame.sprite.Group()
        self.thrust_particle_spawn_timer = 0
        self.THRUST_PARTICLE_SPAWN_INTERVAL = 25 
        self.PARTICLES_PER_EMISSION = random.randint(2, 4) 
        self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4 
        self.cloak_active = False 
        self.cloak_start_time = 0  
        self.cloak_end_time = 0 
        self.last_cloak_activation_time = -float('inf')  
        self.cloak_cooldown_end_time = 0  
        self.is_cloaked_visual = False  
        self.phantom_cloak_alpha = get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING")
        self.phantom_cloak_duration_ms = get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")
        self.crash_sound = crash_sound 
        if self.rect:
            self.collision_rect_width = self.rect.width * 0.7 
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: 
            col_size = self.size * 0.7
            self.collision_rect_width = col_size
            self.collision_rect_height = col_size
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2,
                                               col_size, col_size)

    def _load_sprite(self, sprite_path):
        default_size = self.drone_visual_size
        loaded_successfully = False
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, default_size)
                loaded_successfully = True
            except pygame.error as e:
                print(f"Error loading player sprite '{sprite_path}': {e}") 
        if not loaded_successfully:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            self.original_image.fill((0, 200, 0, 150)) 
            pygame.draw.circle(self.original_image, (255,255,255), (default_size[0]//2, default_size[1]//2), default_size[0]//3, 2) 
        self.image = self.original_image.copy() 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if self.rect:
            self.drone_visual_size = self.rect.size 
            self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: 
            col_size = self.size * 0.7
            self.collision_rect_width = col_size
            self.collision_rect_height = col_size
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2, col_size, col_size)

    def _update_weapon_attributes(self):
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.bullet_size = get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5 
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        else: 
            self.bullet_size = get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        if self.base_fire_rate_multiplier != 0:
            effective_fr_mult = self.base_fire_rate_multiplier
            if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
                for frag_id in self.drone_system.get_collected_fragments_ids():
                    frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                    if frag_conf and frag_conf.get("buff", {}).get("type") == "fire_rate":
                        effective_fr_mult *= frag_conf["buff"]["value"] 
            self.current_shoot_cooldown /= effective_fr_mult 
            self.current_missile_cooldown = get_game_setting("MISSILE_COOLDOWN") / effective_fr_mult
            self.current_lightning_cooldown = get_game_setting("LIGHTNING_COOLDOWN") / effective_fr_mult
        else: 
            self.current_shoot_cooldown = float('inf')
            self.current_missile_cooldown = float('inf')
            self.current_lightning_cooldown = float('inf')

    def _emit_thrust_particles(self, current_time_ms):
        if self.speed_boost_active and self.moving_forward:
            if current_time_ms > self.thrust_particle_spawn_timer:
                self.thrust_particle_spawn_timer = current_time_ms + self.THRUST_PARTICLE_SPAWN_INTERVAL
                num_particles_to_spawn = self.PARTICLES_PER_EMISSION
                emission_base_angle_deg = (self.angle + 180) % 360 
                emission_angle_rad_for_offset = math.radians(self.angle + 180)
                offset_x = math.cos(emission_angle_rad_for_offset) * self.flame_port_offset_distance
                offset_y = math.sin(emission_angle_rad_for_offset) * self.flame_port_offset_distance
                for _ in range(num_particles_to_spawn):
                    particle = Particle(
                        x=self.x, y=self.y, color_list=gs.FLAME_COLORS, 
                        min_speed=gs.get_game_setting("THRUST_PARTICLE_SPEED_MIN_BLAST"),
                        max_speed=gs.get_game_setting("THRUST_PARTICLE_SPEED_MAX_BLAST"),
                        min_size=gs.get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MIN"),
                        max_size=gs.get_game_setting("THRUST_PARTICLE_START_SIZE_BLAST_MAX"),
                        lifetime_frames=gs.get_game_setting("THRUST_PARTICLE_LIFETIME_BLAST"),
                        base_angle_deg=emission_base_angle_deg,
                        spread_angle_deg=gs.get_game_setting("THRUST_PARTICLE_SPREAD_ANGLE"),
                        x_offset=offset_x, y_offset=offset_y, blast_mode=True 
                    )
                    self.thrust_particles.add(particle)

    def _update_thrust_particles(self):
        self.thrust_particles.update()

    def update_movement(self, maze=None, game_area_x_offset=0):
        if self.moving_forward and self.alive:
            angle_rad = math.radians(self.angle)
            dx = math.cos(angle_rad) * self.current_speed 
            dy = math.sin(angle_rad) * self.current_speed
            next_x = self.x + dx
            next_y = self.y + dy
            collided_with_wall = False
            if maze and self.collision_rect: 
                temp_collision_rect = self.collision_rect.copy()
                temp_collision_rect.center = (next_x, next_y)
                if maze.is_wall(temp_collision_rect.centerx, temp_collision_rect.centery,
                                self.collision_rect.width, self.collision_rect.height):
                    collided_with_wall = True
            if collided_with_wall:
                self._handle_wall_collision(True, dx, dy) 
            else:
                self.x = next_x
                self.y = next_y
        if self.collision_rect and self.rect: 
            half_col_width = self.collision_rect.width / 2
            half_col_height = self.collision_rect.height / 2
            min_x_bound = game_area_x_offset + half_col_width
            max_x_bound = WIDTH - half_col_width 
            min_y_bound = half_col_height
            max_y_bound = GAME_PLAY_AREA_HEIGHT - half_col_height 
            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))
            self.rect.center = (int(self.x), int(self.y))
            self.collision_rect.center = self.rect.center

    def update(self, current_time_ms, maze, enemies_group, game_area_x_offset=0):
        if not self.alive:
            self.bullets_group.update(maze, game_area_x_offset)
            self.missiles_group.update(enemies_group, maze, game_area_x_offset)
            self.lightning_zaps_group.update(current_time_ms)
            self._update_thrust_particles() 
            return
        self.update_powerups(current_time_ms) 
        self.update_movement(maze, game_area_x_offset) 
        if self.speed_boost_active and self.moving_forward:
            self._emit_thrust_particles(current_time_ms)
        self._update_thrust_particles()
        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset) 
        self.lightning_zaps_group.update(current_time_ms)
        current_alpha_to_set = 255
        if self.is_cloaked_visual: 
            current_alpha_to_set = self.phantom_cloak_alpha
        if self.original_image: 
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle) 
            self.image = rotated_image.convert_alpha() 
            self.image.set_alpha(current_alpha_to_set) 
            if self.rect: 
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect: 
                    self.collision_rect.center = self.rect.center
            else: 
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect:
                    self.collision_rect.center = self.rect.center
        elif self.rect: 
             self.rect.center = (int(self.x), int(self.y))
             if self.collision_rect: self.collision_rect.center = self.rect.center

    def _handle_wall_collision(self, wall_hit_boolean, dx, dy):
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        if wall_hit_boolean and not self.shield_active and not is_invincible_setting:
            self.take_damage(10, self.crash_sound) 
        self.moving_forward = False

    def rotate(self, direction, rotation_speed_override=None):
        effective_rotation_speed = rotation_speed_override if rotation_speed_override is not None else self.rotation_speed
        if direction == "left":
            self.angle -= effective_rotation_speed
        elif direction == "right":
            self.angle += effective_rotation_speed
        self.angle %= 360  

    def shoot(self, sound=None, missile_sound=None, maze=None, enemies_group=None):
        current_time_ms = pygame.time.get_ticks()
        can_shoot_primary = (current_time_ms - self.last_shot_time) > self.current_shoot_cooldown
        can_shoot_missile = (current_time_ms - self.last_missile_shot_time) > self.current_missile_cooldown
        can_shoot_lightning = (current_time_ms - self.last_lightning_time) > self.current_lightning_cooldown
        nose_offset_factor = (self.rect.height / 2 if self.rect else TILE_SIZE * 0.4) * 0.7
        rad_angle_shoot = math.radians(self.angle)
        raw_bullet_start_x = self.x + math.cos(rad_angle_shoot) * nose_offset_factor
        raw_bullet_start_y = self.y + math.sin(rad_angle_shoot) * nose_offset_factor
        bullet_start_x = raw_bullet_start_x
        bullet_start_y = raw_bullet_start_y
        projectile_check_diameter = self.bullet_size * 2 
        if maze:
            if maze.is_wall(raw_bullet_start_x, raw_bullet_start_y, projectile_check_diameter, projectile_check_diameter):
                max_steps_back = 10 
                step_dist = nose_offset_factor / max_steps_back if max_steps_back > 0 else 0
                found_clear_spawn = False
                for i in range(1, max_steps_back + 1):
                    current_offset = nose_offset_factor - (i * step_dist)
                    if current_offset < 0: current_offset = 0 
                    test_x = self.x + math.cos(rad_angle_shoot) * current_offset
                    test_y = self.y + math.sin(rad_angle_shoot) * current_offset
                    if not maze.is_wall(test_x, test_y, projectile_check_diameter, projectile_check_diameter):
                        bullet_start_x = test_x
                        bullet_start_y = test_y
                        found_clear_spawn = True
                        break
                    if current_offset == 0: 
                        bullet_start_x = test_x
                        bullet_start_y = test_y
                        break
                if not found_clear_spawn: 
                    bullet_start_x = self.x
                    bullet_start_y = self.y
        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING]:
            if can_shoot_primary:
                if sound: sound.play()
                self.last_shot_time = current_time_ms
                angles_to_fire = [0] 
                if self.current_weapon_mode == WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == WEAPON_MODE_RAPID_TRI:
                    angles_to_fire = [-15, 0, 15] 
                for angle_offset in angles_to_fire:
                    effective_bullet_angle = self.angle + angle_offset
                    bullet_speed = get_game_setting("PLAYER_BULLET_SPEED")
                    bullet_lifetime = get_game_setting("PLAYER_BULLET_LIFETIME")
                    bullet_color = get_game_setting("PLAYER_BULLET_COLOR")
                    current_bullet_damage = 15 * self.bullet_damage_multiplier 
                    if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT: current_bullet_damage *= 2.5 
                    bounces = get_game_setting("BOUNCING_BULLET_MAX_BOUNCES") if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0
                    pierces = get_game_setting("PIERCING_BULLET_MAX_PIERCES") if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0
                    can_pierce_walls_flag = (self.current_weapon_mode == WEAPON_MODE_PIERCE) 
                    new_bullet = Bullet(bullet_start_x, bullet_start_y, effective_bullet_angle,
                                        bullet_speed, bullet_lifetime, self.bullet_size, bullet_color,
                                        current_bullet_damage, bounces, pierces,
                                        can_pierce_walls=can_pierce_walls_flag)
                    self.bullets_group.add(new_bullet)
        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if can_shoot_missile:
                if missile_sound: missile_sound.play()
                self.last_missile_shot_time = current_time_ms
                missile_dmg = get_game_setting("MISSILE_DAMAGE") * self.bullet_damage_multiplier
                new_missile = Missile(bullet_start_x, bullet_start_y, self.angle, missile_dmg, enemies_group)
                self.missiles_group.add(new_missile)
        
        # MODIFIED: Always create LightningZap, pass None if no target
        if self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if can_shoot_lightning:
                if sound: sound.play()
                self.last_lightning_time = current_time_ms

                closest_enemy_for_zap = None
                if enemies_group is None:
                    print("PlayerShoot DEBUG: enemies_group is None!")
                elif not enemies_group: 
                    print(f"PlayerShoot DEBUG: enemies_group is EMPTY. Player pos: ({self.x:.1f}, {self.y:.1f})")
                else:
                    min_dist = float('inf')
                    # print(f"PlayerShoot DEBUG: Checking {len(enemies_group)} enemies for lightning. Player pos: ({self.x:.1f}, {self.y:.1f}), Angle: {self.angle:.1f}, Zap Range: {get_game_setting('LIGHTNING_ZAP_RANGE')}")
                    enemy_count_in_range = 0
                    for i, enemy_sprite in enumerate(enemies_group):
                        if not hasattr(enemy_sprite, 'alive') or not enemy_sprite.alive: 
                            continue
                        if not hasattr(enemy_sprite, 'rect'):
                            continue
                        dist = math.hypot(enemy_sprite.rect.centerx - self.x, enemy_sprite.rect.centery - self.y)
                        # print(f"  Enemy {i} at ({enemy_sprite.rect.centerx:.1f}, {enemy_sprite.rect.centery:.1f}), dist: {dist:.1f}, Alive: {enemy_sprite.alive}")
                        if dist < get_game_setting("LIGHTNING_ZAP_RANGE"):
                            enemy_count_in_range +=1
                            if dist < min_dist:
                                min_dist = dist
                                closest_enemy_for_zap = enemy_sprite
                                # print(f"    New closest target for zap: Enemy {i} at dist {min_dist:.1f}")
                    # print(f"PlayerShoot DEBUG: Found {enemy_count_in_range} enemies within zap range.")
                
                if closest_enemy_for_zap:
                    print(f"PlayerShoot DEBUG: Lightning target FINALIZED: Enemy at ({closest_enemy_for_zap.rect.centerx:.1f}, {closest_enemy_for_zap.rect.centery:.1f})")
                else:
                    print("PlayerShoot DEBUG: Lightning target NOT FOUND. Firing straight.")

                lightning_dmg = get_game_setting("LIGHTNING_DAMAGE") * self.bullet_damage_multiplier
                if maze is None:
                    print("CRITICAL WARNING: PlayerDrone.shoot() called for LightningZap with maze=None")

                new_zap = LightningZap(self, closest_enemy_for_zap, lightning_dmg,
                                       get_game_setting("LIGHTNING_LIFETIME"),
                                       maze) 
                self.lightning_zaps_group.add(new_zap)
    # END MODIFICATION

    def take_damage(self, amount, sound=None):
        is_invincible_setting = get_game_setting("PLAYER_INVINCIBILITY", False)
        if is_invincible_setting: return
        effective_amount = amount
        if self.drone_system and hasattr(self.drone_system, 'get_collected_fragments_ids') and CORE_FRAGMENT_DETAILS:
            for frag_id in self.drone_system.get_collected_fragments_ids():
                frag_conf = next((details for _, details in CORE_FRAGMENT_DETAILS.items() if details and details.get("id") == frag_id), None)
                if frag_conf and frag_conf.get("buff_alt", {}).get("type") == "damage_reduction":
                    effective_amount *= (1.0 - frag_conf["buff_alt"]["value"]) 
        if not self.alive: return 
        if self.shield_active: 
            if sound: sound.play()  
            return
        self.health -= effective_amount
        if sound: sound.play() 
        if self.health <= 0:
            self.health = 0
            self.alive = False 

    def activate_shield(self, duration, is_from_speed_boost=False):
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration
        self.shield_duration = duration
        self.shield_glow_pulse_time_offset = pygame.time.get_ticks() * 0.005 
        if is_from_speed_boost:
            self.shield_tied_to_speed_boost = True 
        else:
            self.active_powerup_type = "shield" 
            self.shield_tied_to_speed_boost = False

    def arm_speed_boost(self, duration, multiplier):
        self.speed_boost_duration = duration
        self.speed_boost_multiplier = multiplier
        self.active_powerup_type = "speed_boost"  

    def attempt_speed_boost_activation(self):
        if self.active_powerup_type == "speed_boost" and not self.speed_boost_active and self.moving_forward:
            self.speed_boost_active = True
            self.speed_boost_end_time = pygame.time.get_ticks() + self.speed_boost_duration
            self.original_speed_before_boost = self.current_speed 
            self.current_speed = self.current_speed * self.speed_boost_multiplier 
            self.activate_shield(self.speed_boost_duration, is_from_speed_boost=True) 

    def try_activate_cloak(self, current_time_ms):
        if self.special_ability == "phantom_cloak" and not self.cloak_active and \
           current_time_ms > self.cloak_cooldown_end_time: 
            self.cloak_active = True
            self.is_cloaked_visual = True 
            self.cloak_end_time = current_time_ms + self.phantom_cloak_duration_ms
            self.last_cloak_activation_time = current_time_ms  
            return True 
        return False 

    def cycle_weapon_state(self, force_cycle=True):
        if not force_cycle and self.current_weapon_mode == WEAPON_MODES_SEQUENCE[-1]:
            return False  
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes() 
        return True

    def update_powerups(self, current_time_ms):
        if self.shield_active and current_time_ms > self.shield_end_time:
            if not (self.shield_tied_to_speed_boost and self.speed_boost_active and current_time_ms <= self.speed_boost_end_time):
                self.shield_active = False
                if self.active_powerup_type == "shield": self.active_powerup_type = None 
                self.shield_tied_to_speed_boost = False 
        if self.speed_boost_active and current_time_ms > self.speed_boost_end_time:
            self.speed_boost_active = False
            self.current_speed = self.original_speed_before_boost 
            if self.active_powerup_type == "speed_boost": self.active_powerup_type = None 
            if self.shield_tied_to_speed_boost: 
                self.shield_active = False
                self.shield_tied_to_speed_boost = False
        if self.cloak_active and current_time_ms > self.cloak_end_time:
            self.cloak_active = False
            self.is_cloaked_visual = False 
            self.cloak_cooldown_end_time = current_time_ms + self.phantom_cloak_cooldown_ms 

    def reset(self, x, y, drone_id, drone_stats, drone_sprite_path, health_override=None, preserve_weapon=False):
        previous_drone_id = self.drone_id 
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.alive = True
        self.moving_forward = False
        self.drone_id = drone_id
        self.base_hp = drone_stats.get("hp", get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = drone_stats.get("speed", get_game_setting("PLAYER_SPEED"))
        self.base_turn_speed = drone_stats.get("turn_speed", get_game_setting("ROTATION_SPEED"))
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0)
        self.max_health = self.base_hp
        self.health = health_override if health_override is not None else self.max_health 
        self.speed = self.base_speed 
        self.current_speed = self.speed
        self.rotation_speed = self.base_turn_speed
        self.original_speed_before_boost = self.speed 
        if previous_drone_id != self.drone_id or \
           not self.original_image or \
           (self.original_image and self.original_image.get_width() == 0):
            self._load_sprite(drone_sprite_path)
        else: 
            if self.original_image:
                self.image = pygame.transform.rotate(self.original_image, -self.angle)
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
                if self.collision_rect:
                    self.collision_rect.center = self.rect.center
        if self.original_image and not self.image:
             self.image = pygame.transform.rotate(self.original_image, -self.angle)
        if self.image and not self.rect:
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        elif self.rect: 
            self.rect.center = (int(self.x), int(self.y))
        if self.rect: 
            self.drone_visual_size = self.rect.size
            self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0,0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        if not preserve_weapon: 
            initial_weapon_mode_gs = get_game_setting("INITIAL_WEAPON_MODE")
            try:
                self.weapon_mode_index = WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
            except ValueError:
                self.weapon_mode_index = 0
            self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_attributes() 
        self.bullets_group.empty()
        self.missiles_group.empty()
        self.lightning_zaps_group.empty()
        self.last_shot_time = 0
        self.last_missile_shot_time = 0
        self.last_lightning_time = 0
        self.reset_active_powerups() 

    def reset_active_powerups(self):
        self.shield_active = False
        self.shield_end_time = 0
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.current_speed = self.base_speed  
        self.original_speed_before_boost = self.base_speed
        self.cloak_active = False
        self.is_cloaked_visual = False
        self.cloak_end_time = 0
        self.active_powerup_type = None
        self.thrust_particles.empty()
        self.shield_tied_to_speed_boost = False

    def get_position(self):
        return (self.x, self.y)

    def draw(self, surface):
        if not self.alive and not self.bullets_group and not self.missiles_group and not self.lightning_zaps_group and not self.thrust_particles:
            return
        self.thrust_particles.draw(surface) 
        if self.alive and self.image and self.original_image:  
            surface.blit(self.image, self.rect) 
            if self.shield_active:
                current_time = pygame.time.get_ticks()
                pulse_factor = (math.sin(current_time * 0.012 + self.shield_glow_pulse_time_offset) + 1) / 2
                shield_alpha = int(180 + pulse_factor * 75) 
                shield_color_tuple = POWERUP_TYPES.get("shield", {}).get("color", LIGHT_BLUE)
                final_shield_color = (*shield_color_tuple[:3], shield_alpha) 
                try:
                    if self.image.get_width() > 0 and self.image.get_height() > 0:
                        drone_mask = pygame.mask.from_surface(self.image)
                        outline_points = drone_mask.outline(1) 
                        if outline_points:
                            screen_outline_points = [(p[0] + self.rect.left, p[1] + self.rect.top) for p in outline_points]
                            line_thickness = int(2 + pulse_factor * 2) 
                            pygame.draw.polygon(surface, final_shield_color, screen_outline_points, line_thickness)
                    else:
                        pass 
                except pygame.error as e: 
                    pass 
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        for zap in self.lightning_zaps_group: 
            zap.draw(surface)
        if self.alive:
            self.draw_health_bar(surface)

    def draw_health_bar(self, surface):
        if not self.alive or not self.rect: return 
        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3 
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        pygame.draw.rect(surface, (80,0,0) if health_percentage < 0.3 else (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED
        if health_percentage >= 0.6: fill_color = GREEN
        elif health_percentage >= 0.3: fill_color = YELLOW
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
