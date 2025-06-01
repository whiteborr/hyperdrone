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
    from .bullet import Bullet
except ImportError:
    print("Warning (turret.py): Could not import Bullet from .bullet. Using placeholder.")
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
        def update(self, maze, offset): self.lifetime -=1;_ = maze; _ = offset;  
        def draw(self, surface): surface.blit(self.image, self.rect)


class Turret(pygame.sprite.Sprite):
    TURRET_COST = 50
    UPGRADE_COST = 100
    BASE_RANGE = TILE_SIZE * 3
    BASE_FIRE_RATE = 1000  
    BASE_DAMAGE = 10
    MAX_UPGRADE_LEVEL = 3 

    def __init__(self, x, y, game_controller_ref):
        """
        Initializes a Turret.
        Args:
            x (int): Center x-coordinate.
            y (int): Center y-coordinate.
            game_controller_ref: Reference to the main game controller for accessing sounds, etc.
        """
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.game_controller_ref = game_controller_ref 

        self.size = int(TILE_SIZE * 0.8)
        self.turret_base_color = (100, 100, 120) 
        self.turret_barrel_color = (150, 150, 170) 
        self.turret_upgrade_colors = [
            (100, 100, 120), 
            (100, 150, 120), 
            (150, 150, 100), 
            (180, 100, 100)  
        ]


        self.angle = 0  
        self.target = None 
        self.upgrade_level = 0 

        # Initialize show_range_indicator BEFORE first call to _draw_turret
        self.show_range_indicator = False 

        self._apply_upgrade_stats() 

        self.last_shot_time = pygame.time.get_ticks() - random.randint(0, int(self.fire_rate)) 
        
        self.bullets = pygame.sprite.Group() 

        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y))) # Ensure center is int
        self._draw_turret() # Initial draw after all necessary attributes are set

    def _apply_upgrade_stats(self):
        """Applies stats based on the current upgrade_level."""
        self.range = self.BASE_RANGE + (self.upgrade_level * TILE_SIZE * 0.5)
        self.fire_rate = float(self.BASE_FIRE_RATE * (0.85 ** self.upgrade_level))
        self.damage = self.BASE_DAMAGE * (1.25 ** self.upgrade_level)
        
        print(f"Turret ({self.x},{self.y}) stats Lvl {self.upgrade_level}. Range: {self.range:.0f}, FireRate: {self.fire_rate:.0f}ms, Dmg: {self.damage:.1f}")


    def _draw_turret(self):
        """Draws the turret on its self.image surface."""
        self.image.fill((0, 0, 0, 0))  

        base_rect = pygame.Rect(0, 0, self.size, self.size)
        base_rect.center = (self.size // 2, self.size // 2)
        current_base_color = self.turret_upgrade_colors[min(self.upgrade_level, len(self.turret_upgrade_colors)-1)]
        pygame.draw.rect(self.image, current_base_color, base_rect, border_radius=int(self.size*0.1))
        pygame.draw.rect(self.image, WHITE, base_rect, 1, border_radius=int(self.size*0.1))


        barrel_length = self.size * 0.6
        barrel_width = self.size * 0.15
        
        end_x = self.size // 2 + barrel_length * math.cos(math.radians(self.angle))
        end_y = self.size // 2 + barrel_length * math.sin(math.radians(self.angle))
        start_x = self.size // 2
        start_y = self.size // 2

        pygame.draw.line(self.image, self.turret_barrel_color, (start_x, start_y), (end_x, end_y), int(barrel_width))
        pygame.draw.circle(self.image, self.turret_barrel_color, (start_x, start_y), int(barrel_width*1.2)) 

        # The range indicator itself will be drawn on the main screen by UIManager/BuildMenu
        # if self.show_range_indicator is True, not on the turret's own image,
        # so it doesn't rotate with the turret.
        # The _draw_turret method only needs to draw the turret itself.


    def find_target(self, enemies_group):
        """Finds the closest enemy within range."""
        self.target = None 
        closest_enemy = None
        min_dist_sq = self.range ** 2 

        for enemy in enemies_group:
            if not enemy.alive: 
                continue
            
            dist_sq = (enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - self.y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        
        self.target = closest_enemy

    def aim_at_target(self):
        """Aims the turret barrel at the current target."""
        if self.target and self.target.alive:
            dx = self.target.rect.centerx - self.x
            dy = self.target.rect.centery - self.y
            self.angle = math.degrees(math.atan2(dy, dx))
            self._draw_turret() 
            return True
        # If no target, or target is dead, turret might slowly sweep or point forward
        # For now, it just keeps its last angle if no valid target.
        # self.angle = 0 # Or some default aiming angle
        # self._draw_turret() # Redraw if angle changes to default
        return False 

    def shoot(self):
        """Fires a bullet at the current target if conditions are met."""
        current_time = pygame.time.get_ticks()
        if self.target and self.target.alive and (current_time - self.last_shot_time > int(self.fire_rate)):
            self.last_shot_time = current_time

            barrel_tip_offset = self.size * 0.3 
            spawn_x = self.x + barrel_tip_offset * math.cos(math.radians(self.angle))
            spawn_y = self.y + barrel_tip_offset * math.sin(math.radians(self.angle))

            bullet_speed = PLAYER_BULLET_SPEED * 0.8
            bullet_lifetime = PLAYER_BULLET_LIFETIME * 0.7
            bullet_size = PLAYER_DEFAULT_BULLET_SIZE * 0.8
            bullet_color = GOLD 
            
            new_bullet = Bullet(
                spawn_x, spawn_y, self.angle,
                bullet_speed, bullet_lifetime, int(bullet_size), bullet_color,
                int(self.damage) 
            )
            self.bullets.add(new_bullet)
            if self.game_controller_ref and hasattr(self.game_controller_ref, 'play_sound'):
                self.game_controller_ref.play_sound('turret_shoot_placeholder', 0.3) 

    def upgrade(self):
        """Upgrades the turret if possible."""
        if self.upgrade_level < self.MAX_UPGRADE_LEVEL:
            self.upgrade_level += 1
            self._apply_upgrade_stats()
            self._draw_turret() 
            return True 
        print(f"Turret at ({self.x},{self.y}) is already max level {self.MAX_UPGRADE_LEVEL}.")
        return False


    def update(self, enemies_group, maze_ref, game_area_x_offset=0):
        """
        Updates the turret's logic: find target, aim, shoot, update bullets.
        """
        self.find_target(enemies_group)
        if self.aim_at_target(): 
            self.shoot()
        
        self.bullets.update(maze_ref, game_area_x_offset) 


    def draw(self, surface):
        """Draws the turret and its bullets."""
        surface.blit(self.image, self.rect)
        self.bullets.draw(surface)

        # The actual drawing of the range indicator when a turret is selected
        # should be handled by the UIManager or BuildMenu, drawing directly onto the main screen
        # so it's not part of the turret's rotated image.
        # if self.show_range_indicator and self.game_controller.is_build_phase:
        #    pygame.draw.circle(surface, (*CYAN[:3], 70), self.rect.center, int(self.range), 2)
