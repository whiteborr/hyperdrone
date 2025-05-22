import pygame
import random
import math

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color_list, min_speed, max_speed, min_size, max_size, gravity=0.1, shrink_rate=0.1, lifetime_frames=30):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        
        self.color = random.choice(color_list)
        self.size = random.uniform(min_size, max_size)
        self.initial_size = self.size # Store initial size for shrinking calculation

        # Create a circular surface for the particle
        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(self.x, self.y))

        angle = random.uniform(0, 2 * math.pi)  # Radians
        speed = random.uniform(min_speed, max_speed)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.gravity = gravity
        self.shrink_rate = shrink_rate
        self.lifetime = lifetime_frames
        self.current_lifetime = 0

    def update(self):
        self.current_lifetime += 1
        if self.current_lifetime >= self.lifetime:
            self.kill() # Remove sprite when lifetime is over
            return

        # Apply movement
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))

        # Apply shrinking
        current_size_factor = max(0, 1 - (self.current_lifetime / self.lifetime))
        new_size = self.initial_size * current_size_factor
        
        if new_size < 1:
            self.kill()
            return
        
        # Re-render the particle if size changed significantly (or just always for simplicity here)
        # For performance, you might only re-render if size changes by a certain threshold
        self.size = new_size
        self.image = pygame.Surface([self.size * 2, self.size * 2], pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.color, (self.size, self.size), self.size)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        # Optional: Fade out
        # alpha = max(0, 255 * (1 - (self.current_lifetime / self.lifetime)))
        # self.image.set_alpha(int(alpha))

    def draw(self, surface): # Though typically particles are drawn by group.draw()
        if self.alive(): # Check if the sprite is still alive
            surface.blit(self.image, self.rect)