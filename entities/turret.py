# entities/turret.py
import pygame
import math
import random
import os
import logging 

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY, CYAN, GOLD,
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
    class Bullet(pygame.sprite.Sprite): # Minimal placeholder
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, max_bounces=0, max_pierces=0, can_pierce_walls=False): 
            super().__init__(); self.image = pygame.Surface([max(1,size*2), max(1,size*2)]); self.image.fill(color)
            self.rect = self.image.get_rect(center=(x,y)); self.alive = True; self.lifetime = lifetime; self.damage = damage
        def update(self, maze, offset): self.lifetime -=1; _ = maze; _ = offset; 
        def draw(self, surface):
            if self.alive: surface.blit(self.image, self.rect)
    class Missile(Bullet): pass
    class LightningZap(Bullet): pass 

logger = logging.getLogger(__name__)
if not logger.hasHandlers(): 
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


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
        self.rect = None

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
        self.turret_barrel_color_fallback = (150, 150, 170)
        logger.debug(f"Turret initialized at ({x},{y}), Level {self.upgrade_level}, Weapon Mode: {self.current_weapon_mode}")


    def _load_sprite_for_weapon_mode(self):
        image_path = TURRET_IMAGE_PATHS.get(self.current_weapon_mode, TURRET_IMAGE_PATHS[WEAPON_MODE_DEFAULT])
        loaded_successfully = False
        if os.path.exists(image_path):
            try:
                loaded_image = pygame.image.load(image_path).convert_alpha()
                self.original_image = pygame.transform.smoothscale(loaded_image, self.SPRITE_SIZE)
                loaded_successfully = True
            except pygame.error as e:
                logger.error(f"Turret: Error loading sprite '{image_path}': {e}")
                self.original_image = None
        else:
            logger.warning(f"Turret: Sprite path not found '{image_path}'.")
            self.original_image = None

        if not loaded_successfully: 
            self.original_image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA)
            logger.debug("Turret: Using fallback sprite.")
            pygame.draw.rect(self.original_image, self.turret_base_color_fallback, self.original_image.get_rect(), border_radius=3)

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

        logger.debug(f"Turret attributes updated for ({self.x:.0f},{self.y:.0f}). Mode: {self.current_weapon_mode}, Dmg: {self.current_damage}, Cooldown: {self.current_shoot_cooldown:.2f}, Range: {self.current_range:.2f}, BulletSize: {self.current_bullet_size}")
        self._load_sprite_for_weapon_mode() 

    def _draw_turret(self):
        if self.original_image:
            self.image = pygame.transform.rotate(self.original_image, -self.angle) 
            if self.rect: 
                self.rect = self.image.get_rect(center=self.rect.center)
            else: 
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        else: 
            self.image = pygame.Surface(self.SPRITE_SIZE, pygame.SRCALPHA)
            self.image.fill((255,0,0,100)) 
            if self.rect:
                 self.rect = self.image.get_rect(center=self.rect.center)
            else:
                self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        
        if not self.rect: 
             self.rect = pygame.Rect(self.x - self.SPRITE_SIZE[0]//2, self.y - self.SPRITE_SIZE[1]//2, self.SPRITE_SIZE[0], self.SPRITE_SIZE[1])


    def find_target(self, enemies_group):
        self.target = None
        closest_enemy = None
        min_dist_sq = self.current_range ** 2 
        
        if not enemies_group: 
            return

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
            
            current_angle_norm = self.angle % 360
            new_angle_norm = (new_angle_deg + 360) % 360 

            if abs(current_angle_norm - new_angle_norm) > 1: 
                self.angle = new_angle_deg
                self._draw_turret() 
            return True
        return False

    def shoot(self, enemies_group, maze_ref):
        current_time = pygame.time.get_ticks()
        if not self.target or not self.target.alive or not self.rect:
            return

        rad_angle_shoot = math.radians(self.angle)
        
        spawn_offset_from_center = (self.SPRITE_SIZE[0] / 2) + (self.current_bullet_size / 2) + 2 
        
        base_spawn_x = self.x + spawn_offset_from_center * math.cos(rad_angle_shoot)
        base_spawn_y = self.y + spawn_offset_from_center * math.sin(rad_angle_shoot)

        logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) ATTEMPTING shoot. Target: {self.target.rect.center if self.target else 'None'}. Angle: {self.angle:.1f}. Base Spawn_XY: ({base_spawn_x:.1f},{base_spawn_y:.1f})")

        if self.current_weapon_mode not in [WEAPON_MODE_HEATSEEKER, WEAPON_MODE_LIGHTNING, WEAPON_MODE_HEATSEEKER_PLUS_BULLETS]:
            if (current_time - self.last_shot_time) > self.current_shoot_cooldown:
                self.last_shot_time = current_time
                angles_to_fire = [0] 
                if self.current_weapon_mode in [WEAPON_MODE_TRI_SHOT, WEAPON_MODE_RAPID_TRI]:
                    angles_to_fire = [-15, 0, 15] 

                for angle_offset in angles_to_fire:
                    eff_angle = self.angle + angle_offset
                    spawn_x_bullet = base_spawn_x 
                    spawn_y_bullet = base_spawn_y 

                    bounces = 0 
                    pierces = 0
                    can_pierce_w = False
                    if self.current_weapon_mode == WEAPON_MODE_BOUNCE:
                        bounces = BOUNCING_BULLET_MAX_BOUNCES
                    elif self.current_weapon_mode == WEAPON_MODE_PIERCE:
                        pierces = PIERCING_BULLET_MAX_PIERCES
                        can_pierce_w = True 
                    else: # Default for WEAPON_MODE_DEFAULT, RAPID_SINGLE, RAPID_TRI, BIG_SHOT
                        bounces = 2 # MODIFIED: Give default/other standard bullets 2 bounces

                    new_bullet = Bullet(spawn_x_bullet, spawn_y_bullet, eff_angle, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
                                        self.current_bullet_size, PLAYER_BULLET_COLOR, int(self.current_damage),
                                        max_bounces=bounces, max_pierces=pierces, can_pierce_walls=can_pierce_w)
                    self.bullets.add(new_bullet)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED standard/variant. Mode: {self.current_weapon_mode}. Bullets: {len(self.bullets)}")
                if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                    self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3)


        if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER or self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
            if (current_time - self.last_missile_shot_time) > self.current_missile_cooldown:
                self.last_missile_shot_time = current_time
                
                missile_spawn_offset_adj = (self.SPRITE_SIZE[0] / 2) + (MISSILE_SIZE / 2) + 2 
                missile_spawn_x = self.x + missile_spawn_offset_adj * math.cos(rad_angle_shoot)
                missile_spawn_y = self.y + missile_spawn_offset_adj * math.sin(rad_angle_shoot)
                
                new_missile = Missile(missile_spawn_x, missile_spawn_y, self.angle, int(self.current_damage), enemies_group) 
                self.missiles.add(new_missile)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED MISSILE. Missiles: {len(self.missiles)}")
                if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                    self.game_controller_ref.play_sound('missile_launch', 0.4)

            if self.current_weapon_mode == WEAPON_MODE_HEATSEEKER_PLUS_BULLETS:
                 if (current_time - self.last_shot_time) > self.current_shoot_cooldown_std_bullet: 
                    self.last_shot_time = current_time 
                    
                    std_spawn_x = base_spawn_x 
                    std_spawn_y = base_spawn_y
                    
                    new_bullet = Bullet(std_spawn_x, std_spawn_y, self.angle, PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME,
                                        PLAYER_DEFAULT_BULLET_SIZE, PLAYER_BULLET_COLOR, int(self.current_damage_std_bullet),
                                        max_bounces=2) # MODIFIED: Give these bullets 2 bounces as well
                    self.bullets.add(new_bullet)
                    logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) Fired rapid bullet (Seeker+). Bullets: {len(self.bullets)}")
                    if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                         self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.2)

        elif self.current_weapon_mode == WEAPON_MODE_LIGHTNING:
            if (current_time - self.last_lightning_time) > self.current_lightning_cooldown:
                self.last_lightning_time = current_time
                game_area_x_offset = 0 
                if self.game_controller_ref and self.game_controller_ref.maze:
                    game_area_x_offset = self.game_controller_ref.maze.game_area_x_offset

                new_zap = LightningZap(player_ref=self, initial_target_enemy_ref=self.target, 
                                       damage=int(self.current_damage), lifetime_frames=LIGHTNING_LIFETIME,
                                       maze_ref=maze_ref,
                                       game_area_x_offset=game_area_x_offset)
                self.lightning_zaps.add(new_zap)
                logger.debug(f"Turret ({self.x:.0f},{self.y:.0f}) FIRED LIGHTNING. Zaps: {len(self.lightning_zaps)}")
                if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                    self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3) 


    def upgrade(self):
        if self.weapon_mode_index < self.MAX_UPGRADE_LEVEL:
            self.weapon_mode_index += 1
            self.upgrade_level = self.weapon_mode_index 
            self._update_weapon_attributes()
            logger.info(f"Turret at ({self.x:.0f},{self.y:.0f}) upgraded to level {self.upgrade_level}. New mode: {self.current_weapon_mode}")
            return True
        logger.info(f"Turret at ({self.x:.0f},{self.y:.0f}) is already at max upgrade level {self.MAX_UPGRADE_LEVEL}.")
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
             if self.rect: 
                 pygame.draw.rect(surface, RED, self.rect, 2)
             logger.warning(f"Turret at ({self.x},{self.y}) missing image or rect for drawing.")

        if self.show_range_indicator and self.rect:
            range_color = (0,100,255, 70) 
            temp_range_surface = pygame.Surface((int(self.current_range * 2), int(self.current_range * 2)), pygame.SRCALPHA)
            pygame.draw.circle(temp_range_surface, range_color, (int(self.current_range), int(self.current_range)), int(self.current_range))
            surface.blit(temp_range_surface, (self.rect.centerx - self.current_range, self.rect.centery - self.current_range))

        if self.bullets: self.bullets.draw(surface)
        if self.missiles: self.missiles.draw(surface)
        if self.lightning_zaps:
            for zap in self.lightning_zaps: zap.draw(surface) 
            
    def take_damage(self, amount):
        pass 