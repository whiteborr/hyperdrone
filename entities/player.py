# entities/player.py
import pygame
import math
import os
import random
import logging 

import game_settings as gs

from .bullet import Bullet, Missile, LightningZap
from .particle import Particle
from .base_drone import BaseDrone
from .powerup_manager import PowerUpManager


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
        self.base_speed = base_speed_from_stats  # Store base speed for powerups
        
        self.is_cruising = False 
        self.max_health = self.base_hp
        self.health = self.max_health
        
        # Initialize PowerUpManager
        self.powerup_manager = PowerUpManager(self)
        
        self.original_image = None
        self.image = None
        
        initial_weapon_mode_gs = gs.get_game_setting("INITIAL_WEAPON_MODE")
        try:
            self.weapon_mode_index = gs.WEAPON_MODES_SEQUENCE.index(initial_weapon_mode_gs)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = gs.WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        
        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.lightning_zaps_group = pygame.sprite.Group()
        self.last_shot_time = 0
        self.current_shoot_cooldown = gs.PLAYER_BASE_SHOOT_COOLDOWN
        self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
        
        # Initialize weapon properties based on initial weapon mode
        self._update_weapon_properties()
        self._load_sprite()

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
        self.missiles_group.update(enemies_group, maze, game_area_x_offset)
        if hasattr(self, 'lightning_zaps_group'):
            self.lightning_zaps_group.update(current_time_ms)

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
            
            # Create bullets based on weapon mode
            if self.current_weapon_mode == gs.WEAPON_MODE_TRI_SHOT or self.current_weapon_mode == gs.WEAPON_MODE_RAPID_TRI:
                # Create tri-shot bullets
                for angle_offset in [-15, 0, 15]:
                    shot_angle = self.angle + angle_offset
                    new_bullet = Bullet(spawn_x, spawn_y, shot_angle, gs.PLAYER_BULLET_SPEED, 
                                       gs.PLAYER_BULLET_LIFETIME, self.bullet_size, 
                                       gs.PLAYER_BULLET_COLOR, 15)
                    self.bullets_group.add(new_bullet)
            elif self.current_weapon_mode == gs.WEAPON_MODE_BOUNCE:
                # Create bouncing bullet
                new_bullet = Bullet(spawn_x, spawn_y, self.angle, gs.PLAYER_BULLET_SPEED, 
                                   gs.PLAYER_BULLET_LIFETIME, self.bullet_size, 
                                   gs.PLAYER_BULLET_COLOR, 15, max_bounces=gs.BOUNCING_BULLET_MAX_BOUNCES)
                self.bullets_group.add(new_bullet)
            elif self.current_weapon_mode == gs.WEAPON_MODE_PIERCE:
                # Create piercing bullet that can pass through walls
                new_bullet = Bullet(spawn_x, spawn_y, self.angle, gs.PLAYER_BULLET_SPEED, 
                                   gs.PLAYER_BULLET_LIFETIME, self.bullet_size, 
                                   gs.PLAYER_BULLET_COLOR, 15, max_pierces=gs.PIERCING_BULLET_MAX_PIERCES,
                                   can_pierce_walls=True)
                self.bullets_group.add(new_bullet)
            elif self.current_weapon_mode == gs.WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == gs.WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                # Create heatseeker missile
                if missile_sound_asset_key and self.asset_manager:
                    missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
                    if missile_sound: missile_sound.play()
                new_missile = Missile(spawn_x, spawn_y, self.angle, gs.get_game_setting("MISSILE_DAMAGE"), enemies_group)
                self.missiles_group.add(new_missile)
                
                # Add regular bullets for HEATSEEKER_PLUS_BULLETS mode
                if self.current_weapon_mode == gs.WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                    new_bullet = Bullet(spawn_x, spawn_y, self.angle, gs.PLAYER_BULLET_SPEED, 
                                       gs.PLAYER_BULLET_LIFETIME, self.bullet_size, 
                                       gs.PLAYER_BULLET_COLOR, 15)
                    self.bullets_group.add(new_bullet)
            elif self.current_weapon_mode == gs.WEAPON_MODE_LIGHTNING:
                # Create lightning zap
                closest_enemy = None
                min_distance = float('inf')
                
                if enemies_group:
                    for enemy in enemies_group:
                        if enemy.alive:
                            dx = enemy.rect.centerx - self.rect.centerx
                            dy = enemy.rect.centery - self.rect.centery
                            distance = math.sqrt(dx*dx + dy*dy)
                            if distance < min_distance and distance < gs.LIGHTNING_ZAP_RANGE:
                                min_distance = distance
                                closest_enemy = enemy
                
                lightning_damage = gs.get_game_setting("LIGHTNING_DAMAGE", 15)
                lightning_lifetime = gs.get_game_setting("LIGHTNING_LIFETIME", 30)
                new_zap = LightningZap(self, closest_enemy, lightning_damage, lightning_lifetime, maze)
                self.lightning_zaps_group.add(new_zap)
            else:
                # Default single bullet
                new_bullet = Bullet(spawn_x, spawn_y, self.angle, gs.PLAYER_BULLET_SPEED, 
                                   gs.PLAYER_BULLET_LIFETIME, self.bullet_size, 
                                   gs.PLAYER_BULLET_COLOR, 15)
                self.bullets_group.add(new_bullet)
            
    def cycle_weapon_state(self):
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(gs.WEAPON_MODES_SEQUENCE)
        self.current_weapon_mode = gs.WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self._update_weapon_properties()
        self._load_sprite() 
        
    def _update_weapon_properties(self):
        # Update bullet properties based on weapon mode
        if self.current_weapon_mode == gs.WEAPON_MODE_BIG_SHOT:
            self.bullet_size = gs.get_game_setting("PLAYER_BIG_BULLET_SIZE")
            self.current_shoot_cooldown = gs.get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN") * 1.5
        elif self.current_weapon_mode in [gs.WEAPON_MODE_RAPID_SINGLE, gs.WEAPON_MODE_RAPID_TRI]:
            self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = gs.get_game_setting("PLAYER_RAPID_FIRE_COOLDOWN")
        elif self.current_weapon_mode == gs.WEAPON_MODE_BOUNCE:
            self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = gs.get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        elif self.current_weapon_mode == gs.WEAPON_MODE_PIERCE:
            self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = gs.get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")
        else:
            self.bullet_size = gs.get_game_setting("PLAYER_DEFAULT_BULLET_SIZE")
            self.current_shoot_cooldown = gs.get_game_setting("PLAYER_BASE_SHOOT_COOLDOWN")

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
        self.missiles_group.draw(surface)
        
        # Draw lightning zaps
        for zap in self.lightning_zaps_group:
            if hasattr(zap, 'draw'):
                zap.draw(surface, camera)

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
    def activate_shield(self, duration_ms):
        """Activate shield effect for the specified duration"""
        self.powerup_manager.activate_shield(duration_ms)
        
    def arm_speed_boost(self, duration_ms, multiplier=1.5):
        """Store speed boost for later activation with UP key"""
        self.powerup_manager.arm_speed_boost(duration_ms, multiplier)
        
    def activate_speed_boost(self):
        """Activate armed speed boost when UP key is pressed"""
        self.powerup_manager.activate_speed_boost()
        
    def update(self, current_time_ms, maze, enemies_group, player_actions, game_area_x_offset=0):
        if not self.alive: return
        
        # Update power-up states
        self.powerup_manager.update(current_time_ms)
        
        self.moving_forward = self.is_cruising
        
        super().update(maze, game_area_x_offset)
        
        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset)
        if hasattr(self, 'lightning_zaps_group'):
            self.lightning_zaps_group.update(current_time_ms)
            
# Method removed - now handled by PowerUpManager
            
    def take_damage(self, amount, sound_key_on_hit=None):
        if not self.alive: return
        
        # Check if invincibility is enabled in settings
        if gs.get_game_setting("PLAYER_INVINCIBILITY", False):
            # Play sound but don't reduce health
            if sound_key_on_hit and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_key_on_hit)
                if sound: sound.play()
            return
        
        # Check if shield is active
        if self.powerup_manager.handle_damage(amount):
            # Shield absorbs all damage
            if sound_key_on_hit and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_key_on_hit)
                if sound: sound.play()
            return
            
        self.health -= amount
        if sound_key_on_hit and self.asset_manager:
            sound = self.asset_manager.get_sound(sound_key_on_hit)
            if sound: sound.play()
        if self.health <= 0:
            self.health = 0
            self.alive = False
            
    def draw(self, surface, camera=None):
        # Draw power-up effects first (behind the drone)
        self.powerup_manager.draw(surface, camera)
        
        if self.alive and self.original_image:
            rotated_image = pygame.transform.rotate(self.original_image, -self.angle)
            draw_rect = rotated_image.get_rect(center=self.rect.center)
            surface.blit(rotated_image, draw_rect)
            
            # Draw health bar above the drone
            self.draw_health_bar(surface, camera)
            
        self.bullets_group.draw(surface)
        self.missiles_group.draw(surface)
        
        # Draw lightning zaps
        for zap in self.lightning_zaps_group:
            if hasattr(zap, 'draw'):
                zap.draw(surface, camera)