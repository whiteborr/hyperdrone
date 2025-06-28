# ui/settings_ui.py
from pygame import Surface, SRCALPHA
from pygame.time import get_ticks
from math import sin
from settings_manager import get_setting
from constants import WHITE, GOLD, CYAN
from .ui_common import UICommon

class SettingsUI:
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self._cached_width = get_setting("display", "WIDTH", 1920)
        self._cached_height = get_setting("display", "HEIGHT", 1080)

        fonts = UICommon.load_fonts()
        self.font_title = fonts['title']
        self.font_setting = fonts['ui']
        self.font_small = fonts['small']

    def draw(self, screen, ui_flow_controller):
        width, height = screen.get_size()
        UICommon.draw_background(screen)

        board_width = 960
        board_height = 900
        board_x = (width - board_width) // 2
        board_y = (height - board_height) // 2

        UICommon.draw_main_frame(screen, board_x, board_y, board_width, board_height)
        self._draw_title(screen, "SETTINGS", board_x + board_width // 2 - 90, board_y + 30)
        self._draw_settings(screen, ui_flow_controller, board_x + 60, board_y + 120)
        self._draw_instructions(screen, board_x, board_y, board_width, board_height)
        UICommon.draw_scanlines(screen)

    def _draw_title(self, screen, text, x, y):
        UICommon.draw_text_with_shadow(screen, text, self.font_title, GOLD, (x, y))

    def _draw_settings(self, screen, ui_flow_controller, start_x, start_y):
        settings_items = ui_flow_controller.settings_items_data
        selected_index = ui_flow_controller.selected_setting_index

        row_height = 35
        row_width = 800
        label_col = 0
        value_col = 480

        for i_actual in range(len(settings_items)):
            item = settings_items[i_actual]
            y_pos = start_y + i_actual * row_height

            # Highlight for selected row
            if i_actual == selected_index:
                color = GOLD
                glow_alpha = int(80 + 40 * sin(get_ticks() * 0.005))
                glow_surf = Surface((row_width, 35), SRCALPHA)
                glow_surf.fill((*GOLD, glow_alpha))
                screen.blit(glow_surf, (start_x - 10, y_pos - 4))
            else:
                color = CYAN

            # Label
            UICommon.draw_text_with_shadow(screen, item['label'], self.font_setting, color, (start_x + label_col, y_pos))

            # Value
            val_text = self._get_setting_value_text(item)
            UICommon.draw_text_with_shadow(screen, val_text, self.font_setting, color, (start_x + value_col, y_pos))

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
            try:
                val_text = item['get_display'](current_val)
            except Exception:
                val_text = str(current_val)
        else:
            val_text = str(current_val) if current_val is not None else "N/A"

        if item['type'] in ["numeric", "choice"]:
            val_text = f"< {val_text} >"

        return val_text

    def _draw_instructions(self, screen, board_x, board_y, board_width, board_height):
        instructions = "Use [UP/DOWN] to navigate  •  [LEFT/RIGHT] to change  •  [ESC] to return"
        text_width, _ = self.font_small.size(instructions)
        x = board_x + (board_width - text_width) // 2
        y = board_y + board_height + 20 
        UICommon.draw_text_with_shadow(screen, instructions, self.font_small, WHITE, (x, y))
