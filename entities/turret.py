# entities/turret.py
import pygame
import math
import random
import os
import logging

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY, CYAN, GOLD, ORANGE,
    PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    PLAYER_BULLET_COLOR, WEAPON_MODES_SEQUENCE, WEAPON_MODE_DEFAULT,
    WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI,
    WEAPON_MODE_BIG_SHOT, WEAPON_MODE_BOUNCE, WEAPON_MODE_PIERCE,
    WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS,
    WEAPON_MODE_LIGHTNING, PLAYER_BASE_SHOOT_COOLDOWN, PLAYER_RAPID_FIRE_COOLDOWN,
    MISSILE_COOLDOWN, MISSILE_DAMAGE, MISSILE_SPEED, MISSILE_LIFETIME, MISSILE_COLOR, MISSILE_SIZE,
    LIGHTNING_COOLDOWN, LIGHTNING_DAMAGE, LIGHTNING_LIFETIME, LIGHTNING_COLOR,
    BOUNCING_BULLET_MAX_BOUNCES, PIERCING_BULLET_MAX_PIERCES, PLAYER_BIG_BULLET_SIZE
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


TURRET_ASSET_KEYS = {
    WEAPON_MODE_DEFAULT: "turret_default_base_img", WEAPON_MODE_TRI_SHOT: "turret_trishot_base_img",
    WEAPON_MODE_RAPID_SINGLE: "turret_default_base_img", WEAPON_MODE_RAPID_TRI: "turret_trishot_base_img",
    WEAPON_MODE_BIG_SHOT: "turret_default_base_img", WEAPON_MODE_BOUNCE: "turret_default_base_img",
    WEAPON_MODE_PIERCE: "turret_default_base_img", WEAPON_MODE_HEATSEEKER: "turret_seeker_base_img",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "turret_seeker_base_img", WEAPON_MODE_LIGHTNING: "turret_lightning_base_img",
}

class Turret(pygame.sprite.Sprite):
    TURRET_COST = gs.get_game_setting("TURRET_BASE_COST", 50)
    UPGRADE_COST = gs.get_game_setting("TURRET_UPGRADE_COST", 100)
    MAX_UPGRADE_LEVEL = len(WEAPON_MODES_SEQUENCE) -1
    MAX_TURRETS = gs.get_game_setting("MAX_TURRETS_DEFENSE_MODE", 10)

    BASE_RANGE = TILE_SIZE * 3
    SPRITE_SIZE = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))

    def __init__(self, x, y, game_controller_ref, asset_manager):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.game_controller_ref, self.asset_manager = game_controller_ref, asset_manager
        self.angle, self.target, self.upgrade_level = 0, None, 0
        self.show_range_indicator = False
        self.weapon_mode_index = 0
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self.original_image, self.image = None, None
        self.rect = pygame.Rect(0, 0, self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
        self.rect.center = (int(self.x), int(self.y))
        self.last_shot_time = pygame.time.get_ticks()
        self.last_missile_shot_time = pygame.time.get_ticks()
        self.last_lightning_time = pygame.time.get_ticks()
        self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN
        self.current_missile_cooldown = MISSILE_COOLDOWN
        self.current_lightning_cooldown = LIGHTNING_COOLDOWN
        self.current_bullet_size = PLAYER_DEFAULT_BULLET_SIZE
        self.current_damage, self.current_range = 10, self.BASE_RANGE
        self._update_weapon_attributes()
        self.bullets = pygame.sprite.Group()
        self.missiles = pygame.sprite.Group()
        self.lightning_zaps = pygame.sprite.Group()
        self.turret_base_color_fallback = (100, 100, 120)
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
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]
        self.current_damage = 15 + (self.upgrade_level * 5)
        self.current_bullet_size = PLAYER_DEFAULT_BULLET_SIZE
        self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN / (1 + 0.1 * self.upgrade_level)
        self.current_range = self.BASE_RANGE + (self.upgrade_level * TILE_SIZE * 0.25)
        if self.current_weapon_mode == WEAPON_MODE_BIG_SHOT:
            self.current_bullet_size = PLAYER_BIG_BULLET_SIZE
            self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN * 1.5 / (1 + 0.1 * self.upgrade_level)
            self.current_damage = 30 + (self.upgrade_level * 10)
        elif self.current_weapon_mode in [WEAPON_MODE_RAPID_SINGLE, WEAPON_MODE_RAPID_TRI]:
            self.current_shoot_cooldown = PLAYER_RAPID_FIRE_COOLDOWN / (1 + 0.15 * self.upgrade_level)
            self.current_damage = 10 + (self.upgrade_level * 3)
        elif self.current_weapon_mode in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            self.current_damage = MISSILE_DAMAGE + (self.upgrade_level * 15)
            self.current_missile_cooldown = MISSILE_COOLDOWN / (1 + 0.1 * self.upgrade_level)
            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                 self.current_damage_std_bullet = 10 + (self.upgrade_level * 3)
                 self.current_shoot_cooldown_std_bullet = PLAYER_RAPID_FIRE_COOLDOWN / (1 + 0.15 * self.upgrade_level)
        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            self.current_damage = LIGHTNING_DAMAGE + (self.upgrade_level * 7)
            self.current_lightning_cooldown = LIGHTNING_COOLDOWN / (1 + 0.1 * self.upgrade_level)
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
                bounces, pierces, pierce_walls = (BOUNCING_BULLET_MAX_BOUNCES, 0, False) if self.current_weapon_mode == WEAPON_MODE_BOUNCE else (0, PIERCING_BULLET_MAX_PIERCES, True) if self.current_weapon_mode == WEAPON_MODE_PIERCE else (2,0,False)
                for angle_offset in angles:
                    self.bullets.add(Bullet(spawn_x, spawn_y, self.angle + angle_offset, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, self.current_bullet_size, PLAYER_BULLET_COLOR, int(self.current_damage), max_bounces=bounces, max_pierces=pierces, can_pierce_walls=pierce_walls))
        if self.current_weapon_mode in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            if (current_time - self.last_missile_shot_time) > self.current_missile_cooldown: self.last_missile_shot_time = current_time; self.missiles.add(Missile(spawn_x, spawn_y, self.angle, int(self.current_damage), enemies_group))
            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS and (current_time - self.last_shot_time) > self.current_shoot_cooldown_std_bullet:
                self.last_shot_time = current_time; self.bullets.add(Bullet(spawn_x, spawn_y, self.angle, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BULLET_COLOR, int(self.current_damage_std_bullet), max_bounces=2))
        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING and (current_time - self.last_lightning_time) > self.current_lightning_cooldown:
            self.last_lightning_time = current_time; self.lightning_zaps.add(LightningZap(self, self.target, int(self.current_damage), LIGHTNING_LIFETIME, maze_ref, getattr(self.game_controller_ref.maze, 'game_area_x_offset', 0)))

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
        if camera:
            if self.image and self.rect:
                scaled_size = (int(self.rect.width * camera.zoom_level), int(self.rect.height * camera.zoom_level))
                if scaled_size[0] > 0 and scaled_size[1] > 0:
                    scaled_image = pygame.transform.smoothscale(self.image, scaled_size)
                    screen_rect = camera.apply_to_rect(self.rect)
                    surface.blit(scaled_image, screen_rect)
            if self.show_range_indicator and self.rect:
                range_color = (*CYAN[:3], 70)
                # Draw a scaled circle directly on the screen surface
                screen_center = camera.apply_to_pos(self.rect.center)
                scaled_radius = self.current_range * camera.zoom_level
                if scaled_radius > 1:
                    pygame.draw.circle(surface, range_color, screen_center, int(scaled_radius), 2)
        else: # Fallback for non-camera drawing
            if self.image and self.rect: surface.blit(self.image, self.rect)
            if self.show_range_indicator and self.rect:
                pygame.draw.circle(surface, (*CYAN[:3], 70), self.rect.center, int(self.current_range), 2)
        
        # Draw projectiles, passing camera down
        for proj_group in [self.bullets, self.missiles, self.lightning_zaps]:
            for proj in proj_group:
                proj.draw(surface, camera)

    def take_damage(self, amount):
        pass