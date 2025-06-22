# entities/temporary_barricade.py
import pygame.sprite
import pygame.time
import pygame.draw
import pygame.transform
from pygame import Surface, SRCALPHA, Rect
from random import randint
import logging

from settings_manager import get_setting
from constants import GREEN, WHITE, RED, YELLOW

logger = logging.getLogger(__name__)

class TemporaryBarricade(pygame.sprite.Sprite):
    def __init__(self, x, y, size, health, lifetime_ms, asset_manager):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.size = size
        self.max_health = health
        self.health = health
        self.lifetime_ms = lifetime_ms
        self.spawn_time = pygame.time.get_ticks()
        self.alive = True
        self.asset_manager = asset_manager

        self.original_image = self._create_barricade_image()
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self.collision_rect = self.rect.inflate(-size * 0.1, -size * 0.1) # Slightly smaller collision box

    def _create_barricade_image(self):
        """Creates a visual representation for the barricade."""
        barricade_surface = Surface((self.size, self.size), SRCALPHA)
        barricade_surface.fill((0, 0, 0, 0)) # Transparent background

        # Outer shape (e.g., a thick square or cross)
        outer_color = (60, 150, 60, 200) # Dark green
        pygame.draw.rect(barricade_surface, outer_color, (0, 0, self.size, self.size), border_radius=5)
        
        # Inner glow/detail
        inner_padding = self.size * 0.15
        inner_rect = Rect(inner_padding, inner_padding, self.size - 2*inner_padding, self.size - 2*inner_padding)
        inner_color = (100, 200, 100, 255) # Lighter green
        pygame.draw.rect(barricade_surface, inner_color, inner_rect, border_radius=3)

        # Cross beams
        line_color = WHITE
        line_thickness = max(1, int(self.size * 0.05))
        pygame.draw.line(barricade_surface, line_color, (self.size * 0.2, self.size * 0.2), (self.size * 0.8, self.size * 0.8), line_thickness)
        pygame.draw.line(barricade_surface, line_color, (self.size * 0.8, self.size * 0.2), (self.size * 0.2, self.size * 0.8), line_thickness)

        return barricade_surface

    def take_damage(self, amount):
        if not self.alive: return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            # Play destruction sound and create particles
            if hasattr(self.asset_manager, 'game_controller'):
                self.asset_manager.game_controller.play_sound('barricade_destroy_sound') # Need to add this sound later
                self.asset_manager.game_controller._create_explosion(self.x, self.y, num_particles=10, specific_sound_key=None, is_enemy=False)
            logger.info(f"Barricade at ({self.x:.1f}, {self.y:.1f}) destroyed.")

    def update(self):
        if not self.alive:
            self.kill()
            return

        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time > self.lifetime_ms:
            self.alive = False
            self.kill()
            logger.debug(f"Barricade at ({self.x:.1f}, {self.y:.1f}) expired.")
            return

        # Simple pulsing/fading effect towards end of life
        time_left_ratio = (self.lifetime_ms - (current_time - self.spawn_time)) / self.lifetime_ms
        alpha = int(255 * min(1.0, max(0.2, time_left_ratio * 1.5))) # Fade out slowly
        self.image = self.original_image.copy()
        self.image.set_alpha(alpha)

        # Health-based color change (optional)
        health_ratio = self.health / self.max_health
        if health_ratio < 0.3:
            current_tint = RED
        elif health_ratio < 0.6:
            current_tint = YELLOW
        else:
            current_tint = GREEN # Healthy green
        
        # Apply tint as an overlay (simple blending)
        tint_surface = Surface(self.image.get_size(), SRCALPHA)
        tint_surface.fill((*current_tint[:3], 50)) # Semi-transparent tint
        self.image.blit(tint_surface, (0,0), special_flags=pygame.BLEND_RGBA_MULT)


    def draw(self, surface, camera=None):
        if not self.alive or not self.image or not self.rect:
            return
        
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
            # Ensure scaled image has positive dimensions
            if screen_rect.width > 0 and screen_rect.height > 0:
                scaled_image = pygame.transform.scale(self.image, screen_rect.size)
                surface.blit(scaled_image, screen_rect)
            # No need for fallback if dimensions are non-positive, just skip blit
        else:
            surface.blit(self.image, self.rect)
        
        # Optional: Draw a health bar above the barricade
        self._draw_health_bar(surface, camera)

    def _draw_health_bar(self, surface, camera=None):
        if not self.alive or not self.rect:
            return
            
        bar_w, bar_h = self.rect.width * 0.8, 4
        
        if camera:
            screen_rect = camera.apply_to_rect(self.rect)
        else:
            screen_rect = self.rect
            
        bar_x = screen_rect.centerx - bar_w / 2
        bar_y = screen_rect.top - bar_h - 2
        
        fill_w = bar_w * (self.health / self.max_health if self.max_health > 0 else 0)
        
        # Color based on health percentage
        if self.health / self.max_health > 0.6:
            fill_color = GREEN
        elif self.health / self.max_health > 0.3:
            fill_color = YELLOW
        else:
            fill_color = RED
            
        pygame.draw.rect(surface, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
        
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(fill_w), bar_h))
            
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)
