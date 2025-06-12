import pygame
import math # Added import math
from settings_manager import get_setting # New settings management system

class EscapeZone(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.size = int(get_setting("gameplay", "TILE_SIZE", 80) * 1.5) # Make it a bit larger than a tile
        self.image = pygame.Surface([self.size, self.size], pygame.SRCALPHA)
        # Use get_setting for safety, in case ESCAPE_ZONE_COLOR is modified by user or missing
        self.color = get_setting("gameplay", "ESCAPE_ZONE_COLOR", (0, 255, 128)) # Bright green, default opaque
        
        # Simple pulsing visual
        self.pulse_time = 0
        self.pulse_speed = 0.05 # Controls speed of pulsing
        self.min_alpha = 100
        self.max_alpha = 220
        
        self._draw_shape() # Initial draw

        self.rect = self.image.get_rect(center=(x, y))

    def _draw_shape(self, alpha_override=None):
        self.image.fill((0,0,0,0)) # Clear surface
        
        current_alpha = alpha_override
        if current_alpha is None:
            # Pulse alpha
            pulse_val = (math.sin(self.pulse_time) + 1) / 2 # 0 to 1
            current_alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * pulse_val
        
        # Ensure color has 3 components (RGB) before adding alpha
        base_color_rgb = self.color[:3] 
        color_with_alpha = (*base_color_rgb, int(current_alpha))

        num_rects = 4
        max_rect_size = self.size
        for i in range(num_rects):
            rect_size = max_rect_size * ((num_rects - i) / num_rects)
            # Ensure rect_size is at least 1 to avoid issues with drawing
            rect_size = max(1, rect_size) 
            
            rect_alpha_factor = ((num_rects - i * 0.5) / num_rects) * 0.7
            rect_alpha = int(current_alpha * rect_alpha_factor) 
            rect_alpha = max(0, min(255, rect_alpha))
            
            temp_color = (*base_color_rgb, rect_alpha)
            
            offset = (self.size - rect_size) / 2
            # Ensure border_radius is not larger than half of the smallest dimension of the rect
            radius = int(rect_size * 0.2)
            if rect_size > 0: # Only draw if size is positive
                 # Ensure radius is valid for pygame.draw.rect
                radius = min(radius, int(rect_size / 2))
                pygame.draw.rect(self.image, temp_color, (offset, offset, rect_size, rect_size), border_radius=radius)
                if i == 0: # Innermost rect a bit brighter and outlined
                    inner_color = (*base_color_rgb, min(255, rect_alpha + 50))
                    pygame.draw.rect(self.image, inner_color, (offset, offset, rect_size, rect_size), border_radius=radius, width=2)


    def update(self):
        self.pulse_time += self.pulse_speed
        self._draw_shape()

    def draw(self, surface): 
        surface.blit(self.image, self.rect)

