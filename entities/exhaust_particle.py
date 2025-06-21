import pygame.sprite
import pygame.draw
from pygame import Surface, SRCALPHA
from random import choice, uniform, randint
from math import radians, cos, sin
from constants import FLAME_COLORS

class ExhaustParticle(pygame.sprite.Sprite):
    """A specialized particle class for exhaust flames"""
    
    def __init__(self, x, y, angle_deg):
        super().__init__()
        
        # Position and movement
        self.x = float(x)
        self.y = float(y)
        self.angle_rad = radians(angle_deg + uniform(-15, 15))
        self.speed = uniform(1.5, 3.0)
        self.vx = -cos(self.angle_rad) * self.speed  # Negative because it's exhaust (opposite direction)
        self.vy = -sin(self.angle_rad) * self.speed
        
        # Appearance
        self.color = choice(FLAME_COLORS)
        self.size = uniform(5, 10)
        self.initial_size = self.size
        
        # Lifetime
        self.max_lifetime = randint(15, 25)
        self.lifetime = 0
        
        # Create surface
        self.image = Surface((int(self.size * 2), int(self.size * 2)), SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._redraw()
    
    def _redraw(self):
        """Redraw the particle with current properties"""
        self.image.fill((0, 0, 0, 0))  # Clear with transparency
        
        # Calculate alpha based on remaining lifetime
        life_ratio = 1.0 - (self.lifetime / self.max_lifetime)
        alpha = int(255 * life_ratio)
        
        # Draw the flame particle
        center = (self.image.get_width() // 2, self.image.get_height() // 2)
        pygame.draw.circle(
            self.image, 
            (*self.color[:3], alpha),  # RGB from color, alpha based on lifetime
            center, 
            int(self.size)
        )
    
    def update(self):
        """Update particle position and appearance"""
        self.lifetime += 1
        if self.lifetime >= self.max_lifetime:
            self.kill()
            return
        
        # Move the particle
        self.x += self.vx
        self.y += self.vy
        
        # Shrink the particle
        self.size = self.initial_size * (1.0 - (self.lifetime / self.max_lifetime))
        
        # Redraw and update rect
        self._redraw()
        self.rect.center = (int(self.x), int(self.y))
    
    def draw(self, surface, camera=None):
        """Draw the particle to the surface"""
        if not self.alive():
            return
            
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            if screen_rect.width > 0 and screen_rect.height > 0:
                surface.blit(self.image, screen_rect.topleft)
        else:
            surface.blit(self.image, self.rect.topleft)