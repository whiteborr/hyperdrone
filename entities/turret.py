# entities/turret.py
import pygame
import math
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY, CYAN, GOLD,
    PLAYER_BULLET_SPEED, PLAYER_BULLET_LIFETIME, PLAYER_DEFAULT_BULLET_SIZE,
    PLAYER_BULLET_COLOR, WEAPON_MODES_SEQUENCE 
)
try:
    from .bullet import Bullet # Ensure this is importing your Bullet class
except ImportError:
    print("Warning (turret.py): Could not import Bullet from .bullet. Using placeholder.")
    # Minimal placeholder if Bullet class is not found (should not happen in full project)
    class Bullet(pygame.sprite.Sprite): 
        def __init__(self, x, y, angle, speed, lifetime, size, color, damage, 
                     bounces=0, pierces=0, can_pierce_walls=False):
            super().__init__()
            self.image = pygame.Surface([size*2, size*2]) 
            self.image.fill(color)
            self.rect = self.image.get_rect(center=(x,y))
            self.alive = True
            self.lifetime = lifetime
            self.damage = damage 
        def update(self, maze, offset): 
            self.lifetime -=1
            if self.lifetime <= 0:
                self.alive = False
                self.kill()
            _ = maze; _ = offset
        def draw(self, surface): 
            if self.alive: surface.blit(self.image, self.rect)


class Turret(pygame.sprite.Sprite):
    TURRET_COST = gs.get_game_setting("TURRET_BASE_COST", 50) 
    UPGRADE_COST = gs.get_game_setting("TURRET_UPGRADE_COST", 100) 
    BASE_RANGE = TILE_SIZE * 3
    BASE_FIRE_RATE = 1000  # Milliseconds
    BASE_DAMAGE = 10
    MAX_UPGRADE_LEVEL = gs.get_game_setting("TURRET_MAX_UPGRADE_LEVEL", 3) 

    def __init__(self, x, y, game_controller_ref):
        super().__init__()
        self.x = float(x) 
        self.y = float(y)
        self.game_controller_ref = game_controller_ref 
        self.size = int(TILE_SIZE * 0.8) 
        self.turret_base_color = (100, 100, 120) 
        self.turret_barrel_color = (150, 150, 170) 
        self.turret_upgrade_colors = [ 
            (100, 100, 120), (100, 150, 120), 
            (150, 150, 100), (180, 100, 100)  
        ]
        self.angle = 0  
        self.target = None 
        self.upgrade_level = 0 
        self.show_range_indicator = False 
        self._apply_upgrade_stats() 
        self.last_shot_time = pygame.time.get_ticks() - random.randint(0, int(self.fire_rate)) 
        self.bullets = pygame.sprite.Group() 
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA) 
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) 
        self._draw_turret() 
        print(f"DEBUG Turret: Initialized at ({self.x:.0f}, {self.y:.0f}), Fire Rate: {self.fire_rate:.0f}ms, Range: {self.range:.0f}, Damage: {self.damage:.1f}")

    def _apply_upgrade_stats(self):
        self.range = self.BASE_RANGE + (self.upgrade_level * TILE_SIZE * 0.5)
        self.fire_rate = float(self.BASE_FIRE_RATE * (0.85 ** self.upgrade_level))
        self.damage = self.BASE_DAMAGE * (1.25 ** self.upgrade_level)

    def _draw_turret(self):
        self.image.fill((0, 0, 0, 0))  
        base_rect_size = self.size
        base_rect = pygame.Rect(0, 0, base_rect_size, base_rect_size)
        base_rect.center = (self.size // 2, self.size // 2) 
        current_base_color = self.turret_upgrade_colors[min(self.upgrade_level, len(self.turret_upgrade_colors)-1)]
        pygame.draw.rect(self.image, current_base_color, base_rect, border_radius=int(base_rect_size*0.1))
        pygame.draw.rect(self.image, WHITE, base_rect, 1, border_radius=int(base_rect_size*0.1)) 
        barrel_length = self.size * 0.6 
        barrel_width = self.size * 0.15 
        center_of_image_x = self.size // 2
        center_of_image_y = self.size // 2
        barrel_end_x = center_of_image_x + barrel_length * math.cos(math.radians(self.angle))
        barrel_end_y = center_of_image_y + barrel_length * math.sin(math.radians(self.angle))
        pygame.draw.line(self.image, self.turret_barrel_color, 
                         (center_of_image_x, center_of_image_y), 
                         (barrel_end_x, barrel_end_y), 
                         int(barrel_width))
        pygame.draw.circle(self.image, self.turret_barrel_color, (center_of_image_x, center_of_image_y), int(barrel_width*1.2)) 

    def find_target(self, enemies_group):
        self.target = None 
        closest_enemy = None
        min_dist_sq = self.range ** 2 
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
            self.angle = math.degrees(math.atan2(dy, dx))
            self._draw_turret() 
            return True 
        return False 

    def shoot(self):
        current_time = pygame.time.get_ticks()
        can_shoot = self.target and self.target.alive and (current_time - self.last_shot_time > int(self.fire_rate))
        if can_shoot:
            self.last_shot_time = current_time
            barrel_tip_offset = self.size * 0.75 
            spawn_x = self.x + barrel_tip_offset * math.cos(math.radians(self.angle))
            spawn_y = self.y + barrel_tip_offset * math.sin(math.radians(self.angle))
            bullet_speed = PLAYER_BULLET_SPEED * 0.8
            bullet_lifetime = 300 
            bullet_size = 10      
            bullet_color = (255, 0, 255) # Magenta
            print(f"DEBUG Turret ({self.x:.0f},{self.y:.0f}): FIRING BULLET. Target: {self.target.rect.center if self.target else 'None'}. Angle: {self.angle:.1f}. Spawn: ({spawn_x:.0f},{spawn_y:.0f}), Size: {bullet_size}, Lifetime: {bullet_lifetime}")
            new_bullet = Bullet(spawn_x, spawn_y, self.angle, bullet_speed, bullet_lifetime, int(bullet_size), bullet_color, int(self.damage))
            self.bullets.add(new_bullet) 
            if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3) 

    def upgrade(self):
        if self.upgrade_level < self.MAX_UPGRADE_LEVEL:
            self.upgrade_level += 1; self._apply_upgrade_stats(); self._draw_turret(); return True 
        return False

    def update(self, enemies_group, maze_ref, game_area_x_offset=0):
        self.find_target(enemies_group)
        if self.aim_at_target(): self.shoot()
        self.bullets.update(maze_ref, game_area_x_offset) 

    def draw(self, surface):
        # print(f"DEBUG Turret ({self.x:.0f},{self.y:.0f}): Turret.draw() CALLED.") # Basic call confirmation
        surface.blit(self.image, self.rect) 
        
        if self.bullets is not None:
            num_bullets_in_group = len(self.bullets)
            if num_bullets_in_group > 0:
                # Print periodically to avoid flooding, but ensure it prints if bullets are present
                if not hasattr(self, '_last_turret_draw_log_time') or pygame.time.get_ticks() - self._last_turret_draw_log_time > 500: # Log every 500ms if bullets exist
                    print(f"DEBUG Turret ({self.x:.0f},{self.y:.0f}): Turret.draw() - Bullet group has {num_bullets_in_group} sprites. Manually iterating to call Bullet.draw().")
                    self._last_turret_draw_log_time = pygame.time.get_ticks()
            
            # Manual iteration to call draw on each bullet
            for i, bullet_sprite in enumerate(self.bullets.sprites()): 
                # print(f"DEBUG Turret ({self.x:.0f},{self.y:.0f}): Manually calling draw for bullet #{i+1} (Obj: {bullet_sprite}) in group.")
                if hasattr(bullet_sprite, 'draw') and callable(getattr(bullet_sprite, 'draw')):
                    bullet_sprite.draw(surface) # Explicitly call draw on each bullet
                else:
                    print(f"CRITICAL DEBUG Turret: Bullet sprite {bullet_sprite} (index {i}) missing draw method or not callable.")
            # self.bullets.draw(surface) # Original group draw call is replaced by manual iteration for this debug step
        else:
            print(f"CRITICAL DEBUG Turret ({self.x:.0f},{self.y:.0f}): Turret.draw() - self.bullets group IS NONE.")
