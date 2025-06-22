# entities/energy_particle.py
import pygame
import math

class EnergyParticle(pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, target_x, target_y, asset_manager=None):
        super().__init__()
        self.x = float(start_x)
        self.y = float(start_y)
        self.start_pos = (start_x, start_y)
        self.target_pos = (target_x, target_y)
        self.speed = 6.0
        self.radius = 8
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        self._update_image()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.asset_manager = asset_manager
        self.arrived = False

        dx = target_x - start_x
        dy = target_y - start_y
        distance = math.hypot(dx, dy)
        self.velocity = (dx / distance * self.speed, dy / distance * self.speed)

    def _update_image(self):
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, (255, 215, 0), (8, 8), self.radius)
        pygame.draw.circle(self.image, (255, 255, 180, 120), (8, 8), self.radius + 4, 2)

    def update(self):
        if self.arrived:
            self.kill()
            return

        self.x += self.velocity[0]
        self.y += self.velocity[1]
        self.rect.center = (int(self.x), int(self.y))

        # Check for arrival (simple radius check)
        if math.hypot(self.target_pos[0] - self.x, self.target_pos[1] - self.y) < 10:
            self.arrived = True

    def has_arrived(self):
        return self.arrived
