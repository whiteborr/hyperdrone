# entities/glitching_wall.py
import pygame.sprite
import pygame.draw
import pygame.time
from pygame import Surface, SRCALPHA
from random import randint, choice
from math import sin
from settings_manager import get_setting
from constants import DARK_PURPLE, MAGENTA, WHITE

class GlitchingWall(pygame.sprite.Sprite):
    """
    A wall that flickers in and out of existence, damaging the player on contact when solid.
    """
    def __init__(self, x, y):
        super().__init__()

        # Get settings for easy configuration
        self.tile_size = get_setting("gameplay", "TILE_SIZE", 80)
        self.on_duration = get_setting("hazards", "GLITCH_WALL_ON_DURATION_MS", 2000)
        self.off_duration = get_setting("hazards", "GLITCH_WALL_OFF_DURATION_MS", 1500)
        self.damage = get_setting("hazards", "GLITCH_WALL_DAMAGE", 15)

        # State and timer
        self.is_solid = True
        self.last_toggle_time = pygame.time.get_ticks() + randint(0, self.on_duration)
        self.pulse_timer = 0

        # Create the visual surface
        self.image = Surface((self.tile_size, self.tile_size), SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collision_rect = self.rect.copy() # Collision rect matches visual rect

        self._update_visuals()

    def _update_visuals(self):
        """Redraws the wall based on its current state (solid or off)."""
        self.image.fill((0, 0, 0, 0)) # Clear the surface

        if self.is_solid:
            # Create a pulsing, glitchy effect when the wall is solid
            self.pulse_timer += 0.1
            base_alpha = 150
            pulse_alpha = base_alpha + (sin(self.pulse_timer) + 1) * 50 # Oscillates between 150-250
            
            # Draw several overlapping rectangles for a distorted look
            for i in range(4):
                color = (*choice([DARK_PURPLE, MAGENTA]), int(pulse_alpha / (i + 1)))
                offset_x = randint(-4, 4)
                offset_y = randint(-4, 4)
                inner_rect = self.image.get_rect().inflate(-i * 6 + offset_x, -i * 6 + offset_y)
                pygame.draw.rect(self.image, color, inner_rect, border_radius=3)
            
            # White border to define the shape clearly
            pygame.draw.rect(self.image, WHITE, self.image.get_rect(), 2, border_radius=3)
        else:
            # Draw a faint, barely visible outline when the wall is off
            pygame.draw.rect(self.image, (*DARK_PURPLE, 30), self.image.get_rect(), 2, border_radius=3)

    def update(self):
        """Updates the wall's state based on its on/off timer."""
        current_time = pygame.time.get_ticks()
        
        # Determine the duration for the current state
        duration = self.on_duration if self.is_solid else self.off_duration

        # Check if it's time to toggle the state
        if current_time - self.last_toggle_time > duration:
            self.is_solid = not self.is_solid
            self.last_toggle_time = current_time

        # Update the visual representation
        self._update_visuals()

    def draw(self, surface, camera=None):
        """Draws the glitching wall."""
        if camera:
            surface.blit(self.image, camera.apply_to_rect(self.rect))
        else:
            surface.blit(self.image, self.rect)