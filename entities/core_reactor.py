# entities/core_reactor.py
import pygame
import math
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY
)

class CoreReactor(pygame.sprite.Sprite):
    def __init__(self, x, y, health=500, size_in_tiles=2):
        super().__init__()

        self.x = float(x)
        self.y = float(y)
        self.max_health = int(health)
        self.current_health = int(health)
        self.alive = True

        self.size = int(TILE_SIZE * size_in_tiles)
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)

        self.base_color = (50, 50, 200)  # A deep, stable blue for the core
        self.pulse_color_bright = (100, 150, 255) # Brighter, slightly different hue for pulsing
        self.pulse_speed = 0.03
        self.pulse_timer = random.uniform(0, math.pi * 2)

        self._draw_reactor_visual()  # Initial draw

        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        self.health_bar_height = 10
        self.health_bar_width_ratio = 1.0
        self.health_bar_y_offset = 10

    def _draw_reactor_visual(self):
        """
        Draws the reactor's visual appearance onto its self.image surface.
        Restored to original pulsating visual.
        """
        self.image.fill((0, 0, 0, 0))  # Clear the surface with full transparency

        self.pulse_timer += self.pulse_speed
        if self.pulse_timer > math.pi * 2:
            self.pulse_timer -= math.pi * 2

        pulse_factor = (math.sin(self.pulse_timer) + 1) / 2

        r = int(self.base_color[0] + (self.pulse_color_bright[0] - self.base_color[0]) * pulse_factor)
        g = int(self.base_color[1] + (self.pulse_color_bright[1] - self.base_color[1]) * pulse_factor)
        b = int(self.base_color[2] + (self.pulse_color_bright[2] - self.base_color[2]) * pulse_factor)
        current_core_color = (r, g, b)

        center_x, center_y = self.size // 2, self.size // 2
        num_layers = 3

        for i in range(num_layers):
            layer_size_ratio = 1 - i * 0.25
            layer_size = self.size * layer_size_ratio
            layer_rect = pygame.Rect(0, 0, int(layer_size), int(layer_size))
            layer_rect.center = (center_x, center_y)

            layer_alpha = int(200 * (1 - i * 0.3))
            layer_color_tuple = current_core_color
            if i % 2 == 1:
                 layer_color_tuple = (min(255,r+30), min(255,g+30), min(255,b+30))

            pygame.draw.rect(self.image, (*layer_color_tuple, layer_alpha), layer_rect, border_radius=int(self.size * 0.05))

        pygame.draw.rect(self.image, WHITE, (0, 0, self.size, self.size), 2, border_radius=int(self.size*0.05))


    def take_damage(self, amount, game_controller_ref=None):
        if not self.alive:
            return
        self.current_health -= amount
        if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
            game_controller_ref.play_sound('reactor_hit_placeholder')

        if self.current_health <= 0:
            self.current_health = 0
            self.alive = False
            if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
                game_controller_ref.play_sound('reactor_destroyed_placeholder')

    def draw_health_bar(self, surface):
        if not self.alive and self.current_health == 0:
            return

        bar_width = self.size * self.health_bar_width_ratio
        bar_x = self.rect.centerx - bar_width / 2
        bar_y = self.rect.bottom + self.health_bar_y_offset
        health_percentage = 0.0
        if self.max_health > 0:
            health_percentage = max(0, self.current_health / self.max_health)
        filled_width = bar_width * health_percentage
        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, self.health_bar_height))
        fill_color = RED
        if health_percentage > 0.6: fill_color = GREEN
        elif health_percentage > 0.3: fill_color = YELLOW
        if filled_width > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(filled_width), self.health_bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, self.health_bar_height), 1)

    def update(self):
        if self.alive:
            self._draw_reactor_visual()

    def draw(self, surface):
        if self.image and self.rect:
             surface.blit(self.image, self.rect)
        if self.alive or self.current_health > 0:
            if self.rect:
                 self.draw_health_bar(surface)