# entities/weapon_strategies.py
import pygame.time
from math import radians, cos, sin, sqrt
from pygame import Surface, SRCALPHA
from pygame.draw import circle
from settings_manager import get_setting
from .bullet import Bullet, Missile, LightningZap
from constants import (
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
)

def create_weapon_strategy(weapon_mode, player_drone):
    """
    Factory method to create the appropriate weapon strategy based on weapon mode.
    
    Maps weapon mode constants to their corresponding strategy implementations.
    This factory pattern allows for easy extension of the weapon system without
    modifying existing code.
    
    Args:
        weapon_mode (int): The weapon mode constant (e.g., WEAPON_MODE_TRI_SHOT)
        player_drone (PlayerDrone): The player drone instance that will use this weapon
        
    Returns:
        BaseWeaponStrategy: An instance of the appropriate weapon strategy
        
    Example:
        strategy = create_weapon_strategy(WEAPON_MODE_LIGHTNING, player)
        player.current_weapon_strategy = strategy
    """
    strategy_map = {
        WEAPON_MODE_DEFAULT: DefaultWeaponStrategy,
        WEAPON_MODE_TRI_SHOT: TriShotWeaponStrategy,
        WEAPON_MODE_RAPID_SINGLE: RapidSingleWeaponStrategy,
        WEAPON_MODE_RAPID_TRI: RapidTriShotWeaponStrategy,
        WEAPON_MODE_BIG_SHOT: BigShotWeaponStrategy,
        WEAPON_MODE_BOUNCE: BounceWeaponStrategy,
        WEAPON_MODE_PIERCE: PierceWeaponStrategy,
        WEAPON_MODE_HEATSEEKER: HeatseekerWeaponStrategy,
        WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: HeatseekerPlusBulletsWeaponStrategy,
        WEAPON_MODE_LIGHTNING: LightningWeaponStrategy
    }
    
    strategy_class = strategy_map.get(weapon_mode, DefaultWeaponStrategy)
    return strategy_class(player_drone)

class BaseWeaponStrategy:
    """
    Base class for all weapon strategies implementing the Strategy pattern.
    
    Defines the common interface and shared functionality for all weapon types.
    Each weapon strategy encapsulates the specific firing behavior, projectile
    creation, and timing for a particular weapon mode.
    
    Key Features:
    - Cooldown management for rate of fire control
    - Common projectile properties (speed, damage, lifetime)
    - Sound effect integration
    - Maze and enemy group references for advanced weapons
    
    Attributes:
        player (PlayerDrone): The player drone using this weapon
        bullet_speed (float): Speed of projectiles fired by this weapon
        bullet_damage (int): Damage dealt by projectiles
        shoot_cooldown (int): Milliseconds between shots
        last_shot_time (int): Timestamp of last shot for cooldown calculation
    """
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
        """
        Base fire method that handles common logic and delegates to _create_projectile.
        
        Manages cooldown checking, spawn position calculation, sound effects,
        and delegates actual projectile creation to subclass implementations.
        This template method pattern ensures consistent behavior across all weapons.
        
        Args:
            sound_asset_key (str, optional): Sound effect key for regular shots
            missile_sound_asset_key (str, optional): Sound effect key for missiles
            
        Returns:
            bool: True if weapon fired successfully, False if on cooldown
        """
        current_time_ms = pygame.time.get_ticks()
        if not self.can_shoot(current_time_ms):
            return False
            
        self.last_shot_time = current_time_ms
        
        # Calculate spawn position
        rad_angle = radians(self.player.angle)
        spawn_x = self.player.x + cos(rad_angle) * (self.player.rect.width / 2)
        spawn_y = self.player.y + sin(rad_angle) * (self.player.rect.height / 2)
        
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
        """
        Creates the specific projectile(s) for this weapon type.
        
        Template method that must be implemented by each weapon strategy to
        define its unique firing behavior. Called by the base fire() method
        after cooldown and positioning calculations.
        
        Args:
            spawn_x (float): X coordinate where projectile should spawn
            spawn_y (float): Y coordinate where projectile should spawn
            missile_sound_asset_key (str, optional): Sound key for missile weapons
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
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
                           self.bullet_color, self.bullet_damage, bullet_type='Big Shot')
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
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.shoot_cooldown = get_setting("weapons", "MISSILE_COOLDOWN", 3000)  # 3 seconds cooldown
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        # Create heatseeker missile
        if missile_sound_asset_key and self.asset_manager:
            missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
            if missile_sound: missile_sound.play()
        
        missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30)
        new_missile = Missile(spawn_x, spawn_y, self.player.angle, missile_damage, self.enemies_group)
        self.player.missiles_group.add(new_missile)

class HeatseekerPlusBulletsWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.shoot_cooldown = get_setting("weapons", "MISSILE_COOLDOWN", 3000)  # 3 seconds cooldown
        self.rapid_fire_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
        self.last_bullet_time = 0  # Separate tracking for bullet firing
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        current_time_ms = pygame.time.get_ticks()
        
        # Create heatseeker missile (on missile cooldown)
        if missile_sound_asset_key and self.asset_manager:
            missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
            if missile_sound: missile_sound.play()
        
        missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30)
        new_missile = Missile(spawn_x, spawn_y, self.player.angle, missile_damage, self.enemies_group)
        self.player.missiles_group.add(new_missile)
        
        # Create rapid fire bullet
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
        self.player.bullets_group.add(new_bullet)
        
        # Update last bullet time for rapid fire rate
        self.last_bullet_time = current_time_ms
    
    def fire(self, sound_asset_key=None, missile_sound_asset_key=None):
        """Override fire method to handle separate cooldowns for missiles and bullets"""
        current_time_ms = pygame.time.get_ticks()
        
        # Check if we can fire a missile (using the main cooldown)
        can_fire_missile = current_time_ms - self.last_shot_time > self.shoot_cooldown
        
        # Check if we can fire a bullet (using rapid fire cooldown)
        can_fire_bullet = current_time_ms - self.last_bullet_time > self.rapid_fire_cooldown
        
        # If we can fire a missile, do the full firing sequence
        if can_fire_missile:
            return super().fire(sound_asset_key, missile_sound_asset_key)
        
        # If we can only fire a bullet, do that
        elif can_fire_bullet:
            # Calculate spawn position
            rad_angle = radians(self.player.angle)
            spawn_x = self.player.x + cos(rad_angle) * (self.player.rect.width / 2)
            spawn_y = self.player.y + sin(rad_angle) * (self.player.rect.height / 2)
            
            # Play sound if provided
            if sound_asset_key and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_asset_key)
                if sound: sound.play()
            
            # Create just a bullet
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                               self.bullet_lifetime, self.bullet_size, 
                               self.bullet_color, self.bullet_damage)
            self.player.bullets_group.add(new_bullet)
            
            # Update last bullet time
            self.last_bullet_time = current_time_ms
            return True
            
        return False

class LightningWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone):
        super().__init__(player_drone)
        self.charge_start_time = 0
        self.is_charging = False
        self.charge_duration = 5000  # 5 seconds
        self.shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        
    def start_charging(self):
        """Start charging the lightning weapon"""
        if not self.is_charging:
            self.is_charging = True
            self.charge_start_time = pygame.time.get_ticks()
            
    def stop_charging_and_fire(self, sound_asset_key=None):
        """Stop charging and fire if fully charged"""
        if not self.is_charging:
            return False
            
        current_time = pygame.time.get_ticks()
        charge_time = current_time - self.charge_start_time
        
        self.is_charging = False
        
        if charge_time >= self.charge_duration:
            # Fully charged, fire chain lightning
            self._fire_chain_lightning(sound_asset_key)
            return True
        return False
        
    def _fire_chain_lightning(self, sound_asset_key=None):
        """Fire the charged lightning"""
        # Find closest enemy
        closest_enemy = None
        min_distance = float('inf')
        lightning_range = get_setting("weapons", "LIGHTNING_ZAP_RANGE", 250)
        
        if self.enemies_group:
            for enemy in self.enemies_group:
                if enemy.alive:
                    # Skip boss enemies for targeting
                    if hasattr(enemy, 'enemy_type') and 'boss' in enemy.enemy_type.lower():
                        continue
                    if hasattr(enemy, '__class__') and 'guardian' in enemy.__class__.__name__.lower():
                        continue
                        
                    dx = enemy.rect.centerx - self.player.rect.centerx
                    dy = enemy.rect.centery - self.player.rect.centery
                    distance = sqrt(dx*dx + dy*dy)
                    if distance < min_distance and distance < lightning_range:
                        min_distance = distance
                        closest_enemy = enemy
        
        if closest_enemy:
            # Play sound if provided
            if sound_asset_key and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_asset_key)
                if sound: sound.play()
                
            # Create lightning zap with chaining
            lightning_lifetime = get_setting("weapons", "LIGHTNING_LIFETIME", 30)
            new_zap = LightningZap(self.player, closest_enemy, 9999, lightning_lifetime, self.maze, game_area_x_offset=0, color_override=None, enemies_group=self.enemies_group)
            self.player.lightning_zaps_group.add(new_zap)
            
    def get_charge_progress(self):
        """Get charging progress (0.0 to 1.0)"""
        if not self.is_charging:
            return 0.0
        current_time = pygame.time.get_ticks()
        charge_time = current_time - self.charge_start_time
        return min(1.0, charge_time / self.charge_duration)
        
    def is_fully_charged(self):
        """Check if weapon is fully charged"""
        return self.is_charging and self.get_charge_progress() >= 1.0
        
    def draw_charging_effect(self, surface, camera=None):
        """Draw charging visual effect around player"""
        if not self.is_charging:
            return
            
        progress = self.get_charge_progress()
        if progress <= 0:
            return
            
        # Draw charging circle around player
        player_center = self.player.rect.center
        if camera:
            player_center = camera.apply_to_point(player_center)
            
        # Pulsing circle effect
        base_radius = 30
        max_radius = 60
        current_radius = int(base_radius + (max_radius - base_radius) * progress)
        
        # Color intensity based on charge
        intensity = int(100 + 155 * progress)
        charge_color = (intensity, intensity, 255)
        
        # Draw multiple circles for glow effect
        for i in range(3):
            alpha = int(50 * (1 - i * 0.3) * progress)
            radius = current_radius + i * 5
            
            # Create temporary surface for alpha blending
            temp_surface = Surface((radius * 2 + 10, radius * 2 + 10), SRCALPHA)
            circle(temp_surface, (*charge_color, alpha), (radius + 5, radius + 5), radius, 2)
            surface.blit(temp_surface, (player_center[0] - radius - 5, player_center[1] - radius - 5))
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        """Create normal lightning bullet"""
        # Create bright yellow lightning bullet to make it visible
        new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           (255, 255, 0), self.bullet_damage)
        self.player.bullets_group.add(new_bullet)