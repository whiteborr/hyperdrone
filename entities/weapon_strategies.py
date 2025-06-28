# entities/weapon_strategies.py
from pygame.time import get_ticks
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
    Factory method to create weapon strategy with upgrade level support.
    """
    from constants import WeaponModes
    
    # Basic weapons
    if weapon_mode in [WeaponModes.DEFAULT, WeaponModes.TRI_SHOT, WeaponModes.RAPID_SINGLE, WeaponModes.RAPID_TRI]:
        strategy_map = {
            WeaponModes.DEFAULT: DefaultWeaponStrategy,
            WeaponModes.TRI_SHOT: TriShotWeaponStrategy,
            WeaponModes.RAPID_SINGLE: RapidSingleWeaponStrategy,
            WeaponModes.RAPID_TRI: RapidTriShotWeaponStrategy
        }
        return strategy_map[weapon_mode](player_drone)
    
    # Big Shot Tree
    elif weapon_mode in [WeaponModes.BIG_SHOT_FIRE, WeaponModes.BIG_SHOT_EARTH, WeaponModes.BIG_SHOT_WATER, WeaponModes.BIG_SHOT_AIR, WeaponModes.BIG_SHOT_CONVERGENCE]:
        level = [WeaponModes.BIG_SHOT_FIRE, WeaponModes.BIG_SHOT_EARTH, WeaponModes.BIG_SHOT_WATER, WeaponModes.BIG_SHOT_AIR, WeaponModes.BIG_SHOT_CONVERGENCE].index(weapon_mode) + 1
        return BigShotWeaponStrategy(player_drone, level)
    
    # Bounce/Pierce Tree
    elif weapon_mode in [WeaponModes.BOUNCE, WeaponModes.PIERCE, WeaponModes.RICOCHET_CHAIN, WeaponModes.TUNNEL_SHOT, WeaponModes.DISRUPTOR_CORE]:
        level = [WeaponModes.BOUNCE, WeaponModes.PIERCE, WeaponModes.RICOCHET_CHAIN, WeaponModes.TUNNEL_SHOT, WeaponModes.DISRUPTOR_CORE].index(weapon_mode) + 1
        return BounceWeaponStrategy(player_drone, level)
    
    # Heatseeker Tree
    elif weapon_mode in [WeaponModes.HEATSEEKER, WeaponModes.HEATSEEKER_PLUS_BULLETS, WeaponModes.TRACK_SPIKE, WeaponModes.GORGON_MARK, WeaponModes.ORBITAL_ECHO]:
        level = [WeaponModes.HEATSEEKER, WeaponModes.HEATSEEKER_PLUS_BULLETS, WeaponModes.TRACK_SPIKE, WeaponModes.GORGON_MARK, WeaponModes.ORBITAL_ECHO].index(weapon_mode) + 1
        return HeatseekerWeaponStrategy(player_drone, level)
    
    # Lightning Tree
    elif weapon_mode in [WeaponModes.ARC_SPARK, WeaponModes.LIGHTNING, WeaponModes.CHAIN_BURST, WeaponModes.MINDLASH, WeaponModes.QUASINET]:
        level = [WeaponModes.ARC_SPARK, WeaponModes.LIGHTNING, WeaponModes.CHAIN_BURST, WeaponModes.MINDLASH, WeaponModes.QUASINET].index(weapon_mode) + 1
        return LightningWeaponStrategy(player_drone, level)
    
    # Fallback
    return DefaultWeaponStrategy(player_drone)

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
        current_time_ms = get_ticks()
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
            if sound:
                from settings_manager import get_setting
                fx_volume = get_setting("audio", "VOLUME_FX", 7) / 10.0
                sound.set_volume(0.7 * fx_volume)
                sound.play()
        
        # Call the specific implementation
        self._create_projectile(spawn_x, spawn_y, missile_sound_asset_key)
        return True
    
    def can_shoot(self, current_time_ms=None):
        """Check if enough time has passed since the last shot"""
        if current_time_ms is None:
            current_time_ms = get_ticks()
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
    def __init__(self, player_drone, level=1):
        super().__init__(player_drone)
        self.level = level
        self.bullet_size = get_setting("weapons", "PLAYER_BIG_BULLET_SIZE", 8) + (level - 1) * 2
        self.shoot_cooldown = max(300, get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500) * (2 - level * 0.1))
        self.bullet_damage = self.bullet_damage + (level - 1) * 10
        
        # Elemental colors
        self.element_colors = {
            1: (255, 100, 0),    # Fire - Orange
            2: (139, 69, 19),    # Earth - Brown
            3: (0, 100, 255),    # Water - Blue
            4: (200, 255, 200),  # Air - Light Green
            5: (255, 255, 255)   # Convergence - White
        }
        self.bullet_color = self.element_colors.get(level, self.bullet_color)
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        if self.level >= 5:  # Convergence - multiple shots
            for angle_offset in [-20, -10, 0, 10, 20]:
                shot_angle = self.player.angle + angle_offset
                new_bullet = Bullet(spawn_x, spawn_y, shot_angle, self.bullet_speed, 
                               self.bullet_lifetime, self.bullet_size, 
                               self.bullet_color, self.bullet_damage, bullet_type='Convergence Shot')
                self.player.bullets_group.add(new_bullet)
        else:
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, bullet_type=f'Elemental Shot L{self.level}')
            self.player.bullets_group.add(new_bullet)

class BounceWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone, level=1):
        super().__init__(player_drone)
        self.level = level
        self.bullet_damage = self.bullet_damage + (level - 1) * 5
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        if self.level == 1:  # Bounce
            bounces = get_setting("weapons", "BOUNCING_BULLET_MAX_BOUNCES", 3)
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_bounces=bounces)
        elif self.level == 2:  # Pierce
            pierces = get_setting("weapons", "PIERCING_BULLET_MAX_PIERCES", 2)
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_pierces=pierces, can_pierce_walls=True)
        elif self.level == 3:  # Ricochet Chain
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_bounces=6, max_pierces=1)
        elif self.level == 4:  # Tunnel Shot
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage, max_pierces=5, can_pierce_walls=True)
        else:  # Disruptor Core
            for angle_offset in [-15, 0, 15]:
                shot_angle = self.player.angle + angle_offset
                new_bullet = Bullet(spawn_x, spawn_y, shot_angle, self.bullet_speed, 
                               self.bullet_lifetime, self.bullet_size, 
                               self.bullet_color, self.bullet_damage, max_bounces=3, max_pierces=2, can_pierce_walls=True)
                self.player.bullets_group.add(new_bullet)
            return
        
        self.player.bullets_group.add(new_bullet)



class HeatseekerWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone, level=1):
        super().__init__(player_drone)
        self.level = level
        base_cooldown = get_setting("weapons", "MISSILE_COOLDOWN", 3000)
        self.shoot_cooldown = max(1000, base_cooldown - (level - 1) * 400)
        self.rapid_fire_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
        self.last_bullet_time = 0
    
    def _create_projectile(self, spawn_x, spawn_y, missile_sound_asset_key=None):
        if missile_sound_asset_key and self.asset_manager:
            missile_sound = self.asset_manager.get_sound(missile_sound_asset_key)
            if missile_sound:
                fx_volume = get_setting("audio", "VOLUME_FX", 7) / 10.0
                missile_sound.set_volume(0.7 * fx_volume)
                missile_sound.play()
        
        missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30) + (self.level - 1) * 15
        
        if self.level >= 2:  # Heatseeker + Bullets and above
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           self.bullet_color, self.bullet_damage)
            self.player.bullets_group.add(new_bullet)
        
        if self.level >= 3:  # Track Spike - multiple missiles
            missile_count = min(3, self.level - 1)
            for i in range(missile_count):
                angle_offset = (i - missile_count // 2) * 10
                missile_angle = self.player.angle + angle_offset
                new_missile = Missile(spawn_x, spawn_y, missile_angle, missile_damage, self.enemies_group)
                self.player.missiles_group.add(new_missile)
        else:
            new_missile = Missile(spawn_x, spawn_y, self.player.angle, missile_damage, self.enemies_group)
            self.player.missiles_group.add(new_missile)



class LightningWeaponStrategy(BaseWeaponStrategy):
    def __init__(self, player_drone, level=1):
        super().__init__(player_drone)
        self.level = level
        self.charge_start_time = 0
        self.is_charging = False
        self.charge_duration = max(2000, 5000 - (level - 1) * 500)  # Faster charge at higher levels
        self.shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        self.lightning_damage = get_setting("weapons", "LIGHTNING_DAMAGE", 25) + (level - 1) * 15
        
    def start_charging(self):
        """Start charging the lightning weapon"""
        if not self.is_charging:
            self.is_charging = True
            self.charge_start_time = get_ticks()
            
    def stop_charging_and_fire(self, sound_asset_key=None):
        """Stop charging and fire if fully charged"""
        if not self.is_charging:
            return False
            
        current_time = get_ticks()
        charge_time = current_time - self.charge_start_time
        
        self.is_charging = False
        
        if charge_time >= self.charge_duration:
            # Fully charged, fire chain lightning
            self._fire_chain_lightning(sound_asset_key)
            return True
        return False
        
    def _fire_chain_lightning(self, sound_asset_key=None):
        """Fire the charged lightning with level-based effects"""
        lightning_range = get_setting("weapons", "LIGHTNING_ZAP_RANGE", 250) + (self.level - 1) * 50
        
        # Find targets based on level
        targets = []
        if self.enemies_group:
            for enemy in self.enemies_group:
                if enemy.alive:
                    if hasattr(enemy, 'enemy_type') and 'boss' in enemy.enemy_type.lower():
                        continue
                    if hasattr(enemy, '__class__') and 'guardian' in enemy.__class__.__name__.lower():
                        continue
                        
                    dx = enemy.rect.centerx - self.player.rect.centerx
                    dy = enemy.rect.centery - self.player.rect.centery
                    distance = sqrt(dx*dx + dy*dy)
                    if distance < lightning_range:
                        targets.append((enemy, distance))
        
        if targets:
            targets.sort(key=lambda x: x[1])  # Sort by distance
            max_targets = min(self.level * 2, len(targets))  # More targets at higher levels
            
            if sound_asset_key and self.asset_manager:
                sound = self.asset_manager.get_sound(sound_asset_key)
                if sound:
                    fx_volume = get_setting("audio", "VOLUME_FX", 7) / 10.0
                    sound.set_volume(0.7 * fx_volume)
                    sound.play()
            
            lightning_lifetime = get_setting("weapons", "LIGHTNING_LIFETIME", 30)
            for i in range(max_targets):
                target_enemy = targets[i][0]
                damage = self.lightning_damage if i == 0 else self.lightning_damage // 2  # Reduced damage for chained targets
                new_zap = LightningZap(self.player, target_enemy, damage, lightning_lifetime, self.maze, game_area_x_offset=0, color_override=None, enemies_group=self.enemies_group)
                self.player.lightning_zaps_group.add(new_zap)
            
    def get_charge_progress(self):
        """Get charging progress (0.0 to 1.0)"""
        if not self.is_charging:
            return 0.0
        current_time = get_ticks()
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
        """Create lightning projectile based on level"""
        if self.level == 1:  # Arc Spark - simple lightning bullet
            new_bullet = Bullet(spawn_x, spawn_y, self.player.angle, self.bullet_speed, 
                           self.bullet_lifetime, self.bullet_size, 
                           (255, 255, 0), self.bullet_damage)
            self.player.bullets_group.add(new_bullet)
        else:  # Higher levels use charged lightning
            self._fire_chain_lightning()
