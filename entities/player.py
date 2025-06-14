# entities/player.py
import pygame
import math
import os
import random
import logging 

from settings_manager import get_setting
from constants import (
    WHITE, RED, GREEN, YELLOW, BLACK, BLUE, CYAN, GOLD,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
)

from .bullet import Bullet, Missile, LightningZap
from .particle import Particle
from .base_drone import BaseDrone
from .powerup_manager import PowerUpManager
from .weapon_strategies import (
    DefaultWeaponStrategy, TriShotWeaponStrategy, RapidSingleWeaponStrategy, RapidTriShotWeaponStrategy,
    BigShotWeaponStrategy, BounceWeaponStrategy, PierceWeaponStrategy, HeatseekerWeaponStrategy,
    HeatseekerPlusBulletsWeaponStrategy, LightningWeaponStrategy
)


logger = logging.getLogger(__name__)


class PlayerDrone(BaseDrone): 
    def __init__(self, x, y, drone_id, drone_stats, asset_manager, sprite_asset_key, crash_sound_key, drone_system):
        base_speed_from_stats = drone_stats.get("speed", get_setting("gameplay", "PLAYER_SPEED", 3))
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.drone_visual_size = (int(tile_size * 0.7), int(tile_size * 0.7))
        super().__init__(x, y, size=self.drone_visual_size[0], speed=base_speed_from_stats)
        
        self.drone_id = drone_id
        self.drone_system = drone_system  
        self.asset_manager = asset_manager
        self.sprite_asset_key = sprite_asset_key
        self.crash_sound_key = crash_sound_key
        
        # Initialize last_shot_time and current_shoot_cooldown for UI
        self.last_shot_time = pygame.time.get_ticks()
        self.current_shoot_cooldown = 0
        
        self.base_hp = drone_stats.get("hp", get_setting("gameplay", "PLAYER_MAX_HEALTH", 100))
        self.base_turn_speed = drone_stats.get("turn_speed", get_setting("gameplay", "ROTATION_SPEED", 5))
        self.rotation_speed = self.base_turn_speed
        self.base_speed = base_speed_from_stats  # Store base speed for powerups
        
        self.is_cruising = False 
        self.max_health = self.base_hp
        self.health = self.max_health
        
        # Initialize PowerUpManager
        self.powerup_manager = PowerUpManager(self)
        
        self.original_image = None
        self.image = None
        
        initial_weapon_mode = get_setting("gameplay", "INITIAL_WEAPON_MODE", 0)
        weapon_modes_sequence = get_setting("gameplay", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        try:
            self.weapon_mode_index = weapon_modes_sequence.index(initial_weapon_mode)
        except ValueError:
            self.weapon_mode_index = 0 
        self.current_weapon_mode = weapon_modes_sequence[self.weapon_mode_index]
        
        self.bullets_group = pygame.sprite.Group()
        self.missiles_group = pygame.sprite.Group()
        self.lightning_zaps_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()  # Initialize enemies_group
        
        # Current weapon strategy will be set by set_weapon_mode
        
        # Set initial weapon strategy
        self.current_weapon_strategy = None
        self.set_weapon_mode(self.current_weapon_mode)
        self._load_sprite()

    def _load_sprite(self):
        # Always use the base drone sprite first
        loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        
        # If we have a valid image, use it
        if loaded_image:
            # We now assume the source image faces RIGHT and do not apply any correction here.
            self.original_image = pygame.transform.smoothscale(loaded_image, self.drone_visual_size)
        else:
            self.original_image = self.asset_manager._create_fallback_surface(size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150))
        
        self.image = self.original_image.copy()
        current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
        self.rect = self.image.get_rect(center=current_center)
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)
        
    def _update_drone_sprite(self):
        """Update the drone sprite based on the current weapon mode"""
        # Get the drone ID and weapon mode
        drone_id = self.drone_id.lower()  # Ensure lowercase for consistency
        weapon_mode = self.current_weapon_mode
        
        # Map weapon modes to their sprite names
        from constants import (
            WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
            WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
            WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
            WEAPON_MODE_LIGHTNING
        )
        
        weapon_sprite_names = {
            WEAPON_MODE_DEFAULT: "default",
            WEAPON_MODE_TRI_SHOT: "tri_shot",
            WEAPON_MODE_RAPID_SINGLE: "rapid_single",
            WEAPON_MODE_RAPID_TRI: "rapid_tri_shot",
            WEAPON_MODE_BIG_SHOT: "big_shot",
            WEAPON_MODE_BOUNCE: "bounce",
            WEAPON_MODE_PIERCE: "pierce",
            WEAPON_MODE_HEATSEEKER: "heatseeker",
            WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "heatseeker_plus_bullets",
            WEAPON_MODE_LIGHTNING: "lightning"
        }
        
        # Get the weapon sprite name
        weapon_sprite_name = weapon_sprite_names.get(weapon_mode, "default")
        
        # Try to load the weapon-specific drone sprite
        weapon_sprite_key = f"drone_{weapon_sprite_name}"
        loaded_image = self.asset_manager.get_image(weapon_sprite_key)
        
        # If not found, fall back to the default drone sprite
        if not loaded_image:
            loaded_image = self.asset_manager.get_image(self.sprite_asset_key)
        
        # If we have a valid image, use it
        if loaded_image:
            self.original_image = pygame.transform.smoothscale(loaded_image, self.drone_visual_size)
        else:
            # This should rarely happen as we already checked for the default sprite in _load_sprite
            self.original_image = self.asset_manager._create_fallback_surface(size=self.drone_visual_size, text=self.drone_id[:1], color=(0,200,0,150))
        
        # Update the image and maintain the current center position
        current_center = self.rect.center if hasattr(self, 'rect') and self.rect else (int(self.x), int(self.y))
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=current_center)
        self.collision_rect = self.rect.inflate(-self.rect.width * 0.3, -self.rect.height * 0.3)

    def update(self, current_time_ms, maze, enemies_group, player_actions, game_area_x_offset=0):
        if not self.alive: return
        
        # Store enemies_group for weapon strategies that need it
        self.enemies_group = enemies_group
        
        # Update power-up states
        self.powerup_manager.update(current_time_ms)
        
        # Update weapon strategy with current maze and enemies
        if self.current_weapon_strategy:
            self.current_weapon_strategy.update_maze(maze)
            self.current_weapon_strategy.update_enemies_group(enemies_group)
        
        self.moving_forward = self.is_cruising
        
        super().update(maze, game_area_x_offset)
        
        self.bullets_group.update(maze, game_area_x_offset)
        self.missiles_group.update(enemies_group, maze, game_area_x_offset)
        if hasattr(self, 'lightning_zaps_group'):
            self.lightning_zaps_group.update(current_time_ms)

    def rotate(self, direction):
        super().rotate(direction, self.rotation_speed)
            
    def shoot(self, sound_asset_key=None, missile_sound_asset_key=None, maze=None, enemies_group=None):
        # Update references if provided
        if enemies_group is not None:
            self.enemies_group = enemies_group
            if self.current_weapon_strategy:
                self.current_weapon_strategy.update_enemies_group(enemies_group)
        
        if maze is not None and self.current_weapon_strategy:
            self.current_weapon_strategy.update_maze(maze)
        
        # Delegate firing logic to the current weapon strategy
        if self.current_weapon_strategy:
            if self.current_weapon_strategy.fire(sound_asset_key, missile_sound_asset_key):
                # Update last_shot_time for UI cooldown display
                self.last_shot_time = pygame.time.get_ticks()
                # Ensure the drone sprite matches the current weapon mode
                self._update_drone_sprite()
            
    def cycle_weapon_state(self):
        weapon_modes_sequence = get_setting("gameplay", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.weapon_mode_index = (self.weapon_mode_index + 1) % len(weapon_modes_sequence)
        self.current_weapon_mode = weapon_modes_sequence[self.weapon_mode_index]
        self.set_weapon_mode(self.current_weapon_mode)
        self._update_drone_sprite()
        
    def set_weapon_mode(self, mode):
        """Set the current weapon strategy based on the weapon mode"""
        from .weapon_strategies import create_weapon_strategy
        
        self.current_weapon_mode = mode
        self.current_weapon_strategy = create_weapon_strategy(mode, self)
        
        # Update cooldown value for UI
        self.current_shoot_cooldown = self.current_weapon_strategy.get_cooldown()
        self._update_drone_sprite()
        
        # Reset last_shot_time attribute needed by UI
        self.last_shot_time = pygame.time.get_ticks()

    def take_damage(self, amount, sound_key_on_hit=None):
        if not self.alive: return
        
        # Check if invincibility is enabled in settings
        if get_setting("gameplay", "PLAYER_INVINCIBILITY", False):
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
                
    def draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect: return
        bar_width = self.rect.width * 0.8
        bar_height = 5
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.top - bar_height - 3
        health_percentage = self.health / self.max_health if self.max_health > 0 else 0
        filled_width = int(bar_width * health_percentage)
        fill_color = GREEN if health_percentage > 0.6 else YELLOW if health_percentage > 0.3 else RED
        pygame.draw.rect(surface, (50,50,50), (bar_x, bar_y, bar_width, bar_height))
        if filled_width > 0: pygame.draw.rect(surface, fill_color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
        
    def activate_shield(self, duration_ms):
        """Activate shield effect for the specified duration"""
        self.powerup_manager.activate_shield(duration_ms)
        
    def arm_speed_boost(self, duration_ms, multiplier=1.5):
        """Store speed boost for later activation with UP key"""
        self.powerup_manager.arm_speed_boost(duration_ms, multiplier)
        
    def activate_speed_boost(self):
        """Activate armed speed boost when UP key is pressed"""
        self.powerup_manager.activate_speed_boost()