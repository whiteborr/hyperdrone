# entities/weapon_strategies.py
import pygame
import math
from settings_manager import get_setting
from .bullet import Bullet, Missile, LightningZap
from constants import (
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
)

class BaseWeaponStrategy:
    def __init__(self, player_drone):
        self.player = player_drone
        self.enemies_group = player_drone.enemies_group if hasattr(player_drone, 'enemies_group') else None
        self.maze = None
        self.asset_manager = player_drone.asset_manager if hasattr(player_drone, 'asset_manager') else None
        
        # Common bullet settings
        self.bullet_speed = get_setting("weapons", "PLAYER_BULLET_SPEED", 8)
        self.bullet_lifetime = get_setting("weapons", "PLAYER_BULLET_LIFETIME", 60)
        self.bullet_color = get_setting("weapons", "PLAYER_BULLET_COLOR", (0, 200, 255))
        self.bullet_damage = get_setting("weapons", "PLAYER_BULLET_DAMAGE", 15)
        self.bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 5)
        self.shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        self.last_shot_time = 0
        
    def get_cooldown(self):
        """Return the cooldown time for this weapon strategy"""
        return self.shoot_cooldown
    
    def fire(self, sound_asset_key=None, missile_sound_asset_key=None):
        """Base fire method that handles common logic and delegates to _create_projectile"""
        current_time_ms = pygame.time.get_ticks()
        if not self.can_shoot(current_time_ms):
            return False
            
        self.last_shot_time = current_time_ms
        
        # Calculate spawn position
        rad_angle = math.radians(self.player.angle)
        spawn_x = self.player.x + math.cos(rad_angle) * (self.player.rect.width / 2)
        spawn_y = self.player.y + math.sin(rad_angle) * (self.player.rect.height / 2)
        
        # Play sound if provided
        if sound_asset_key and self.asset_manager:
            sound = self.asset_manager.get_sound(sound_asset_key)
            if sound: sound.play()
        
        # Call the specific implementation
        self._create_projectile(spawn_x, spawn_y, missile_sound_asset_key)
        return True
    
    def can_shoot(self, current_time_ms=None):
        """Check if enough time has passed since the last shot"""
        if current_time_ms is None:
            current_time_ms = pygame.time.get_ticks()
        return current_time_ms - self.last_shot_time > self.shoot_cooldown
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        """To be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def update_maze(self, maze):
        """Update the maze reference"""
        self.maze = maze
    
    def update_enemies_group(self, enemies_group):
        """Update the enemies group reference"""
        self.enemies_group = enemies_group

class DefaultWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create single bullet
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
        self.player.bullets_group.add(new_bullet)

class TriShotWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create tri-shot bullets
        for angle_offset in [-15, 0, 15]:
            shot_angle = self.player.angle + angle_offset
            new_bullet = Bullet(spawn_x, spawn_y, shot_angle, self.bullet_speed, 
                               self.bullet_lifetime, self.bullet_size, 
                               self.bullet_color, self.bullet_damage)
            self.player.bullets_group.add(new_bullet)

class RapidSingleWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.shoot_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create single bullet with rapid fire
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
        self.player.bullets_group.add(new_bullet)

class RapidTriShotWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.shoot_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create tri-shot bullets with rapid fire
        for angle_offset in [-15, 0, 15]:
            shot_angle = self.player.angle + angle_offset
            new_bullet = Bullet(spawn_x, spawn_y, shot_angle, self.bullet_speed, 
                               self.bullet_lifetime, self.bullet_size, 
                               self.bullet_color, self.bullet_damage)
            self.player.bullets_group.add(new_bullet)

class BigShotWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.bullet_size = get_setting("weapons", "PLAYER_BIG_BULLET_SIZE", 8)
        self.shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500) * 1.5
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create big bullet
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
        self.player.bullets_group.add(new_bullet)

class BounceWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create bouncing bullet
        bounces = get_setting("weapons", "BOUNCING_BULLET_MAX_BOUNCES", 3)
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_bounces=bounces)
        self.player.bullets_group.add(new_bullet)

class PierceWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create piercing bullet
        pierces = get_setting("weapons", "PIERCING_BULLET_MAX_PIERCES", 2)
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_pierces=pierces,
                           can_pierce_walls=True)
        self.player.bullets_group.add(new_bullet)

class HeatseekerWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create heatseeker missile
        if missile_sound_asset_key and self.asset_manager:
            missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
            if missile_sound: missile_sound.play()
        
        missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30)
        new_missile = Missile(spawn_x, spawn_y, self.player.angle, missile_damage, self.enemies_group)
        self.player.missiles_group.add(new_missile)

class HeatseekerPlusBulletsWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create heatseeker missile
        if missile_sound_asset_key and self.asset_manager:
            missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
            if missile_sound: missile_sound.play()
        
        missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30)
        new_missile = Missile(spawn_x, spawn_y, self.player.angle, missile_damage, self.enemies_group)
        self.player.missiles_group.add(new_missile)
        
        # Add regular bullet
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
        self.player.bullets_group.add(new_bullet)

class LightningWeaponStrategy(BaseWeaponStrategy):
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Find closest enemy
        closest_enemy = None
        min_distance = float('inf')
        lightning_range = get_setting("weapons", "LIGHTNING_ZAP_RANGE", 250)
        
        if self.enemies_group:
            for enemy in self.enemies_group:
                if enemy.alive:
                    dx = enemy.rect.centerx - self.player.rect.centerx
                    dy = enemy.rect.centery - self.player.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    if distance < min_distance and distance < lightning_range:
                        min_distance = distance
                        closest_enemy = enemy
        
        # Create lightning zap
        lightning_damage = get_setting("weapons", "LIGHTNING_DAMAGE", 25)
        lightning_lifetime = get_setting("weapons", "LIGHTNING_LIFETIME", 30)
        new_zap = LightningZap(self.player, closest_enemy, lightning_damage, lightning_lifetime, self.maze)
        self.player.lightning_zaps_group.add(new_zap)