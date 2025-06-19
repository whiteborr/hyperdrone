# entities/turret.py
import pygame
import math
import random
import os
import logging

from settings_manager import get_setting
from constants import (
    WHITE, RED, GREEN, YELLOW, DARK_GREY, CYAN, GOLD, ORANGE,
    WEAPON_MODE_DEFAULT, WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING
)
try:
    from .bullet import Bullet, Missile, LightningZap
except ImportError:
    logging.error("Turret: Could not import Bullet, Missile, or LightningZap from .bullet. Using placeholders.")
    class Bullet(pygame.sprite.Sprite): pass
    class Missile(Bullet): pass
    class LightningZap(Bullet): pass


logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


# Get turret asset keys from settings
TURRET_ASSET_KEYS = {
    WEAPON_MODE_DEFAULT: "turret_default",
    WEAPON_MODE_TRI_SHOT: "turret_tri_shot",
    WEAPON_MODE_RAPID_SINGLE: "turret_rapid_single",
    WEAPON_MODE_RAPID_TRI: "turret_rapid_tri",
    WEAPON_MODE_BIG_SHOT: "turret_big_shot",
    WEAPON_MODE_BOUNCE: "turret_bounce",
    WEAPON_MODE_PIERCE: "turret_pierce",
    WEAPON_MODE_HEATSEEKER: "turret_heatseeker",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "turret_heatseeker_plus",
    WEAPON_MODE_LIGHTNING: "turret_lightning",
}

class Turret(pygame.sprite.Sprite):
    TURRET_COST = get_setting("gameplay", "TURRET_BASE_COST", 50)
    UPGRADE_COST = get_setting("gameplay", "TURRET_UPGRADE_COST", 200)
    MAX_UPGRADE_LEVEL = len(get_setting("gameplay", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])) - 1
    MAX_TURRETS = get_setting("gameplay", "MAX_TURRETS_DEFENSE_MODE", 10)

    BASE_RANGE = get_setting("gameplay", "TILE_SIZE", 80) * 3
    SPRITE_SIZE = (int(get_setting("gameplay", "TILE_SIZE", 80) * 0.8), int(get_setting("gameplay", "TILE_SIZE", 80) * 0.8))

    def __init__(self, x, y, game_controller_ref, asset_manager):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.game_controller_ref, self.asset_manager = game_controller_ref, asset_manager
        self.angle, self.target, self.upgrade_level = 0, None, 0
        self.show_range_indicator = False
        self.weapon_mode_index = 0
        self.turret_base_color_fallback = (100, 100, 120)
        weapon_modes = get_setting("gameplay", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.current_weapon_mode = weapon_modes[self.weapon_mode_index]
        self.original_image, self.image = None, None
        self.rect = pygame.Rect(0, 0, self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
        self.rect.center = (int(self.x), int(self.y))
        self.last_shot_time = pygame.time.get_ticks()
        self.last_missile_shot_time = pygame.time.get_ticks()
        self.last_lightning_time = pygame.time.get_ticks()
        self.current_shoot_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        self.current_missile_cooldown = get_setting("weapons", "MISSILE_COOLDOWN", 2000)
        self.current_lightning_cooldown = get_setting("weapons", "LIGHTNING_COOLDOWN", 1000)
        self.current_bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 5)
        self.current_damage, self.current_range = 10, self.BASE_RANGE
        self._update_weapon_attributes()
        self.bullets = pygame.sprite.Group()
        self.missiles = pygame.sprite.Group()
        self.lightning_zaps = pygame.sprite.Group()
        self._ensure_drawable_state()

    def _ensure_drawable_state(self):
        if not hasattr(self, 'original_image') or self.original_image is None: self._load_sprite_for_weapon_mode()
        if not hasattr(self, 'image') or self.image is None: self._draw_turret()
        if not hasattr(self, 'rect') or self.rect is None:
            if self.image: self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            else: self.rect = pygame.Rect(int(self.x - self.SPRITE_SIZE[0]//2), int(self.y - self.SPRITE_SIZE[1]//2), self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
        elif self.image and self.rect.size != self.image.get_size(): self.rect = self.image.get_rect(center=self.rect.center)

    def _load_sprite_for_weapon_mode(self):
        asset_key = TURRET_ASSET_KEYS.get(self.current_weapon_mode, TURRET_ASSET_KEYS[WEAPON_MODE_DEFAULT])
        loaded_image = self.asset_manager.get_image(asset_key)
        if loaded_image:
            try: self.original_image = pygame.transform.smoothscale(loaded_image, self.SPRITE_SIZE)
            except (ValueError, pygame.error) as e: logger.error(f"Turret: Error scaling sprite for key '{asset_key}': {e}"); self.original_image = None
        else: logger.warning(f"Turret: Sprite for key '{asset_key}' not found."); self.original_image = None
        if self.original_image is None:
            self.original_image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(self.original_image, self.turret_base_color_fallback, self.original_image.get_rect(), border_radius=3)
            pygame.draw.rect(self.original_image, (50,50,50), pygame.Rect(self.SPRITE_SIZE[0]*0.4, self.SPRITE_SIZE[1]*0.7, self.SPRITE_SIZE[0]*0.2, self.SPRITE_SIZE[1]*0.3))
        self._draw_turret()

    def _update_weapon_attributes(self):
        weapon_modes = get_setting("gameplay", "WEAPON_MODES_SEQUENCE", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.current_weapon_mode = weapon_modes[self.weapon_mode_index]
        self.current_damage = 15 + (self.upgrade_level * 5)
        self.current_bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 5)
        player_base_cooldown = get_setting("weapons", "PLAYER_BASE_SHOOT_COOLDOWN", 500)
        self.current_shoot_cooldown = player_base_cooldown / (1 + 0.1 * self.upgrade_level)
        tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.current_range = self.BASE_RANGE + (self.upgrade_level * tile_size * 0.25)
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.current_bullet_size = get_setting("weapons", "PLAYER_BIG_BULLET_SIZE", 8)
            self.current_shoot_cooldown = player_base_cooldown * 1.5 / (1 + 0.1 * self.upgrade_level)
            self.current_damage = 30 + (self.upgrade_level * 10)
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI]:
            rapid_fire_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
            self.current_shoot_cooldown = rapid_fire_cooldown / (1 + 0.15 * self.upgrade_level)
            self.current_damage = 10 + (self.upgrade_level * 3)
        elif self.current_weapon_mode in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            missile_damage = get_setting("weapons", "MISSILE_DAMAGE", 30)
            missile_cooldown = get_setting("weapons", "MISSILE_COOLDOWN", 2000)
            self.current_damage = missile_damage + (self.upgrade_level * 15)
            self.current_missile_cooldown = missile_cooldown / (1 + 0.1 * self.upgrade_level)
            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                 self.current_damage_std_bullet = 10 + (self.upgrade_level * 3)
                 rapid_fire_cooldown = get_setting("weapons", "PLAYER_RAPID_FIRE_COOLDOWN", 250)
                 self.current_shoot_cooldown_std_bullet = rapid_fire_cooldown / (1 + 0.15 * self.upgrade_level)
        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            lightning_damage = get_setting("weapons", "LIGHTNING_DAMAGE", 25)
            lightning_cooldown = get_setting("weapons", "LIGHTNING_COOLDOWN", 1000)
            self.current_damage = lightning_damage + (self.upgrade_level * 7)
            self.current_lightning_cooldown = lightning_cooldown / (1 + 0.1 * self.upgrade_level)
        self._load_sprite_for_weapon_mode()

    def _draw_turret(self):
        if not self.original_image: self.original_image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA); self.original_image.fill(self.turret_base_color_fallback)
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=self.rect.center if self.rect else (int(self.x), int(self.y)))

    def find_target(self, enemies_group):
        self.target = None; closest_enemy = None; min_dist_sq = self.current_range ** 2
        if not enemies_group: return
        for enemy in enemies_group:
            if not enemy.alive: continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq: min_dist_sq = dist_sq; closest_enemy = enemy
        self.target = closest_enemy

    def aim_at_target(self):
        if self.target and self.target.alive:
            dx, dy = self.target.rect.centerx - self.x, self.target.rect.centery - self.y
            new_angle_deg = math.degrees(math.atan2(dy, dx))
            if abs((new_angle_deg - self.angle + 180) % 360 - 180) > 0.5:
                self.angle = new_angle_deg; self._draw_turret()
            return True
        return False

    def shoot(self, enemies_group, maze_ref):
        current_time = pygame.time.get_ticks()
        if not self.target or not self.target.alive or not self.rect: return
        rad_angle = math.radians(self.angle); spawn_offset = (self.SPRITE_SIZE[0] / 2) + 2
        spawn_x, spawn_y = self.x + spawn_offset*math.cos(rad_angle), self.y + spawn_offset*math.sin(rad_angle)
        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            if (current_time - self.last_shot_time) > self.current_shoot_cooldown:
                self.last_shot_time = current_time
                angles = [-15, 0, 15] if self.current_weapon_mode in [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_TRI] else [0]
                bounces = get_setting("weapons", "BOUNCING_BULLET_MAX_BOUNCES", 3) if self.current_weapon_mode == WEAPON_MODE_BOUNCE else 0
                pierces = get_setting("weapons", "PIERCING_BULLET_MAX_PIERCES", 2) if self.current_weapon_mode == WEAPON_MODE_PIERCE else 0
                pierce_walls = True if self.current_weapon_mode == WEAPON_MODE_PIERCE else False
                bullet_speed = get_setting("weapons", "PLAYER_BULLET_SPEED", 8)
                bullet_lifetime = get_setting("weapons", "PLAYER_BULLET_LIFETIME", 60)
                bullet_color = get_setting("weapons", "PLAYER_BULLET_COLOR", (0, 200, 255))
                for angle_offset in angles:
                    self.bullets.add(Bullet(spawn_x, spawn_y, self.angle + angle_offset, bullet_speed, bullet_lifetime, self.current_bullet_size, bullet_color, int(self.current_damage), max_bounces=bounces, max_pierces=pierces, can_pierce_walls=pierce_walls))
        if self.current_weapon_mode in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            if (current_time - self.last_missile_shot_time) > self.current_missile_cooldown: 
                self.last_missile_shot_time = current_time
                self.missiles.add(Missile(spawn_x, spawn_y, self.angle, int(self.current_damage), enemies_group))
            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS and (current_time - self.last_shot_time) > self.current_shoot_cooldown_std_bullet:
                self.last_shot_time = current_time
                bullet_speed = get_setting("weapons", "PLAYER_BULLET_SPEED", 8)
                bullet_lifetime = get_setting("weapons", "PLAYER_BULLET_LIFETIME", 60)
                bullet_size = get_setting("weapons", "PLAYER_DEFAULT_BULLET_SIZE", 5)
                bullet_color = get_setting("weapons", "PLAYER_BULLET_COLOR", (0, 200, 255))
                self.bullets.add(Bullet(spawn_x, spawn_y, self.angle, bullet_speed, bullet_lifetime, bullet_size, bullet_color, int(self.current_damage_std_bullet), max_bounces=2))
        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING and (current_time - self.last_lightning_time) > self.current_lightning_cooldown:
            self.last_lightning_time = current_time
            lightning_lifetime = get_setting("weapons", "LIGHTNING_LIFETIME", 30)
            self.lightning_zaps.add(LightningZap(self, self.target, int(self.current_damage), lightning_lifetime, maze_ref, getattr(self.game_controller_ref.maze, 'game_area_x_offset', 0)))

    def upgrade(self):
        if self.weapon_mode_index < self.MAX_UPGRADE_LEVEL:
            self.weapon_mode_index += 1; self.upgrade_level = self.weapon_mode_index; self._update_weapon_attributes(); return True
        return False

    def update(self, enemies_group, maze_ref, game_area_x_offset=0):
        self.find_target(enemies_group)
        if self.aim_at_target(): self.shoot(enemies_group, maze_ref)
        self.bullets.update(maze_ref, game_area_x_offset)
        self.missiles.update(enemies_group, maze_ref, game_area_x_offset)
        self.lightning_zaps.update(pygame.time.get_ticks())

    def draw(self, surface, camera=None):
        # Always use non-camera drawing
        if self.image and self.rect: 
            surface.blit(self.image, self.rect)
        if self.show_range_indicator and self.rect:
            pygame.draw.circle(surface, (*CYAN[:3], 70), self.rect.center, int(self.current_range), 2)
        
        # Draw projectiles, passing camera down (which is now None)
        for proj_group in [self.bullets, self.missiles, self.lightning_zaps]:
            for proj in proj_group:
                proj.draw(surface, None)

    def take_damage(self, amount):
        pass