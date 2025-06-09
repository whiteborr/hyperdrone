# entities/core_reactor.py
import pygame
import math
import random

import game_settings as gs
from game_settings import (
    TILE_SIZE, WHITE, RED, GREEN, YELLOW, DARK_GREY
)

class CoreReactor(pygame.sprite.Sprite):
    def __init__(self, x, y, asset_manager, health=500, size_in_tiles=2):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.max_health, self.current_health = int(health), int(health)
        self.alive = True
        self.size = int(TILE_SIZE * size_in_tiles)
        self.original_image = asset_manager.get_image("core_reactor_image")
        if self.original_image:
            self.image = pygame.transform.smoothscale(self.original_image, (self.size, self.size))
        else:
            # Fallback if image fails to load
            self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
            self.image.fill((0,0,0,0))
            pygame.draw.rect(self.image, (50, 50, 200), self.image.get_rect(), border_radius=int(self.size*0.1))
            pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 3, border_radius=int(self.size*0.1))

        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        self.health_bar_height = 10
        self.health_bar_width_ratio = 1.0
        self.health_bar_y_offset = 10

    def _draw_reactor_visual(self):
        self.image.fill((0, 0, 0, 0))
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
        if not self.alive: return
        self.current_health -= amount
        if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
            game_controller_ref.play_sound('reactor_hit_placeholder')
        if self.current_health <= 0:
            self.current_health = 0
            self.alive = False
            if game_controller_ref and hasattr(game_controller_ref, 'play_sound'):
                game_controller_ref.play_sound('reactor_destroyed_placeholder')

    def draw_health_bar(self, surface, camera):
        if not self.alive and self.current_health == 0:
            return

        # Use a fixed screen-space size for the health bar so it doesn't shrink
        bar_width = self.size * 0.8
        bar_height = 8
        
        # Get the screen position of the reactor's rect
        screen_rect = camera.apply_to_rect(self.rect)
        
        bar_x = screen_rect.centerx - bar_width / 2
        bar_y = screen_rect.bottom + self.health_bar_y_offset / camera.zoom_level # Adjust offset based on zoom

        health_percentage = self.current_health / self.max_health if self.max_health > 0 else 0
        filled_width = bar_width * health_percentage
        
        pygame.draw.rect(surface, DARK_GREY, (bar_x, bar_y, bar_width, bar_height))
        fill_color = RED if health_percentage < 0.3 else YELLOW if health_percentage < 0.6 else GREEN
        if filled_width > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(filled_width), bar_height))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def update(self):
        pass

    def draw(self, surface, camera=None):
        if not self.image or not self.rect: return
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            if self.image.get_size() != screen_rect.size and screen_rect.width > 0 and screen_rect.height > 0:
                scaled_image = pygame.transform.smoothscale(self.image, screen_rect.size)
                surface.blit(scaled_image, screen_rect)
            else:
                surface.blit(self.image, screen_rect)
        else:
            surface.blit(self.image, self.rect)
        
        if (self.alive or self.current_health > 0) and self.rect:
             self.draw_health_bar(surface, camera)

        if self.alive or self.current_health > 0:
            if self.rect:
                 self.draw_health_bar(surface, camera)