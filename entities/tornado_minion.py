# entities/tornado_minion.py
from pygame.time import get_ticks
from random import uniform
from math import pi, cos, sin
from .enemy import Enemy
from settings_manager import get_setting

class TornadoMinion(Enemy):
    """
    A small, swirling minion spawned by the Tempest boss.
    It moves erratically and has a limited lifespan.
    """
    def __init__(self, game, x, y, config):
        super().__init__(game, x, y, config)
        self.lifespan = get_setting("bosses", "tempest", "TORNADO_LIFESPAN", 5000)  # in milliseconds
        self.spawn_time = get_ticks()
        self.speed = get_setting("bosses", "tempest", "TORNADO_SPEED", 4)
        
        # Set a random initial direction
        self.angle = uniform(0, 2 * pi)

    def update(self, maze, player, bullets, game_area_x_offset=0):
        current_time = get_ticks()

        # Check if lifespan has expired
        if current_time - self.spawn_time > self.lifespan:
            self.kill()
            return
            
        # Add a little randomness to the movement direction
        self.angle += uniform(-0.1, 0.1)

        # Move in the current direction
        self.x += cos(self.angle) * self.speed
        self.y += sin(self.angle) * self.speed
        self.rect.topleft = (self.x, self.y)

        # Keep the minion within the game area (optional, can also just let them fly off)
        self._keep_in_bounds()

    def _keep_in_bounds(self):
        screen_width = get_setting("display", "SCREEN_WIDTH", 1920)
        screen_height = get_setting("display", "SCREEN_HEIGHT", 1080)
        if self.rect.left < 0 or self.rect.right > screen_width:
            self.angle = pi - self.angle
        if self.rect.top < 0 or self.rect.bottom > screen_height:
            self.angle = -self.angle

