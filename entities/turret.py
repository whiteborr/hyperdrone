# entities/turret.py
import pygame
import math
from entities.bullet import Bullet

class Turret(pygame.sprite.Sprite):
    def __init__(self, x, y, asset_manager):
        super().__init__()
        self.asset_manager = asset_manager
        self.health = 100
        self.max_health = 100
        
        # Create simple turret sprite
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (100, 100, 100), (0, 0, 40, 40))
        pygame.draw.rect(self.image, (150, 150, 150), (15, 5, 10, 30))
        
        self.rect = self.image.get_rect(center=(x, y))
        self.bullets_group = pygame.sprite.Group()
        
        self.shoot_cooldown = 1000  # 1 second
        self.last_shot_time = 0
        self.range = 200
        
    def update(self, current_time, enemies_group):
        # Find closest enemy in range
        closest_enemy = None
        min_distance = float('inf')
        
        for enemy in enemies_group:
            dx = enemy.rect.centerx - self.rect.centerx
            dy = enemy.rect.centery - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < self.range and distance < min_distance:
                closest_enemy = enemy
                min_distance = distance
        
        # Shoot at closest enemy
        if closest_enemy and current_time - self.last_shot_time > self.shoot_cooldown:
            self._shoot_at_target(closest_enemy)
            self.last_shot_time = current_time
        
        # Update bullets
        self.bullets_group.update(None, 0)
    
    def _shoot_at_target(self, target):
        # Calculate angle to target
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        angle = math.atan2(dy, dx)
        
        # Create bullet
        bullet = Bullet(
            self.rect.centerx, self.rect.centery,
            angle, 6, 20, (255, 255, 0), self.asset_manager, 20
        )
        self.bullets_group.add(bullet)
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
    
    def draw(self, surface):
        surface.blit(self.image, self.rect)
        
        # Draw health bar
        if self.health < self.max_health:
            bar_width = 40
            bar_height = 4
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.top - 10
            
            # Background
            pygame.draw.rect(surface, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            # Health
            health_width = int((self.health / self.max_health) * bar_width)
            pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, health_width, bar_height))
        
        # Draw bullets
        for bullet in self.bullets_group:
            bullet.draw(surface)