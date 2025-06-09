# entities/player.py
import pygame
import math
import os
import random
import logging 

import game_settings as gs

try:
    from .bullet import Bullet, Missile, LightningZap
    from .particle import Particle
    from .base_drone import BaseDrone
except ImportError:
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(pygame.sprite.Sprite): pass
    class LightningZap(pygame.sprite.Sprite): pass 
    class Particle(pygame.sprite.Sprite): pass
    class BaseDrone(pygame.sprite.Sprite):
        def __init__(self, x,y,speed, size=None): super().__init__(); self.x=x;self.y=y;self.speed=speed;self.rect=pygame.Rect(0,0,32,32)
        def update_movement(self, maze=None, game_area_x_offset=0): pass
        def reset(self, x, y): self.x=x; self.y=y
        def _handle_wall_collision(self, maze, dx, dy): return dx, dy

logger = logging.getLogger(__name__)


class PlayerDrone(BaseDrone): 
    def __init__(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, crash_sound_key, drone_system):
        base_speed_from_stats = drone_stats.get("speed", gs.get_game_setting("PLAYER_SPEED"))
        self.drone_visual_size = (int(gs.TILE_SIZE * 0.7), int(gs.TILE_SIZE * 0.7))
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats)
        
        self.drone_id = drone_id
        self.drone_system = drone_system  
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.crash_sound_key = crash_sound_key
        self.x = float(x) 
        self.y = float(y)
        self.base_hp = drone_stats.get("hp", gs.get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_speed = base_speed_from_stats
        self.base_turn_speed = drone_stats.get("turn_speed", gs.get_game_setting("ROTATION_SPEED"))
        self.base_fire_rate_multiplier = drone_stats.get("fire_rate_multiplier", 1.0)
        self.special_ability = drone_stats.get("special_ability")  
        self.bullet_damage_multiplier = drone_stats.get("bullet_damage_multiplier", 1.0) 
        self.max_health = self.base_hp
        self.health = self.max_health
        self.rotation_speed = self.base_turn_speed
        self.is_cruising = False
        self.original_image = None
        self.image = None
        self._load_sprite()
        
        initial_weapon_mode_gs = gs.get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = gs.WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = gs.WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        
        self.bullets_group = pygame.sprite.Group() 
        self.missiles_group = pygame.sprite.Group() 
        self.lightning_zaps_group = pygame.sprite.Group() 
        
        self.last_shot_time, self.last_missile_shot_time, self.last_lightning_time = 0, 0, 0
        
        self.current_shoot_cooldown = gs.get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        self.current_missile_cooldown = gs.get_game_setting("MISSILE_COOLDOWN")
        self.current_lightning_cooldown = gs.get_game_setting("LIGHTNING_COOLDOWN")
        self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        self._update_weapon_attributes()
        
        self.active_powerup_type = None 
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_duration = gs.get_game_setting("SHIELD_POWERUP_DURATION")  
        self.shield_glow_pulse_time_offset = random.uniform(0, 2 * math.pi) 
        
        self.speed_boost_active = False
        self.speed_boost_end_time = 0
        self.speed_boost_duration = gs.get_game_setting("SPEED_BOOST_POWERUP_DURATION")
        self.speed_boost_multiplier = gs.POWERUP_TYPES.get("speed_boost", {}).get("multiplier", 1.8)
        self.original_speed_before_boost = self.speed 
        self.shield_tied_to_speed_boost = False 
        
        self.thrust_particles = pygame.sprite.Group()
        self.thrust_particle_spawn_timer = 0
        self.THRUST_PARTICLE_SPAWN_INTERVAL = 25 
        self.PARTICLES_PER_EMISSION = random.randint(2, 4) 
        self.flame_port_offset_distance = self.drone_visual_size[1] * 0.4 
        
        self.cloak_active, self.is_cloaked_visual = False, False
        self.cloak_end_time, self.cloak_cooldown_end_time = 0, 0
        self.phantom_cloak_alpha = gs.get_game_setting("PHANTOM_CLOAK_ALPHA_SETTING")
        self.phantom_cloak_duration_ms = gs.get_game_setting("PHANTOM_CLOAK_DURATION_MS")
        self.phantom_cloak_cooldown_ms = gs.get_game_setting("PHANTOM_CLOAK_COOLDOWN_MS")
        
        if self.rect:
            self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)
        else:
            col_size = self.size * 0.7
            self.collision_rect = pygame.Rect(self.x - col_size/2, self.y - col_size/2, col_size, col_size)

    def _load_sprite(self):
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        if loaded_image:
            self.original_image = pygame.transform.smoothscale(loaded_image, self.drone_visual_size)
        else:
            self.original_image = self.asset_manager._create_fallback_surface(
                size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150)
            )
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)

    def _update_weapon_attributes(self):
        pass

    def _emit_thrust_particles(self, current_time_ms):
        pass

    def _update_thrust_particles(self):
        self.thrust_particles.update()

    def update(self, current_time_ms, maze, enemies_group, player_actions, game_area_x_offset=0):
        if not self.alive:
            self.bullets_group.update(maze, game_area_x_offset)
            self.missiles_group.update(enemies_group, maze, game_area_x_offset) 
            self.lightning_zaps_group.update(current_time_ms)
            self._update_thrust_particles()
            return
        
        self.moving_forward = self.is_cruising
        self.update_powerups(current_time_ms) 
        self.update_movement(maze, game_area_x_offset) 
        
        if player_actions.is_shooting:
            self.shoot(
                sound_asset_key='shoot',
                missile_sound_asset_key='missile_launch',
                maze=maze,
                enemies_group=enemies_group
            )

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
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            if self.collision_rect: self.collision_rect.center = self.rect.center

    def _handle_wall_collision(self, maze, dx, dy):
        final_dx, final_dy = super()._handle_wall_collision(maze, dx, dy)
        collision_occurred = abs(final_dx - dx) > 1e-6 or abs(final_dy - dy) > 1e-6

        if collision_occurred:
            if not self.shield_active and not gs.get_game_setting("PLAYER_INVINCIBILITY"):
                self.take_damage(10, self.crash_sound_key)
            self.is_cruising = False
        
        return final_dx, final_dy

    def rotate(self, direction, rotation_speed_override=None):
        pass

    def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
        pass

    def take_damage(self, amount, sound_key_on_hit=None):
        pass

    def activate_shield(self, duration, is_from_speed_boost=False):
        pass

    def arm_speed_boost(self, duration, multiplier):
        pass

    def attempt_speed_boost_activation(self):
        pass

    def try_activate_cloak(self, current_time_ms):
        pass

    def cycle_weapon_state(self, force_cycle=True):
        pass

    def update_powerups(self, current_time_ms):
        pass

    def reset(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, preserve_weapon=False):
        pass

    def reset_active_powerups(self):
        pass

    def get_position(self):
        return (self.x, self.y)

    def draw(self, surface, camera=None):
        if not self.alive and not any([self.bullets_group, self.missiles_group, self.lightning_zaps_group, self.thrust_particles]):
            return
        
        if camera:
            for group in [self.thrust_particles, self.bullets_group, self.missiles_group]:
                for sprite in group:
                    sprite.draw(surface, camera)
            for zap in self.lightning_zaps_group: zap.draw(surface, camera)
        else:
            self.thrust_particles.draw(surface)
            self.bullets_group.draw(surface)
            self.missiles_group.draw(surface)
            for zap in self.lightning_zaps_group: zap.draw(surface)

        if self.alive and self.image:
            final_rect = camera.apply_to_rect(self.rect) if camera else self.rect
            surface.blit(self.image, final_rect)
            
            if self.shield_active:
                pulse_factor = (math.sin(pygame.time.get_ticks() * 0.012 + self.shield_glow_pulse_time_offset) + 1) / 2
                shield_alpha = int(180 + pulse_factor * 75)
                shield_color_tuple = gs.POWERUP_TYPES.get("shield", {}).get("color", gs.LIGHT_BLUE)
                final_shield_color = (*shield_color_tuple[:3], shield_alpha)
                shield_radius = max(final_rect.width, final_rect.height) / 2 * 1.1
                pygame.draw.circle(surface, final_shield_color, final_rect.center, int(shield_radius), 3)
            
        if self.alive:
            self.draw_health_bar(surface, camera)

    def draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        
        screen_rect = camera.apply_to_rect(self.rect) if camera else self.rect
        bar_width = screen_rect.width * 0.8
        bar_height = 5
        bar_x = screen_rect.centerx - bar_width / 2
        bar_y = screen_rect.top - bar_height - 3
        
        health_percentage = max(0, self.health / self.max_health) if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        
        fill_color = gs.RED
        if health_percentage > 0.6: fill_color = gs.GREEN
        elif health_percentage > 0.3: fill_color = gs.YELLOW
        
        pygame.draw.rect(surface, (80,0,0), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(filled_width), bar_height))
        pygame.draw.rect(surface, gs.WHITE, (bar_x, bar_y, bar_width, bar_height), 1)