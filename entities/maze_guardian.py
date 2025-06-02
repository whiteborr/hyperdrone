import pygame
import math
import random
import os

from .enemy import Enemy 
from .bullet import LightningZap 
from entities.bullet import Bullet as EnemyBullet 

import game_settings as gs
from game_settings import (
    TILE_SIZE, WIDTH, GAME_PLAY_AREA_HEIGHT,
    DARK_GREY, YELLOW, GREEN, RED, WHITE, 
    MAZE_GUARDIAN_HEALTH, MAZE_GUARDIAN_SPEED, MAZE_GUARDIAN_COLOR,
    MAZE_GUARDIAN_LASER_DAMAGE, MAZE_GUARDIAN_LASER_COOLDOWN, MAZE_GUARDIAN_LASER_SWEEP_ARC,
    MAZE_GUARDIAN_SHIELD_DURATION_MS, MAZE_GUARDIAN_SHIELD_COOLDOWN_MS,
    MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS, MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS,
    MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS,
    SENTINEL_DRONE_HEALTH, SENTINEL_DRONE_SPEED, SENTINEL_DRONE_SPRITE_PATH,
    MAZE_GUARDIAN_BULLET_SPEED, MAZE_GUARDIAN_BULLET_LIFETIME,
    MAZE_GUARDIAN_BULLET_COLOR, MAZE_GUARDIAN_BULLET_DAMAGE,
    ARCHITECT_VAULT_ACCENT_COLOR, LIGHT_BLUE,
    TOTAL_CORE_FRAGMENTS_NEEDED 
)

class MazeGuardian(Enemy):
    def __init__(self, x, y, player_ref, maze_ref, game_controller_ref, boss_id="MAZE_GUARDIAN"):
        self.image_size = (int(TILE_SIZE * 2.5), int(TILE_SIZE * 2.5)) 

        super().__init__(
            x=x, y=y,
            player_bullet_size_base=gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE"), 
            shoot_sound=game_controller_ref.sounds.get('enemy_shoot'), 
            sprite_path=gs.get_game_setting("MAZE_GUARDIAN_SPRITE_PATH"),
            target_player_ref=player_ref
        )

        self.boss_id = boss_id
        self.player_ref = player_ref
        self.maze_ref = maze_ref
        self.game_controller_ref = game_controller_ref 

        self.original_x = x
        self.original_y = y

        self.max_health = gs.get_game_setting("MAZE_GUARDIAN_HEALTH")
        self.health = self.max_health
        self.speed = gs.get_game_setting("MAZE_GUARDIAN_SPEED") 

        self.current_phase = 1 
        self.last_phase_change_time = pygame.time.get_ticks()

        self.last_shot_time = pygame.time.get_ticks()
        self.basic_shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 1.5 
        self.enhanced_shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 0.8 

        self.last_laser_time = pygame.time.get_ticks() - gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN") // 2 
        self.laser_cooldown = gs.get_game_setting("MAZE_GUARDIAN_LASER_COOLDOWN")
        self.laser_active = False 
        self.laser_end_time = 0

        self.shield_active = False
        self.shield_end_time = 0
        self.last_shield_activate_time = pygame.time.get_ticks()
        self.shield_duration = gs.get_game_setting("MAZE_GUARDIAN_SHIELD_DURATION_MS")
        self.shield_cooldown = gs.get_game_setting("MAZE_GUARDIAN_SHIELD_COOLDOWN_MS")
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) 

        self.last_minion_spawn_time = pygame.time.get_ticks()
        self.minion_spawn_cooldown = gs.get_game_setting("MAZE_GUARDIAN_MINION_SPAWN_COOLDOWN_MS")
        self.max_active_minions = 3 

        self.last_arena_shift_time = pygame.time.get_ticks()
        self.arena_shift_interval = gs.get_game_setting("MAZE_GUARDIAN_ARENA_SHIFT_INTERVAL_MS")
        self.arena_shift_duration = gs.get_game_setting("MAZE_GUARDIAN_ARENA_SHIFT_DURATION_MS")
        self.arena_shifting_active = False
        self.arena_shift_end_time = 0
        
        if self.rect: 
            self.collision_rect_width = self.rect.width * 0.7
            self.collision_rect_height = self.rect.height * 0.7
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = self.rect.center
        else: 
            self.collision_rect_width = self.image_size[0] * 0.7
            self.collision_rect_height = self.image_size[1] * 0.7
            self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
            self.collision_rect.center = (self.x, self.y)

        self.laser_beams = pygame.sprite.Group() 

    def _load_sprite(self, sprite_path):
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, self.image_size)
            except pygame.error as e:
                print(f"Error loading MAZE_GUARDIAN sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: 
                print(f"Warning: MAZE_GUARDIAN sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None:
            self.original_image = pygame.Surface(self.image_size, pygame.SRCALPHA)
            pygame.draw.circle(self.original_image, MAZE_GUARDIAN_COLOR,
                               (self.image_size[0] // 2, self.image_size[1] // 2),
                               self.image_size[0] // 2 - 5)
            pygame.draw.rect(self.original_image, RED, self.original_image.get_rect(), 5) 

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def update(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        if not self.alive:
            self.bullets.update(maze, game_area_x_offset)
            self.laser_beams.update(current_time) 
            if not self.bullets and not self.laser_beams:
                self.kill() 
            return

        self._check_phase_transition(current_time)
        
        if self.player_ref and self.player_ref.alive:
            dx_player = self.player_ref.x - self.x
            dy_player = self.player_ref.y - self.y
            self.angle = math.degrees(math.atan2(dy_player, dx_player))
            
            if self.current_phase == 3: 
                 self.speed = gs.get_game_setting("MAZE_GUARDIAN_SPEED") * 1.2 
                 distance_to_player = math.hypot(dx_player, dy_player)
                 preferred_distance = TILE_SIZE * 3
                 if distance_to_player > preferred_distance:
                     self.x += (dx_player / distance_to_player) * self.speed * 0.5 
                     self.y += (dy_player / distance_to_player) * self.speed * 0.5
                 elif distance_to_player < preferred_distance * 0.8: 
                     self.x -= (dx_player / distance_to_player) * self.speed * 0.3
                     self.y -= (dy_player / distance_to_player) * self.speed * 0.3
            else:
                 self.speed = gs.get_game_setting("MAZE_GUARDIAN_SPEED")


        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if self.collision_rect: 
            self.collision_rect.center = self.rect.center

        self._update_shield_state(current_time)
        self._update_arena_shift_state(current_time, maze) 
        self.bullets.update(maze, game_area_x_offset)
        self.laser_beams.update(current_time)


        if self.current_phase == 1:
            self._perform_basic_ranged_attack(current_time)
            self._try_laser_sweep(current_time) 
        elif self.current_phase == 2:
            self._perform_basic_ranged_attack(current_time, enhanced=True)
            self._try_laser_sweep(current_time)
            self._try_summon_mini_drones(current_time) 
            self._try_activate_shield(current_time)
        elif self.current_phase == 3:
            self._perform_basic_ranged_attack(current_time, enhanced=True, triple_shot=True)
            self._try_laser_sweep(current_time, wide_sweep=True)
            self._try_arena_shift_initiate(current_time) 

    def _check_phase_transition(self, current_time):
        if not self.max_health > 0: return 
        health_ratio = self.health / self.max_health
        if health_ratio <= 0.3 and self.current_phase != 3:
            self.current_phase = 3
            self.game_controller_ref.play_sound('vault_alarm', 0.7)
            self.game_controller_ref.architect_vault_message = "MAZE GUARDIAN: CRITICAL LOCKDOWN! ARENA COLLAPSE!"
            self.game_controller_ref.architect_vault_message_timer = current_time + 4000
            self.last_arena_shift_time = current_time + 1000 
        elif health_ratio <= 0.65 and self.current_phase == 1: 
            self.current_phase = 2
            self.game_controller_ref.play_sound('ui_confirm')
            self.game_controller_ref.architect_vault_message = "MAZE GUARDIAN: DEFENSIVE SYSTEMS ONLINE!"
            self.game_controller_ref.architect_vault_message_timer = current_time + 3000

    def _perform_basic_ranged_attack(self, current_time, enhanced=False, triple_shot=False):
        cooldown_to_use = self.enhanced_shoot_cooldown if enhanced else self.basic_shoot_cooldown
        if current_time - self.last_shot_time > cooldown_to_use:
            if self.player_ref and self.player_ref.alive:
                dx = self.player_ref.x - self.x
                dy = self.player_ref.y - self.y
                angle_to_player = math.degrees(math.atan2(dy, dx))

                fire_angles = [angle_to_player]
                if triple_shot:
                    fire_angles = [angle_to_player - 15, angle_to_player, angle_to_player + 15]

                for angle in fire_angles:
                    bullet_speed = gs.get_game_setting("MAZE_GUARDIAN_BULLET_SPEED")
                    bullet_lifetime = gs.get_game_setting("MAZE_GUARDIAN_BULLET_LIFETIME")
                    bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE") // 1.5 
                    bullet_color = gs.get_game_setting("MAZE_GUARDIAN_BULLET_COLOR")
                    bullet_damage = gs.get_game_setting("MAZE_GUARDIAN_BULLET_DAMAGE")

                    fire_offset = self.rect.width / 2 + 10 
                    spawn_x = self.x + math.cos(math.radians(angle)) * fire_offset
                    spawn_y = self.y + math.sin(math.radians(angle)) * fire_offset

                    new_bullet = EnemyBullet(spawn_x, spawn_y, angle, bullet_speed,
                                        bullet_lifetime, int(bullet_size), bullet_color, bullet_damage) 
                    self.bullets.add(new_bullet)
                if self.shoot_sound:
                    self.shoot_sound.play()
            self.last_shot_time = current_time

    def _try_laser_sweep(self, current_time, wide_sweep=False): 
        if not self.laser_active and current_time - self.last_laser_time > self.laser_cooldown:
            self.laser_active = True
            laser_duration_frames = gs.get_game_setting("LIGHTNING_LIFETIME") 
            self.laser_end_time = current_time + (laser_duration_frames * (1000 // gs.get_game_setting("FPS"))) 
            self.last_laser_time = current_time 
            self.game_controller_ref.play_sound('laser_charge')

            game_area_x_offset = self.game_controller_ref.maze.game_area_x_offset if self.game_controller_ref.maze else 0
            laser_zap = LightningZap(
                player_ref=self, 
                initial_target_enemy_ref=None, 
                damage=gs.get_game_setting("MAZE_GUARDIAN_LASER_DAMAGE"),
                lifetime_frames=laser_duration_frames, 
                maze_ref=self.maze_ref,
                game_area_x_offset = game_area_x_offset,
                color_override=RED 
            )
            self.laser_beams.add(laser_zap) 
            self.game_controller_ref.play_sound('laser_fire')

    def _update_laser_state(self, current_time): 
        if self.laser_active and current_time > self.laser_end_time:
            self.laser_active = False

    def _try_summon_mini_drones(self, current_time):
        if not hasattr(self.game_controller_ref, 'enemy_manager'):
            print("Error (MazeGuardian): GameController reference has no EnemyManager.")
            return

        active_minions_count = sum(1 for e in self.game_controller_ref.enemy_manager.get_sprites() if isinstance(e, SentinelDrone) and e.alive)

        if active_minions_count < self.max_active_minions and \
           current_time - self.last_minion_spawn_time > self.minion_spawn_cooldown:
            
            spawn_x, spawn_y = self.game_controller_ref._get_safe_spawn_point(TILE_SIZE, TILE_SIZE) 
            if spawn_x is not None:
                if hasattr(self.game_controller_ref.enemy_manager, 'spawn_sentinel_drone_at_location'):
                     self.game_controller_ref.enemy_manager.spawn_sentinel_drone_at_location(spawn_x, spawn_y)
                     self.game_controller_ref.play_sound('minion_spawn') 
                     self.last_minion_spawn_time = current_time
                else:
                    print("Error (MazeGuardian): EnemyManager has no spawn_sentinel_drone_at_location method.")


    def _try_activate_shield(self, current_time):
        if not self.shield_active and current_time - self.last_shield_activate_time > self.shield_cooldown:
            self.shield_active = True
            self.shield_end_time = current_time + self.shield_duration
            self.last_shield_activate_time = current_time
            self.game_controller_ref.play_sound('shield_activate') 

    def _update_shield_state(self, current_time):
        if self.shield_active and current_time > self.shield_end_time:
            self.shield_active = False

    def _try_arena_shift_initiate(self, current_time):
        if not self.arena_shifting_active and current_time - self.last_arena_shift_time > self.arena_shift_interval:
            self.arena_shifting_active = True
            self.arena_shift_end_time = current_time + self.arena_shift_duration
            self.last_arena_shift_time = current_time
            self.game_controller_ref.play_sound('wall_shift') 
            if hasattr(self.maze_ref, 'toggle_dynamic_walls'):
                self.maze_ref.toggle_dynamic_walls(activate=True) 

    def _update_arena_shift_state(self, current_time, maze): 
        if self.arena_shifting_active and current_time > self.arena_shift_end_time:
            self.arena_shifting_active = False
            if hasattr(maze, 'toggle_dynamic_walls'): 
                maze.toggle_dynamic_walls(activate=False) 

    def take_damage(self, amount):
        if not self.alive:
            return

        if self.shield_active:
            self.game_controller_ref.play_sound('ui_denied', 0.5) 
            return

        self.health -= amount
        self.game_controller_ref.play_sound('boss_hit') 
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.game_controller_ref.play_sound('boss_death') 
            if hasattr(self.game_controller_ref, '_maze_guardian_defeated'):
                 self.game_controller_ref._maze_guardian_defeated()


    def draw(self, surface):
        if not self.alive and not self.bullets and not self.laser_beams: 
            return

        if self.alive and self.image:
            surface.blit(self.image, self.rect)
            self._draw_health_bar(surface)
            if self.shield_active:
                self._draw_shield_effect(surface)

        self.bullets.draw(surface) 
        self.laser_beams.draw(surface) 

    def _draw_health_bar(self, surface):
        if not self.game_controller_ref or not hasattr(self.game_controller_ref, 'ui_manager') or \
           not hasattr(self.game_controller_ref.ui_manager, '_render_text_safe'): 
            return 

        bar_width = self.rect.width * 1.2
        bar_height = 10 
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 15 
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage

        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED
        if health_percentage >= 0.66: fill_color = GREEN
        elif health_percentage >= 0.33: fill_color = YELLOW
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2) 

        phase_text_surf = None
        font_key = "small_text" 
        phase_color = WHITE
        if self.current_phase == 1:
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase I", font_key, phase_color)
        elif self.current_phase == 2:
            phase_color = YELLOW
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase II", font_key, phase_color)
        elif self.current_phase == 3:
            phase_color = RED
            phase_text_surf = self.game_controller_ref.ui_manager._render_text_safe("Phase III", font_key, phase_color)

        if phase_text_surf:
            text_rect = phase_text_surf.get_rect(midbottom=(bar_x + bar_width / 2, bar_y - 5))
            surface.blit(phase_text_surf, text_rect)

    def _draw_shield_effect(self, surface):
        if not self.shield_active: return
        current_time = pygame.time.get_ticks()
        pulse_factor = (math.sin(current_time * 0.008 + self.shield_glow_pulse_time_offset) + 1) / 2 
        glow_alpha = int(100 + pulse_factor * 60) 
        glow_scale = 1.15 + (pulse_factor * 0.1) 
        glow_color_tuple = ARCHITECT_VAULT_ACCENT_COLOR 

        glow_width = int(self.image.get_width() * glow_scale)
        glow_height = int(self.image.get_height() * glow_scale)

        if glow_width > 0 and glow_height > 0 and self.original_image: 
            temp_glow_base = pygame.transform.smoothscale(self.original_image, (glow_width, glow_height))
            rotated_glow_base = pygame.transform.rotate(temp_glow_base, -self.angle)
            
            try:
                glow_shape_mask = pygame.mask.from_surface(rotated_glow_base)
                glow_shape_surface = glow_shape_mask.to_surface(setcolor=glow_color_tuple, unsetcolor=(0,0,0,0))
                glow_shape_surface.set_alpha(glow_alpha)
                glow_rect = glow_shape_surface.get_rect(center=self.rect.center)
                surface.blit(glow_shape_surface, glow_rect)
            except (pygame.error, ValueError) as e: 
                fallback_glow_radius = int((self.rect.width / 2) * glow_scale)
                if fallback_glow_radius > 0:
                    fallback_glow_surface = pygame.Surface((fallback_glow_radius * 2, fallback_glow_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(fallback_glow_surface, (*glow_color_tuple[:3], glow_alpha),
                                    (fallback_glow_radius, fallback_glow_radius), fallback_glow_radius)
                    surface.blit(fallback_glow_surface, fallback_glow_surface.get_rect(center=self.rect.center))

# Sentinel Drone (Mini-drone summoned by MazeGuardian)
class SentinelDrone(Enemy):
    def __init__(self, x, y, player_bullet_size_base, shoot_sound=None, sprite_path=None, target_player_ref=None):
        self.image_size = (int(TILE_SIZE * 0.6), int(TILE_SIZE * 0.6)) 

        super().__init__(
            x=x, y=y,
            player_bullet_size_base=player_bullet_size_base,
            shoot_sound=shoot_sound,
            sprite_path=sprite_path or gs.get_game_setting("SENTINEL_DRONE_SPRITE_PATH"),
            target_player_ref=target_player_ref
        )
        self.max_health = gs.get_game_setting("SENTINEL_DRONE_HEALTH")
        self.health = self.max_health
        self.speed = gs.get_game_setting("SENTINEL_DRONE_SPEED")
        self.shoot_cooldown = gs.get_game_setting("ENEMY_BULLET_COOLDOWN") * 0.7 

    def _load_sprite(self, sprite_path): 
        default_size = self.image_size 
        if sprite_path and os.path.exists(sprite_path):
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.original_image = pygame.transform.scale(loaded_image, default_size)
            except pygame.error as e:
                print(f"Error loading sentinel sprite '{sprite_path}': {e}. Using fallback.")
                self.original_image = None
        else:
            if sprite_path: print(f"Warning: Sentinel sprite path not found: {sprite_path}. Using fallback.")
            self.original_image = None

        if self.original_image is None:
            self.original_image = pygame.Surface(default_size, pygame.SRCALPHA)
            points = [
                (default_size[0] // 2, 0), (default_size[0], default_size[1] // 2),
                (default_size[0] // 2, default_size[1]), (0, default_size[1] // 2)
            ]
            pygame.draw.polygon(self.original_image, gs.get_game_setting("DARK_PURPLE",(70,0,100)), points) 
            pygame.draw.polygon(self.original_image, WHITE, points, 1)


        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.collision_rect_width = self.rect.width * 0.8
        self.collision_rect_height = self.rect.height * 0.8
        self.collision_rect = pygame.Rect(0, 0, self.collision_rect_width, self.collision_rect_height)
        self.collision_rect.center = self.rect.center


    def update(self, player_pos_pixels, maze, current_time, game_area_x_offset=0):
        if not self.alive:
            if not self.bullets:
                self.kill()
            self.bullets.update(maze, game_area_x_offset)
            return

        if self.player_ref and self.player_ref.alive:
            dx = self.player_ref.x - self.x
            dy = self.player_ref.y - self.y
            distance = math.hypot(dx, dy)

            if distance > 0: 
                self.angle = math.degrees(math.atan2(dy, dx))
                move_x = (dx / distance) * self.speed
                move_y = (dy / distance) * self.speed
                
                prev_x, prev_y = self.x, self.y
                self.x += move_x
                self.y += move_y

                if maze and self.collision_rect:
                    self.collision_rect.center = (self.x, self.y)
                    if maze.is_wall(self.collision_rect.centerx, self.collision_rect.centery, self.collision_rect.width, self.collision_rect.height):
                        self.x = prev_x 
                        self.y = prev_y 
                        self.angle += 180 
                        self.angle %= 360


            half_width = self.rect.width / 2 if self.rect else TILE_SIZE * 0.3
            half_height = self.rect.height / 2 if self.rect else TILE_SIZE * 0.3
            min_x_bound = game_area_x_offset + half_width
            max_x_bound = WIDTH - half_width
            min_y_bound = half_height
            max_y_bound = GAME_PLAY_AREA_HEIGHT - half_height
            self.x = max(min_x_bound, min(self.x, max_x_bound))
            self.y = max(min_y_bound, min(self.y, max_y_bound))


            if current_time - self.last_shot_time > self.shoot_cooldown and distance < TILE_SIZE * 8:
                self.shoot(self.angle) 
                self.last_shot_time = current_time

        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        if self.collision_rect:
            self.collision_rect.center = self.rect.center

        self.bullets.update(maze, game_area_x_offset)