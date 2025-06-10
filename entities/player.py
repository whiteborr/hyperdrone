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
        
        self.base_hp = drone_stats.get("hp", gs.get_game_setting("PLAYER_MAX_HEALTH"))
        self.base_turn_speed = drone_stats.get("turn_speed", gs.get_game_setting("ROTATION_SPEED"))
        self.rotation_speed = self.base_turn_speed
        
        self.is_cruising = False 
        self.max_health = self.base_hp
        self.health = self.max_health
        
        self.original_image = None
        self.image = None
        
        initial_weapon_mode_gs = gs.get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = gs.WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = gs.WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._load_sprite()
        
        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.lightning_zaps_group = pygame.sprite.Group()
        self.last_shot_time = 0
        self.current_shoot_cooldown = gs.PLAYER_BASE_SHOOT_COOLDOWN
        self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")

    def _load_sprite(self):
        # This logic for swapping sprites on weapon change is preserved
        weapon_sprite_path = gs.WEAPON_MODE_ICONS.get(self.current_weapon_mode)
        loaded_image = None
        if weapon_sprite_path and isinstance(weapon_sprite_path, str):
            asset_key = weapon_sprite_path.replace("assets/", "").replace("\\", "/")
            loaded_image = self.asset_manager.get_image(asset_key)

        if not loaded_image:
            loaded_image = self.asset_manager.get_image(self.sprite_asset_key)

        if loaded_image:
            # We now assume the source image faces RIGHT and do not apply any correction here.
            self.original_image = pygame.transform.smoothscale(loaded_image, self.drone_visual_size)
        else:
            self.original_image = self.asset_manager._create_fallback_surface(size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150))
        
        self.image = self.original_image.copy()
        current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
        self.rect = self.image.get_rect(center=current_center)
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)

    def update(self, current_time_ms, maze, enemies_group, player_actions, game_area_x_offset=0):
        if not self.alive: return
        
        self.moving_forward = self.is_cruising
        
        super().update(maze, game_area_x_offset)
        
        self.bullets_group.update(maze, game_area_x_offset)

    def rotate(self, direction):
        super().rotate(direction, self.rotation_speed)
            
    def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
        current_time_ms = pygame.time.get_ticks()
        if (current_time_ms - self.last_shot_time) > self.current_shoot_cooldown:
            self.last_shot_time = current_time_ms
            if sound_asset_key and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_asset_key)
                if sound: sound.play()

            rad_angle = math.radians(self.angle)
            spawn_x = self.x + math.cos(rad_angle) * (self.rect.width / 2)
            spawn_y = self.y + math.sin(rad_angle) * (self.rect.height / 2)
            
            new_bullet = Bullet(spawn_x, spawn_y, self.angle, gs.PLAYER_BULLET_SPEED, gs.PLAYER_BULLET_LIFETIME, self.bullet_size, gs.PLAYER_BULLET_COLOR, 15)
            self.bullets_group.add(new_bullet)
            
    def cycle_weapon_state(self):
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(gs.WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = gs.WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._load_sprite() 

    def take_damage(self, amount, sound_key_on_hit=None):
        if not self.alive: return
        self.health -= amount
        if sound_key_on_hit and self.asset_manager:
            sound = self.asset_manager.get_sound(sound_key_on_hit)
            if sound: sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw(self, surface, camera=None):
        if self.alive and self.original_image:
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle)
            draw_rect = rotated_image.get_rect(center=self.rect.center)
            surface.blit(rotated_image, draw_rect)
            
        self.bullets_group.draw(surface)

    def draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = int(bar_width * health_percentage)
        fill_color = gs.GREEN if health_percentage > 0.6 else gs.YELLOW if health_percentage > 0.3 else gs.RED
        pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, gs.WHITE, (bar_x, bar_y, bar_width, bar_height), 1)