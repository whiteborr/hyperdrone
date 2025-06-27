# ui/ui_common.py
from pygame import Surface, SRCALPHA
from pygame.draw import line, rect
from pygame.font import Font
from pygame.time import get_ticks
from math import sin, cos
from os.path import join, dirname
from constants import GOLD, WHITE, CYAN

class UICommon:
    """Common UI utilities and drawing functions"""
    
    @staticmethod
    def load_fonts():
        """Load common fonts used across UI components"""
        font_path = join(dirname(dirname(__file__)), "assets", "fonts", "neuropol.otf")
        return {
            'title': Font(font_path, 40),
            'subtitle': Font(font_path, 28),
            'ui': Font(font_path, 24),
            'small': Font(font_path, 18)
        }
    
    @staticmethod
    def draw_text_with_shadow(screen, text, font_obj, color, pos, shadow_color=(0, 0, 0), offset=(2, 2)):
        """Draw text with a drop shadow"""
        text_surf = font_obj.render(text, True, shadow_color)
        screen.blit(text_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font_obj.render(text, True, color)
        screen.blit(text_surf, pos)
    
    @staticmethod
    def draw_background(screen):
        """Draw animated grid background"""
        width, height = screen.get_size()
        overlay = Surface((width, height), SRCALPHA)
        time_factor = get_ticks() * 0.001
        bg_alpha = int(200 + 30 * sin(time_factor))
        overlay.fill((5, 15, 35, bg_alpha))

        grid_offset = int(get_ticks() * 0.02) % 50
        for x in range(-grid_offset, width + 50, 50):
            a = int(60 + 40 * sin(time_factor + x * 0.01))
            line(overlay, (20, 60, 120, a), (x, 0), (x, height))
        for y in range(-grid_offset, height + 50, 50):
            a = int(60 + 40 * cos(time_factor + y * 0.01))
            line(overlay, (20, 60, 120, a), (0, y), (width, y))
        screen.blit(overlay, (0, 0))
    
    @staticmethod
    def draw_main_frame(screen, x, y, width, height):
        """Draw animated main frame with glow effects"""
        # Animated main background
        panel_surface = Surface((width, height), SRCALPHA)
        time_factor = get_ticks() * 0.002
        bg_alpha = int(220 + 20 * sin(time_factor))
        panel_surface.fill((20, 35, 60, bg_alpha))
        screen.blit(panel_surface, (x, y))
        
        # Animated border glow
        border_alpha = int(120 + 80 * sin(time_factor * 2))
        rect(screen, (0, 200, 255, border_alpha), (x-1, y-1, width+2, height+2), 3, border_radius=12)
        rect(screen, (0, 255, 255, 150), (x, y, width, height), 2, border_radius=10)
        
        # Enhanced corner details with glow
        corner_size = 40
        glow_alpha = int(150 + 100 * sin(time_factor * 3))
        
        # Top-left corner
        line(screen, (*GOLD, glow_alpha), (x-2, y + corner_size), (x-2, y-2), 5)
        line(screen, (*GOLD, glow_alpha), (x-2, y-2), (x + corner_size, y-2), 5)
        line(screen, GOLD, (x, y + corner_size), (x, y), 3)
        line(screen, GOLD, (x, y), (x + corner_size, y), 3)
        
        # Top-right corner
        line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y-2), (x + width+2, y-2), 5)
        line(screen, (*GOLD, glow_alpha), (x + width+2, y-2), (x + width+2, y + corner_size), 5)
        line(screen, GOLD, (x + width - corner_size, y), (x + width, y), 3)
        line(screen, GOLD, (x + width, y), (x + width, y + corner_size), 3)

        # Bottom-left corner
        line(screen, (*GOLD, glow_alpha), (x-2, y + height - corner_size), (x-2, y + height+2), 5)
        line(screen, (*GOLD, glow_alpha), (x-2, y + height+2), (x + corner_size, y + height+2), 5)
        line(screen, GOLD, (x, y + height - corner_size), (x, y + height), 3)
        line(screen, GOLD, (x, y + height), (x + corner_size, y + height), 3)
        
        # Bottom-right corner
        line(screen, (*GOLD, glow_alpha), (x + width - corner_size, y + height+2), (x + width+2, y + height+2), 5)
        line(screen, (*GOLD, glow_alpha), (x + width+2, y + height+2), (x + width+2, y + height - corner_size), 5)
        line(screen, GOLD, (x + width - corner_size, y + height), (x + width, y + height), 3)
        line(screen, GOLD, (x + width, y + height), (x + width, y + height - corner_size), 3)
    
    @staticmethod
    def draw_scanlines(screen):
        """Draw animated scanlines effect"""
        width, height = screen.get_size()
        scanline_surface = Surface((width, height), SRCALPHA)
        
        scanline_offset = (get_ticks() * 0.5) % 6
        time_factor = get_ticks() * 0.001
        
        for y in range(int(scanline_offset), height, 6):
            alpha = int(50 + 20 * sin(time_factor + y * 0.1))
            alpha = max(10, min(80, alpha))
            line(scanline_surface, (0, 20, 40, alpha), (0, y), (width, y), 1)
        
        bright_line_y = int((get_ticks() * 0.1) % height)
        line(scanline_surface, (0, 100, 200, 60), (0, bright_line_y), (width, bright_line_y), 2)
        
        screen.blit(scanline_surface, (0, 0))