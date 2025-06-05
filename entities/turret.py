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
    # Minimal placeholders
    class Bullet(pygame.sprite.Sprite):
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False):
            super().__init__(); self.image = pygame.Surface([max(1,size*2), max(1,size*2)], pygame.SRCALPHA); self.image.fill(color if color else (255,0,0))
            self.rect = self.image.get_rect(center=(x,y)); self.alive = True; self.lifetime = lifetime; self.damage = damage
        def update(self, maze, offset): self.lifetime -=1; _=maze; _=offset
        def draw(self, surface):
            if self.alive and self.rect and self.image: surface.blit(self.image, self.rect)

    class Missile(Bullet): pass
    class LightningZap(Bullet):
        def __init__(self, player_ref, initial_target_enemy_ref, damage, lifetime_frames, maze_ref, game_area_x_offset=0, color_override=None):
            x, y = player_ref.x, player_ref.y; angle = player_ref.angle
            super().__init__(x, y, angle, 0, lifetime_frames, 5, color_override if color_override else LIGHTNING_COLOR, damage)
            self.current_start_pos = (x,y); self.current_target_pos = (x + 50, y)
        def draw(self, surface):
             if self.alive and self.rect: pygame.draw.line(surface, self.image.get_at((0,0)), self.current_start_pos, self.current_target_pos, 2)


logger = logging.getLogger(__name__)
# BasicConfig should ideally be called once at the application entry point.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')


TURRET_IMAGE_PATHS = {
    WEAPON_MODE_DEFAULT: "assets/images/level_elements/turret1.png",
    WEAPON_MODE_TRI_SHOT: "assets/images/level_elements/turret2.png",
    WEAPON_MODE_RAPID_SINGLE: "assets/images/level_elements/turret1.png",
    WEAPON_MODE_RAPID_TRI: "assets/images/level_elements/turret2.png",
    WEAPON_MODE_BIG_SHOT: "assets/images/level_elements/turret1.png",
    WEAPON_MODE_BOUNCE: "assets/images/level_elements/turret1.png",
    WEAPON_MODE_PIERCE: "assets/images/level_elements/turret1.png",
    WEAPON_MODE_HEATSEEKER: "assets/images/level_elements/turret3.png",
    WEAPON_MODE_HEATSEEKER_PLUS_BULLETS: "assets/images/level_elements/turret3.png",
    WEAPON_MODE_LIGHTNING: "assets/images/level_elements/turret4.png",
}

class Turret(pygame.sprite.Sprite):
    TURRET_COST = gs.get_game_setting("TURRET_BASE_COST", 50)
    UPGRADE_COST = gs.get_game_setting("TURRET_UPGRADE_COST", 100)
    MAX_UPGRADE_LEVEL = len(WEAPON_MODES_SEQUENCE) -1
    MAX_TURRETS = gs.get_game_setting("MAX_TURRETS_DEFENSE_MODE", 10)

    BASE_RANGE = TILE_SIZE * 3
    SPRITE_SIZE = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))

    def __init__(self, x, y, game_controller_ref):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.game_controller_ref = game_controller_ref
        self.angle = 0
        self.target = None
        self.upgrade_level = 0
        self.show_range_indicator = False

        self.weapon_mode_index = 0
        self.current_weapon_mode = WEAPON_MODES_SEQUENCE[self.weapon_mode_index]

        self.original_image = None
        self.image = None
        self.rect = pygame.Rect(0, 0, self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
        self.rect.center = (int(self.x), int(self.y))

        self.last_shot_time = pygame.time.get_ticks()
        self.last_missile_shot_time = pygame.time.get_ticks()
        self.last_lightning_time = pygame.time.get_ticks()

        self.current_shoot_cooldown = PLAYER_BASE_SHOOT_COOLDOWN
        self.current_missile_cooldown = MISSILE_COOLDOWN
        self.current_lightning_cooldown = LIGHTNING_COOLDOWN
        self.current_bullet_size = PLAYER_DEFAULT_BULLET_SIZE
        self.current_damage = 10
        self.current_range = self.BASE_RANGE

        self._update_weapon_attributes()

        self.bullets = pygame.sprite.Group()
        self.missiles = pygame.sprite.Group()
        self.lightning_zaps = pygame.sprite.Group()

        self.turret_base_color_fallback = (100, 100, 120)
        self._ensure_drawable_state()
        logger.debug(f"Turret ID {id(self)} initialized at ({x},{y}), Level {self.upgrade_level}, Weapon Mode: {self.current_weapon_mode}. Rect: {self.rect}, Image: {'Set' if self.image else 'None'}")

    def _ensure_drawable_state(self):
        """Ensures self.image and self.rect are valid for drawing by Group.draw()."""
        if not hasattr(self, 'original_image') or self.original_image is None:
            self._load_sprite_for_weapon_mode()

        if not hasattr(self, 'image') or self.image is None:
            self._draw_turret()

        if not hasattr(self, 'rect') or self.rect is None:
            if self.image:
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            else:
                self.rect = pygame.Rect(int(self.x - self.SPRITE_SIZE[0]//2), int(self.y - self.SPRITE_SIZE[1]//2), self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
                self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                self.image.fill((255,100,0,100)) # Orange error fallback
                logger.error(f"Turret ID {id(self)} _ensure_drawable_state: Critical - image AND rect were None. Forced creation.")
        elif self.image and self.rect.size != self.image.get_size():
             current_center = self.rect.center # Preserve center
             self.rect = self.image.get_rect(center=current_center)


    def _load_sprite_for_weapon_mode(self):
        image_path = TURRET_IMAGE_PATHS.get(self.current_weapon_mode, TURRET_IMAGE_PATHS[WEAPON_MODE_DEFAULT])
        if os.path.exists(image_path):
            try:
                loaded_image = pygame.image.load(image_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, self.SPRITE_SIZE)
            except pygame.error as e:
                logger.error(f"Turret ID {id(self)}: Error loading sprite '{image_path}': {e}")
                self.original_image = None
        else:
            logger.warning(f"Turret ID {id(self)}: Sprite path not found '{image_path}'.")
            self.original_image = None

        if not self.original_image:
            self.original_image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA)
            pygame.draw.rect(self.original_image, self.turret_base_color_fallback, self.original_image.get_rect(), border_radius=3)
            barrel_rect = pygame.Rect(self.SPRITE_SIZE[0] * 0.4, self.SPRITE_SIZE[1] * 0.7, self.SPRITE_SIZE[0] * 0.2, self.SPRITE_SIZE[1] * 0.3) # Pointing "up"
            pygame.draw.rect(self.original_image, (50,50,50), barrel_rect)
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
        elif self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
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
        if not self.original_image:
             self.original_image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA)
             self.original_image.fill(self.turret_base_color_fallback)
        current_center = self.rect.center if self.rect else (int(self.x), int(self.y))
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=current_center)


    def find_target(self, enemies_group):
        self.target = None
        closest_enemy = None
        min_dist_sq = self.current_range ** 2
        if not enemies_group: return

        for enemy in enemies_group:
            if not enemy.alive: continue
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        self.target = closest_enemy

    def aim_at_target(self):
        if self.target and self.target.alive:
            dx = self.target.rect.centerx - self.x
            dy = self.target.rect.centery - self.y
            target_angle_rad = math.atan2(dy, dx)
            new_angle_deg = math.degrees(target_angle_rad)
            angle_diff = (new_angle_deg - self.angle + 180) % 360 - 180
            if abs(angle_diff) > 0.5:
                self.angle = new_angle_deg
                self._draw_turret()
            return True
        return False

    def shoot(self, enemies_group, maze_ref):
        current_time = pygame.time.get_ticks()
        if not self.target or not self.target.alive or not self.rect:
            return

        rad_angle_shoot = math.radians(self.angle)
        spawn_offset_from_center = (self.SPRITE_SIZE[0] / 2) + 2
        base_spawn_x = self.x + spawn_offset_from_center * math.cos(rad_angle_shoot)
        base_spawn_y = self.y + spawn_offset_from_center * math.sin(rad_angle_shoot)

        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            if (current_time - self.last_shot_time) > self.current_shoot_cooldown:
                self.last_shot_time = current_time
                angles_to_fire = [0]
                if self.current_weapon_mode in [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_TRI]: angles_to_fire = [-15, 0, 15]
                bullet_lifetime_actual = gs.get_game_setting("PLAYER_BULLET_LIFETIME", 100)
                for angle_offset in angles_to_fire:
                    eff_angle = self.angle + angle_offset
                    bounces, pierces, can_pierce_w = 2, 0, False
                    if self.current_weapon_mode == WEAPON_MODE_BOUNCE: bounces = BOUNCING_BULLET_MAX_BOUNCES
                    elif self.current_weapon_mode == WEAPON_MODE_PIERCE: pierces, can_pierce_w = PIERCING_BULLET_MAX_PIERCES, True
                    new_bullet = Bullet(base_spawn_x, base_spawn_y, eff_angle, PLAYER_BULLET_SPEED, bullet_lifetime_actual,
                                        self.current_bullet_size, PLAYER_BULLET_COLOR, int(self.current_damage),
                                        max_bounces=bounces, max_pierces=pierces, can_pierce_walls=can_pierce_w)
                    self.bullets.add(new_bullet)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED standard/variant. Mode: {self.current_weapon_mode}. Bullets in group: {len(self.bullets)}")
                # if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'): self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3)

        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if (current_time - self.last_missile_shot_time) > self.current_missile_cooldown:
                self.last_missile_shot_time = current_time
                new_missile = Missile(base_spawn_x, base_spawn_y, self.angle, int(self.current_damage), enemies_group)
                self.missiles.add(new_missile)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED MISSILE. Missiles in group: {len(self.missiles)}")
                # if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'): self.game_controller_ref.play_sound('missile_launch', 0.4)

            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                 if (current_time - self.last_shot_time) > self.current_shoot_cooldown_std_bullet:
                    self.last_shot_time = current_time
                    bullet_lifetime_actual = gs.get_game_setting("PLAYER_BULLET_LIFETIME", 100)
                    new_bullet = Bullet(base_spawn_x, base_spawn_y, self.angle, PLAYER_BULLET_SPEED, bullet_lifetime_actual,
                                        PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BULLET_COLOR, int(self.current_damage_std_bullet), max_bounces=2)
                    self.bullets.add(new_bullet)
                    logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) Fired rapid bullet (Seeker+). Bullets in group: {len(self.bullets)}")
                    # if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'): self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.2)

        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if (current_time - self.last_lightning_time) > self.current_lightning_cooldown:
                self.last_lightning_time = current_time
                game_area_x_offset = self.game_controller_ref.maze.game_area_x_offset if self.game_controller_ref and hasattr(self.game_controller_ref, 'maze') and self.game_controller_ref.maze else 0
                lightning_lifetime_frames_actual = gs.get_game_setting("LIGHTNING_LIFETIME", 120)

                new_zap = LightningZap(player_ref=self, initial_target_enemy_ref=self.target,
                                       damage=int(self.current_damage), lifetime_frames=lightning_lifetime_frames_actual,
                                       maze_ref=maze_ref, game_area_x_offset=game_area_x_offset)
                self.lightning_zaps.add(new_zap)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED LIGHTNING. Zaps in group: {len(self.lightning_zaps)}")
                # if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'): self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3)

    def upgrade(self):
        if self.weapon_mode_index < self.MAX_UPGRADE_LEVEL:
            self.weapon_mode_index += 1
            self.upgrade_level = self.weapon_mode_index
            self._update_weapon_attributes()
            logger.info(f"Turret at ({self.x:.0f},{self.y:.0f}) upgraded to level {self.upgrade_level}. New mode: {self.current_weapon_mode}")
            return True
        return False

    def update(self, enemies_group, maze_ref, game_area_x_offset=0):
        self.find_target(enemies_group)
        if self.aim_at_target():
            self.shoot(enemies_group, maze_ref)

        self.bullets.update(maze_ref, game_area_x_offset)
        self.missiles.update(enemies_group, maze_ref, game_area_x_offset)
        self.lightning_zaps.update(pygame.time.get_ticks())

    def draw(self, surface):
        if self.image and self.rect:
            surface.blit(self.image, self.rect)
        else:
             # Fallback drawing if image/rect is missing
             fallback_rect = self.rect if self.rect else pygame.Rect(int(self.x - self.SPRITE_SIZE[0]//2), int(self.y - self.SPRITE_SIZE[1]//2), self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])
             pygame.draw.rect(surface, gs.ORANGE, fallback_rect, 3)
             if not self.image: logger.warning(f"Turret ID {id(self)} DRAWING FALLBACK (Orange Rect) because self.image is None.")
             if not self.rect: logger.warning(f"Turret ID {id(self)} DRAWING FALLBACK (Orange Rect) because self.rect is None.")


        if self.show_range_indicator and self.rect:
            range_color = (0,100,255, 70)
            temp_range_surface = pygame.Surface((int(self.current_range * 2), int(self.current_range * 2)), pygame.SRCALPHA)
            pygame.draw.circle(temp_range_surface, range_color, (int(self.current_range), int(self.current_range)), int(self.current_range))
            surface.blit(temp_range_surface, (self.rect.centerx - self.current_range, self.rect.centery - self.current_range))

        # Draw bullets
        if self.bullets and len(self.bullets) > 0:
            self.bullets.draw(surface)

        # Draw missiles
        if self.missiles and len(self.missiles) > 0:
            self.missiles.draw(surface)

        # Draw lightning zaps
        if self.lightning_zaps and len(self.lightning_zaps) > 0:
            for zap in self.lightning_zaps: # Iterate and call draw for each zap
                if hasattr(zap, 'draw') and callable(getattr(zap, 'draw')):
                     zap.draw(surface)

    def take_damage(self, amount):
        # Turrets are currently invulnerable in Maze Defense
        pass
