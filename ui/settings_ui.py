# ui/settings_ui.py
import pygame
from pygame import Surface, draw, font
from pygame.time import get_ticks
from math import sin, cos
from os.path import join, dirname
from settings_manager import get_setting
from constants import WHITE, YELLOW, GOLD, CYAN, GREY

class SettingsUI:
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self._cached_width = get_setting("display", "WIDTH", 1920)
        self._cached_height = get_setting("display", "HEIGHT", 1080)
        
        # Initialize fonts with cyberpunk styling
        font_path = join(dirname(dirname(__file__)), "assets", "fonts", "neuropol.otf")
        self.font_title = font.Font(font_path, 40)
        self.font_setting = font.Font(font_path, 24)
        self.font_small = font.Font(font_path, 18)
        self.scanline_offset = 0

    def draw(self, screen, ui_flow_controller):
        width, height = screen.get_size()
        self._draw_background(screen)
        
        board_width = 1400
        board_height = 800
        board_x = (width - board_width) // 2
        board_y = (height - board_height) // 2
        
        self._draw_main_frame(screen, board_x, board_y, board_width, board_height)
        self._draw_title(screen, "SETTINGS", board_x + board_width // 2 - 80, board_y + 30)
        self._draw_settings(screen, ui_flow_controller, board_x + 80, board_y + 120)
        self._draw_instructions(screen, board_x, board_y, board_width, board_height)
        self._draw_scanlines(screen)

    def _draw_background(self, screen):
        width, height = screen.get_size()
        overlay = Surface((width, height), pygame.SRCALPHA)
        time_factor = get_ticks() * 0.001
        bg_alpha = int(200 + 30 * sin(time_factor))
        overlay.fill((5, 15, 35, bg_alpha))

        grid_offset = int(get_ticks() * 0.02) % 50
        for x in range(-grid_offset, width + 50, 50):
            a = int(60 + 40 * sin(time_factor + x * 0.01))
            draw.line(overlay, (20, 60, 120, a), (x, 0), (x, height))
        for y in range(-grid_offset, height + 50, 50):
            a = int(60 + 40 * cos(time_factor + y * 0.01))
            draw.line(overlay, (20, 60, 120, a), (0, y), (width, y))
        screen.blit(overlay, (0, 0))

    def _draw_main_frame(self, screen, x, y, width, height):
        panel_surface = Surface((width, height), pygame.SRCALPHA)
        time_factor = get_ticks() * 0.002
        bg_alpha = int(220 + 20 * sin(time_factor))
        panel_surface.fill((20, 35, 60, bg_alpha))
        screen.blit(panel_surface, (x, y))
        
        border_alpha = int(120 + 80 * sin(time_factor * 2))
        draw.rect(screen, (0, 200, 255, border_alpha), (x-1, y-1, width+2, height+2), 3, border_radius=12)
        draw.rect(screen, (0, 255, 255, 150), (x, y, width, height), 2, border_radius=10)
        
        corner_size = 40
        glow_alpha = int(150 + 100 * sin(time_factor * 3))
        
        # Corner decorations
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y + corner_size), (x-2, y-2), 5)
        draw.line(screen, (*GOLD, glow_alpha), (x-2, y-2), (x + corner_size, y-2), 5)
        draw.line(screen, GOLD, (x, y + corner_size), (x, y), 3)
        draw.line(screen, GOLD, (x, y), (x + corner_size, y), 3)

    def _draw_title(self, screen, text, x, y):
        self._draw_text_with_shadow(screen, text, self.font_title, GOLD, (x, y))

    def _draw_settings(self, screen, ui_flow_controller, start_x, start_y):
        settings_items = ui_flow_controller.settings_items_data
        selected_index = ui_flow_controller.selected_setting_index
        
        max_visible = 12
        start_idx = max(0, selected_index - max_visible // 2)
        start_idx = min(start_idx, max(0, len(settings_items) - max_visible))
        end_idx = min(len(settings_items), start_idx + max_visible)
        
        for i_display, i_actual in enumerate(range(start_idx, end_idx)):
            item = settings_items[i_actual]
            y_pos = start_y + i_display * 40
            
            # Highlight selected item
            if i_actual == selected_index:
                color = GOLD
                glow_alpha = int(80 + 40 * sin(get_ticks() * 0.005))
                glow_surf = Surface((1000, 35), pygame.SRCALPHA)
                glow_surf.fill((*GOLD, glow_alpha))
                screen.blit(glow_surf, (start_x - 20, y_pos - 5))
            else:
                color = CYAN
            
            # Setting label
            self._draw_text_with_shadow(screen, item['label'], self.font_setting, color, (start_x, y_pos))
            
            # Setting value
            val_text = self._get_setting_value_text(item)
            self._draw_text_with_shadow(screen, val_text, self.font_setting, color, (start_x + 600, y_pos))

    def _get_setting_value_text(self, item):
        if item['type'] == 'action':
            return "[PRESS ENTER]"
        
        category = item.get('category', 'gameplay')
        current_val = get_setting(category, item['key'], None)
        val_to_format = current_val
        
        if item.get("is_ms_to_sec") and val_to_format is not None:
            val_to_format /= 1000
        
        if 'display_format' in item and val_to_format is not None:
            val_text = item['display_format'].format(val_to_format)
        elif 'get_display' in item and current_val is not None:
            val_text = item['get_display'](current_val)
        else:
            val_text = str(current_val) if current_val is not None else "N/A"
        
        if item['type'] in ["numeric", "choice"]:
            val_text = f"< {val_text} >"
        
        return val_text

    def _draw_text_with_shadow(self, screen, text, font_obj, color, pos, shadow_color=(0, 0, 0), offset=(2, 2)):
        text_surf = font_obj.render(text, True, shadow_color)
        screen.blit(text_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font_obj.render(text, True, color)
        screen.blit(text_surf, pos)

    def _draw_scanlines(self, screen):
        width, height = screen.get_size()
        scanline_surface = Surface((width, height), pygame.SRCALPHA)
        
        self.scanline_offset = (self.scanline_offset + 0.5) % 6
        time_factor = get_ticks() * 0.001
        
        for y in range(int(self.scanline_offset), height, 6):
            alpha = int(50 + 20 * sin(time_factor + y * 0.1))
            alpha = max(10, min(80, alpha))
            draw.line(scanline_surface, (0, 20, 40, alpha), (0, y), (width, y), 1)
        
        bright_line_y = int((get_ticks() * 0.1) % height)
        draw.line(scanline_surface, (0, 100, 200, 60), (0, bright_line_y), (width, bright_line_y), 2)
        
        screen.blit(scanline_surface, (0, 0))

    def _draw_instructions(self, screen, board_x, board_y, board_width, board_height):
        instructions = "Use [↑↓] to navigate • [←→] to change values • [ESC] to return"
        self._draw_text_with_shadow(screen, instructions, self.font_small, WHITE,
                                    (board_x + board_width // 2 - 250, board_y + board_height - 50))