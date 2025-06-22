# entities/energy_particle.py
import pygame
import math

class EnergyParticle(pygame.sprite.Sprite):
    """
    An animated particle that can use a custom image and travels from a start
    point to a target, shrinking over its journey.
    """
    def __init__(self, start_x, start_y, target_x, target_y, image_surface=None, start_size=32, end_size=8):
        super().__init__()
        self.x = float(start_x)
        self.y = float(start_y)
        self.start_pos = (start_x, start_y)
        self.target_pos = (target_x, target_y)
        self.speed = 15.0  # Increased speed for a snappier feel
        self.arrived = False

        # Size interpolation properties
        self.start_size = start_size
        self.end_size = end_size
        self.current_size = start_size
        
        # Image properties
        self.image_provided = image_surface is not None
        if self.image_provided:
            self.original_image = image_surface
        else:
            # Fallback to drawing a circle if no image is given
            self.original_image = None

        # Initial render and rect setup
        self.image = pygame.Surface((self.start_size, self.start_size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._update_image()

        # Velocity calculation
        dx = target_x - start_x
        dy = target_y - start_y
        self.total_distance = math.hypot(dx, dy)
        if self.total_distance == 0: self.total_distance = 1 # Avoid division by zero
        self.velocity = (dx / self.total_distance * self.speed, dy / self.total_distance * self.speed)

    def _update_image(self):
        """Renders the particle at its current size."""
        size = int(self.current_size)
        if size <= 1: size = 1
        
        current_center = self.rect.center
        
        if self.image_provided:
            # Scale the provided image to the current size
            self.image = pygame.transform.smoothscale(self.original_image, (size, size))
        else:
            # Fallback drawing logic if no image was provided
            self.image = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            self.image.fill((0, 0, 0, 0))
            pygame.draw.circle(self.image, (255, 215, 0), (size, size), size // 2)
            pygame.draw.circle(self.image, (255, 255, 180, 120), (size, size), size, 2)
        
        self.rect = self.image.get_rect(center=current_center)

    def update(self):
        """Moves the particle and updates its size."""
        if self.arrived:
            self.kill()
            return

        # Move particle
        self.x += self.velocity[0]
        self.y += self.velocity[1]
        
        # Calculate progress to target
        distance_traveled = math.hypot(self.x - self.start_pos[0], self.y - self.start_pos[1])
        progress = min(1.0, distance_traveled / self.total_distance)
        
        # Interpolate size from start_size to end_size based on progress (shrinking effect)
        self.current_size = self.start_size + (self.end_size - self.start_size) * progress
        
        self.rect.center = (int(self.x), int(self.y))
        self._update_image()

        # Check for arrival
        if math.hypot(self.target_pos[0] - self.x, self.target_pos[1] - self.y) < self.speed:
            self.arrived = True
            
    def has_arrived(self):
        return self.arrived